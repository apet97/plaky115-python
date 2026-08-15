"""Public low-level HTTP seam.

Exposes the request/response primitives over an injected httpx2 client:
`async_request` / `async_request_with_response` for the async stack and
`request` / `request_with_response` for the sync stack, plus the shared
header helpers. Resource methods and clients build on these.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, cast

import httpx2

from plaky115.config import (
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
)
from plaky115.errors import PlakyTimeoutError
from plaky115.runtime.rate_limit import RateLimitTracker
from plaky115.runtime.request_builders import merge_headers_into
from plaky115.user_agent import build_user_agent

__all__ = [
    "ApiResponse",
    "AsyncByteStream",
    "AsyncHeadersProvider",
    "AsyncRequestHook",
    "AsyncResponseHook",
    "HeadersProvider",
    "RequestHook",
    "RequestOptions",
    "RequestSpec",
    "ResponseHook",
    "SyncByteStream",
    "async_request",
    "async_request_with_response",
    "async_resolve_headers",
    "merge_headers_into",
    "request",
    "request_with_response",
    "resolve_headers",
]

ResponseType = Literal["json", "text", "bytes", "stream", "void"]

HeadersProvider = Callable[[], Mapping[str, str]]
AsyncHeadersProvider = Callable[[], Awaitable[Mapping[str, str]]]

RequestHookContext = dict[str, Any]
RequestHook = Callable[[RequestHookContext], RequestHookContext]
AsyncRequestHook = Callable[[RequestHookContext], Awaitable[RequestHookContext]]
ResponseHookContext = dict[str, Any]
ResponseHook = Callable[[ResponseHookContext], None]
AsyncResponseHook = Callable[[ResponseHookContext], Awaitable[None]]


@dataclass(frozen=True)
class RequestSpec:
    """One HTTP operation: method, path, and encodings."""

    method: str
    path: str
    query: Mapping[str, Any] | None = None
    body: Any = None
    files: Mapping[str, tuple[str | None, bytes, str]] | None = None
    response_type: ResponseType = "json"
    operation_id: str | None = None


@dataclass(frozen=True)
class RequestOptions:
    """Per-request options resolved by the client."""

    api_key: str | Callable[[], Any]
    server_url: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = 0
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    headers: Mapping[str, str] | Callable[[], Any] | None = None
    user_agent: str | None = None
    idempotency_key: str | None = None
    request_hook: Callable[..., Any] | None = None
    response_hook: Callable[..., Any] | None = None
    on_dispatch: Callable[[], None] | None = field(default=None, compare=False)
    rate_limit_tracker: RateLimitTracker | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ApiResponse:
    """Response envelope: parsed data plus transport metadata."""

    data: Any
    status: int
    headers: Mapping[str, str]
    url: str
    request_id: str | None = None


class SyncByteStream(Iterator[bytes]):
    """A response-owned synchronous byte stream with deterministic cleanup."""

    def __init__(self, response: Any) -> None:
        self._response = response
        self._iterator = iter(cast("Iterator[bytes]", response.iter_bytes()))
        self._closed = False

    def __next__(self) -> bytes:
        try:
            return next(self._iterator)
        except StopIteration:
            self.close()
            raise
        except httpx2.TimeoutException as exc:
            self.close()
            raise PlakyTimeoutError() from exc
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._response.close()

    def __enter__(self) -> SyncByteStream:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncByteStream(AsyncIterator[bytes]):
    """A response-owned asynchronous byte stream with deterministic cleanup."""

    def __init__(self, response: Any, *, timeout: float | None = None) -> None:
        self._response = response
        self._iterator = response.aiter_bytes()
        self._closed = False
        self._timeout = timeout

    async def __anext__(self) -> bytes:
        try:
            async with asyncio.timeout(self._timeout):
                return await self._iterator.__anext__()
        except StopAsyncIteration:
            await self.aclose()
            raise
        except (TimeoutError, httpx2.TimeoutException) as exc:
            await self.aclose()
            raise PlakyTimeoutError() from exc
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._response.aclose()

    async def __aenter__(self) -> AsyncByteStream:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


def resolve_headers(
    headers: Mapping[str, str] | HeadersProvider | None,
) -> Mapping[str, str] | None:
    """Resolve a synchronous headers value or provider."""
    if not headers:
        return None
    if callable(headers):
        resolved: Any = headers()
        if not isinstance(resolved, Mapping):
            raise TypeError("PlakyClient: headers provider returned an invalid value")
        return cast(Mapping[str, str], resolved)
    return headers


async def async_resolve_headers(
    headers: Mapping[str, str] | AsyncHeadersProvider | HeadersProvider | None,
) -> Mapping[str, str] | None:
    """Resolve an async (or literal) headers value or provider."""
    if not headers:
        return None
    if callable(headers):
        resolved: Any = headers()
        if inspect.isawaitable(resolved):
            resolved = await resolved
        if not isinstance(resolved, Mapping):
            raise TypeError("PlakyClient: headers provider returned an invalid value")
        return cast(Mapping[str, str], resolved)
    return headers


def resolve_api_key(api_key: str | Callable[[], Any]) -> str:
    resolved: Any = api_key() if callable(api_key) else api_key
    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("PlakyClient: api key provider returned an invalid value")
    return resolved


async def async_resolve_api_key(api_key: str | Callable[[], Any]) -> str:
    resolved: Any = api_key() if callable(api_key) else api_key
    if inspect.isawaitable(resolved):
        resolved = await resolved
    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("PlakyClient: api key provider returned an invalid value")
    return resolved


def build_base_headers(
    spec: RequestSpec,
    options: RequestOptions,
    api_key: str,
    user_headers: Mapping[str, str] | None,
) -> dict[str, str]:
    """Assemble headers in the pinned order; user headers may override."""
    headers: dict[str, str] = {
        "accept": "application/json",
        "user-agent": options.user_agent or build_user_agent(),
        "x-api-key": api_key,
    }
    merge_headers_into(headers, user_headers)
    if spec.body is not None and "content-type" not in headers:
        headers["content-type"] = "application/json"
    if options.idempotency_key and "idempotency-key" not in headers:
        headers["idempotency-key"] = options.idempotency_key
    return headers


# The transport implementations live in plaky115.runtime; re-exported here
# as the stable public seam.
def request(client: Any, spec: RequestSpec, options: RequestOptions) -> Any:
    from plaky115.runtime.transport import sync_request

    return sync_request(client, spec, options)


def request_with_response(client: Any, spec: RequestSpec, options: RequestOptions) -> ApiResponse:
    from plaky115.runtime.transport import sync_request_with_response

    return sync_request_with_response(client, spec, options)


async def async_request(client: Any, spec: RequestSpec, options: RequestOptions) -> Any:
    from plaky115.runtime.async_transport import async_request as _impl

    return await _impl(client, spec, options)


async def async_request_with_response(
    client: Any, spec: RequestSpec, options: RequestOptions
) -> ApiResponse:
    from plaky115.runtime.async_transport import async_request_with_response as _impl

    return await _impl(client, spec, options)
