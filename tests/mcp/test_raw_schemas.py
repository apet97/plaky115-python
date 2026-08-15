"""Generated raw-tool schemas stay strict, descriptive, and contract-owned."""

from __future__ import annotations

import httpx2
import pytest
from jsonschema import Draft202012Validator
from mcp.client import Client

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.server import build_server

pytestmark = pytest.mark.anyio


def settings() -> ServerSettings:
    return ServerSettings(
        api_key="plk_x",
        mode="generated",
        scopes=frozenset({"read", "write", "destructive"}),
    )


async def test_raw_schema_carries_contract_descriptions_and_strict_request_body() -> None:
    sdk = AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(lambda _: httpx2.Response(200))
    )
    async with Client(build_server(settings(), sdk)) as client:
        tool = next(
            tool for tool in (await client.list_tools()).tools if tool.name == "plaky_create_item"
        )

    schema = tool.input_schema
    assert schema["additionalProperties"] is False
    assert schema["properties"]["spaceId"]["description"]
    assert schema["properties"]["spaceId"]["oneOf"][1]["pattern"] == "^(0|[1-9][0-9]*)$"
    assert schema["properties"]["body"]["additionalProperties"] is False


async def test_raw_body_schemas_accept_decimal_string_int64_values() -> None:
    async with (
        AsyncPlakyClient(
            api_key="plk_x", transport=httpx2.MockTransport(lambda _: httpx2.Response(200))
        ) as sdk,
        Client(build_server(settings(), sdk)) as client,
    ):
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    item_body_schema = tools["plaky_create_item"].input_schema["properties"]["body"]
    item_comment_body_schema = tools["plaky_create_item_comment"].input_schema["properties"][
        "body"
    ]

    Draft202012Validator.check_schema(item_body_schema)
    assert not list(
        Draft202012Validator(item_body_schema).iter_errors(  # pyright: ignore[reportUnknownMemberType]
            {
                "title": "Child item",
                "groupId": "9007199254740993",
                "parentId": "9007199254740994",
            }
        )
    )
    assert item_body_schema["additionalProperties"] is False
    assert not list(
        Draft202012Validator(item_comment_body_schema).iter_errors(  # pyright: ignore[reportUnknownMemberType]
            {"text": "Reply", "repliesToId": "9007199254740993"}
        )
    )
    assert item_comment_body_schema["additionalProperties"] is False
    Draft202012Validator.check_schema(item_comment_body_schema)
    assert not list(
        Draft202012Validator(item_comment_body_schema).iter_errors(  # pyright: ignore[reportUnknownMemberType]
            {"text": "Reply", "repliesToId": None}
        )
    )
    for invalid in ("not-an-id", "01", "", -1, 9_223_372_036_854_775_808):
        assert list(
            Draft202012Validator(item_body_schema).iter_errors(  # pyright: ignore[reportUnknownMemberType]
                {"title": "Child item", "groupId": invalid}
            )
        )
    assert list(
        Draft202012Validator(item_comment_body_schema).iter_errors(  # pyright: ignore[reportUnknownMemberType]
            {"text": None}
        )
    )


async def test_raw_schema_rejects_invalid_id_and_enum_before_dispatch() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return httpx2.Response(200, json={"data": [], "hasMore": False})

    sdk = AsyncPlakyClient(api_key="plk_x", transport=httpx2.MockTransport(handler))
    async with Client(build_server(settings(), sdk)) as client:
        bad_id = await client.call_tool("plaky_get_space", {"spaceId": True})
        bad_enum = await client.call_tool(
            "plaky_list_items", {"spaceId": 1, "boardId": 2, "subitemsBehaviour": "all"}
        )

    assert bad_id.is_error
    assert bad_enum.is_error
    assert calls == []


async def test_raw_comment_replies_to_id_is_validated_before_dispatch() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return httpx2.Response(201, json={"id": 1})

    async with (
        AsyncPlakyClient(api_key="plk_x", transport=httpx2.MockTransport(handler)) as sdk,
        Client(build_server(settings(), sdk)) as client,
    ):
        result = await client.call_tool(
            "plaky_create_item_comment",
            {
                "spaceId": 1,
                "boardId": 2,
                "itemId": 3,
                "body": {"text": "Reply", "repliesToId": "not-an-id"},
            },
        )

    assert result.is_error
    assert calls == []
