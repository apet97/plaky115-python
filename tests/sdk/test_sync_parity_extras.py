"""Sync twins and paginator coverage: resolvers, workflows, transport paths."""

import json

import httpx2
import pytest

from plaky115 import (
    Page,
    PlakyAmbiguousMatchError,
    PlakyClient,
    PlakyConnectionError,
    PlakyNotFoundError,
    PlakyPartialMutationError,
    PlakyServerError,
    PlakyTimeoutError,
    bulk_update_items,
    export_items,
    iterate_item_chunks,
    iterate_item_export_chunks,
    read_item_chunk,
    read_item_export_chunk,
    resolve_item,
    resolve_item_file_on_item,
    resolve_item_group_in_board,
    resolve_items_in_board,
    resolve_space_and_board,
    resolve_team,
    resolve_user,
    with_retries,
    workspace_map,
)
from plaky115.pagination import AsyncPaginator, SyncPaginator

pytestmark = pytest.mark.anyio

ITEMS_PAGE_1 = {
    "data": [
        {"id": 1, "title": "One", "fields": [{"key": "s", "name": "Status", "value": "To do"}]},
        {"id": 2, "title": "Two"},
    ],
    "hasMore": True,
}
ITEMS_PAGE_2 = {"data": [{"id": 3, "title": "Three"}], "hasMore": False}


def handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    method = request.method
    if path == "/v1/public/spaces":
        return httpx2.Response(
            200,
            json={
                "data": [{"id": 1, "title": "Alpha", "boards": [{"id": 7, "title": "B"}]}],
                "hasMore": False,
            },
        )
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
    if path == "/v1/public/spaces/1/boards":
        return httpx2.Response(200, json={"data": [{"id": 7, "title": "B"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(
            200, json={"id": 7, "title": "B", "fields": [{"key": "s", "name": "Status"}]}
        )
    if path == "/v1/public/spaces/1/boards/7/items" and method == "GET":
        page = int(dict(request.url.params).get("page", "1"))
        return httpx2.Response(200, json=ITEMS_PAGE_1 if page == 1 else ITEMS_PAGE_2)
    if path == "/v1/public/spaces/1/boards/7/items/1":
        return httpx2.Response(200, json={"id": 1, "title": "One"})
    if path.startswith("/v1/public/spaces/1/boards/7/items/") and method == "PATCH":
        item_id = path.split("/items/")[1].split("/")[0]
        if item_id == "13":
            return httpx2.Response(500, json={"message": "boom"})
        return httpx2.Response(200, json={"id": int(item_id)})
    if path == "/v1/public/teams/9":
        return httpx2.Response(200, json={"id": 9, "title": "Team"})
    if path == "/v1/public/users":
        return httpx2.Response(
            200, json={"data": [{"id": 5, "email": "ada@x.com"}], "hasMore": False}
        )
    if path == "/v1/public/spaces/1/boards/7/item-groups":
        return httpx2.Response(
            200, json={"data": [{"id": 55, "title": "Group"}], "hasMore": False}
        )
    if path == "/v1/public/spaces/1/boards/7/items/1/files":
        return httpx2.Response(200, json=[{"id": 66, "name": "f.txt"}])
    return httpx2.Response(404, json={"message": "nope"})


def make_client() -> PlakyClient:
    return PlakyClient(api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler))


def test_sync_resolvers() -> None:
    with make_client() as client:
        space, board = resolve_space_and_board(client, space=1, board="b")
        assert space.id == 1 and board.id == 7
        assert resolve_team(client, 9).id == 9
        assert resolve_user(client, {"email": "ada@x.com"}).id == 5
        assert resolve_item(client, space=1, board=7, item=1).id == 1
        items = resolve_items_in_board(client, space_id=1, board_id=7, items=[1])
        assert [i.id for i in items] == [1]
        mixed = resolve_items_in_board(client, space_id=1, board_id=7, items=["three"])
        assert [i.id for i in mixed] == [3]
        assert (
            resolve_item_group_in_board(client, space_id=1, board_id=7, item_group="group").id
            == 55
        )
        assert (
            resolve_item_file_on_item(
                client, space_id=1, board_id=7, item_id=1, item_file="f.txt"
            ).id
            == 66
        )
        with pytest.raises(PlakyNotFoundError):
            resolve_team(client, "missing team")
        with pytest.raises(PlakyAmbiguousMatchError):
            resolve_items_in_board(client, space_id=1, board_id=7, items=["t"])


def test_sync_workspace_map_and_export() -> None:
    with make_client() as client:
        tree = workspace_map(client)
        assert tree[0]["id"] == 1
        jsonl = export_items(client, space=1, board=7, format="jsonl")
        assert len(jsonl.splitlines()) == 3
        csv_out = export_items(client, space=1, board=7, format="csv")
        assert csv_out.splitlines()[0] == "id,title,Status"


def test_sync_chunks_and_export_chunks() -> None:
    with make_client() as client:
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


def test_sync_bulk_update_receipts_and_errors() -> None:
    with make_client() as client:
        receipts = bulk_update_items(
            client,
            space=1,
            board=7,
            updates=[{"item_id": 1, "body": {"s": "x"}}, {"item_id": 13, "body": {"s": "y"}}],
        )
        assert [r.status for r in receipts] == ["completed", "ambiguous"]
        with pytest.raises(PlakyPartialMutationError):
            bulk_update_items(
                client,
                space=1,
                board=7,
                updates=[{"item_id": 13, "body": {}}],
                throw_on_error=True,
            )
        dry = bulk_update_items(
            client, space=1, board=7, updates=[{"item_id": 1, "body": {}}], dry_run=True
        )
        assert dry[0].status == "planned"

        progress: list[tuple[int, int]] = []
        bulk_update_items(
            client,
            space=1,
            board=7,
            updates=[{"item_id": 1, "body": {}}],
            on_progress=lambda done, total: progress.append((done, total)),
        )
        assert progress == [(1, 1)]

        def explode(done: int, total: int) -> None:
            raise RuntimeError("progress boom")

        with pytest.raises(PlakyPartialMutationError, match="progress reporting failed"):
            bulk_update_items(
                client, space=1, board=7, updates=[{"item_id": 1, "body": {}}], on_progress=explode
            )


def test_sync_transport_error_paths() -> None:
    def failing(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down")

    with (
        PlakyClient(
            api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(failing)
        ) as client,
        pytest.raises(PlakyConnectionError),
    ):
        client.users.me()

    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow")

    with (
        PlakyClient(
            api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(slow)
        ) as client,
        pytest.raises(PlakyTimeoutError),
    ):
        client.users.me()

    calls = 0

    def retryable(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(503, headers={"retry-after": "0"})
        return httpx2.Response(200, json={"id": 1})

    with PlakyClient(
        api_key="plk_x", max_retries=1, transport=httpx2.MockTransport(retryable)
    ) as client:
        assert client.users.me().id == 1
    assert calls == 2

    # Low-level escape hatch.
    with make_client() as client:
        envelope = client.request_with_response("GET", "/v1/public/spaces/1")
        assert envelope.status == 200 and envelope.data["id"] == 1
        assert client.request("GET", "/v1/public/spaces/1")["id"] == 1


def test_sync_with_options_shares_pool() -> None:
    with make_client() as client:
        clone = client.with_options(timeout=5)
        assert clone.server_url == client.server_url
        assert clone.spaces.get("1").id == 1


def test_with_retries_sync() -> None:
    calls = 0

    def flaky() -> int:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise PlakyServerError("boom", status=500, method="GET", url="u", headers={})
        return 42

    assert with_retries(flaky, base_delay_ms=0) == 42
    assert calls == 2
    with pytest.raises(Exception, match="withRetries only supports kind=read"):
        with_retries(lambda: 1, kind="write")


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


def test_sync_search_progress_and_cursor_errors() -> None:
    from plaky115 import search_items, search_items_detailed
    from plaky115.runtime.chunks import PageCursor

    with make_client() as client:
        progress: list[tuple[int, int]] = []
        result = search_items_detailed(
            client,
            space=1,
            board=7,
            query="o",
            on_progress=lambda scanned, limit: progress.append((scanned, limit)),
        )
        assert result.matched >= 2 and progress
        assert search_items(client, space=1, board=7, query="three") != []
        with pytest.raises(ValueError, match="cursor must contain a positive page"):
            search_items_detailed(
                client, space=1, board=7, query="x", cursor=PageCursor(page=0, index=0)
            )
        with pytest.raises(ValueError, match="cursor index 9 exceeds page 1 length"):
            search_items_detailed(
                client, space=1, board=7, query="x", cursor=PageCursor(page=1, index=9)
            )
