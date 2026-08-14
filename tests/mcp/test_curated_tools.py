"""Curated tool coverage: find, plan_mutation, workflows, compat, envelope."""

from typing import Any

import httpx2
import pytest
from mcp.client import Client

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import (
    PlakyAmbiguousMatchError,
    PlakyConnectionError,
    PlakyDecodeError,
    PlakyOutputLimitError,
    PlakyPartialMutationError,
    PlakyRateLimitError,
    PlakyTimeoutError,
    UploadValidationError,
)
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.errors import error_envelope, internal_error
from plaky115_mcp.server import build_server

pytestmark = pytest.mark.anyio

FILE_B64 = "aGVsbG8="  # "hello"


def handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    method = request.method
    if path == "/v1/public/spaces" and method == "GET":
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
        return httpx2.Response(200, json={"id": 7, "title": "B", "fields": []})
    if path == "/v1/public/spaces/1/boards/7/items" and method == "GET":
        return httpx2.Response(
            200, json={"data": [{"id": 3, "title": "Find me"}], "hasMore": False}
        )
    if path == "/v1/public/spaces/1/boards/7/items/3/comments" and method == "GET":
        return httpx2.Response(200, json=[{"id": 5, "content": "hi"}])
    if path == "/v1/public/users":
        return httpx2.Response(
            200, json={"data": [{"id": 5, "name": "Ada", "email": "a@x.com"}], "hasMore": False}
        )
    if path == "/v1/public/teams":
        return httpx2.Response(200, json={"data": [{"id": 9, "title": "Team"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7/item-groups" and method == "GET":
        return httpx2.Response(200, json={"data": [{"id": 55, "title": "G"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7/item-groups" and method == "POST":
        return httpx2.Response(201, json={"id": 56, "title": "New"})
    if path == "/v1/public/spaces/1/boards/7/item-groups/55" and method == "PUT":
        return httpx2.Response(200, json={"id": 55, "title": "Updated"})
    if path == "/v1/public/spaces/1/boards/7/items/3/files" and method == "GET":
        return httpx2.Response(200, json=[{"id": 66, "name": "f.txt"}])
    if path == "/v1/public/spaces/1/boards/7/items/3/files" and method == "POST":
        return httpx2.Response(201, json={"id": 67, "name": "up.txt"})
    if path == "/v1/public/spaces/1/boards/7/items/3/files/66" and method == "PUT":
        return httpx2.Response(200, json={"id": 66, "name": "renamed.txt"})
    if path == "/v1/public/spaces/1/boards/7/items/3/comments" and method == "POST":
        return httpx2.Response(200, json={"id": 6, "content": "added"})
    if path == "/v1/public/spaces/1/boards/7/items/3/fields" and method == "PATCH":
        return httpx2.Response(200, json={"id": 3, "title": "Updated"})
    return httpx2.Response(404, json={"message": "nope"})


def make_server(**overrides: Any):
    defaults: dict[str, Any] = {
        "api_key": "plk_x",
        "mode": "curated",
        "scopes": frozenset({"read", "write"}),
        "enable_compat_workflow": True,
    }
    defaults.update(overrides)
    sdk = AsyncPlakyClient(api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(handler))
    return build_server(ServerSettings(**defaults), sdk)


async def test_find_all_kinds() -> None:
    async with Client(make_server()) as client:
        for kind, args, expected_id in [
            ("space", {}, 1),
            ("board", {"spaceId": "1"}, 7),
            ("item", {"spaceId": "1", "boardId": "7"}, 3),
            ("user", {}, 5),
            ("team", {}, 9),
            ("itemGroup", {"spaceId": "1", "boardId": "7"}, 55),
            ("itemFile", {"spaceId": "1", "boardId": "7", "itemId": "3"}, 66),
        ]:
            query = {
                "space": "alpha",
                "board": "b",
                "item": "find",
                "user": "ada",
                "team": "team",
                "itemGroup": "g",
                "itemFile": "f.txt",
            }[kind]
            result = await client.call_tool("plaky_find", {"kind": kind, "query": query, **args})
            assert result.is_error is False, (kind, result.structured_content)
            assert result.structured_content["id"] == expected_id, kind

        bad_kind = await client.call_tool("plaky_find", {"kind": "nope", "query": "x"})
        assert bad_kind.structured_content["error"]["category"] == "usage"
        missing_scope = await client.call_tool("plaky_find", {"kind": "board", "query": "b"})
        assert missing_scope.structured_content["error"]["category"] == "usage"


async def test_plan_mutation_operations() -> None:
    writes: list[str] = []

    def counting_handler(request: httpx2.Request) -> httpx2.Response:
        if request.method != "GET":
            writes.append(f"{request.method} {request.url.path}")
        return handler(request)

    sdk = AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(counting_handler)
    )
    server = build_server(
        ServerSettings(
            api_key="plk_x",
            mode="curated",
            scopes=frozenset({"read", "write"}),
            enable_compat_workflow=True,
        ),
        sdk,
    )
    async with Client(server) as client:
        cases: list[tuple[str, dict[str, Any]]] = [
            ("createItem", {"body": {"title": "T"}}),
            ("updateItemFields", {"itemId": "3", "body": {"s": "1"}}),
            ("createItemComment", {"itemId": "3", "body": {"text": "hi"}}),
            (
                "updateItemComment",
                {"itemId": "3", "itemCommentId": "5", "body": {"text": "e"}},
            ),
            ("createItemGroup", {"body": {"title": "G", "color": "#AABBCC"}}),
            (
                "updateItemGroup",
                {"itemGroupId": "55", "body": {"title": "G", "color": "#AABBCC", "ranking": "a"}},
            ),
            ("updateItemFile", {"itemId": "3", "itemFileId": "66", "body": {"name": "n.txt"}}),
            (
                "uploadItemFile",
                {"itemId": "3", "body": {"fileBase64": FILE_B64, "fileName": "up.txt"}},
            ),
        ]
        for operation, extra in cases:
            result = await client.call_tool(
                "plaky_plan_mutation",
                {"operation": operation, "spaceId": "1", "boardId": "7", **extra},
            )
            assert result.is_error is False, (operation, result.structured_content)
            plan = result.structured_content
            assert plan["dryRun"] is True and plan["writeCount"] == 1
            if operation == "uploadItemFile":
                assert "fileBase64" not in str(plan)
                assert plan["upload"]["decodedBytes"] == 5
        assert writes == []

        invalid = await client.call_tool(
            "plaky_plan_mutation",
            {"operation": "createItemGroup", "spaceId": "1", "boardId": "7", "body": {}},
        )
        assert invalid.structured_content["error"]["category"] == "validation"
        unknown = await client.call_tool(
            "plaky_plan_mutation",
            {"operation": "deleteEverything", "spaceId": "1", "boardId": "7", "body": {}},
        )
        assert unknown.structured_content["error"]["category"] == "usage"
        missing = await client.call_tool(
            "plaky_plan_mutation",
            {"operation": "updateItemFields", "spaceId": "1", "boardId": "7", "body": {}},
        )
        assert missing.structured_content["error"]["category"] == "validation"


async def test_read_workflows() -> None:
    async with Client(make_server()) as client:
        tree = await client.call_tool(
            "plaky_execute_read_workflow", {"workflow": "workspace.map", "args": {}}
        )
        assert tree.structured_content["data"][0]["boards"] == [{"id": 7, "title": "B"}]

        thread = await client.call_tool(
            "plaky_execute_read_workflow",
            {
                "workflow": "comments.thread",
                "args": {"spaceId": "1", "boardId": "7", "itemId": "3"},
            },
        )
        assert thread.structured_content["data"][0]["content"] == "hi"

        export = await client.call_tool(
            "plaky_execute_read_workflow",
            {"workflow": "export.items", "args": {"spaceId": "1", "boardId": "7"}},
        )
        assert export.structured_content["complete"] is True
        assert export.structured_content["format"] == "jsonl"

        csv_export = await client.call_tool(
            "plaky_execute_read_workflow",
            {
                "workflow": "export.items",
                "args": {"spaceId": "1", "boardId": "7", "format": "csv"},
            },
        )
        assert csv_export.structured_content["body"].startswith("id,title")

        bad_format = await client.call_tool(
            "plaky_execute_read_workflow",
            {
                "workflow": "export.items",
                "args": {"spaceId": "1", "boardId": "7", "format": "xml"},
            },
        )
        assert bad_format.is_error

        # A csvSafety typo must fail, not silently disable formula protection.
        bad_safety = await client.call_tool(
            "plaky_execute_read_workflow",
            {
                "workflow": "export.items",
                "args": {
                    "spaceId": "1",
                    "boardId": "7",
                    "format": "csv",
                    "csvSafety": "Spreadsheet",
                },
            },
        )
        assert bad_safety.is_error
        assert bad_safety.structured_content["error"]["category"] == "validation"


async def test_workspace_context_tool() -> None:
    async with Client(make_server()) as client:
        result = await client.call_tool("plaky_workspace_context", {})
        assert result.structured_content["data"][0]["id"] == 1


async def test_mutation_workflows_execute() -> None:
    async with Client(make_server()) as client:
        cases: list[tuple[str, dict[str, Any]]] = [
            (
                "comments.add",
                {"spaceId": "1", "boardId": "7", "itemId": "3", "body": {"text": "hi"}},
            ),
            (
                "itemGroups.create",
                {"spaceId": "1", "boardId": "7", "body": {"title": "G", "color": "#AABBCC"}},
            ),
            (
                "itemGroups.update",
                {
                    "spaceId": "1",
                    "boardId": "7",
                    "itemGroupId": "55",
                    "body": {"title": "G", "color": "#AABBCC", "ranking": "a"},
                },
            ),
            (
                "itemFiles.upload",
                {
                    "spaceId": "1",
                    "boardId": "7",
                    "itemId": "3",
                    "body": {"fileBase64": FILE_B64, "fileName": "up.txt"},
                },
            ),
            (
                "itemFiles.update",
                {
                    "spaceId": "1",
                    "boardId": "7",
                    "itemId": "3",
                    "itemFileId": "66",
                    "body": {"name": "renamed.txt"},
                },
            ),
            (
                "items.updateFields",
                {"spaceId": "1", "boardId": "7", "itemId": "3", "body": {"s": "1"}},
            ),
        ]
        for workflow, args in cases:
            live = await client.call_tool(
                "plaky_execute_mutation_workflow",
                {"workflow": workflow, "args": args, "dryRun": False},
            )
            assert live.is_error is False, (workflow, live.structured_content)
            assert live.structured_content["receipt"]["status"] == "completed", workflow

        bulk = await client.call_tool(
            "plaky_execute_mutation_workflow",
            {
                "workflow": "items.updateFields",
                "args": {
                    "spaceId": "1",
                    "boardId": "7",
                    "updates": [{"item_id": "3", "body": {"s": "1"}}],
                },
                "dryRun": False,
            },
        )
        assert bulk.structured_content["receipts"][0]["status"] == "completed"
        assert bulk.structured_content["dryRun"] is False


async def test_bulk_update_dry_run_is_labeled() -> None:
    """A bulk dry-run must say so instead of reading like a failed live run."""
    async with Client(make_server()) as client:
        planned = await client.call_tool(
            "plaky_execute_mutation_workflow",
            {
                "workflow": "items.updateFields",
                "args": {
                    "spaceId": "1",
                    "boardId": "7",
                    "updates": [{"item_id": "3", "body": {"s": "1"}}],
                },
            },
        )
        assert planned.is_error is False
        assert planned.structured_content["dryRun"] is True
        assert planned.structured_content["receipts"][0]["status"] == "planned"
        from mcp.types import TextContent

        first = planned.content[0]
        assert isinstance(first, TextContent)
        assert "dry-run" in first.text, first.text


def make_failing_write_server(**overrides: Any):
    """Server whose transport fails every non-GET request after dispatch."""

    def failing_handler(request: httpx2.Request) -> httpx2.Response:
        if request.method != "GET":
            raise httpx2.ReadTimeout("read timed out", request=request)
        return handler(request)

    defaults: dict[str, Any] = {
        "api_key": "plk_x",
        "mode": "curated",
        "scopes": frozenset({"read", "write"}),
        "enable_compat_workflow": True,
    }
    defaults.update(overrides)
    sdk = AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(failing_handler)
    )
    return build_server(ServerSettings(**defaults), sdk)


@pytest.mark.parametrize("tool", ["plaky_execute_mutation_workflow", "plaky_execute_workflow"])
async def test_failed_live_mutation_reports_ambiguous_receipt(tool: str) -> None:
    """A failure after dispatch must report attempted/mayHaveCommitted, not preflight."""
    async with Client(make_failing_write_server()) as client:
        result = await client.call_tool(
            tool,
            {
                "workflow": "items.create",
                "args": {"spaceId": "1", "boardId": "7", "body": {"title": "T"}},
                "dryRun": False,
            },
        )
        assert result.is_error is True
        error = result.structured_content["error"]
        assert error["attempted"] is True, error
        assert error["mayHaveCommitted"] is True, error
        assert error["phase"] != "preflight", error


async def test_preflight_mutation_failure_reports_no_attempt() -> None:
    """A validation failure before dispatch must stay attempted=false/preflight."""
    async with Client(make_failing_write_server()) as client:
        result = await client.call_tool(
            "plaky_execute_mutation_workflow",
            {
                "workflow": "itemFiles.upload",
                "args": {
                    "spaceId": "1",
                    "boardId": "7",
                    "itemId": "3",
                    "body": {"fileBase64": "not-base64!!!", "fileName": "up.txt"},
                },
                "dryRun": False,
            },
        )
        assert result.is_error is True
        error = result.structured_content["error"]
        assert error["attempted"] is False, error
        assert error["mayHaveCommitted"] is False, error
        assert error["phase"] == "preflight", error


async def test_compat_dispatcher_handles_both_classes() -> None:
    async with Client(make_server()) as client:
        read = await client.call_tool(
            "plaky_execute_workflow", {"workflow": "workspace.map", "args": {}}
        )
        assert read.is_error is False
        dry = await client.call_tool(
            "plaky_execute_workflow",
            {
                "workflow": "items.create",
                "args": {"spaceId": "1", "boardId": "7", "body": {"title": "T"}},
            },
        )
        assert dry.structured_content["dryRun"] is True
        unknown = await client.call_tool(
            "plaky_execute_workflow", {"workflow": "nope", "args": {}}
        )
        assert unknown.structured_content["error"]["category"] == "usage"


def test_error_envelope_category_table() -> None:
    cases: list[tuple[BaseException, str, bool]] = [
        (
            PlakyRateLimitError(
                "r", status=429, method="GET", url="u", headers={}, retry_after_ms=1000
            ),
            "api",
            True,
        ),
        (PlakyTimeoutError(), "timeout", True),
        (PlakyConnectionError(), "connection", True),
        (PlakyDecodeError("d"), "decode", False),
        (ValueError("v"), "validation", False),
        (UploadValidationError("u", code="invalid-limit"), "validation", False),
        (PlakyOutputLimitError("bytes", 10), "usage", False),
        (PlakyAmbiguousMatchError("a", [], 0), "plaky", False),
        (RuntimeError("r"), "plaky", False),
    ]
    for error, category, retryable in cases:
        envelope = error_envelope(error)
        assert envelope.error.category == category, type(error).__name__
        assert envelope.error.retryable is retryable, type(error).__name__

    rate = error_envelope(
        PlakyRateLimitError(
            "r",
            status=429,
            method="GET",
            url="u",
            headers={},
            retry_after_ms=1000,
            request_id="rid",
            code="TOO_MANY",
        )
    )
    assert rate.error.retry_after_ms == 1000
    assert rate.error.request_id == "rid"
    assert rate.error.code == "TOO_MANY"

    from plaky115.runtime.mutations import new_receipt

    partial = error_envelope(
        PlakyPartialMutationError("p", receipts=(new_receipt("op", 0, {"a": "1"}),))
    )
    assert partial.error.receipts[0].operation == "op"

    internal = internal_error(RuntimeError("secret plk_boom"))
    assert "plk_boom" not in internal.error.message
    assert "correlation" in internal.error.message
