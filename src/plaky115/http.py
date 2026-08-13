"""Public low-level HTTP seam.

Exposes the request/response primitives over an injected httpx2 client:
`async_request` / `async_request_with_response` for the async stack and
`request` / `request_with_response` for the sync stack, plus the shared
header helpers. Resource methods and clients build on these.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from plaky115.config import (
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
)
from plaky115.runtime.rate_limit import RateLimitTracker
from plaky115.runtime.request_builders import merge_headers_into
from plaky115.user_agent import build_user_agent

__all__ = [
    "ApiResponse",
    "AsyncHeadersProvider",
    "AsyncRequestHook",
    "AsyncResponseHook",
    "HeadersProvider",
    "RequestHook",
    "RequestOptions",
    "RequestSpec",
    "ResponseHook",
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
    rate_limit_tracker: RateLimitTracker | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ApiResponse:
    """Response envelope: parsed data plus transport metadata."""

    data: Any
    status: int
    headers: Mapping[str, str]
    url: str
    request_id: str | None = None


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


def iter_response_stream(stream: Iterator[bytes]) -> Iterator[bytes]:  # pragma: no cover
    return stream


def aiter_response_stream(
    stream: AsyncIterator[bytes],
) -> AsyncIterator[bytes]:  # pragma: no cover
    return stream
