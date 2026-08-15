"""Request override precedence and dispatch-boundary behavior."""

from __future__ import annotations

import httpx2
import pytest

from plaky115 import AsyncPlakyClient, PlakyClient, RequestOverrides
from plaky115.resources._common import with_idempotency


def test_method_idempotency_override_wins_and_preserves_empty_value() -> None:
    original = RequestOverrides(timeout=9, idempotency_key="options")
    overridden = with_idempotency(original, "argument")
    assert overridden is not None
    assert overridden.idempotency_key == "argument"
    assert overridden.timeout == 9

    suppressed = with_idempotency(original, "")
    assert suppressed is not None
    assert suppressed.idempotency_key == ""


def test_sync_method_idempotency_header_and_explicit_empty_suppression() -> None:
    headers: list[dict[str, str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        headers.append(dict(request.headers))
        return httpx2.Response(204)

    with PlakyClient(api_key="plk_x", transport=httpx2.MockTransport(handler)) as client:
        client.items.delete(
            space_id=1,
            board_id=2,
            item_id=3,
            idempotency_key="argument",
            options=RequestOverrides(idempotency_key="options"),
        )
        client.items.delete(
            space_id=1,
            board_id=2,
            item_id=3,
            idempotency_key="",
            options=RequestOverrides(idempotency_key="options"),
        )

    assert headers[0]["idempotency-key"] == "argument"
    assert "idempotency-key" not in headers[1]


@pytest.mark.anyio
async def test_async_method_idempotency_header_matches_sync() -> None:
    headers: list[dict[str, str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        headers.append(dict(request.headers))
        return httpx2.Response(204)

    async with AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(handler)
    ) as client:
        await client.items.delete(
            space_id=1,
            board_id=2,
            item_id=3,
            idempotency_key="argument",
            options=RequestOverrides(idempotency_key="options"),
        )
        await client.items.delete(
            space_id=1,
            board_id=2,
            item_id=3,
            idempotency_key="",
            options=RequestOverrides(idempotency_key="options"),
        )

    assert headers[0]["idempotency-key"] == "argument"
    assert "idempotency-key" not in headers[1]
