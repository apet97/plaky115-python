"""In-memory MCP gates: registry, modes/scopes, envelopes, caps, workflows."""

import json
from typing import Any

import httpx2
import pytest
from mcp.client import Client

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.compaction import MAX_RESULT_BYTES, make_result
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.registry import ToolSpec, validate_spec
from plaky115_mcp.server import build_server
from plaky115_mcp.tools.raw import build_raw_tools

pytestmark = pytest.mark.anyio


def api_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    method = request.method
    if path == "/v1/public/spaces" and method == "GET":
        return httpx2.Response(200, json={"data": [{"id": 1, "title": "Alpha"}], "hasMore": False})
    if path == "/v1/public/spaces/1" and method == "GET":
        return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
    if path == "/v1/public/spaces/1/boards/7" and method == "GET":
        return httpx2.Response(200, json={"id": 7, "title": "Board"})
    if path == "/v1/public/spaces/1/boards/7/items" and method == "GET":
        return httpx2.Response(
            200,
            json={"data": [{"id": 3, "title": "Find me"}], "hasMore": False},
        )
    if path == "/v1/public/spaces/1/boards/7/items" and method == "POST":
        return httpx2.Response(201, json={"id": 99, "title": "Created"})
    if path == "/v1/public/spaces/1/boards/7/items/3/comments" and method == "GET":
        return httpx2.Response(200, json=[{"id": 5, "content": "hi"}])
    if path == "/v1/public/spaces/1/boards/7/items/3" and method == "DELETE":
        return httpx2.Response(200)
    return httpx2.Response(404, json={"message": "nope"})


def sdk_client() -> AsyncPlakyClient:
    return AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(api_handler)
    )


def settings(**overrides: Any) -> ServerSettings:
    defaults: dict[str, Any] = {"api_key": "plk_x"}
    defaults.update(overrides)
    return ServerSettings(**defaults)


ALL_SCOPES = frozenset({"read", "write", "destructive"})


async def test_default_is_curated_read_only() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    names = sorted(t.name for t in tools)
    assert names == [
        "plaky_execute_read_workflow",
        "plaky_find",
        "plaky_plan_mutation",
        "plaky_search_docs",
        "plaky_workspace_context",
    ]
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True


async def test_generated_mode_mounts_exactly_32_raw_tools() -> None:
    server = build_server(settings(mode="generated", scopes=ALL_SCOPES), sdk_client())
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    assert len(tools) == 32
    assert all(t.name.startswith("plaky_") for t in tools)
    assert len({t.name for t in tools}) == 32


async def test_generated_read_scope_filters_mutations() -> None:
    server = build_server(settings(mode="generated"), sdk_client())
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    assert len(tools) == 17  # the seventeen read operations
    for tool in tools:
        assert tool.annotations is not None and tool.annotations.read_only_hint


async def test_all_mode_excludes_compat_dispatcher_by_default() -> None:
    server = build_server(settings(mode="all", scopes=ALL_SCOPES), sdk_client())
    async with Client(server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
    assert len(names) == 38
    assert "plaky_execute_workflow" not in names

    compat = build_server(
        settings(mode="all", scopes=ALL_SCOPES, enable_compat_workflow=True), sdk_client()
    )
    async with Client(compat) as client:
        names = {t.name for t in (await client.list_tools()).tools}
    assert "plaky_execute_workflow" in names
    assert len(names) == 39


async def test_every_tool_has_title_description_and_hints() -> None:
    server = build_server(
        settings(mode="all", scopes=ALL_SCOPES, enable_compat_workflow=True), sdk_client()
    )
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    for tool in tools:
        assert tool.title, tool.name
        assert tool.description and len(tool.description) >= 10, tool.name
        assert len(tool.name) <= 64
        annotations = tool.annotations
        assert annotations is not None, tool.name
        for hint in ("read_only_hint", "destructive_hint", "idempotent_hint", "open_world_hint"):
            assert isinstance(getattr(annotations, hint), bool), tool.name
        assert tool.input_schema.get("additionalProperties") is False, tool.name
        assert tool.output_schema is not None, tool.name


async def test_unknown_arguments_fail_validation() -> None:
    server = build_server(settings(mode="generated"), sdk_client())
    async with Client(server) as client:
        result = await client.call_tool("plaky_list_spaces", {"bogus": 1})
    assert result.is_error


async def test_raw_success_and_error_envelope() -> None:
    server = build_server(settings(mode="generated"), sdk_client())
    async with Client(server) as client:
        ok = await client.call_tool("plaky_list_spaces", {"pageSize": 5})
        assert ok.is_error is False
        assert ok.structured_content == {"data": [{"id": 1, "title": "Alpha"}], "hasMore": False}

        missing = await client.call_tool("plaky_get_space", {"spaceId": "9"})
        assert missing.is_error is True
        error = missing.structured_content["error"]
        assert error["name"] == "PlakyNotFoundError"
        assert error["category"] == "api"
        assert error["status"] == 404
        assert error["retryable"] is False
        assert error["attempted"] is False
        assert error["mayHaveCommitted"] is False


async def test_delete_returns_ok_true_and_tracks_attempts() -> None:
    server = build_server(settings(mode="generated", scopes=ALL_SCOPES), sdk_client())
    async with Client(server) as client:
        result = await client.call_tool(
            "plaky_delete_item", {"spaceId": "1", "boardId": "7", "itemId": "3"}
        )
        assert result.structured_content == {"ok": True}

        failed = await client.call_tool(
            "plaky_delete_item", {"spaceId": "1", "boardId": "7", "itemId": "404"}
        )
        error = failed.structured_content["error"]
        assert error["attempted"] is True
        assert error["mayHaveCommitted"] is True  # post-dispatch failure is ambiguous
        assert error["phase"] == "response"


async def test_comments_list_presents_data_envelope() -> None:
    server = build_server(settings(mode="generated"), sdk_client())
    async with Client(server) as client:
        result = await client.call_tool(
            "plaky_list_item_comments", {"spaceId": "1", "boardId": "7", "itemId": "3"}
        )
    assert result.structured_content == {"data": [{"id": 5, "content": "hi"}]}


async def test_upload_rejects_non_canonical_base64_without_network() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return httpx2.Response(201, json={"id": 1})

    client_sdk = AsyncPlakyClient(api_key="plk_x", transport=httpx2.MockTransport(handler))
    server = build_server(settings(mode="generated", scopes=ALL_SCOPES), client_sdk)
    async with Client(server) as client:
        result = await client.call_tool(
            "plaky_upload_item_file",
            {
                "spaceId": "1",
                "boardId": "7",
                "itemId": "3",
                "fileBase64": "not canonical!",
                "fileName": "a.txt",
            },
        )
    assert result.is_error
    assert result.structured_content["error"]["category"] == "validation"
    assert calls == []


async def test_search_docs_and_dispatchers() -> None:
    server = build_server(settings(), sdk_client())
    async with Client(server) as client:
        docs = await client.call_tool("plaky_search_docs", {"query": "listSpaces"})
        assert docs.is_error is False
        assert any(e["id"] == "listSpaces" for e in docs.structured_content["data"])

        unknown = await client.call_tool(
            "plaky_execute_read_workflow", {"workflow": "items.create", "args": {}}
        )
        assert unknown.is_error  # read dispatcher cannot invoke mutations
        assert unknown.structured_content["error"]["category"] == "usage"

        search = await client.call_tool(
            "plaky_execute_read_workflow",
            {
                "workflow": "items.search",
                "args": {"spaceId": "1", "boardId": "7", "query": "find"},
            },
        )
        assert search.is_error is False
        assert search.structured_content["matched"] == 1


async def test_mutation_dispatcher_dry_run_default_and_execution() -> None:
    writes: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.method == "POST":
            writes.append(request.url.path)
        return api_handler(request)

    client_sdk = AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler)
    )
    server = build_server(
        settings(mode="curated", scopes=frozenset({"read", "write"})), client_sdk
    )
    async with Client(server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert "plaky_execute_mutation_workflow" in names

        args = {"spaceId": "1", "boardId": "7", "body": {"title": "T"}}
        dry = await client.call_tool(
            "plaky_execute_mutation_workflow", {"workflow": "items.create", "args": args}
        )
        assert dry.is_error is False
        assert dry.structured_content["dryRun"] is True
        assert writes == []

        live = await client.call_tool(
            "plaky_execute_mutation_workflow",
            {"workflow": "items.create", "args": args, "dryRun": False},
        )
        assert live.is_error is False
        assert live.structured_content["receipt"]["status"] == "completed"
        assert live.structured_content["receipt"]["mayHaveCommitted"] is False
        assert writes == ["/v1/public/spaces/1/boards/7/items"]

        bad = await client.call_tool(
            "plaky_execute_mutation_workflow", {"workflow": "nope", "args": {}}
        )
        assert bad.is_error
        assert bad.structured_content["error"]["category"] == "usage"


def test_structured_content_is_redacted() -> None:
    """API-key-shaped tokens in workspace data never reach structured output."""
    result = make_result(
        text="key plk_abc123 here",
        structured={"data": [{"title": "my key is plk_abc123"}]},
    )
    dumped = json.dumps(result.model_dump(by_alias=True, exclude_none=True))
    assert "plk_abc123" not in dumped


async def test_result_cap_returns_structured_usage_error() -> None:
    big = make_result(text="x", structured={"data": ["y" * (MAX_RESULT_BYTES + 100)]})
    assert big.is_error is True
    assert big.structured_content["error"]["category"] == "usage"
    payload = big.model_dump(by_alias=True, exclude_none=True)
    assert (
        len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
        <= MAX_RESULT_BYTES
    )


def test_result_cap_boundaries_ascii_and_multibyte() -> None:
    # Exactly at the cap passes; one byte over degrades. The envelope adds a
    # fixed overhead, computed via a probe result.
    probe = make_result(text="p", structured={"pad": ""})
    from plaky115_mcp.compaction import result_bytes

    overhead = result_bytes(probe)
    fits = MAX_RESULT_BYTES - overhead
    at_cap = make_result(text="p", structured={"pad": "a" * fits})
    assert at_cap.is_error is False
    over_cap = make_result(text="p", structured={"pad": "a" * (fits + 1)})
    assert over_cap.is_error is True
    # Multibyte: each č is 2 UTF-8 bytes (escaped JSON keeps unicode raw).
    multibyte_fits = fits // 2
    at_cap_mb = make_result(text="p", structured={"pad": "č" * multibyte_fits})
    assert at_cap_mb.is_error is False
    over_cap_mb = make_result(text="p", structured={"pad": "č" * (multibyte_fits + 1)})
    assert over_cap_mb.is_error is True


async def test_concurrent_calls_do_not_share_mutation_state() -> None:
    import asyncio

    server = build_server(settings(mode="generated", scopes=ALL_SCOPES), sdk_client())
    async with Client(server) as client:
        results = await asyncio.gather(
            client.call_tool("plaky_delete_item", {"spaceId": "1", "boardId": "7", "itemId": "3"}),
            client.call_tool(
                "plaky_delete_item", {"spaceId": "1", "boardId": "7", "itemId": "404"}
            ),
        )
    ok, failed = results
    assert ok.structured_content == {"ok": True}
    assert failed.structured_content["error"]["attempted"] is True


def test_spec_validation_gate() -> None:
    specs = build_raw_tools(sdk_client())
    assert len(specs) == 32
    for spec in specs:
        validate_spec(spec)
    destructive = {s.name for s in specs if "destructive" in s.scopes}
    assert destructive == {
        "plaky_delete_item",
        "plaky_delete_item_comment",
        "plaky_delete_item_group",
        "plaky_archive_item_group",
        "plaky_delete_item_file",
    }


def test_invalid_spec_rejected() -> None:
    from mcp.types import ToolAnnotations

    async def handler() -> None:  # pragma: no cover - never called
        return None

    with pytest.raises(ValueError, match="destructive tools require"):
        validate_spec(
            ToolSpec(
                name="plaky_bad",
                title="Bad",
                description="A destructive tool without the destructive scope.",
                handler=handler,
                scopes=frozenset({"write"}),
                annotations=ToolAnnotations(
                    read_only_hint=False,
                    destructive_hint=True,
                    idempotent_hint=False,
                    open_world_hint=True,
                ),
            )
        )
