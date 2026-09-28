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
from plaky115.http import ApiResponse, RequestOptions, RequestSpec, resolve_headers
from plaky115.resources._common import RequestOverrides, apply_overrides, combine_headers
from plaky115.resources.boards import BoardsResource
from plaky115.resources.comments import ItemCommentsResource
from plaky115.resources.item_files import ItemFilesResource
from plaky115.resources.item_groups import ItemGroupsResource
from plaky115.resources.items import ItemsResource
from plaky115.resources.reactions import ReactionsResource
from plaky115.resources.spaces import SpacesResource
from plaky115.resources.subscriptions import SubscriptionsResource
from plaky115.resources.teams import TeamsResource
from plaky115.resources.users import UsersResource
from plaky115.runtime.rate_limit import RateLimitTracker, RequestPacer
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
        pacer: RequestPacer | None = None,
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
        self._pacer = pacer

        self.spaces = SpacesResource(self)
        self.boards = BoardsResource(self)
        self.items = ItemsResource(self)
        self.comments = ItemCommentsResource(self)
        self.reactions = ReactionsResource(self)
        self.subscriptions = SubscriptionsResource(self)
        self.users = UsersResource(self)
        self.teams = TeamsResource(self)
        self.item_groups = ItemGroupsResource(self)
        self.item_files = ItemFilesResource(self)

    @property
    def server_url(self) -> str:
        return self._server_url

    def _options(self, overrides: RequestOverrides | None) -> RequestOptions:
        base = self._headers
        extra = overrides.headers if overrides is not None else None
        if extra is None:
            headers = base
        elif callable(base):

            def merged() -> Mapping[str, str]:
                return combine_headers(resolve_headers(base), extra)

            headers = merged
        else:
            headers = combine_headers(base, extra)
        defaults = RequestOptions(
            api_key=self._api_key,
            server_url=self._server_url,
            timeout=self._timeout,
            max_retries=self._max_retries,
            max_response_bytes=self._max_response_bytes,
            user_agent=self._user_agent,
            request_hook=self._request_hook,
            response_hook=self._response_hook,
            rate_limit_tracker=self.rate_limit,
            pacer=self._pacer,
        )
        return apply_overrides(defaults, overrides, headers)

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
            pacer=self._pacer,
        )

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
