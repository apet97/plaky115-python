"""Item export: JSONL and CSV output, chunk continuation, and size limits."""

from typing import Any

import httpx2
import pytest

from fakes import paged_workspace_client, simple_board_async_client
from plaky115 import (
    PlakyClient,
    PlakyMaterializationLimitError,
    async_export_items,
    async_iterate_item_chunks,
    async_iterate_item_export_chunks,
    export_items,
    read_item_export_chunk,
    workspace_map,
)

pytestmark = pytest.mark.anyio


def test_sync_workspace_map_and_export() -> None:
    with paged_workspace_client() as client:
        tree = workspace_map(client)
        assert tree[0]["id"] == 1
        jsonl = export_items(client, space=1, board=7, format="jsonl")
        assert len(jsonl.splitlines()) == 3
        csv_out = export_items(client, space=1, board=7, format="csv")
        assert csv_out.splitlines()[0] == "id,title,Status"


async def test_async_export_and_iterators() -> None:
    async with simple_board_async_client() as client:
        jsonl = await async_export_items(client, space=1, board=7, format="jsonl")
        assert len(jsonl.splitlines()) == 2
        csv_out = await async_export_items(client, space=1, board=7, format="csv")
        assert csv_out.splitlines()[0] == "id,title"

        chunks = [c async for c in async_iterate_item_chunks(client, space=1, board=7)]
        assert chunks[-1].complete

        export_chunks = [
            c
            async for c in async_iterate_item_export_chunks(
                client, space=1, board=7, format="csv", max_items=1
            )
        ]
        assert export_chunks[0].body.splitlines()[0] == "id,title"
        assert len(export_chunks) >= 2

        with pytest.raises(PlakyMaterializationLimitError):
            await async_export_items(client, space=1, board=7, max_items=1)
        with pytest.raises(PlakyMaterializationLimitError):
            await async_export_items(client, space=1, board=7, max_bytes=4)
        with pytest.raises(ValueError, match=r"maxItems must be a non-negative safe integer\."):
            await async_export_items(client, space=1, board=7, max_items=-1)


EXPORT_PAGES: dict[int, dict[str, Any]] = {
    1: {"data": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}], "hasMore": True},
    2: {"data": [{"id": 3, "title": "C"}], "hasMore": False},
}


def export_handler(request_: httpx2.Request) -> httpx2.Response:
    path = request_.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7, "fields": [{"key": "s", "name": "S"}]})
    if path == "/v1/public/spaces/1/boards/7/items":
        page = int(dict(request_.url.params).get("page", "1"))
        return httpx2.Response(200, json=EXPORT_PAGES[page])
    return httpx2.Response(404, json={"message": "nope"})


def export_client() -> PlakyClient:
    return PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(export_handler)
    )


def test_sync_export_chunk_continuation_and_headers() -> None:
    with export_client() as client:
        first = read_item_export_chunk(client, space=1, board=7, format="csv", max_items=2)
        assert first.truncated and first.next_cursor is not None
        assert first.body.splitlines()[0] == "id,title,S"
        second = read_item_export_chunk(
            client,
            space=1,
            board=7,
            format="csv",
            max_items=2,
            cursor=first.next_cursor,
            include_header=False,
        )
        assert second.complete
        assert not second.body.startswith("id,title")

        jsonl_first = read_item_export_chunk(client, space=1, board=7, format="jsonl", max_items=2)
        assert jsonl_first.truncated and jsonl_first.body.count("\n") == 2

        with pytest.raises(Exception, match=r"maxItems must be a non-negative safe integer\."):
            export_items(client, space=1, board=7, max_items=-1)
