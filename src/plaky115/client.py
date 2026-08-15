"""PlakyClient: the real synchronous client over httpx2.Client.

No event-loop bridging: this client never calls asyncio and accepts only
synchronous providers and hooks.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Self

import httpx2

from plaky115.config import (
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_SERVER_URL,
    DEFAULT_TIMEOUT_SECONDS,
    normalize_server_url,
    validate_max_retries,
    validate_response_limit,
    validate_timeout,
)
from plaky115.http import ApiResponse, RequestOptions, RequestSpec
from plaky115.resources._common import RequestOverrides
from plaky115.resources.boards import BoardsResource
from plaky115.resources.comments import ItemCommentsResource
from plaky115.resources.item_files import ItemFilesResource
from plaky115.resources.item_groups import ItemGroupsResource
from plaky115.resources.items import ItemsResource
from plaky115.resources.reactions import ReactionsResource
from plaky115.resources.spaces import SpacesResource
from plaky115.resources.teams import TeamsResource
from plaky115.resources.users import UsersResource
from plaky115.runtime.rate_limit import RateLimitTracker
from plaky115.runtime.transport import sync_request_with_response
from plaky115.user_agent import build_user_agent


class PlakyClient:
    """Synchronous Plaky API client for ordinary scripts and applications."""

    def __init__(
        self,
        *,
        api_key: str | Callable[[], str],
        server_url: str = DEFAULT_SERVER_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        headers: Mapping[str, str] | Callable[[], Mapping[str, str]] | None = None,
        user_agent: str | None = None,
        user_agent_suffix: str | None = None,
        request_hook: Callable[..., Any] | None = None,
        response_hook: Callable[..., Any] | None = None,
        http_client: httpx2.Client | None = None,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        if isinstance(api_key, str) and not api_key.strip():
            raise ValueError("PlakyClient: apiKey is required")
        if http_client is not None and transport is not None:
            raise ValueError("PlakyClient: http_client and transport cannot be used together")
        self._api_key = api_key
        self._server_url = normalize_server_url(server_url)
        self._timeout = validate_timeout(timeout)
        self._max_retries = validate_max_retries(max_retries)
        self._max_response_bytes = validate_response_limit(max_response_bytes)
        self._headers = headers
        if user_agent is not None:
            self._user_agent = user_agent
        elif user_agent_suffix:
            self._user_agent = build_user_agent(user_agent_suffix)
        else:
            self._user_agent = None
        self._request_hook = request_hook
        self._response_hook = response_hook
        self._owns_http = http_client is None
        self._http = http_client or httpx2.Client(transport=transport)
        self.rate_limit = RateLimitTracker()

        self.spaces = SpacesResource(self)
        self.boards = BoardsResource(self)
        self.items = ItemsResource(self)
        self.comments = ItemCommentsResource(self)
        self.reactions = ReactionsResource(self)
        self.users = UsersResource(self)
        self.teams = TeamsResource(self)
        self.item_groups = ItemGroupsResource(self)
        self.item_files = ItemFilesResource(self)

    @property
    def server_url(self) -> str:
        return self._server_url

    def _options(self, overrides: RequestOverrides | None) -> RequestOptions:
        headers = self._headers
        if overrides is not None and overrides.headers is not None:
            base = self._headers
            if callable(base):

                def merged() -> Mapping[str, str]:
                    from plaky115.http import resolve_headers
                    from plaky115.runtime.request_builders import merge_headers_into

                    resolved = resolve_headers(base) or {}
                    assert overrides is not None and overrides.headers is not None
                    combined: dict[str, str] = {k.lower(): v for k, v in resolved.items()}
                    merge_headers_into(combined, overrides.headers)
                    return combined

                headers = merged
            elif base:
                from plaky115.runtime.request_builders import merge_headers_into

                combined = {k.lower(): v for k, v in base.items()}
                merge_headers_into(combined, overrides.headers)
                headers = combined
            else:
                headers = overrides.headers
        return RequestOptions(
            api_key=self._api_key,
            server_url=self._server_url,
            timeout=(
                overrides.timeout
                if overrides is not None and overrides.timeout is not None
                else self._timeout
            ),
            max_retries=(
                overrides.max_retries
                if overrides is not None and overrides.max_retries is not None
                else self._max_retries
            ),
            max_response_bytes=(
                overrides.max_response_bytes
                if overrides is not None and overrides.max_response_bytes is not None
                else self._max_response_bytes
            ),
            headers=headers,
            user_agent=self._user_agent,
            idempotency_key=overrides.idempotency_key if overrides is not None else None,
            request_hook=self._request_hook,
            response_hook=self._response_hook,
            on_dispatch=overrides.on_dispatch if overrides is not None else None,
            rate_limit_tracker=self.rate_limit,
        )

    def execute(self, spec: RequestSpec, options: RequestOverrides | None) -> Any:
        envelope = sync_request_with_response(self._http, spec, self._options(options))
        return envelope.data

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        response_type: str = "json",
        options: RequestOverrides | None = None,
    ) -> Any:
        """Low-level escape hatch returning the parsed body."""
        return self.request_with_response(
            method, path, query=query, body=body, response_type=response_type, options=options
        ).data

    def request_with_response(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        response_type: str = "json",
        options: RequestOverrides | None = None,
    ) -> ApiResponse:
        """Low-level escape hatch returning the full response envelope."""
        spec = RequestSpec(
            method=method,
            path=path,
            query=query,
            body=body,
            response_type=response_type,  # type: ignore[arg-type]
        )
        return sync_request_with_response(self._http, spec, self._options(options))

    def with_options(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        headers: Mapping[str, str] | Callable[[], Mapping[str, str]] | None = None,
        user_agent: str | None = None,
    ) -> PlakyClient:
        """Return a new client sharing the HTTP connection pool."""
        return PlakyClient(
            api_key=self._api_key,
            server_url=self._server_url,
            timeout=self._timeout if timeout is None else timeout,
            max_retries=self._max_retries if max_retries is None else max_retries,
            max_response_bytes=(
                self._max_response_bytes if max_response_bytes is None else max_response_bytes
            ),
            headers=self._headers if headers is None else headers,
            user_agent=self._user_agent if user_agent is None else user_agent,
            request_hook=self._request_hook,
            response_hook=self._response_hook,
            http_client=self._http,
        )

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
