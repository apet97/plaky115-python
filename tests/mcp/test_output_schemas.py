"""Published MCP output schemas for the high-value tool results."""

from __future__ import annotations

from typing import Any

import httpx2
import pytest
from jsonschema import Draft202012Validator
from mcp.client import Client

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.server import build_server

pytestmark = pytest.mark.anyio


def assert_matches_output_schema(tool_schema: dict[str, Any], result: Any) -> None:
    assert result.structured_content is not None
    errors = list(
        Draft202012Validator(tool_schema).iter_errors(  # pyright: ignore[reportUnknownMemberType]
            result.structured_content
        )
    )
    assert not errors, errors


async def test_high_value_tools_publish_owned_success_and_error_unions() -> None:
    sdk = AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(lambda _: httpx2.Response(200))
    )
    settings = ServerSettings(
        api_key="plk_x",
        mode="all",
        scopes=frozenset({"read", "write", "destructive"}),
    )
    async with Client(build_server(settings, sdk)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    expected_models = {
        "plaky_plan_mutation": ("PlanMutationSuccess",),
        "plaky_execute_mutation_workflow": (
            "PlanMutationSuccess",
            "CompletedMutationSuccess",
            "BulkMutationSuccess",
        ),
        "plaky_execute_read_workflow": (
            "WorkspaceMapSuccess",
            "ItemSearchSuccess",
            "CommentsThreadSuccess",
            "ExportItemsSuccess",
        ),
        "plaky_board_view": ("BoardViewSuccess",),
        "plaky_get_item_file_download": ("DownloadLinkSuccess",),
    }
    for name, success_models in expected_models.items():
        schema = tools[name].output_schema
        assert schema is not None
        definitions = schema["$defs"]
        assert "ErrorEnvelope" in definitions
        for success_model in success_models:
            assert definitions[success_model]["additionalProperties"] is False


async def test_raw_descriptions_state_scope_pagination_and_live_write_safety() -> None:
    sdk = AsyncPlakyClient(
        api_key="plk_x", transport=httpx2.MockTransport(lambda _: httpx2.Response(200))
    )
    settings = ServerSettings(
        api_key="plk_x",
        mode="generated",
        scopes=frozenset({"read", "write", "destructive"}),
    )
    async with Client(build_server(settings, sdk)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    download_description = tools["plaky_get_item_file_download"].description
    list_items_description = tools["plaky_list_items"].description
    create_item_description = tools["plaky_create_item"].description
    assert download_description is not None
    assert list_items_description is not None
    assert create_item_description is not None
    assert "read scope" in download_description.lower()
    assert "paginat" in list_items_description.lower()
    create_item_description = create_item_description.lower()
    assert "live write" in create_item_description
    assert "no dry-run" in create_item_description
    assert (
        "receipt" in create_item_description and "do not repeat blindly" in create_item_description
    )


async def test_high_value_success_and_error_results_match_published_schemas() -> None:
    def success_handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/v1/public/spaces/1":
            return httpx2.Response(200, json={"id": 1, "title": "Space"})
        if request.url.path == "/v1/public/spaces/1/boards/7":
            return httpx2.Response(
                200, json={"id": 7, "title": "Board", "fields": [], "groups": []}
            )
        if request.url.path == "/v1/public/spaces/1/boards/7/items":
            return httpx2.Response(200, json={"data": [], "hasMore": False})
        if request.url.path.endswith("/files/4/download"):
            return httpx2.Response(
                200, json={"url": "https://example.invalid/download", "expiresInSeconds": 60}
            )
        return httpx2.Response(404, json={"message": "missing"})

    settings = ServerSettings(
        api_key="plk_x",
        mode="all",
        scopes=frozenset({"read", "write", "destructive"}),
    )
    async with (
        AsyncPlakyClient(api_key="plk_x", transport=httpx2.MockTransport(success_handler)) as sdk,
        Client(build_server(settings, sdk)) as client,
    ):
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        successes = {
            "plaky_plan_mutation": await client.call_tool(
                "plaky_plan_mutation",
                {"operation": "createItem", "spaceId": 1, "boardId": 7, "body": {"title": "Plan"}},
            ),
            "plaky_execute_mutation_workflow": await client.call_tool(
                "plaky_execute_mutation_workflow",
                {
                    "workflow": "items.create",
                    "args": {"spaceId": 1, "boardId": 7, "body": {"title": "Plan"}},
                },
            ),
            "plaky_execute_read_workflow": await client.call_tool(
                "plaky_execute_read_workflow",
                {"workflow": "items.search", "args": {"spaceId": 1, "boardId": 7, "query": ""}},
            ),
            "plaky_board_view": await client.call_tool(
                "plaky_board_view", {"spaceId": 1, "board": 7}
            ),
            "plaky_get_item_file_download": await client.call_tool(
                "plaky_get_item_file_download",
                {"spaceId": 1, "boardId": 7, "itemId": 3, "itemFileId": 4},
            ),
        }
        for name, result in successes.items():
            assert result.is_error is False, result.structured_content
            schema = tools[name].output_schema
            assert schema is not None
            assert_matches_output_schema(schema, result)

    async with (
        AsyncPlakyClient(
            api_key="plk_x", transport=httpx2.MockTransport(lambda _: httpx2.Response(404))
        ) as sdk,
        Client(build_server(settings, sdk)) as client,
    ):
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        errors = {
            "plaky_plan_mutation": await client.call_tool(
                "plaky_plan_mutation",
                {"operation": "updateItemFields", "spaceId": 1, "boardId": 7, "body": {}},
            ),
            "plaky_execute_mutation_workflow": await client.call_tool(
                "plaky_execute_mutation_workflow", {"workflow": "unknown", "args": {}}
            ),
            "plaky_execute_read_workflow": await client.call_tool(
                "plaky_execute_read_workflow", {"workflow": "unknown", "args": {}}
            ),
            "plaky_board_view": await client.call_tool(
                "plaky_board_view", {"spaceId": 1, "board": 7}
            ),
            "plaky_get_item_file_download": await client.call_tool(
                "plaky_get_item_file_download",
                {"spaceId": 1, "boardId": 7, "itemId": 3, "itemFileId": 4},
            ),
        }
        for name, result in errors.items():
            assert result.is_error is True, result.structured_content
            schema = tools[name].output_schema
            assert schema is not None
            assert_matches_output_schema(schema, result)
