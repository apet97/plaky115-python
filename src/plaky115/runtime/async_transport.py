"""Async transport core: attempt loop, retries, timeouts, bounded reads.

Ported from sdk/src/runtime/http.ts + internal/fetcher.ts at the pinned
source (docs/port/spec-transport.md).

Guarantees:
- Only GET requests retry (429/5xx/timeout/connection); writes make exactly
  one network attempt even with an idempotency key.
- The timeout budget is per attempt and covers providers, hooks, network
  I/O, body reads, and parsing; backoff sleeps sit outside it.
- Task cancellation propagates; it is never wrapped as a connection error.
- Non-streaming bodies are bounded; oversized bodies fail without
  materializing the rest.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, cast

import httpx2

from plaky115.errors import (
    PlakyConnectionError,
    PlakyDecodeError,
    PlakyResponseTooLargeError,
    PlakyTimeoutError,
    classify,
)
from plaky115.http import (
    ApiResponse,
    RequestOptions,
    RequestSpec,
    async_resolve_api_key,
    async_resolve_headers,
    build_base_headers,
)
from plaky115.runtime.request_builders import assert_trusted_request_url, build_url
from plaky115.runtime.responses import get_request_id, parse_json_preserving_int64
from plaky115.runtime.retry_policy import (
    can_retry,
    can_retry_error,
    parse_retry_after,
    retry_delay_ms,
    should_retry_response,
)


def encode_json_body(body: Any) -> bytes:
    from pydantic import BaseModel

    if isinstance(body, BaseModel):
        return body.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


async def read_bounded(response: httpx2.Response, limit: int) -> bytes:
    """Read a streamed body, stopping before the limit is exceeded."""
    content_length = response.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > limit:
        await response.aclose()
        raise PlakyResponseTooLargeError(limit)
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > limit:
            await response.aclose()
            raise PlakyResponseTooLargeError(limit)
        chunks.append(chunk)
    return b"".join(chunks)


def parse_body(
    raw: bytes,
    response_type: str,
    status: int,
    request_id: str | None,
) -> Any:
    if response_type == "void" or status in (204, 205):
        return None
    if response_type == "bytes":
        return raw
    text = raw.decode("utf-8", errors="replace").removeprefix("﻿")
    if response_type == "text":
        return text
    if not text:
        return None
    try:
        return parse_json_preserving_int64(text)
    except ValueError as exc:
        raise PlakyDecodeError(
            "Failed to parse the Plaky API response body.",
            status=status,
            request_id=request_id,
        ) from exc


def parse_error_body(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace").removeprefix("﻿")
    if not text:
        return None
    try:
        return parse_json_preserving_int64(text)
    except ValueError:
        return text


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def async_request_with_response(
    client: httpx2.AsyncClient,
    spec: RequestSpec,
    options: RequestOptions,
) -> ApiResponse:
    method = spec.method.upper()
    operation_id = spec.operation_id or f"{method} {spec.path}"
    max_retries = options.max_retries if can_retry(method) else 0
    timeout = options.timeout if options.timeout and options.timeout > 0 else None

    attempt = 0
    while True:
        retry_after_header: str | None = None
        try:
            async with asyncio.timeout(timeout):
                api_key = await async_resolve_api_key(options.api_key)
                user_headers = await async_resolve_headers(options.headers)
                headers = build_base_headers(spec, options, api_key, user_headers)
                url = build_url(options.server_url, spec.path, spec.query)

                if options.request_hook is not None:
                    context = {"url": url, "headers": headers, "operation_id": operation_id}
                    rewritten = await _maybe_await(options.request_hook(context))
                    if (
                        not isinstance(rewritten, dict)
                        or "url" not in rewritten
                        or "headers" not in rewritten
                    ):
                        raise ValueError("PlakyClient: request hook returned an invalid URL")
                    rewritten_typed = cast(dict[str, Any], rewritten)
                    url = str(rewritten_typed["url"])
                    headers = cast(dict[str, str], rewritten_typed["headers"])
                    assert_trusted_request_url(url, options.server_url)

                content: bytes | None = None
                files = None
                if spec.files is not None:
                    files = {
                        name: (file_name, data, content_type)
                        for name, (file_name, data, content_type) in spec.files.items()
                    }
                    headers.pop("content-type", None)
                elif spec.body is not None:
                    content = encode_json_body(spec.body)

                request = client.build_request(
                    method,
                    url,
                    content=content,
                    files=files,
                    headers=headers,
                )
                # Honor user deletions of SDK-managed headers: the HTTP
                # client adds its own defaults, which would resurrect them.
                for managed in ("accept", "user-agent"):
                    if managed not in headers and managed in request.headers:
                        del request.headers[managed]
                try:
                    response = await client.send(request, stream=True, follow_redirects=False)
                except httpx2.TimeoutException as exc:
                    raise PlakyTimeoutError() from exc
                except (httpx2.HTTPError, OSError) as exc:
                    raise PlakyConnectionError() from exc

                try:
                    if options.rate_limit_tracker is not None:
                        options.rate_limit_tracker.observe(dict(response.headers))

                    status = response.status_code
                    request_id = get_request_id(dict(response.headers))

                    if not (200 <= status <= 299):
                        if should_retry_response(method, status, attempt, max_retries):
                            retry_after_header = response.headers.get("retry-after")
                            await response.aclose()
                            raise _RetrySignal()
                        raw = await read_bounded(response, options.max_response_bytes)
                        error_body = parse_error_body(raw)
                        if options.response_hook is not None:
                            await _maybe_await(
                                options.response_hook(
                                    {
                                        "url": url,
                                        "status": status,
                                        "headers": dict(response.headers),
                                        "body": error_body,
                                        "operation_id": operation_id,
                                    }
                                )
                            )
                        retry_after = response.headers.get("retry-after")
                        raise classify(
                            status=status,
                            method=method,
                            url=url,
                            headers=dict(response.headers),
                            body=error_body,
                            request_id=request_id,
                            retry_after_ms=parse_retry_after(retry_after),
                        )

                    if spec.response_type == "stream":
                        return ApiResponse(
                            data=response.aiter_bytes(),
                            status=status,
                            headers=dict(response.headers),
                            url=url,
                            request_id=request_id,
                        )
                    raw = await read_bounded(response, options.max_response_bytes)
                    data = parse_body(raw, spec.response_type, status, request_id)
                    if options.response_hook is not None:
                        await _maybe_await(
                            options.response_hook(
                                {
                                    "url": url,
                                    "status": status,
                                    "headers": dict(response.headers),
                                    "body": data,
                                    "operation_id": operation_id,
                                }
                            )
                        )
                    return ApiResponse(
                        data=data,
                        status=status,
                        headers=dict(response.headers),
                        url=url,
                        request_id=request_id,
                    )
                finally:
                    if spec.response_type != "stream":
                        await response.aclose()
        except _RetrySignal:
            pass  # retryable status; fall through to backoff
        except (TimeoutError, PlakyTimeoutError) as exc:
            if not can_retry_error(method, attempt, max_retries):
                if isinstance(exc, PlakyTimeoutError):
                    raise
                raise PlakyTimeoutError() from exc
        except PlakyConnectionError:
            if not can_retry_error(method, attempt, max_retries):
                raise

        await asyncio.sleep(retry_delay_ms(retry_after_header, attempt) / 1000)
        attempt += 1


class _RetrySignal(Exception):
    pass


async def async_request(
    client: httpx2.AsyncClient,
    spec: RequestSpec,
    options: RequestOptions,
) -> Any:
    envelope = await async_request_with_response(client, spec, options)
    return envelope.data
