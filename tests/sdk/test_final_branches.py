"""Last branch sweep: CLI in-process, find scopes, workspace fallback, edges."""

from typing import Any

import httpx2
import pytest
from mcp.client import Client

from plaky115 import (
    AsyncPlakyClient,
    PlakyClient,
    PlakyNotFoundError,
    async_workspace_map,
    resolve_user,
    workspace_map,
)
from plaky115.resolvers import _pick, _RefMatch  # pyright: ignore[reportPrivateUsage]
from plaky115.runtime.redaction import bound_text
from plaky115.runtime.upload import validate_upload_limit
from plaky115.workflows.mutation_plans import (
    normalize_item_create_plan,
    normalize_item_group_create_plan,
)
from plaky115_mcp.compaction import MAX_TEXT_CHARS, compact_entity, make_result
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.errors import error_envelope
from plaky115_mcp.server import build_server

pytestmark = pytest.mark.anyio


# --- CLI in-process ---------------------------------------------------------


def test_cli_main_stdio_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import anyio

    import plaky115_mcp.cli as cli

    ran: list[Any] = []
    monkeypatch.setenv("PLAKY115_API_KEY", "plk_unit")

    def fake_run(fn: Any) -> None:
        ran.append(fn)

    monkeypatch.setattr(anyio, "run", fake_run)
    assert cli.main(["--transport", "stdio"]) == 0
    assert len(ran) == 1


def test_cli_main_http_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn

    import plaky115_mcp.cli as cli

    served: list[Any] = []
    monkeypatch.setenv("PLAKY115_API_KEY", "plk_unit")

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served.append(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_serve)
    assert cli.main(["--transport", "streamable-http", "--port", "8123"]) == 0
    assert served[0]["port"] == 8123
    assert served[0]["host"] == "127.0.0.1"


def test_cli_main_blank_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import plaky115_mcp.cli as cli

    monkeypatch.setenv("PLAKY115_API_KEY", "   ")
    monkeypatch.delenv("PLAKY115_API_KEY_AUTH", raising=False)
    assert cli.main(["--transport", "stdio"]) == 2


def test_cli_non_loopback_with_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn

    import plaky115_mcp.cli as cli

    served: list[Any] = []
    monkeypatch.setenv("PLAKY115_API_KEY", "plk_unit")

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served.append(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_serve)
    assert (
        cli.main(
            [
                "--transport",
                "streamable-http",
                "--host",
                "0.0.0.0",
                "--allowed-host",
                "mcp.example",
                "--allowed-origin",
                "https://mcp.example",
            ]
        )
        == 0
    )
    assert served[0]["host"] == "0.0.0.0"


# --- plaky_find missing-scope branches --------------------------------------


async def test_find_scope_requirements() -> None:
    sdk = AsyncPlakyClient(
        api_key="plk_x",
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json={})),
    )
    server = build_server(ServerSettings(api_key="plk_x"), sdk)
    async with Client(server) as client:
        for kind, args in [
            ("item", {"spaceId": "1"}),
            ("itemGroup", {}),
            ("itemFile", {"spaceId": "1", "boardId": "7"}),
        ]:
            result = await client.call_tool("plaky_find", {"kind": kind, "query": "x", **args})
            assert result.is_error
            assert result.structured_content["error"]["category"] == "usage", kind


# --- workspace fallback boards fetch ----------------------------------------


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


# --- resolver leftovers ------------------------------------------------------


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


# --- plan/upload/compaction edges --------------------------------------------


def test_plan_normalizer_conflicts_and_types() -> None:
    with pytest.raises(TypeError, match="cannot both be provided"):
        normalize_item_create_plan(
            space_id=1, board_id=7, body={"title": "t", "groupId": 1, "groupTitle": "g"}
        )
    with pytest.raises(TypeError, match=r"body\.groupTitle must be a non-empty string"):
        normalize_item_create_plan(space_id=1, board_id=7, body={"groupTitle": " "})
    plan = normalize_item_create_plan(
        space_id=1, board_id=7, body={"title": "t", "groupTitle": "Launch"}
    )
    assert plan.requires_live_resolution is True
    with pytest.raises(TypeError, match=r"body\.groupId must be a number or decimal string"):
        normalize_item_create_plan(space_id=1, board_id=7, body={"groupId": 1.5})
    with pytest.raises(TypeError, match="spaceId:"):
        normalize_item_group_create_plan(
            space_id="01", board_id=7, body={"title": "t", "color": "#AABBCC"}
        )
    with pytest.raises(TypeError, match=r"body\.ranking must be a non-empty string when provided"):
        normalize_item_group_create_plan(
            space_id=1, board_id=7, body={"title": "t", "color": "#AABBCC", "ranking": " "}
        )


def test_upload_limit_type_check() -> None:
    from plaky115 import UploadValidationError

    with pytest.raises(UploadValidationError):
        validate_upload_limit("many")  # type: ignore[arg-type]


def test_compaction_edges() -> None:
    unknown = compact_entity({str(i): i for i in range(30)}, "mystery")
    assert len(unknown) == 20  # bounded fallback for unknown kinds
    nested = compact_entity({"id": 1, "group": {"id": 9, "title": "x"}}, "item")
    assert nested["group"] == 9
    long_text = make_result(text="y" * (MAX_TEXT_CHARS + 50), structured={"ok": True})
    text_block = long_text.content[0]
    assert len(getattr(text_block, "text", "")) == MAX_TEXT_CHARS


def test_error_envelope_receipts_kwarg() -> None:
    from plaky115.runtime.mutations import new_receipt

    envelope = error_envelope(ValueError("v"), receipts=(new_receipt("op", 0, {"a": "1"}),))
    assert envelope.error.receipts[0].operation == "op"


def test_bound_text_exact_limit() -> None:
    assert bound_text("abc", 3) == "abc"
    assert bound_text("abcd", 3) == "ab…"


# --- sync comments iterate/list_all -----------------------------------------


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
