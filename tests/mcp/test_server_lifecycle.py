"""Server lifecycle closes only a client owned by the server factory."""

from __future__ import annotations

from typing import Any, cast

import pytest

from plaky115_mcp.server import _owned_client_lifespan

pytestmark = pytest.mark.anyio


class ClosingClient:
    def __init__(self) -> None:
        self.close_calls = 0

    async def aclose(self) -> None:
        self.close_calls += 1


async def test_owned_lifespan_closes_client_once() -> None:
    client = ClosingClient()
    factory = _owned_client_lifespan(cast("Any", client))
    async with factory(cast("Any", None)):
        assert client.close_calls == 0
    assert client.close_calls == 1
