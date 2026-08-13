"""Resolver API-404 conversion branches, canonical ids, compat dispatcher, export caps."""

from typing import Any

import httpx2
import pytest

from plaky115 import (
    AsyncPlakyClient,
    PlakyClient,
    PlakyMaterializationLimitError,
    PlakyNotFoundError,
    async_resolve_item_file_on_item,
    async_resolve_item_group_in_board,
    async_resolve_items_in_board,
    async_resolve_space,
    async_resolve_space_and_board,
    async_resolve_team,
    export_items,
    read_item_export_chunk,
    resolve_item,
    resolve_item_file_on_item,
    resolve_item_group_in_board,
    resolve_space,
    resolve_team,
)
from plaky115.resolvers import _canonical_id  # pyright: ignore[reportPrivateUsage]

pytestmark = pytest.mark.anyio


def not_found_handler(request: httpx2.Request) -> httpx2.Response:
    """Space 1 and board 7 exist; every other direct GET is a 404."""
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "S"})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7, "title": "B"})
    if path.endswith("/items") and request.method == "GET":
        return httpx2.Response(200, json={"data": [], "hasMore": False})
    return httpx2.Response(404, json={"message": "missing"})


def sync_client() -> PlakyClient:
    return PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(not_found_handler)
    )


def async_client() -> AsyncPlakyClient:
    return AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(not_found_handler)
    )


def test_sync_resolver_404_conversions() -> None:
    with sync_client() as client:
        with pytest.raises(PlakyNotFoundError, match="space not found: id=99"):
            resolve_space(client, 99)
        with pytest.raises(PlakyNotFoundError, match="board not found: id=88"):
            resolve_item(client, space=1, board=88, item=3)
        with pytest.raises(PlakyNotFoundError, match="team not found: id=77"):
            resolve_team(client, 77)
        with pytest.raises(PlakyNotFoundError, match="item group not found: id=66"):
            resolve_item_group_in_board(client, space_id=1, board_id=7, item_group=66)
        with pytest.raises(PlakyNotFoundError, match="item file not found: id=55"):
            resolve_item_file_on_item(client, space_id=1, board_id=7, item_id=3, item_file=55)
        with pytest.raises(PlakyNotFoundError, match="item not found: id=44"):
            resolve_item(client, space=1, board=7, item=44)


async def test_async_resolver_404_conversions() -> None:
    async with async_client() as client:
        with pytest.raises(PlakyNotFoundError, match="space not found: id=99"):
            await async_resolve_space(client, 99)
        with pytest.raises(PlakyNotFoundError, match="board not found: id=88"):
            await async_resolve_space_and_board(client, space=1, board=88)
        with pytest.raises(PlakyNotFoundError, match="team not found: id=77"):
            await async_resolve_team(client, 77)
        with pytest.raises(PlakyNotFoundError, match="item group not found: id=66"):
            await async_resolve_item_group_in_board(client, space_id=1, board_id=7, item_group=66)
        with pytest.raises(PlakyNotFoundError, match="item file not found: id=55"):
            await async_resolve_item_file_on_item(
                client, space_id=1, board_id=7, item_id=3, item_file=55
            )
        with pytest.raises(PlakyNotFoundError, match="item not found: id=44"):
            await async_resolve_items_in_board(client, space_id=1, board_id=7, items=[44])


def test_canonical_id_rejections() -> None:
    with pytest.raises(ValueError, match="canonical non-negative decimal"):
        _canonical_id(True)
    with pytest.raises(ValueError, match="canonical non-negative decimal"):
        _canonical_id(1.5)
    with pytest.raises(ValueError, match="safe non-negative integer"):
        _canonical_id(-1)
    with pytest.raises(ValueError, match="exceeds signed int64"):
        _canonical_id("99999999999999999999")
    assert _canonical_id("0") == "0"


# --- compat dispatcher error branches ----------------------------------------


class FakeContext:
    async def report_progress(self, *args: Any, **kwargs: Any) -> None:
        return None


async def test_execute_workflow_compat_dispatcher_errors() -> None:
    from plaky115_mcp.tools.curated.execute_mutation_workflow import (
        build_execute_mutation_workflow,
    )
    from plaky115_mcp.tools.curated.execute_workflow import build_execute_workflow

    def crash(request: httpx2.Request) -> httpx2.Response:
        raise RuntimeError("wire exploded")

    sdk = AsyncPlakyClient(api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(crash))
    ctx: Any = FakeContext()
    dispatch = build_execute_workflow(sdk).handler
    unknown = await dispatch(workflow="nope", args={}, ctx=ctx)
    assert unknown.is_error
    known_fail = await dispatch(workflow="workspace.map", args={}, ctx=ctx)
    assert known_fail.is_error
    bad_args = await dispatch(
        workflow="items.create", args={"body": "not-a-dict"}, ctx=ctx, dryRun=True
    )
    assert bad_args.is_error

    mutate = build_execute_mutation_workflow(sdk).handler
    unknown_m = await mutate(workflow="workspace.map", args={}, ctx=ctx)
    assert unknown_m.is_error
    bad_args_m = await mutate(
        workflow="items.create", args={"body": "not-a-dict"}, ctx=ctx, dryRun=True
    )
    assert bad_args_m.is_error
    live_fail = await mutate(
        workflow="items.create",
        args={"spaceId": "1", "boardId": "7", "body": {"title": "t"}},
        ctx=ctx,
        dryRun=False,
    )
    assert live_fail.is_error


# --- export byte caps ---------------------------------------------------------


EXPORT_PAGES: dict[int, dict[str, Any]] = {
    1: {"data": [{"id": 1, "title": "A" * 40}, {"id": 2, "title": "B" * 40}], "hasMore": False},
}


def export_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7, "fields": []})
    if path == "/v1/public/spaces/1/boards/7/items":
        return httpx2.Response(200, json=EXPORT_PAGES[1])
    return httpx2.Response(404, json={"message": "nope"})


def test_export_byte_caps() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(export_handler)
    ) as client:
        with pytest.raises(PlakyMaterializationLimitError):
            export_items(client, space=1, board=7, format="jsonl", max_bytes=10)
        with pytest.raises(PlakyMaterializationLimitError):
            export_items(client, space=1, board=7, format="csv", max_bytes=10)
        with pytest.raises(PlakyMaterializationLimitError):
            read_item_export_chunk(client, space=1, board=7, format="csv", max_bytes=2)


# --- RESOLVER_URL pass-through: local not-found is never double-wrapped -------


def test_sync_local_not_found_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    from plaky115.resolvers import _local_not_found  # pyright: ignore[reportPrivateUsage]

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise _local_not_found("local boom")

    with sync_client() as client:
        cases: list[tuple[Any, str, Any]] = [
            (client.spaces, "get", lambda: resolve_space(client, 99)),
            (client.teams, "get", lambda: resolve_team(client, 77)),
            (
                client.item_groups,
                "get",
                lambda: resolve_item_group_in_board(client, space_id=1, board_id=7, item_group=66),
            ),
            (
                client.item_files,
                "get",
                lambda: resolve_item_file_on_item(
                    client, space_id=1, board_id=7, item_id=3, item_file=55
                ),
            ),
            (client.items, "get", lambda: resolve_item(client, space=1, board=7, item=44)),
            (client.boards, "get", lambda: resolve_item(client, space=1, board=88, item=3)),
        ]
        for resource, attr, call in cases:
            with monkeypatch.context() as patch:
                patch.setattr(resource, attr, boom)
                with pytest.raises(PlakyNotFoundError, match="local boom"):
                    call()


async def test_async_local_not_found_passes_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from plaky115.resolvers import _local_not_found  # pyright: ignore[reportPrivateUsage]

    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise _local_not_found("local boom")

    async with async_client() as client:
        cases: list[tuple[Any, str, Any]] = [
            (client.spaces, "get", lambda: async_resolve_space(client, 99)),
            (client.teams, "get", lambda: async_resolve_team(client, 77)),
            (
                client.item_groups,
                "get",
                lambda: async_resolve_item_group_in_board(
                    client, space_id=1, board_id=7, item_group=66
                ),
            ),
            (
                client.item_files,
                "get",
                lambda: async_resolve_item_file_on_item(
                    client, space_id=1, board_id=7, item_id=3, item_file=55
                ),
            ),
            (
                client.items,
                "get",
                lambda: async_resolve_items_in_board(client, space_id=1, board_id=7, items=[44]),
            ),
            (
                client.boards,
                "get",
                lambda: async_resolve_space_and_board(client, space=1, board=88),
            ),
        ]
        for resource, attr, call in cases:
            with monkeypatch.context() as patch:
                patch.setattr(resource, attr, boom)
                with pytest.raises(PlakyNotFoundError, match="local boom"):
                    await call()
