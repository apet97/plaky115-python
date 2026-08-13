"""Branch coverage for resolver rewraps, async exports, CLI units, providers."""

import argparse
from typing import Any

import httpx2
import pytest

from plaky115 import (
    AsyncPlakyClient,
    PlakyClient,
    PlakyMaterializationLimitError,
    PlakyNotFoundError,
    async_export_items,
    async_iterate_item_chunks,
    async_iterate_item_export_chunks,
    async_resolve_board,
    async_resolve_item,
    async_resolve_item_file_on_item,
    async_resolve_item_group_in_board,
    async_resolve_items_in_board,
    async_resolve_team,
    async_with_retries,
    resolve_board,
    resolve_item_file_on_item,
    resolve_item_group_in_board,
    resolve_items_in_board,
    resolve_space,
    resolve_team,
)
from plaky115.http import async_resolve_headers, resolve_headers
from plaky115.resolvers import _as_id, _canonical_id  # pyright: ignore[reportPrivateUsage]

pytestmark = pytest.mark.anyio


def handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
    if path == "/v1/public/spaces":
        return httpx2.Response(200, json={"data": [{"id": 1, "title": "Alpha"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7, "title": "B", "fields": []})
    if path == "/v1/public/spaces/1/boards":
        return httpx2.Response(200, json={"data": [{"id": 7, "title": "B"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7/items":
        return httpx2.Response(
            200,
            json={
                "data": [{"id": 3, "title": "One"}, {"id": 4, "title": "Two"}],
                "hasMore": False,
            },
        )
    if path == "/v1/public/spaces/1/boards/7/items/3":
        return httpx2.Response(200, json={"id": 3, "title": "One"})
    return httpx2.Response(404, json={"message": "nope"})


def make_async() -> AsyncPlakyClient:
    return AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    )


def make_sync() -> PlakyClient:
    return PlakyClient(api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler))


async def test_async_resolver_not_found_rewraps() -> None:
    async with make_async() as client:
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
    with make_sync() as client:
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


async def test_async_export_and_iterators() -> None:
    async with make_async() as client:
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


async def test_async_with_retries() -> None:
    calls = 0

    async def flaky() -> int:
        nonlocal calls
        calls += 1
        if calls < 2:
            from plaky115 import PlakyServerError

            raise PlakyServerError("boom", status=500, method="GET", url="u", headers={})
        return 7

    assert await async_with_retries(flaky, base_delay_ms=0) == 7
    assert calls == 2


def test_header_provider_resolution() -> None:
    assert resolve_headers(None) is None
    assert resolve_headers({"A": "1"}) == {"A": "1"}
    assert resolve_headers(lambda: {"B": "2"}) == {"B": "2"}
    with pytest.raises(TypeError, match="headers provider returned an invalid value"):
        resolve_headers(lambda: "nope")  # type: ignore[arg-type,return-value]


async def test_async_header_provider_resolution() -> None:
    async def provider() -> dict[str, str]:
        return {"C": "3"}

    assert await async_resolve_headers(provider) == {"C": "3"}
    assert await async_resolve_headers({"D": "4"}) == {"D": "4"}
    with pytest.raises(TypeError):
        await async_resolve_headers(lambda: 42)  # type: ignore[arg-type,return-value]


async def test_client_hooks_and_headers_merge() -> None:
    seen: dict[str, Any] = {}

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        return httpx2.Response(200, json={"id": 1})

    client = AsyncPlakyClient(
        api_key="plk_x",
        headers={"X-Base": "b"},
        transport=httpx2.MockTransport(capture),
    )
    from plaky115.resources._common import RequestOverrides

    async with client:
        await client.spaces.get("1", options=RequestOverrides(headers={"X-Extra": "e"}))
    assert seen["headers"]["x-base"] == "b"
    assert seen["headers"]["x-extra"] == "e"

    # Callable base headers merged with per-call overrides.
    client2 = AsyncPlakyClient(
        api_key="plk_x",
        headers=lambda: {"X-Base": "callable"},
        transport=httpx2.MockTransport(capture),
    )
    async with client2:
        await client2.spaces.get("1", options=RequestOverrides(headers={"X-Extra": "e2"}))
    assert seen["headers"]["x-base"] == "callable"
    assert seen["headers"]["x-extra"] == "e2"


def test_sync_client_headers_merge() -> None:
    seen: dict[str, Any] = {}

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        return httpx2.Response(200, json={"id": 1})

    from plaky115.resources._common import RequestOverrides

    with PlakyClient(
        api_key="plk_x",
        headers=lambda: {"X-Base": "s"},
        transport=httpx2.MockTransport(capture),
    ) as client:
        client.spaces.get("1", options=RequestOverrides(headers={"X-Extra": "e"}))
    assert seen["headers"]["x-base"] == "s"

    with PlakyClient(
        api_key="plk_x",
        user_agent_suffix="tester/1.0",
        transport=httpx2.MockTransport(capture),
    ) as client:
        client.spaces.get("1")
    assert seen["headers"]["user-agent"].endswith("tester/1.0")


def test_cli_units() -> None:
    from plaky115_mcp.cli import build_parser, make_settings

    parser = build_parser()
    args = parser.parse_args(["--mode", "all", "--scope", "write", "--scope", "read"])
    import os

    os.environ["PLAKY115_API_KEY"] = "plk_unit"
    try:
        settings = make_settings(args)
    finally:
        del os.environ["PLAKY115_API_KEY"]
    assert settings.mode == "all"
    assert settings.scopes == frozenset({"read", "write"})

    bad = parser.parse_args(["--scope", "destructive"])
    os.environ["PLAKY115_API_KEY"] = "plk_unit"
    try:
        with pytest.raises(ValueError, match="destructive scope requires"):
            make_settings(bad)
    finally:
        del os.environ["PLAKY115_API_KEY"]


def test_cli_http_guard_requires_origin() -> None:
    from plaky115_mcp.cli import _run_http  # pyright: ignore[reportPrivateUsage]

    args = argparse.Namespace(host="0.0.0.0", port=8000, allowed_origin=None)
    assert _run_http(object(), args) == 2


def test_settings_validation() -> None:
    from plaky115_mcp.config import ServerSettings, resolve_api_key, resolve_server_url

    with pytest.raises(ValueError, match="API key must be non-blank"):
        ServerSettings(api_key=" ")
    with pytest.raises(ValueError, match="invalid mode"):
        ServerSettings(api_key="plk_x", mode="wild")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="invalid scopes"):
        ServerSettings(api_key="plk_x", scopes=frozenset({"read", "root"}))
    with pytest.raises(ValueError, match="read scope is always required"):
        ServerSettings(api_key="plk_x", scopes=frozenset({"write"}))
    assert resolve_api_key({"PLAKY115_API_KEY_AUTH": "plk_alt"}) == "plk_alt"
    with pytest.raises(ValueError, match="PLAKY115_API_KEY"):
        resolve_api_key({})
    assert resolve_server_url(None, {"PLAKY115_BASE_URL": "https://x.example"}) == (
        "https://x.example"
    )
    assert resolve_server_url("https://cli.example", {}) == "https://cli.example"
