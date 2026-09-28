"""Pagination: strict page roots, paginators, comment iteration, and bounded chunks."""

import json
from typing import Any

import httpx2
import pytest

from fakes import paged_workspace_client
from plaky115 import (
    AsyncPlakyClient,
    Page,
    PlakyClient,
    iterate_item_chunks,
    iterate_item_export_chunks,
    read_item_chunk,
    read_item_export_chunk,
)
from plaky115.errors import (
    PlakyMaterializationLimitError,
    PlakyOutputLimitError,
    PlakyResponseContractError,
)
from plaky115.pagination import (
    AsyncPaginator,
    SyncPaginator,
    assert_array_result,
    assert_paged_result,
)
from plaky115.runtime.chunks import (
    DEFAULT_CHUNK_MAX_BYTES,
    DEFAULT_CHUNK_MAX_ITEMS,
    MAX_MATERIALIZED_BYTES,
    MAX_MATERIALIZED_ITEMS,
    BoundedChunk,
    PageCursor,
    assert_materialized_collection,
    iterate_paged_chunks,
    read_paged_chunk,
    sync_read_paged_chunk,
    utf8_byte_length,
)

pytestmark = pytest.mark.anyio


def test_constants() -> None:
    assert DEFAULT_CHUNK_MAX_ITEMS == 100
    assert DEFAULT_CHUNK_MAX_BYTES == 1_048_576
    assert MAX_MATERIALIZED_ITEMS == 10_000
    assert MAX_MATERIALIZED_BYTES == 16_777_216


@pytest.mark.parametrize(
    ("value", "pointer"),
    [
        (None, "/"),
        ([], "/"),
        ("x", "/"),
        ({}, "/data"),
        ({"data": "not-a-list", "hasMore": False}, "/data"),
        ({"data": []}, "/hasMore"),
        ({"data": [], "hasMore": "yes"}, "/hasMore"),
        ({"data": [], "hasMore": True}, "/hasMore"),  # empty page claiming more
    ],
)
def test_paged_root_rejections(value: Any, pointer: str) -> None:
    with pytest.raises(PlakyResponseContractError) as info:
        assert_paged_result(value, "listSpaces")
    assert info.value.pointer == pointer
    assert str(info.value) == f"Invalid listSpaces response at {pointer}."


def test_paged_root_accepts_valid() -> None:
    assert assert_paged_result({"data": [1], "hasMore": False}, "op")["data"] == [1]
    assert assert_paged_result({"data": [], "hasMore": False}, "op")["hasMore"] is False


def test_array_root() -> None:
    assert assert_array_result([1, 2], "listItemComments") == [1, 2]
    with pytest.raises(PlakyResponseContractError):
        assert_array_result({"data": []}, "listItemComments")


def make_fetcher(pages: list[dict[str, Any]]) -> Any:
    calls: list[int] = []

    async def fetcher(page: int, page_size: int) -> dict[str, Any]:
        calls.append(page)
        return pages[page - 1]

    return fetcher, calls


async def test_chunk_exact_continuation() -> None:
    fetcher, calls = make_fetcher(
        [
            {"data": [1, 2], "hasMore": True},
            {"data": [3], "hasMore": False},
        ]
    )
    first = await read_paged_chunk(fetcher, max_items=1)
    assert first.data == (1,)
    assert first.truncated and not first.complete
    assert first.next_cursor == PageCursor(page=1, index=1)

    rest = await read_paged_chunk(fetcher, cursor=first.next_cursor)
    assert rest.data == (2, 3)
    assert rest.complete and rest.next_cursor is None
    assert calls == [1, 1, 2]  # no duplicate items delivered


async def test_single_oversized_item_raises() -> None:
    fetcher, _ = make_fetcher([{"data": [{"big": "x" * 100}], "hasMore": False}])
    with pytest.raises(PlakyOutputLimitError) as info:
        await read_paged_chunk(fetcher, max_bytes=10)
    assert "Output bytes limit of 10 was reached" in str(info.value)


async def test_zero_max_items_fails_immediately() -> None:
    fetcher, calls = make_fetcher([])
    with pytest.raises(PlakyOutputLimitError):
        await read_paged_chunk(fetcher, max_items=0)
    assert calls == []


async def test_byte_accounting_uses_utf8() -> None:
    assert utf8_byte_length("čšž") == 6
    # Two 6-byte items with an 11-byte budget: only the first fits.
    fetcher, _ = make_fetcher([{"data": ["čš", "žđ"], "hasMore": False}])
    chunk = await read_paged_chunk(fetcher, max_bytes=11)
    # JSON serialization adds quotes: "čš" is 6 chars = 2+4 bytes.
    assert chunk.data == ("čš",)
    assert chunk.next_cursor == PageCursor(page=1, index=1)


async def test_cursor_index_beyond_page_is_contract_error() -> None:
    fetcher, _ = make_fetcher([{"data": [1], "hasMore": False}])
    with pytest.raises(PlakyResponseContractError):
        await read_paged_chunk(fetcher, cursor=PageCursor(page=1, index=5))


async def test_cursor_validation() -> None:
    fetcher, _ = make_fetcher([])
    with pytest.raises(ValueError, match=r"cursor\.page must be a positive safe integer\."):
        await read_paged_chunk(fetcher, cursor=PageCursor(page=0, index=0))
    with pytest.raises(ValueError, match=r"cursor\.index must be a non-negative safe integer\."):
        await read_paged_chunk(fetcher, cursor=PageCursor(page=1, index=-1))


async def test_iterate_chunks_yields_until_complete() -> None:
    fetcher, _calls = make_fetcher(
        [
            {"data": [1, 2, 3], "hasMore": True},
            {"data": [4], "hasMore": False},
        ]
    )
    chunks: list[BoundedChunk[Any]] = []
    async for chunk in iterate_paged_chunks(fetcher, max_items=2):
        chunks.append(chunk)
    assert [c.data for c in chunks] == [(1, 2), (3, 4)]
    assert chunks[-1].complete


async def test_iterate_chunks_close_stops_fetching() -> None:
    fetcher, calls = make_fetcher(
        [
            {"data": [1, 2], "hasMore": True},
            {"data": [3], "hasMore": False},
        ]
    )
    iterator = aiter(iterate_paged_chunks(fetcher, max_items=1))
    first = await anext(iterator)
    assert first.data == (1,)
    await iterator.aclose()  # type: ignore[attr-defined]
    assert calls == [1]


def test_materialized_collection_guards() -> None:
    with pytest.raises(PlakyMaterializationLimitError):
        assert_materialized_collection([1, 2, 3], 2, 10_000)
    with pytest.raises(PlakyMaterializationLimitError):
        assert_materialized_collection([{"k": "x" * 100}], 10, 20)
    assert_materialized_collection([1, 2], 2, 1000)


def _pages(page: int, size: int) -> Page[int]:
    data = {1: [1, 2], 2: [3]}[page]
    return Page[int].model_validate({"data": data, "hasMore": page == 1})


def test_sync_paginator_methods() -> None:
    paginator = SyncPaginator(_pages, page_size=2)
    assert paginator.first_page().data == [1, 2]
    assert [p.data for p in paginator.pages()] == [[1, 2], [3]]
    assert paginator.to_list() == [1, 2, 3]
    assert SyncPaginator(_pages, page_size=2).to_list(limit=2) == [1, 2]
    assert list(SyncPaginator(_pages, page_size=2, limit=1)) == [1]
    with pytest.raises(ValueError, match=r"pageSize must be a positive integer\."):
        SyncPaginator(_pages, page_size=0)
    with pytest.raises(ValueError, match=r"limit must be a non-negative integer\."):
        SyncPaginator(_pages, limit=-1)


async def test_async_paginator_methods() -> None:
    async def fetch(page: int, size: int) -> Page[int]:
        return _pages(page, size)

    paginator = AsyncPaginator(fetch, page_size=2)
    assert (await paginator.first_page()).data == [1, 2]
    pages: list[list[int]] = []
    async for page in paginator.pages():
        pages.append(list(page.data))
    assert pages == [[1, 2], [3]]
    assert await paginator.to_list() == [1, 2, 3]
    assert await AsyncPaginator(fetch, page_size=2).to_list(limit=2) == [1, 2]
    collected = [item async for item in AsyncPaginator(fetch, page_size=2, limit=1)]
    assert collected == [1]


async def test_async_paginator_page_guard() -> None:
    async def endless(page: int, size: int) -> Page[int]:
        return Page[int].model_validate({"data": [page], "hasMore": True})

    paginator = AsyncPaginator(endless, page_size=1)
    with pytest.raises(ValueError, match=r"Pagination exceeded 10000 pages\."):
        await paginator.to_list()


def test_sync_comments_iterate_and_list_all() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/comments"):
            return httpx2.Response(
                200, json=[{"id": 1, "content": "a"}, {"id": 2, "content": "b"}]
            )
        return httpx2.Response(404, json={})

    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    ) as client:
        collected = [c.id for c in client.comments.iterate(space_id=1, board_id=7, item_id=3)]
        assert collected == [1, 2]
        limited = client.comments.list_all(space_id=1, board_id=7, item_id=3, limit=1)
        assert [c.id for c in limited] == [1]


async def test_async_comments_iterate_and_list_all() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/comments"):
            return httpx2.Response(200, json=[{"id": 1, "content": "a"}])
        return httpx2.Response(404, json={})

    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    ) as client:
        collected = [
            c.id async for c in client.comments.iterate(space_id=1, board_id=7, item_id=3)
        ]
        assert collected == [1]
        assert len(await client.comments.list_all(space_id=1, board_id=7, item_id=3)) == 1


def test_sync_chunk_reader_edges() -> None:
    pages = [
        {"data": [1, 2], "hasMore": True},
        {"data": [3], "hasMore": False},
    ]
    calls: list[int] = []

    def fetch(page: int, size: int) -> dict[str, Any]:
        calls.append(page)
        return pages[page - 1]

    first = sync_read_paged_chunk(fetch, max_items=1)
    assert first.next_cursor == PageCursor(page=1, index=1)
    rest = sync_read_paged_chunk(fetch, cursor=first.next_cursor)
    assert rest.complete and rest.data == (2, 3)

    from plaky115 import PlakyOutputLimitError

    with pytest.raises(PlakyOutputLimitError):
        sync_read_paged_chunk(fetch, max_items=0)
    with pytest.raises(PlakyOutputLimitError):
        sync_read_paged_chunk(
            lambda p, s: {"data": [{"big": "x" * 99}], "hasMore": False}, max_bytes=5
        )


def test_sync_chunks_and_export_chunks() -> None:
    with paged_workspace_client() as client:
        chunk = read_item_chunk(client, space=1, board=7, max_items=2)
        assert chunk.truncated and chunk.next_cursor is not None
        rest = read_item_chunk(client, space=1, board=7, cursor=chunk.next_cursor)
        assert rest.complete

        chunks = list(iterate_item_chunks(client, space=1, board=7, max_items=2))
        assert [c.returned for c in chunks] == [2, 1]

        export_chunk = read_item_export_chunk(client, space=1, board=7, format="jsonl")
        assert export_chunk.complete and export_chunk.body.endswith("\n")
        assert json.loads(export_chunk.body.splitlines()[0])["id"] == 1

        csv_chunks = list(
            iterate_item_export_chunks(client, space=1, board=7, format="csv", max_items=2)
        )
        assert csv_chunks[0].body.splitlines()[0] == "id,title,Status"
        # Header appears exactly once, in chunk 0.
        assert all("id,title" not in c.body.splitlines()[0] for c in csv_chunks[1:])
