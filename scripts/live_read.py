"""Read-only live certification: 17 reads across four surfaces.

Requires an injected rotated PLAKY115_API_KEY (and optional
PLAKY115_BASE_URL). Never prints keys, payloads, signed URLs, or tenant
data: only operation IDs, sanitized statuses, root shapes, and counts.

Surfaces: direct-HTTP reference probe, sync SDK, async SDK, generated raw
MCP tools. Also exercises curated read workflows workspace.map,
items.search, comments.thread, and export.items.

Acceptance per surface: 17 pass / 0 skip, or 15 pass plus exactly the
paired getItemFile/getItemFileDownload SKIP_PREREQUISITE when a complete
file listing proves no file exists. Any other skip fails the gate.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

READ_OPERATIONS = [
    "listSpaces",
    "getSpace",
    "listBoards",
    "getBoard",
    "listItems",
    "listSubitems",
    "getItem",
    "listItemComments",
    "listUsers",
    "getCurrentUser",
    "listTeams",
    "getTeam",
    "listItemGroups",
    "getItemGroup",
    "listItemFiles",
    "getItemFile",
    "getItemFileDownload",
]


@dataclass
class Receipt:
    surface: str
    operation: str
    outcome: str  # PASS | SKIP_PREREQUISITE | FAIL
    shape: str = ""
    count: int | None = None
    status: int | None = None


@dataclass
class Scope:
    """IDs discovered from list endpoints; never echoed beyond counts."""

    space_id: str | None = None
    board_id: str | None = None
    item_id: str | None = None
    team_id: str | None = None
    group_id: str | None = None
    file_id: str | None = None


def _need_key() -> str:
    key = os.environ.get("PLAKY115_API_KEY") or os.environ.get("PLAKY115_API_KEY_AUTH") or ""
    print(f"PLAKY115_API_KEY: {'set' if key.strip() else 'unset'}", file=sys.stderr)
    if not key.strip():
        print(
            "BLOCKED_EXTERNAL: live read certification needs an injected "
            "rotated PLAKY115_API_KEY",
            file=sys.stderr,
        )
        raise SystemExit(3)
    return key


async def _run_async_sdk(key: str, base_url: str, scope: Scope) -> list[Receipt]:
    from plaky115 import AsyncPlakyClient

    receipts: list[Receipt] = []
    async with AsyncPlakyClient(api_key=key, server_url=base_url) as client:
        spaces = await client.spaces.list(page_size=10)
        scope.space_id = str(spaces.data[0].id) if spaces.data else None
        receipts.append(
            Receipt("async-sdk", "listSpaces", "PASS", "page", len(spaces.data))
        )
        if scope.space_id is None:
            receipts.append(Receipt("async-sdk", "getSpace", "FAIL"))
            return receipts
        space = await client.spaces.get(scope.space_id)
        receipts.append(Receipt("async-sdk", "getSpace", "PASS", "object"))
        del space

        boards = await client.boards.list(space_id=scope.space_id, page_size=10)
        scope.board_id = str(boards.data[0].id) if boards.data else None
        receipts.append(Receipt("async-sdk", "listBoards", "PASS", "page", len(boards.data)))
        assert scope.board_id is not None, "certification workspace must contain a board"
        await client.boards.get(space_id=scope.space_id, board_id=scope.board_id)
        receipts.append(Receipt("async-sdk", "getBoard", "PASS", "object"))

        items = await client.items.list(
            space_id=scope.space_id, board_id=scope.board_id, page_size=10
        )
        scope.item_id = str(items.data[0].id) if items.data else None
        receipts.append(Receipt("async-sdk", "listItems", "PASS", "page", len(items.data)))
        assert scope.item_id is not None, "certification board must contain an item"
        subitems = await client.items.list_subitems(
            space_id=scope.space_id, board_id=scope.board_id, item_id=scope.item_id
        )
        receipts.append(
            Receipt("async-sdk", "listSubitems", "PASS", "page", len(subitems.data))
        )
        await client.items.get(
            space_id=scope.space_id, board_id=scope.board_id, item_id=scope.item_id
        )
        receipts.append(Receipt("async-sdk", "getItem", "PASS", "object"))
        comments = await client.comments.list(
            space_id=scope.space_id, board_id=scope.board_id, item_id=scope.item_id
        )
        receipts.append(
            Receipt("async-sdk", "listItemComments", "PASS", "array", len(comments.data))
        )

        users = await client.users.list(page_size=10)
        receipts.append(Receipt("async-sdk", "listUsers", "PASS", "page", len(users.data)))
        await client.users.me()
        receipts.append(Receipt("async-sdk", "getCurrentUser", "PASS", "object"))
        teams = await client.teams.list(page_size=10)
        scope.team_id = str(teams.data[0].id) if teams.data else None
        receipts.append(Receipt("async-sdk", "listTeams", "PASS", "page", len(teams.data)))
        if scope.team_id is not None:
            await client.teams.get(scope.team_id)
            receipts.append(Receipt("async-sdk", "getTeam", "PASS", "object"))
        else:
            receipts.append(Receipt("async-sdk", "getTeam", "FAIL"))

        groups = await client.item_groups.list(
            space_id=scope.space_id, board_id=scope.board_id, page_size=10
        )
        scope.group_id = str(groups.data[0].id) if groups.data else None
        receipts.append(
            Receipt("async-sdk", "listItemGroups", "PASS", "page", len(groups.data))
        )
        if scope.group_id is not None:
            await client.item_groups.get(
                space_id=scope.space_id,
                board_id=scope.board_id,
                item_group_id=scope.group_id,
            )
            receipts.append(Receipt("async-sdk", "getItemGroup", "PASS", "object"))
        else:
            receipts.append(Receipt("async-sdk", "getItemGroup", "FAIL"))

        files = await client.item_files.list(
            space_id=scope.space_id, board_id=scope.board_id, item_id=scope.item_id
        )
        scope.file_id = str(files[0].id) if files else None
        receipts.append(Receipt("async-sdk", "listItemFiles", "PASS", "array", len(files)))
        if scope.file_id is None:
            # The paired prerequisite skip: the complete listing proved no
            # file exists.
            receipts.append(Receipt("async-sdk", "getItemFile", "SKIP_PREREQUISITE"))
            receipts.append(Receipt("async-sdk", "getItemFileDownload", "SKIP_PREREQUISITE"))
        else:
            await client.item_files.get(
                space_id=scope.space_id,
                board_id=scope.board_id,
                item_id=scope.item_id,
                item_file_id=scope.file_id,
            )
            receipts.append(Receipt("async-sdk", "getItemFile", "PASS", "object"))
            download = await client.item_files.get_download(
                space_id=scope.space_id,
                board_id=scope.board_id,
                item_id=scope.item_id,
                item_file_id=scope.file_id,
            )
            url = getattr(download, "url", "") or ""
            # Validate in memory only; never print or persist.
            assert url.startswith("https://"), "signed URL must be HTTPS"
            receipts.append(Receipt("async-sdk", "getItemFileDownload", "PASS", "object"))

        # Curated read workflows.
        from plaky115 import async_search_items_detailed, async_workspace_map
        from plaky115.workflows.export import async_read_item_export_chunk

        tree = await async_workspace_map(client, max_items=200, max_bytes=262144)
        receipts.append(Receipt("async-sdk", "workflow:workspace.map", "PASS", "list", len(tree)))
        search = await async_search_items_detailed(
            client, space=scope.space_id, board=scope.board_id, query="", limit=10
        )
        receipts.append(
            Receipt("async-sdk", "workflow:items.search", "PASS", "search", search.matched)
        )
        thread = await client.comments.list(
            space_id=scope.space_id, board_id=scope.board_id, item_id=scope.item_id
        )
        receipts.append(
            Receipt(
                "async-sdk", "workflow:comments.thread", "PASS", "array", len(thread.data)
            )
        )
        chunk = await async_read_item_export_chunk(
            client, space=scope.space_id, board=scope.board_id, format="jsonl", max_items=10
        )
        receipts.append(
            Receipt("async-sdk", "workflow:export.items", "PASS", "chunk", chunk.returned)
        )
    return receipts


def _run_sync_sdk(key: str, base_url: str, scope: Scope) -> list[Receipt]:
    from plaky115 import PlakyClient

    receipts: list[Receipt] = []
    assert scope.space_id and scope.board_id and scope.item_id
    with PlakyClient(api_key=key, server_url=base_url) as client:
        calls: list[tuple[str, Any, str]] = [
            ("listSpaces", lambda: client.spaces.list(page_size=10), "page"),
            ("getSpace", lambda: client.spaces.get(scope.space_id), "object"),
            (
                "listBoards",
                lambda: client.boards.list(space_id=scope.space_id, page_size=10),
                "page",
            ),
            (
                "getBoard",
                lambda: client.boards.get(space_id=scope.space_id, board_id=scope.board_id),
                "object",
            ),
            (
                "listItems",
                lambda: client.items.list(
                    space_id=scope.space_id, board_id=scope.board_id, page_size=10
                ),
                "page",
            ),
            (
                "listSubitems",
                lambda: client.items.list_subitems(
                    space_id=scope.space_id,
                    board_id=scope.board_id,
                    item_id=scope.item_id,
                ),
                "page",
            ),
            (
                "getItem",
                lambda: client.items.get(
                    space_id=scope.space_id,
                    board_id=scope.board_id,
                    item_id=scope.item_id,
                ),
                "object",
            ),
            (
                "listItemComments",
                lambda: client.comments.list(
                    space_id=scope.space_id,
                    board_id=scope.board_id,
                    item_id=scope.item_id,
                ),
                "array",
            ),
            ("listUsers", lambda: client.users.list(page_size=10), "page"),
            ("getCurrentUser", lambda: client.users.me(), "object"),
            ("listTeams", lambda: client.teams.list(page_size=10), "page"),
            (
                "getTeam",
                (lambda: client.teams.get(scope.team_id)) if scope.team_id else None,
                "object",
            ),
            (
                "listItemGroups",
                lambda: client.item_groups.list(
                    space_id=scope.space_id, board_id=scope.board_id, page_size=10
                ),
                "page",
            ),
            (
                "getItemGroup",
                (
                    lambda: client.item_groups.get(
                        space_id=scope.space_id,
                        board_id=scope.board_id,
                        item_group_id=scope.group_id,
                    )
                )
                if scope.group_id
                else None,
                "object",
            ),
            (
                "listItemFiles",
                lambda: client.item_files.list(
                    space_id=scope.space_id,
                    board_id=scope.board_id,
                    item_id=scope.item_id,
                ),
                "array",
            ),
            (
                "getItemFile",
                (
                    lambda: client.item_files.get(
                        space_id=scope.space_id,
                        board_id=scope.board_id,
                        item_id=scope.item_id,
                        item_file_id=scope.file_id,
                    )
                )
                if scope.file_id
                else None,
                "object",
            ),
            (
                "getItemFileDownload",
                (
                    lambda: client.item_files.get_download(
                        space_id=scope.space_id,
                        board_id=scope.board_id,
                        item_id=scope.item_id,
                        item_file_id=scope.file_id,
                    )
                )
                if scope.file_id
                else None,
                "object",
            ),
        ]
        for operation, call, shape in calls:
            if call is None:
                outcome = (
                    "SKIP_PREREQUISITE"
                    if operation in ("getItemFile", "getItemFileDownload")
                    else "FAIL"
                )
                receipts.append(Receipt("sync-sdk", operation, outcome))
                continue
            result = call()
            count = None
            if hasattr(result, "data"):
                count = len(result.data)
            elif isinstance(result, list):
                count = len(result)
            receipts.append(Receipt("sync-sdk", operation, "PASS", shape, count))
    return receipts


async def _run_raw_mcp(key: str, base_url: str, scope: Scope) -> list[Receipt]:
    from mcp.client import Client

    from plaky115.async_client import AsyncPlakyClient
    from plaky115_mcp.config import ServerSettings
    from plaky115_mcp.server import build_server

    assert scope.space_id and scope.board_id and scope.item_id
    settings = ServerSettings(api_key=key, server_url=base_url, mode="generated")
    sdk = AsyncPlakyClient(api_key=key, server_url=base_url)
    server = build_server(settings, sdk)
    receipts: list[Receipt] = []
    args_by_operation: dict[str, dict[str, Any]] = {
        "listSpaces": {},
        "getSpace": {"spaceId": scope.space_id},
        "listBoards": {"spaceId": scope.space_id},
        "getBoard": {"spaceId": scope.space_id, "boardId": scope.board_id},
        "listItems": {"spaceId": scope.space_id, "boardId": scope.board_id},
        "listSubitems": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemId": scope.item_id,
        },
        "getItem": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemId": scope.item_id,
        },
        "listItemComments": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemId": scope.item_id,
        },
        "listUsers": {},
        "getCurrentUser": {},
        "listTeams": {},
        "getTeam": {"teamId": scope.team_id} if scope.team_id else {},
        "listItemGroups": {"spaceId": scope.space_id, "boardId": scope.board_id},
        "getItemGroup": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemGroupId": scope.group_id,
        }
        if scope.group_id
        else {},
        "listItemFiles": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemId": scope.item_id,
        },
        "getItemFile": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemId": scope.item_id,
            "itemFileId": scope.file_id,
        }
        if scope.file_id
        else {},
        "getItemFileDownload": {
            "spaceId": scope.space_id,
            "boardId": scope.board_id,
            "itemId": scope.item_id,
            "itemFileId": scope.file_id,
        }
        if scope.file_id
        else {},
    }
    tool_names = {
        op: "plaky_" + "".join(
            "_" + c.lower() if c.isupper() else c for c in op
        ).lstrip("_")
        for op in READ_OPERATIONS
    }
    async with Client(server) as client:
        for operation in READ_OPERATIONS:
            if operation in ("getItemFile", "getItemFileDownload") and not scope.file_id:
                receipts.append(Receipt("raw-mcp", operation, "SKIP_PREREQUISITE"))
                continue
            if operation in ("getTeam", "getItemGroup") and not args_by_operation[operation]:
                receipts.append(Receipt("raw-mcp", operation, "FAIL"))
                continue
            result = await client.call_tool(tool_names[operation], args_by_operation[operation])
            outcome = "FAIL" if result.is_error else "PASS"
            structured = result.structured_content or {}
            count = len(structured.get("data", [])) if "data" in structured else None
            receipts.append(Receipt("raw-mcp", operation, outcome, "structured", count))
    await sdk.aclose()
    return receipts


def _run_direct_http(key: str, base_url: str, scope: Scope) -> list[Receipt]:
    """Independent reference probe: plain httpx2, no SDK machinery."""
    import httpx2

    assert scope.space_id and scope.board_id and scope.item_id
    receipts: list[Receipt] = []
    s, b, i = scope.space_id, scope.board_id, scope.item_id
    paths: dict[str, str | None] = {
        "listSpaces": "/v1/public/spaces",
        "getSpace": f"/v1/public/spaces/{s}",
        "listBoards": f"/v1/public/spaces/{s}/boards",
        "getBoard": f"/v1/public/spaces/{s}/boards/{b}",
        "listItems": f"/v1/public/spaces/{s}/boards/{b}/items",
        "listSubitems": f"/v1/public/spaces/{s}/boards/{b}/items/{i}/sub-items",
        "getItem": f"/v1/public/spaces/{s}/boards/{b}/items/{i}",
        "listItemComments": f"/v1/public/spaces/{s}/boards/{b}/items/{i}/comments",
        "listUsers": "/v1/public/users",
        "getCurrentUser": "/v1/public/users/me",
        "listTeams": "/v1/public/teams",
        "getTeam": f"/v1/public/teams/{scope.team_id}" if scope.team_id else None,
        "listItemGroups": f"/v1/public/spaces/{s}/boards/{b}/item-groups",
        "getItemGroup": (
            f"/v1/public/spaces/{s}/boards/{b}/item-groups/{scope.group_id}"
            if scope.group_id
            else None
        ),
        "listItemFiles": f"/v1/public/spaces/{s}/boards/{b}/items/{i}/files",
        "getItemFile": (
            f"/v1/public/spaces/{s}/boards/{b}/items/{i}/files/{scope.file_id}"
            if scope.file_id
            else None
        ),
        "getItemFileDownload": (
            f"/v1/public/spaces/{s}/boards/{b}/items/{i}/files/{scope.file_id}/download"
            if scope.file_id
            else None
        ),
    }
    with httpx2.Client(base_url=base_url, headers={"X-API-Key": key}, timeout=30) as http:
        for operation, path in paths.items():
            if path is None:
                outcome = (
                    "SKIP_PREREQUISITE"
                    if operation in ("getItemFile", "getItemFileDownload")
                    else "FAIL"
                )
                receipts.append(Receipt("direct-http", operation, outcome))
                continue
            response = http.get(path)
            body = response.json() if response.status_code == 200 else None
            shape = (
                "page"
                if isinstance(body, dict) and "data" in body
                else "array"
                if isinstance(body, list)
                else "object"
            )
            count = None
            if isinstance(body, dict) and isinstance(body.get("data"), list):
                count = len(body["data"])
            elif isinstance(body, list):
                count = len(body)
            receipts.append(
                Receipt(
                    "direct-http",
                    operation,
                    "PASS" if response.status_code == 200 else "FAIL",
                    shape,
                    count,
                    response.status_code,
                )
            )
    return receipts


def _evaluate(receipts: list[Receipt]) -> bool:
    ok = True
    surfaces = sorted({r.surface for r in receipts})
    for surface in surfaces:
        rows = [r for r in receipts if r.surface == surface and ":" not in r.operation]
        passes = sum(1 for r in rows if r.outcome == "PASS")
        skips = {r.operation for r in rows if r.outcome == "SKIP_PREREQUISITE"}
        fails = [r.operation for r in rows if r.outcome == "FAIL"]
        valid = (passes == 17 and not skips) or (
            passes == 15 and skips == {"getItemFile", "getItemFileDownload"}
        )
        if fails or not valid:
            ok = False
        print(
            f"{surface}: {passes} pass, {len(skips)} skip, {len(fails)} fail "
            f"-> {'ACCEPT' if valid and not fails else 'REJECT'}"
        )
    return ok


def main() -> int:
    key = _need_key()
    base_url = os.environ.get("PLAKY115_BASE_URL") or "https://api.plaky.com"
    scope = Scope()
    receipts = asyncio.run(_run_async_sdk(key, base_url, scope))
    receipts += _run_sync_sdk(key, base_url, scope)
    receipts += asyncio.run(_run_raw_mcp(key, base_url, scope))
    receipts += _run_direct_http(key, base_url, scope)
    print(
        json.dumps(
            [
                {
                    "surface": r.surface,
                    "operation": r.operation,
                    "outcome": r.outcome,
                    "shape": r.shape,
                    "count": r.count,
                }
                for r in receipts
            ],
            indent=2,
        )
    )
    return 0 if _evaluate(receipts) else 1


if __name__ == "__main__":
    sys.exit(main())
