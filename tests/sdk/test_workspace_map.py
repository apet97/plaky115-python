"""Workspace map: bounds and the boards fetch when spaces do not embed them."""

import httpx2
import pytest

from fakes import echo_handler
from plaky115 import AsyncPlakyClient, PlakyClient, async_workspace_map, workspace_map

pytestmark = pytest.mark.anyio


def test_workspace_map_bound_validation() -> None:
    from plaky115 import workspace_map

    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(echo_handler)
    ) as client:
        with pytest.raises(ValueError, match=r"maxItems must be a non-negative safe integer\."):
            workspace_map(client, max_items=-1)
        with pytest.raises(ValueError, match=r"maxBytes must be a non-negative safe integer\."):
            workspace_map(client, max_bytes=True)  # type: ignore[arg-type]


def no_embedded_boards_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces":
        return httpx2.Response(200, json={"data": [{"id": 1, "title": "S"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards":
        return httpx2.Response(200, json={"data": [{"id": 7, "title": "B"}], "hasMore": False})
    return httpx2.Response(404, json={"message": "nope"})


async def test_workspace_map_fetches_boards_when_not_embedded() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        transport=httpx2.MockTransport(no_embedded_boards_handler),
    ) as client:
        tree = await async_workspace_map(client)
    assert tree[0]["boards"][0]["id"] == 7


def test_sync_workspace_map_fetches_boards_when_not_embedded() -> None:
    with PlakyClient(
        api_key="plk_x",
        max_retries=0,
        transport=httpx2.MockTransport(no_embedded_boards_handler),
    ) as client:
        tree = workspace_map(client)
    assert tree[0]["boards"][0]["id"] == 7
