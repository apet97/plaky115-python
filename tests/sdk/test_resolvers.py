"""Resolvers: reference parsing, lookups, not-found rewrapping, and bounded pages."""

import httpx2
import pytest

from fakes import paged_workspace_client, simple_board_async_client, simple_board_client
from plaky115 import (
    AsyncPlakyClient,
    PlakyBoundedResultError,
    PlakyClient,
    PlakyNotFoundError,
    async_resolve_board,
    async_resolve_item,
    async_resolve_item_file_on_item,
    async_resolve_item_group_in_board,
    async_resolve_items_in_board,
    async_resolve_team,
    resolve_board,
    resolve_item,
    resolve_item_file_on_item,
    resolve_item_group_in_board,
    resolve_items_in_board,
    resolve_space,
    resolve_space_and_board,
    resolve_team,
    resolve_user,
)
from plaky115.resolvers import _as_id, _canonical_id, _pick, _RefMatch, async_resolve_user

pytestmark = pytest.mark.anyio


def test_sync_resolvers() -> None:
    with paged_workspace_client() as client:
        space, board = resolve_space_and_board(client, space=1, board="b")
        assert space.id == 1 and board.id == 7
        assert resolve_team(client, 9).id == 9
        assert resolve_user(client, {"email": "ada@x.com"}).id == 5
        assert resolve_item(client, space=1, board=7, item=1).id == 1
        items = resolve_items_in_board(client, space_id=1, board_id=7, items=[1])
        assert [i.id for i in items] == [1]
        with pytest.raises(PlakyBoundedResultError, match="inconclusive"):
            resolve_items_in_board(client, space_id=1, board_id=7, items=["three"])
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
        with pytest.raises(PlakyBoundedResultError, match="inconclusive"):
            resolve_items_in_board(client, space_id=1, board_id=7, items=["t"])


async def test_async_resolver_not_found_rewraps() -> None:
    async with simple_board_async_client() as client:
        for coroutine in [
            async_resolve_team(client, 404),
            async_resolve_board(client, space=1, board=404),
            async_resolve_item(client, space=1, board=7, item=404),
            async_resolve_item_group_in_board(client, space_id=1, board_id=7, item_group=404),
            async_resolve_item_file_on_item(
                client, space_id=1, board_id=7, item_id=3, item_file=404
            ),
        ]:
            with pytest.raises(PlakyNotFoundError) as info:
                await coroutine
            assert info.value.url == "plaky115://resolver"
        items = await async_resolve_items_in_board(client, space_id=1, board_id=7, items=[3])
        assert items[0].id == 3
        with pytest.raises(PlakyNotFoundError):
            await async_resolve_items_in_board(client, space_id=1, board_id=7, items=[404])


def test_sync_resolver_not_found_rewraps() -> None:
    with simple_board_client() as client:
        for call in [
            lambda: resolve_team(client, 404),
            lambda: resolve_board(client, space=1, board=404),
            lambda: resolve_item_group_in_board(client, space_id=1, board_id=7, item_group=404),
            lambda: resolve_item_file_on_item(
                client, space_id=1, board_id=7, item_id=3, item_file=404
            ),
            lambda: resolve_items_in_board(client, space_id=1, board_id=7, items=[404]),
            lambda: resolve_space(client, 404),
        ]:
            with pytest.raises(PlakyNotFoundError) as info:
                call()
            assert info.value.url == "plaky115://resolver"


def test_ref_parsing_edges() -> None:
    assert _as_id(True).id is None  # booleans are empty refs
    assert _as_id({"weird": 1}).id is None
    assert _as_id(object()).id is None

    class WithId:
        id = 7

    assert _as_id(WithId()).id == "7"
    for bad in ("01", "1.5", -1, 10**19, None):
        with pytest.raises(ValueError, match="identifier"):
            _canonical_id(bad)


def test_pick_empty_ref_and_field_selector() -> None:
    with pytest.raises(PlakyNotFoundError, match="thing: empty ref"):
        _pick([], _RefMatch(), "thing")
    # Field-specific selector matches only the declared field.
    entries = [{"title": "Alpha", "name": "Beta"}]
    found = _pick(entries, _RefMatch(needle="beta", field="name"), "thing")
    assert found["name"] == "Beta"
    with pytest.raises(PlakyNotFoundError):
        _pick(entries, _RefMatch(needle="alpha", field="name"), "thing")


def test_sync_resolve_user_by_plain_id() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/v1/public/users":
            return httpx2.Response(
                200, json={"data": [{"id": 5, "name": "Ada"}], "hasMore": False}
            )
        return httpx2.Response(404, json={})

    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    ) as client:
        assert resolve_user(client, 5).id == 5
        with pytest.raises(PlakyNotFoundError, match="user not found: id=6"):
            resolve_user(client, 6)


@pytest.mark.parametrize(
    ("data", "has_more", "ref", "error"),
    [
        ([{"id": 5, "email": "ada@example.com"}], True, 5, None),
        ([{"id": 6, "email": "ben@example.com"}], True, 5, PlakyBoundedResultError),
        ([{"id": 6, "email": "ben@example.com"}], False, 5, PlakyNotFoundError),
        (
            [{"id": 5, "email": "ada@example.com"}],
            True,
            {"email": "ada@example.com"},
            PlakyBoundedResultError,
        ),
    ],
)
def test_resolve_user_respects_bounded_pages(
    data: list[dict[str, int | str]],
    has_more: bool,
    ref: int | dict[str, str],
    error: type[Exception] | None,
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/public/users"
        return httpx2.Response(200, json={"data": data, "hasMore": has_more})

    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    ) as client:
        if error is None:
            assert resolve_user(client, ref).id == 5
        else:
            with pytest.raises(error):
                resolve_user(client, ref)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("data", "has_more", "ref", "error"),
    [
        ([{"id": 5, "email": "ada@example.com"}], True, 5, None),
        ([{"id": 6, "email": "ben@example.com"}], True, 5, PlakyBoundedResultError),
        ([{"id": 6, "email": "ben@example.com"}], False, 5, PlakyNotFoundError),
        (
            [{"id": 5, "email": "ada@example.com"}],
            True,
            {"email": "ada@example.com"},
            PlakyBoundedResultError,
        ),
    ],
)
async def test_async_resolve_user_respects_bounded_pages(
    data: list[dict[str, int | str]],
    has_more: bool,
    ref: int | dict[str, str],
    error: type[Exception] | None,
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/public/users"
        return httpx2.Response(200, json={"data": data, "hasMore": has_more})

    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    ) as client:
        if error is None:
            assert (await async_resolve_user(client, ref)).id == 5
        else:
            with pytest.raises(error):
                await async_resolve_user(client, ref)
