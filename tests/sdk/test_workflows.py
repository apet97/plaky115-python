"""Phase 8 gates: fields, resolvers, search, bulk update, export, CSV."""

import json
from pathlib import Path
from typing import Any

import httpx2
import pytest

from plaky115 import (
    AsyncPlakyClient,
    PlakyAmbiguousMatchError,
    PlakyClient,
    PlakyNotFoundError,
    PlakyPartialMutationError,
    async_bulk_update_items,
    async_resolve_items_in_board,
    async_resolve_space,
    async_resolve_user,
    async_search_items_detailed,
    async_workspace_map,
    export_items,
    field_label,
    field_values,
    link_field,
    number_field,
    omit_none,
    person_field,
    read_item_export_chunk,
    resolve_space,
    search_items_detailed,
    status_field,
    string_field,
    tag_field,
    timeline_field,
)
from plaky115.runtime.chunks import PageCursor
from plaky115.workflows.csv import render_items_csv

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# --- fields -----------------------------------------------------------------


def test_field_builders() -> None:
    assert string_field("x") == "x"
    assert status_field(1) == 1
    assert tag_field(["a", 2]) == ["a", 2]
    assert field_values({"a": 1}) == {"a": 1}
    assert omit_none({"a": 1, "b": None}) == {"a": 1}
    assert person_field(users=[1, {"email": "a@x.com"}]) == {
        "users": [{"id": 1}, {"email": "a@x.com"}]
    }
    assert person_field(teams=[]) == {"teams": []}
    assert timeline_field(start="2026-01-01", end="2026-02-01") == {
        "start": "2026-01-01",
        "end": "2026-02-01",
    }
    with pytest.raises(ValueError, match="both start and end are required"):
        timeline_field(start="", end="2026-02-01")
    assert link_field(url="https://x") == {"url": "https://x"}
    assert link_field(url="https://x", text="X") == {"url": "https://x", "text": "X"}
    with pytest.raises(ValueError, match="url is required"):
        link_field(url="")
    assert number_field(1.5) == 1.5
    with pytest.raises(ValueError, match="finite number"):
        number_field(float("nan"))


def test_field_label_precedence() -> None:
    assert field_label({"name": "N", "title": "T", "key": "k"}) == "N"
    assert field_label({"title": "T", "key": "k"}) == "T"
    assert field_label({"key": "k"}) == "k"
    assert field_label({"name": ""}) == ""


# --- CSV golden fixtures ----------------------------------------------------


def test_csv_golden_fixtures() -> None:
    items = json.loads((FIXTURES / "export/items.json").read_text())
    assert (
        render_items_csv(items, "spreadsheet") == (FIXTURES / "export/items.safe.csv").read_text()
    )
    assert render_items_csv(items, "raw") == (FIXTURES / "export/items.raw.csv").read_text()


def test_csv_empty_is_empty_string() -> None:
    assert render_items_csv([]) == ""


# --- resolver fixtures -------------------------------------------------------

SPACES_PAGE = {
    "data": [
        {"id": 1, "title": "Alpha"},
        {"id": 2, "title": "Beta"},
        {"id": 3, "title": "Alpha Two"},
    ],
    "hasMore": False,
}


def resolver_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces":
        return httpx2.Response(200, json=SPACES_PAGE)
    if path == "/v1/public/spaces/2":
        return httpx2.Response(200, json={"id": 2, "title": "Beta"})
    if path == "/v1/public/spaces/99":
        return httpx2.Response(404, json={"message": "missing"})
    if path == "/v1/public/users":
        return httpx2.Response(
            200,
            json={
                "data": [
                    {"id": 5, "name": "Ada", "email": "ada@x.com"},
                    {"id": 6, "name": "Ben", "email": "ben@x.com"},
                ],
                "hasMore": False,
            },
        )
    if path == "/v1/public/spaces/1/boards/7/items/3":
        return httpx2.Response(200, json={"id": 3, "title": "Item"})
    if path == "/v1/public/spaces/1/boards/7/items":
        return httpx2.Response(
            200,
            json={
                "data": [{"id": 3, "title": "One"}, {"id": 4, "title": "Two"}],
                "hasMore": False,
            },
        )
    return httpx2.Response(404, json={"message": "nope"})


def async_client() -> AsyncPlakyClient:
    return AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(resolver_handler)
    )


async def test_resolve_space_by_exact_id_uses_direct_get() -> None:
    async with async_client() as client:
        space = await async_resolve_space(client, 2)
        assert space.id == 2


async def test_resolve_space_text_matching() -> None:
    async with async_client() as client:
        space = await async_resolve_space(client, "beta")
        assert space.id == 2
        with pytest.raises(PlakyAmbiguousMatchError) as ambiguous:
            await async_resolve_space(client, "alpha")
        assert ambiguous.value.candidate_count == 2
        with pytest.raises(PlakyNotFoundError) as missing:
            await async_resolve_space(client, "gamma")
        assert missing.value.url == "plaky115://resolver"
        assert missing.value.method == "LOCAL"


async def test_resolve_missing_id_rewrapped_as_local() -> None:
    async with async_client() as client:
        with pytest.raises(PlakyNotFoundError) as info:
            await async_resolve_space(client, 99)
        assert info.value.url == "plaky115://resolver"
        assert "space not found: id=99" in str(info.value)


async def test_selector_conflicts_fail_before_network() -> None:
    async with async_client() as client:
        with pytest.raises(TypeError, match="entity reference selectors conflict: title, name"):
            await async_resolve_space(client, {"title": "A", "name": "B"})
        with pytest.raises(TypeError, match="title selector must be a non-empty string"):
            await async_resolve_space(client, {"title": ""})


async def test_id_is_authoritative_over_labels() -> None:
    async with async_client() as client:
        space = await async_resolve_space(client, {"id": 2, "title": "Alpha"})
        assert space.id == 2  # label ignored; direct GET used


async def test_resolve_user_always_lists() -> None:
    async with async_client() as client:
        user = await async_resolve_user(client, {"email": "ada@x.com"})
        assert user.id == 5


async def test_resolve_items_all_ids_direct_gets() -> None:
    async with async_client() as client:
        items = await async_resolve_items_in_board(client, space_id=1, board_id=7, items=[3])
        assert [i.id for i in items] == [3]
        # Mixed refs use exactly one list.
        items = await async_resolve_items_in_board(
            client, space_id=1, board_id=7, items=["one", 4]
        )
        assert [i.id for i in items] == [3, 4]
        assert await async_resolve_items_in_board(client, space_id=1, board_id=7, items=[]) == []


def test_sync_resolver_parity() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(resolver_handler)
    ) as client:
        assert resolve_space(client, "beta").id == 2


# --- search -------------------------------------------------------------------


def search_handler_pages(pages: list[dict[str, Any]]) -> Any:
    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path == "/v1/public/spaces/1":
            return httpx2.Response(200, json={"id": 1, "title": "S"})
        if path == "/v1/public/spaces/1/boards/7":
            return httpx2.Response(200, json={"id": 7, "title": "B"})
        if path == "/v1/public/spaces/1/boards/7/items":
            page = int(dict(request.url.params).get("page", "1"))
            return httpx2.Response(200, json=pages[page - 1])
        return httpx2.Response(404, json={"message": "nope"})

    return handler


SEARCH_PAGES = [
    {
        "data": [
            {"id": 1, "title": "Find me"},
            {"id": 2, "title": "Other", "fields": [{"key": "s", "value": {"deep": ["find"]}}]},
            {"id": 3, "title": "Nope", "fields": [{"key": "n", "value": 42}]},
        ],
        "hasMore": True,
    },
    {"data": [{"id": 4, "title": "find again"}], "hasMore": False},
]


async def test_search_nested_scalars_and_completion() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        transport=httpx2.MockTransport(search_handler_pages(SEARCH_PAGES)),
    ) as client:
        result = await async_search_items_detailed(client, space=1, board=7, query="find")
        assert [i.id for i in result.data] == [1, 2, 4]
        assert result.complete and not result.truncated
        assert result.continuation is None
        # Numeric scalar matching
        result = await async_search_items_detailed(client, space=1, board=7, query="42")
        assert [i.id for i in result.data] == [3]


async def test_search_truncation_and_continuation() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        transport=httpx2.MockTransport(search_handler_pages(SEARCH_PAGES)),
    ) as client:
        first = await async_search_items_detailed(client, space=1, board=7, query="find", limit=2)
        assert first.truncated and not first.complete
        assert first.continuation == PageCursor(page=1, index=2)
        rest = await async_search_items_detailed(
            client, space=1, board=7, query="find", cursor=first.continuation
        )
        assert [i.id for i in rest.data] == [4]
        assert rest.complete


async def test_search_limit_validated_before_io() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return httpx2.Response(200, json={})

    async with AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(handler)
    ) as client:
        for bad in (0, -1, True):
            with pytest.raises(ValueError, match="limit must be a finite positive integer"):
                await async_search_items_detailed(client, space=1, board=7, query="x", limit=bad)
    assert calls == []


def test_sync_search_parity() -> None:
    with PlakyClient(
        api_key="plk_x",
        max_retries=0,
        transport=httpx2.MockTransport(search_handler_pages(SEARCH_PAGES)),
    ) as client:
        result = search_items_detailed(client, space=1, board=7, query="find")
        assert result.matched == 3


# --- bulk update ---------------------------------------------------------------


def bulk_handler(fail_item: str | None) -> Any:
    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path == "/v1/public/spaces/1":
            return httpx2.Response(200, json={"id": 1})
        if path == "/v1/public/spaces/1/boards/7":
            return httpx2.Response(200, json={"id": 7})
        if request.method == "PATCH":
            item_id = path.split("/items/")[1].split("/")[0]
            if item_id == fail_item:
                return httpx2.Response(500, json={"message": "boom"})
            return httpx2.Response(200, json={"id": int(item_id)})
        return httpx2.Response(404, json={"message": "nope"})

    return handler


async def test_bulk_update_receipts() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(bulk_handler("4"))
    ) as client:
        receipts = await async_bulk_update_items(
            client,
            space=1,
            board=7,
            updates=[
                {"item_id": 3, "body": {"f": 1}},
                {"item_id": 4, "body": {"f": 2}},
                {"item_id": 5, "body": {"f": 3}},
            ],
        )
    assert [r.status for r in receipts] == ["completed", "ambiguous", "completed"]
    assert receipts[1].may_have_committed is True
    assert receipts[1].error is not None


async def test_bulk_update_validation_before_network() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return httpx2.Response(200, json={})

    async with AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(handler)
    ) as client:
        with pytest.raises(TypeError, match=r"updates\[0\].itemId must be a number"):
            await async_bulk_update_items(
                client, space=1, board=7, updates=[{"item_id": None, "body": {}}]
            )
        with pytest.raises(TypeError, match=r"updates\[0\].body must be a plain object"):
            await async_bulk_update_items(
                client, space=1, board=7, updates=[{"item_id": 3, "body": "x"}]
            )
    assert calls == []


async def test_bulk_update_dry_run_makes_no_writes() -> None:
    writes: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.method == "PATCH":
            writes.append(request.url.path)
        if request.url.path == "/v1/public/spaces/1":
            return httpx2.Response(200, json={"id": 1})
        if request.url.path == "/v1/public/spaces/1/boards/7":
            return httpx2.Response(200, json={"id": 7})
        return httpx2.Response(200, json={})

    async with AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(handler)
    ) as client:
        receipts = await async_bulk_update_items(
            client, space=1, board=7, updates=[{"item_id": 3, "body": {}}], dry_run=True
        )
    assert writes == []
    assert receipts[0].status == "planned"
    assert receipts[0].attempted is False


async def test_bulk_update_throw_on_error_carries_receipts() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(bulk_handler("3"))
    ) as client:
        with pytest.raises(PlakyPartialMutationError) as info:
            await async_bulk_update_items(
                client,
                space=1,
                board=7,
                updates=[{"item_id": 3, "body": {}}, {"item_id": 4, "body": {}}],
                throw_on_error=True,
            )
    assert info.value.failed_index == 0
    assert len(info.value.receipts) == 2


# --- export / workspace map ------------------------------------------------------


def export_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "S"})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(
            200, json={"id": 7, "title": "B", "fields": [{"key": "s", "name": "Status"}]}
        )
    if path == "/v1/public/spaces/1/boards/7/items":
        return httpx2.Response(
            200,
            json={
                "data": [
                    {"id": 1, "title": "A", "fields": [{"key": "s", "value": "To do"}]},
                    {"id": 2, "title": "B"},
                ],
                "hasMore": False,
            },
        )
    if path == "/v1/public/spaces":
        return httpx2.Response(
            200,
            json={
                "data": [{"id": 1, "title": "S", "boards": [{"id": 7, "title": "B"}]}],
                "hasMore": False,
            },
        )
    return httpx2.Response(404, json={"message": "nope"})


def test_export_jsonl_no_trailing_newline() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(export_handler)
    ) as client:
        out = export_items(client, space=1, board=7, format="jsonl")
    lines = out.split("\n")
    assert len(lines) == 2
    assert not out.endswith("\n")
    assert json.loads(lines[0])["id"] == 1


def test_export_chunk_jsonl_every_line_terminated() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(export_handler)
    ) as client:
        chunk = read_item_export_chunk(client, space=1, board=7, format="jsonl")
    assert chunk.complete
    assert chunk.body.endswith("\n")
    assert chunk.body.count("\n") == 2


def test_export_chunk_csv_header_and_schema() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(export_handler)
    ) as client:
        chunk = read_item_export_chunk(client, space=1, board=7, format="csv")
    header = chunk.body.splitlines()[0]
    assert header == "id,title,Status"
    assert chunk.body.endswith("\n")
    assert chunk.complete


async def test_workspace_map_uses_embedded_boards() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return export_handler(request)

    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    ) as client:
        tree = await async_workspace_map(client)
    assert tree == [{"id": 1, "title": "S", "boards": [{"id": 7, "title": "B"}]}]
    assert calls == ["/v1/public/spaces"]  # no per-space board fetch
