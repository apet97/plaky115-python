"""Board View MCP App: tool shaping, caps, template, and doc resources."""

import json
import re
from typing import Any

import httpx2
import pytest
from mcp.client import Client
from mcp.server.apps import APP_MIME_TYPE
from mcp.types import ReadResourceResult, TextResourceContents

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.apps import BOARD_VIEW_URI, board_view_html
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.server import build_server
from plaky115_mcp.tools.curated.board_view import MAX_ITEMS, _shape_value

pytestmark = pytest.mark.anyio

BOARD = {
    "id": 7,
    "title": "Launch",
    "fields": [
        {
            "key": "status-1",
            "name": "Status",
            "type": "STATUS",
            "configuration": {
                "values": [
                    {"key": "s-open", "title": "Open", "color": "#22c55e"},
                    {"key": "s-done", "title": "Done", "color": "#6b7280"},
                ]
            },
        },
        {
            "key": "tag-1",
            "name": "Tags",
            "type": "TAG",
            "configuration": {"values": [{"key": "t-1", "title": "Urgent", "color": "#ef4444"}]},
        },
        {"key": "person-1", "name": "Owner", "type": "PERSON"},
        {"key": "text-1", "name": "Notes", "type": "STRING"},
        {"name": "keyless", "type": "STRING"},
    ],
    "groups": [
        {"id": 100, "title": "Now", "color": "#3b82f6"},
        {"id": 101, "title": "Later", "color": "#a855f7"},
    ],
}

ITEMS: list[dict[str, Any]] = [
    {
        "id": 31,
        "title": "Ship it",
        "group": 100,
        "fields": [
            {"key": "status-1", "type": "STATUS", "value": {"key": "s-open"}},
            {"key": "tag-1", "type": "TAG", "value": [{"key": "t-1"}]},
            {
                "key": "person-1",
                "type": "PERSON",
                "value": {
                    "users": [{"id": 5, "name": "Ada"}],
                    "teams": [{"id": 9, "title": "QA"}],
                },
            },
            {"key": "text-1", "type": "STRING", "value": "x" * 500},
        ],
    },
    {"id": 32, "title": "Write docs", "group": {"id": 101}, "fields": []},
]


def api_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
    if path == "/v1/public/spaces":
        return httpx2.Response(200, json={"data": [{"id": 1, "title": "Alpha"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json=BOARD)
    if path == "/v1/public/spaces/1/boards":
        return httpx2.Response(
            200, json={"data": [{"id": 7, "title": "Launch"}], "hasMore": False}
        )
    if path == "/v1/public/spaces/1/boards/7/items":
        return httpx2.Response(200, json={"data": ITEMS, "hasMore": False})
    return httpx2.Response(404, json={"message": "nope"})


def sdk_client(handler: Any = api_handler) -> AsyncPlakyClient:
    return AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    )


def settings(**overrides: Any) -> ServerSettings:
    defaults: dict[str, Any] = {"api_key": "plk_x"}
    defaults.update(overrides)
    return ServerSettings(**defaults)


def text_content(result: ReadResourceResult) -> TextResourceContents:
    content = result.contents[0]
    assert isinstance(content, TextResourceContents)
    return content


async def test_tool_links_template_and_shapes_board() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        tool = next(t for t in (await client.list_tools()).tools if t.name == "plaky_board_view")
        assert tool.meta == {"ui": {"resourceUri": BOARD_VIEW_URI}}
        assert tool.output_schema is not None

        result = await client.call_tool("plaky_board_view", {"spaceId": 1, "board": 7})
        assert result.is_error is False, result.structured_content
        body = result.structured_content
        assert body["board"] == {"id": 7, "title": "Launch"}
        assert body["space"] == {"id": 1}
        # The keyless field definition is dropped; four columns remain.
        assert [c["key"] for c in body["columns"]] == ["status-1", "tag-1", "person-1", "text-1"]
        assert body["labels"]["status-1"]["s-open"] == {"title": "Open", "color": "#22c55e"}
        assert body["labels"]["tag-1"]["t-1"] == {"title": "Urgent", "color": "#ef4444"}
        assert [g["id"] for g in body["groups"]] == [100, 101]
        assert body["itemCount"] == 2 and body["hasMore"] is False

        first, second = body["items"]
        assert first["groupId"] == 100 and second["groupId"] == 101
        assert first["fields"]["status-1"] == "s-open"
        assert first["fields"]["tag-1"] == ["t-1"]
        assert first["fields"]["person-1"] == ["Ada", "QA"]
        assert len(first["fields"]["text-1"]) == 200  # long text values are trimmed
        assert second["fields"] == {}


async def test_board_resolved_by_title_refetches_fields() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        result = await client.call_tool("plaky_board_view", {"spaceId": 1, "board": "Launch"})
        assert result.is_error is False
        assert [c["key"] for c in result.structured_content["columns"]] != []


async def test_unknown_board_returns_error_envelope() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        result = await client.call_tool("plaky_board_view", {"spaceId": 1, "board": 999})
        assert result.is_error is True
        assert result.structured_content["error"]["category"]


async def test_item_cap_and_truncation_flag() -> None:
    def paged_handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path == "/v1/public/spaces/1":
            return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
        if path == "/v1/public/spaces/1/boards/7":
            return httpx2.Response(200, json={"id": 7, "title": "Big", "fields": [], "groups": []})
        if path == "/v1/public/spaces/1/boards/7/items":
            page = int(request.url.params.get("page", "1"))
            data = [
                {"id": (page - 1) * 100 + n, "title": f"Item {page}-{n}", "group": 1}
                for n in range(100)
            ]
            return httpx2.Response(200, json={"data": data, "hasMore": True})
        return httpx2.Response(404, json={"message": "nope"})

    server = build_server(settings(), sdk_client(paged_handler))
    async with Client(server) as client:
        result = await client.call_tool("plaky_board_view", {"spaceId": 1, "board": 7})
        body = result.structured_content
        assert body["itemCount"] == MAX_ITEMS
        assert body["truncated"] is True and body["hasMore"] is True


async def test_byte_budget_truncates_before_result_cap() -> None:
    def bulky_handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path == "/v1/public/spaces/1":
            return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
        if path == "/v1/public/spaces/1/boards/7":
            return httpx2.Response(
                200,
                json={
                    "id": 7,
                    "title": "Bulky",
                    "fields": [{"key": "link-1", "name": "Link", "type": "LINK"}],
                    "groups": [],
                },
            )
        if path == "/v1/public/spaces/1/boards/7/items":
            data = [
                {
                    "id": n,
                    "title": f"Item {n}",
                    "group": 1,
                    "fields": [
                        {
                            "key": "link-1",
                            "type": "LINK",
                            "value": {"url": "https://e.example/" + "p" * 700, "displayText": "e"},
                        }
                    ],
                }
                for n in range(100)
            ]
            return httpx2.Response(200, json={"data": data, "hasMore": True})
        return httpx2.Response(404, json={"message": "nope"})

    server = build_server(settings(), sdk_client(bulky_handler))
    async with Client(server) as client:
        result = await client.call_tool("plaky_board_view", {"spaceId": 1, "board": 7})
        body = result.structured_content
        assert result.is_error is False  # never degrades to the oversize usage error
        assert body["truncated"] is True
        assert 0 < body["itemCount"] < MAX_ITEMS


def test_shape_value_handles_short_and_expanded_forms() -> None:
    assert _shape_value("STATUS", "s-open") == "s-open"
    assert _shape_value("STATUS", {"key": "s-open", "label": "Open"}) == "s-open"
    assert _shape_value("TAG", ["t-1"]) == ["t-1"]
    assert _shape_value("PERSON", {"users": [5], "teams": []}) == [5]
    assert _shape_value("PERSON", None) is None
    assert _shape_value("NUMBER", 4) == 4
    assert _shape_value("TIMELINE", {"start": "2026-01-01", "end": "2026-01-02"}) == {
        "start": "2026-01-01",
        "end": "2026-01-02",
    }


async def test_template_resource_served_and_self_contained() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        uris = [str(r.uri) for r in (await client.list_resources()).resources]
        assert BOARD_VIEW_URI in uris
        content = text_content(await client.read_resource(BOARD_VIEW_URI))
        assert content.mime_type == APP_MIME_TYPE
        html = content.text
    assert html == board_view_html()
    assert html.lstrip().lower().startswith("<!doctype html>")
    # The Apps handshake methods the host keys on.
    for method in (
        "ui/initialize",
        "ui/notifications/initialized",
        "ui/notifications/tool-input",
        "ui/notifications/tool-result",
        "ui/notifications/host-context-changed",
        "tools/call",
    ):
        assert method in html, method
    # Self-contained: no external scripts, styles, images, or fetches.
    assert not re.search(r"""(?:src|href)\s*=\s*["']https?://""", html)
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert html.count("<script>") == 1 and html.count("</script>") == 1


async def test_structured_result_fits_wire_cap() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        result = await client.call_tool("plaky_board_view", {"spaceId": 1, "board": 7})
        wire = json.dumps(result.structured_content, ensure_ascii=False).encode("utf-8")
        assert len(wire) < 128 * 1024
