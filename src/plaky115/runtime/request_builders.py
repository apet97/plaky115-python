"""URL, query, and header construction shared by both transports.

Ported from sdk/src/runtime/internal/request-builders.ts at the pinned
source (docs/port/spec-transport.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, cast
from urllib.parse import quote_plus, urlsplit

# Query parameters serialized comma-joined (OpenAPI explode: false).
EXPLODE_FALSE_PARAMS = frozenset({"expand"})

QueryValue = Any


def _format_query_value(value: QueryValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def build_query(query: Mapping[str, QueryValue] | None) -> str:
    """Serialize query parameters; None and empty arrays are omitted."""
    if not query:
        return ""
    pairs: list[tuple[str, str]] = []
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, list | tuple):
            entries: list[Any] = [*cast("list[Any] | tuple[Any, ...]", value)]
            if not entries:
                continue
            formatted = [_format_query_value(v) for v in entries]
            if key in EXPLODE_FALSE_PARAMS:
                pairs.append((key, ",".join(formatted)))
            else:
                pairs.extend((key, v) for v in formatted)
        else:
            pairs.append((key, _format_query_value(value)))
    return "&".join(f"{quote_plus(k)}={quote_plus(v)}" for k, v in pairs)


def build_url(server_url: str, path: str, query: Mapping[str, QueryValue] | None = None) -> str:
    base = server_url if server_url.endswith("/") else server_url + "/"
    url = base + path.lstrip("/")
    encoded = build_query(query)
    if encoded:
        url = f"{url}?{encoded}"
    return url


def merge_headers_into(target: dict[str, str], source: Mapping[str, str] | None) -> None:
    """Case-insensitive deterministic merge; empty string deletes a header.

    The target dict is keyed by lowercase header names. Source pairs are
    applied in lowercase-sorted order; set semantics, never append.
    """
    if not source:
        return
    normalized = sorted((k.lower(), v) for k, v in source.items())
    for key, value in normalized:
        if value == "":
            target.pop(key, None)
        else:
            target[key] = value


def assert_trusted_request_url(request_url: str, server_url: str) -> None:
    """A request hook may rewrite path/query but never the trusted origin."""
    try:
        rewritten = _normalized_origin(request_url)
        trusted = _normalized_origin(server_url)
    except ValueError:
        raise ValueError("PlakyClient: request hook returned an invalid URL") from None
    if rewritten != trusted:
        raise ValueError("PlakyClient: request hook must not change the trusted server origin")


def _normalized_origin(url: str) -> tuple[str, str, int]:
    """Return a canonical scheme, IDNA hostname, and effective port tuple."""
    parts = urlsplit(url)
    if parts.username is not None or parts.password is not None:
        raise ValueError
    scheme = parts.scheme.lower()
    hostname = parts.hostname
    if not scheme or not hostname:
        raise ValueError
    normalized_host = hostname.encode("idna").decode("ascii").lower()
    port = parts.port
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
        else:
            raise ValueError
    return scheme, normalized_host, port
