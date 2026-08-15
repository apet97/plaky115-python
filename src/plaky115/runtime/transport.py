"""Synchronous transport core.

Mirrors runtime/async_transport.py over a real httpx2.Client. Timeouts use
the HTTP client's native support (per-attempt network budget); there is no
fake cancellation API. Pure logic (headers, URLs, retry policy, parsing,
classification) is shared with the async transport.
"""

from __future__ import annotations

import time
from typing import Any, cast

import httpx2

from plaky115.errors import (
    PlakyConnectionError,
    PlakyTimeoutError,
    classify,
)
from plaky115.http import (
    ApiResponse,
    RequestOptions,
    RequestSpec,
    SyncByteStream,
    build_base_headers,
    resolve_api_key,
    resolve_headers,
)
from plaky115.runtime.async_transport import (
    encode_json_body,
    parse_body,
    parse_error_body,
)
from plaky115.runtime.request_builders import assert_trusted_request_url, build_url
from plaky115.runtime.responses import get_request_id
from plaky115.runtime.retry_policy import (
    can_retry,
    can_retry_error,
    parse_retry_after,
    retry_delay_ms,
    should_retry_response,
)


def _read_bounded_sync(response: httpx2.Response, limit: int) -> bytes:
    from plaky115.errors import PlakyResponseTooLargeError

    content_length = response.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > limit:
        raise PlakyResponseTooLargeError(limit)
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > limit:
            raise PlakyResponseTooLargeError(limit)
        chunks.append(chunk)
    return b"".join(chunks)


class _RetrySignal(Exception):
    pass


def sync_request_with_response(
    client: httpx2.Client,
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
        phase = "preflight"
        response: httpx2.Response | None = None
        response_transferred = False
        try:
            api_key = resolve_api_key(options.api_key)
            user_headers = resolve_headers(options.headers)
            headers = build_base_headers(spec, options, api_key, user_headers)
            url = build_url(options.server_url, spec.path, spec.query)

            if options.request_hook is not None:
                context = {"url": url, "headers": headers, "operation_id": operation_id}
                rewritten = options.request_hook(context)
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
                timeout=timeout,
            )
            # Honor user deletions of SDK-managed headers: the HTTP client
            # adds its own defaults, which would resurrect them.
            for managed in ("accept", "user-agent"):
                if managed not in headers and managed in request.headers:
                    del request.headers[managed]
            phase = "request"
            if options.on_dispatch is not None:
                options.on_dispatch()
            response = client.send(request, stream=True, follow_redirects=False)
            phase = "response"
            if options.rate_limit_tracker is not None:
                options.rate_limit_tracker.observe(dict(response.headers))

            status = response.status_code
            request_id = get_request_id(dict(response.headers))

            if not (200 <= status <= 299):
                if should_retry_response(method, status, attempt, max_retries):
                    retry_after_header = response.headers.get("retry-after")
                    raise _RetrySignal()
                raw = _read_bounded_sync(response, options.max_response_bytes)
                error_body = parse_error_body(raw)
                if options.response_hook is not None:
                    options.response_hook(
                        {
                            "url": url,
                            "status": status,
                            "headers": dict(response.headers),
                            "body": error_body,
                            "operation_id": operation_id,
                        }
                    )
                raise classify(
                    status=status,
                    method=method,
                    url=url,
                    headers=dict(response.headers),
                    body=error_body,
                    request_id=request_id,
                    retry_after_ms=parse_retry_after(response.headers.get("retry-after")),
                )

            if spec.response_type == "stream":
                response_transferred = True
                return ApiResponse(
                    data=SyncByteStream(response),
                    status=status,
                    headers=dict(response.headers),
                    url=url,
                    request_id=request_id,
                )
            raw = _read_bounded_sync(response, options.max_response_bytes)
            data = parse_body(raw, spec.response_type, status, request_id)
            if options.response_hook is not None:
                options.response_hook(
                    {
                        "url": url,
                        "status": status,
                        "headers": dict(response.headers),
                        "body": data,
                        "operation_id": operation_id,
                    }
                )
            return ApiResponse(
                data=data,
                status=status,
                headers=dict(response.headers),
                url=url,
                request_id=request_id,
            )
        except _RetrySignal:
            pass
        except httpx2.TimeoutException as exc:
            if phase != "request" or not can_retry_error(method, attempt, max_retries):
                raise PlakyTimeoutError() from exc
        except (httpx2.HTTPError, OSError) as exc:
            if phase != "request" or not can_retry_error(method, attempt, max_retries):
                raise PlakyConnectionError() from exc
        finally:
            if response is not None and not response_transferred:
                response.close()

        time.sleep(retry_delay_ms(retry_after_header, attempt) / 1000)
        attempt += 1


def sync_request(client: httpx2.Client, spec: RequestSpec, options: RequestOptions) -> Any:
    return sync_request_with_response(client, spec, options).data
