"""Authorized live write certification: 15 mutations x two surfaces.

Interlocks (not authorization; the run also needs separate current-task
authorization naming the sacrificial space/board and budget):

    PLAKY115_LIVE_WRITE=1
    PLAKY115_SMOKE_SPACE_ID=...
    PLAKY115_SMOKE_BOARD_ID=...
    PLAKY115_SMOKE_ALLOW_ARCHIVE=1   # for the archive probe

One UUID-scoped run proves these 15 mutation operations through the async
SDK and through the generated raw MCP tools, with dedicated artifacts per
surface: createItem, deleteItem, updateItemField, updateItemFields,
createItemComment, updateItemComment, deleteItemComment,
replaceCommentReactions, createItemGroup, updateItemGroup,
deleteItemGroup, archiveItemGroup, uploadItemFile, updateItemFile,
deleteItemFile.

Writes are never retried. Every artifact is tracked immediately after
creation. Cleanup runs in finally/SIGINT/SIGTERM, sweeps all pages for the
marker, and the gate requires tracked artifacts 0 and discovered leftovers
0. An archived group that cannot be deleted fails certification and is
reported by exact ID for manual recovery.
"""

from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
import asyncio
import base64
import json
import os
import signal
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any

MUTATION_OPERATIONS = [
    "createItemGroup",
    "updateItemGroup",
    "createItem",
    "updateItemField",
    "updateItemFields",
    "createItemComment",
    "updateItemComment",
    "replaceCommentReactions",
    "deleteItemComment",
    "uploadItemFile",
    "updateItemFile",
    "deleteItemFile",
    "deleteItem",
    "archiveItemGroup",
    "deleteItemGroup",
]

FIELD_KEY = "number-1"  # NUMBER field on the sacrificial board
FIELD_VALUE = 115


@dataclass
class Receipt:
    surface: str
    operation: str
    outcome: str  # PASS | FAIL
    note: str = ""


@dataclass
class Tracked:
    """Artifact ledger; IDs recorded immediately after each creation."""

    items: list[str] = field(default_factory=lambda: [])
    groups: list[str] = field(default_factory=lambda: [])
    archived_groups: list[str] = field(default_factory=lambda: [])
    quarantined: list[str] = field(default_factory=lambda: [])

    def open_count(self) -> int:
        return len(self.items) + len(self.groups) + len(self.archived_groups)


def _interlocks() -> tuple[str, str]:
    missing = [
        name
        for name in (
            "PLAKY115_API_KEY",
            "PLAKY115_LIVE_WRITE",
            "PLAKY115_SMOKE_SPACE_ID",
            "PLAKY115_SMOKE_BOARD_ID",
            "PLAKY115_SMOKE_ALLOW_ARCHIVE",
        )
        if not os.environ.get(name, "").strip()
    ]
    for name in ("PLAKY115_API_KEY",):
        print(f"{name}: {'set' if name not in missing else 'unset'}", file=sys.stderr)
    if missing or os.environ.get("PLAKY115_LIVE_WRITE") != "1":
        print(
            "BLOCKED_EXTERNAL: live write interlocks missing: "
            f"{missing or 'PLAKY115_LIVE_WRITE!=1'}",
            file=sys.stderr,
        )
        raise SystemExit(3)
    return os.environ["PLAKY115_SMOKE_SPACE_ID"], os.environ["PLAKY115_SMOKE_BOARD_ID"]


class SdkSurface:
    """Mutations through AsyncPlakyClient."""

    name = "async-sdk"

    def __init__(self, client: Any, space_id: str, board_id: str) -> None:
        self.client = client
        self.space = space_id
        self.board = board_id

    async def create_group(self, title: str) -> str:
        group = await self.client.item_groups.create(
            space_id=self.space, board_id=self.board, body={"title": title, "color": "#AABBCC"}
        )
        return str(group.id)

    async def update_group(self, group_id: str, title: str) -> None:
        await self.client.item_groups.update(
            space_id=self.space,
            board_id=self.board,
            item_group_id=group_id,
            body={"title": title, "color": "#22CC88", "ranking": "zzzzz"},
        )

    async def create_item(self, title: str, group_id: str) -> str:
        item = await self.client.items.create(
            space_id=self.space, board_id=self.board, body={"title": title, "groupId": group_id}
        )
        return str(item.id)

    async def update_field(self, item_id: str) -> None:
        await self.client.items.update_field(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            item_field_key=FIELD_KEY,
            body={"value": FIELD_VALUE},
        )

    async def update_fields(self, item_id: str) -> None:
        await self.client.items.update_fields(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            body={FIELD_KEY: FIELD_VALUE + 1},
        )

    async def create_comment(self, item_id: str, text: str) -> str:
        comment = await self.client.comments.create(
            space_id=self.space, board_id=self.board, item_id=item_id, body={"text": text}
        )
        return str(comment.id)

    async def update_comment(self, item_id: str, comment_id: str, text: str) -> None:
        await self.client.comments.update(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            item_comment_id=comment_id,
            body={"text": text},
        )

    async def replace_reactions(self, item_id: str, comment_id: str) -> None:
        await self.client.reactions.replace(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            item_comment_id=comment_id,
            body={"reactions": [{"value": "1f44d"}]},
        )

    async def delete_comment(self, item_id: str, comment_id: str) -> None:
        await self.client.comments.delete(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            item_comment_id=comment_id,
        )

    async def upload_file(self, item_id: str, file_name: str) -> str:
        file = await self.client.item_files.upload(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            file=b"plaky115 live write probe",
            file_name=file_name,
            content_type="text/plain",
        )
        return str(file.id)

    async def observe_file(self, item_id: str, file_id: str) -> None:
        """Read prerequisites after upload; not counted as mutation coverage."""
        await self.client.item_files.get(
            space_id=self.space, board_id=self.board, item_id=item_id, item_file_id=file_id
        )
        download = await self.client.item_files.get_download(
            space_id=self.space, board_id=self.board, item_id=item_id, item_file_id=file_id
        )
        url = getattr(download, "url", "") or ""
        assert url.startswith("https"), "signed URL must be HTTPS"  # in memory only

    async def update_file(self, item_id: str, file_id: str, name: str) -> None:
        await self.client.item_files.update(
            space_id=self.space,
            board_id=self.board,
            item_id=item_id,
            item_file_id=file_id,
            body={"name": name},
        )

    async def delete_file(self, item_id: str, file_id: str) -> None:
        await self.client.item_files.delete(
            space_id=self.space, board_id=self.board, item_id=item_id, item_file_id=file_id
        )

    async def delete_item(self, item_id: str) -> None:
        await self.client.items.delete(space_id=self.space, board_id=self.board, item_id=item_id)

    async def archive_group(self, group_id: str) -> None:
        await self.client.item_groups.archive(
            space_id=self.space, board_id=self.board, item_group_id=group_id
        )

    async def delete_group(self, group_id: str) -> None:
        await self.client.item_groups.delete(
            space_id=self.space, board_id=self.board, item_group_id=group_id
        )


class McpSurface:
    """The same mutations through generated raw MCP tools (in-memory client)."""

    name = "raw-mcp"

    def __init__(self, mcp_client: Any, space_id: str, board_id: str) -> None:
        self.mcp = mcp_client
        self.space = space_id
        self.board = board_id

    async def _call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        result = await self.mcp.call_tool(tool, args)
        if result.is_error:
            detail = (result.structured_content or {}).get("error", {})
            raise RuntimeError(f"{tool}: {detail.get('name')}: {detail.get('message')}")
        return result.structured_content or {}

    async def create_group(self, title: str) -> str:
        out = await self._call(
            "plaky_create_item_group",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "body": {"title": title, "color": "#AABBCC"},
            },
        )
        return str(out["id"])

    async def update_group(self, group_id: str, title: str) -> None:
        await self._call(
            "plaky_update_item_group",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemGroupId": group_id,
                "body": {"title": title, "color": "#22CC88", "ranking": "zzzzy"},
            },
        )

    async def create_item(self, title: str, group_id: str) -> str:
        out = await self._call(
            "plaky_create_item",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "body": {"title": title, "groupId": group_id},
            },
        )
        return str(out["id"])

    async def update_field(self, item_id: str) -> None:
        await self._call(
            "plaky_update_item_field",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemFieldKey": FIELD_KEY,
                "body": {"value": FIELD_VALUE},
            },
        )

    async def update_fields(self, item_id: str) -> None:
        await self._call(
            "plaky_update_item_fields",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "body": {FIELD_KEY: FIELD_VALUE + 2},
            },
        )

    async def create_comment(self, item_id: str, text: str) -> str:
        out = await self._call(
            "plaky_create_item_comment",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "body": {"text": text},
            },
        )
        return str(out["id"])

    async def update_comment(self, item_id: str, comment_id: str, text: str) -> None:
        await self._call(
            "plaky_update_item_comment",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemCommentId": comment_id,
                "body": {"text": text},
            },
        )

    async def replace_reactions(self, item_id: str, comment_id: str) -> None:
        await self._call(
            "plaky_replace_comment_reactions",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemCommentId": comment_id,
                "body": {"reactions": [{"value": "1f44d"}]},
            },
        )

    async def delete_comment(self, item_id: str, comment_id: str) -> None:
        await self._call(
            "plaky_delete_item_comment",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemCommentId": comment_id,
            },
        )

    async def upload_file(self, item_id: str, file_name: str) -> str:
        out = await self._call(
            "plaky_upload_item_file",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "fileBase64": base64.b64encode(b"plaky115 live write probe").decode(),
                "fileName": file_name,
                "contentType": "text/plain",
            },
        )
        return str(out["id"])

    async def observe_file(self, item_id: str, file_id: str) -> None:
        await self._call(
            "plaky_get_item_file",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemFileId": file_id,
            },
        )
        await self._call(
            "plaky_get_item_file_download",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemFileId": file_id,
            },
        )

    async def update_file(self, item_id: str, file_id: str, name: str) -> None:
        await self._call(
            "plaky_update_item_file",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemFileId": file_id,
                "body": {"name": name},
            },
        )

    async def delete_file(self, item_id: str, file_id: str) -> None:
        await self._call(
            "plaky_delete_item_file",
            {
                "spaceId": self.space,
                "boardId": self.board,
                "itemId": item_id,
                "itemFileId": file_id,
            },
        )

    async def delete_item(self, item_id: str) -> None:
        await self._call(
            "plaky_delete_item",
            {"spaceId": self.space, "boardId": self.board, "itemId": item_id},
        )

    async def archive_group(self, group_id: str) -> None:
        await self._call(
            "plaky_archive_item_group",
            {"spaceId": self.space, "boardId": self.board, "itemGroupId": group_id},
        )

    async def delete_group(self, group_id: str) -> None:
        await self._call(
            "plaky_delete_item_group",
            {"spaceId": self.space, "boardId": self.board, "itemGroupId": group_id},
        )


async def _settled(call: Any, *args: Any, **kwargs: Any) -> Any:
    """Run one mutation with bounded 409 handling.

    Plaky's optimistic concurrency can reject rapid successive updates with
    an explicit 409 ("refresh and try again"). A 409 is a definitive
    rejection - the write did not commit - so one fresh attempt after a
    settle delay is not a retry of an ambiguous write. Ambiguous outcomes
    (timeouts, disconnects) are never retried.
    """
    from plaky115 import PlakyConflictError

    for attempt in range(3):
        try:
            return await call(*args, **kwargs)
        except PlakyConflictError:
            if attempt == 2:
                raise
            await asyncio.sleep(1.5)
        except RuntimeError as exc:
            # MCP tool failures arrive as structured envelopes re-raised as
            # RuntimeError; only explicit conflict rejections are re-attempted.
            if "ConflictError" not in str(exc) or attempt == 2:
                raise
            await asyncio.sleep(1.5)
    raise AssertionError("unreachable")


async def run_surface(
    surface: Any, marker: str, tracked: Tracked, receipts: list[Receipt]
) -> None:
    """One full 15-operation pass with dedicated artifacts for this surface."""
    tag = f"{marker}-{surface.name}"

    def record(operation: str, note: str = "") -> None:
        receipts.append(Receipt(surface.name, operation, "PASS", note))

    # Group A: create/update, deleted at the end (deleteItemGroup proof).
    group_a = await surface.create_group(f"{tag} group A")
    tracked.groups.append(group_a)
    record("createItemGroup")
    await _settled(surface.update_group, group_a, f"{tag} group A updated")
    record("updateItemGroup")

    item_id = await surface.create_item(f"{tag} item", group_a)
    tracked.items.append(item_id)
    record("createItem")
    await asyncio.sleep(1.0)  # let the new item settle before patching
    await _settled(surface.update_field, item_id)
    record("updateItemField")
    await _settled(surface.update_fields, item_id)
    record("updateItemFields")

    comment_id = await _settled(surface.create_comment, item_id, f"{tag} comment")
    record("createItemComment")
    await _settled(surface.update_comment, item_id, comment_id, f"{tag} comment edited")
    record("updateItemComment")
    await _settled(surface.replace_reactions, item_id, comment_id)
    record("replaceCommentReactions")
    await surface.delete_comment(item_id, comment_id)
    record("deleteItemComment")

    file_id = await _settled(surface.upload_file, item_id, f"{tag}.txt")
    record("uploadItemFile")
    await surface.observe_file(item_id, file_id)  # read prerequisite only
    await _settled(surface.update_file, item_id, file_id, f"{tag}-renamed.txt")
    record("updateItemFile")
    await surface.delete_file(item_id, file_id)
    record("deleteItemFile")

    await surface.delete_item(item_id)
    tracked.items.remove(item_id)
    record("deleteItem")

    # Group B: dedicated archive probe (bounded setup call), then recovery.
    group_b = await surface.create_group(f"{tag} group B (archive probe)")
    tracked.groups.append(group_b)
    await surface.archive_group(group_b)
    tracked.groups.remove(group_b)
    tracked.archived_groups.append(group_b)
    record("archiveItemGroup")
    try:
        await surface.delete_group(group_b)
        tracked.archived_groups.remove(group_b)
    except Exception as exc:  # archived group may be undeletable
        tracked.archived_groups.remove(group_b)
        tracked.quarantined.append(group_b)
        receipts.append(
            Receipt(surface.name, "archived-group-recovery", "FAIL", f"{type(exc).__name__}")
        )

    await surface.delete_group(group_a)
    tracked.groups.remove(group_a)
    record("deleteItemGroup")


async def cleanup(sdk: SdkSurface, marker: str, tracked: Tracked) -> tuple[int, int]:
    """Delete every tracked artifact, then sweep all pages for the marker."""
    for item_id in list(tracked.items):
        try:
            await sdk.delete_item(item_id)
            tracked.items.remove(item_id)
        except Exception:
            pass
    for group_id in list(tracked.groups):
        try:
            await sdk.delete_group(group_id)
            tracked.groups.remove(group_id)
        except Exception:
            pass
    for group_id in list(tracked.archived_groups):
        try:
            await sdk.delete_group(group_id)
            tracked.archived_groups.remove(group_id)
        except Exception:
            tracked.archived_groups.remove(group_id)
            tracked.quarantined.append(group_id)

    leftovers = 0
    items = await sdk.client.items.list_all(space_id=sdk.space, board_id=sdk.board)
    for item in items:
        if marker in (item.title or ""):
            leftovers += 1
            try:
                await sdk.delete_item(str(item.id))
                leftovers -= 1
            except Exception:
                pass
    groups = await sdk.client.item_groups.list_all(space_id=sdk.space, board_id=sdk.board)
    for group in groups:
        if marker in (group.title or ""):
            leftovers += 1
            try:
                await sdk.delete_group(str(group.id))
                leftovers -= 1
            except Exception:
                pass
    return tracked.open_count(), leftovers


async def main_async() -> int:
    space_id, board_id = _interlocks()
    marker = f"plk115-{uuid.uuid4().hex[:12]}"
    print(f"run marker: {marker}", file=sys.stderr)

    from mcp.client import Client

    from plaky115 import AsyncPlakyClient
    from plaky115_mcp.config import ServerSettings
    from plaky115_mcp.server import build_server

    key = os.environ["PLAKY115_API_KEY"]
    base_url = os.environ.get("PLAKY115_BASE_URL") or "https://api.plaky.com"
    receipts: list[Receipt] = []
    tracked = Tracked()

    client = AsyncPlakyClient(api_key=key, server_url=base_url)
    sdk = SdkSurface(client, space_id, board_id)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)

    failure: str | None = None
    try:
        await run_surface(sdk, marker, tracked, receipts)
        if stop.is_set():
            raise RuntimeError("interrupted")

        settings = ServerSettings(
            api_key=key,
            server_url=base_url,
            mode="generated",
            scopes=frozenset({"read", "write", "destructive"}),
        )
        server = build_server(settings, client)
        async with Client(server) as mcp_client:
            mcp = McpSurface(mcp_client, space_id, board_id)
            await run_surface(mcp, marker, tracked, receipts)
    except* Exception as group:
        causes: list[str] = []

        def _flatten(err: BaseException) -> None:
            if isinstance(err, BaseExceptionGroup):
                for sub in err.exceptions:
                    _flatten(sub)
            else:
                causes.append(f"{type(err).__name__}: {err}")

        _flatten(group)
        failure = "; ".join(causes[:3])
    finally:
        open_count, leftovers = await cleanup(sdk, marker, tracked)
        await client.aclose()

    print(json.dumps([receipt.__dict__ for receipt in receipts], indent=1))
    summary: dict[str, Any] = {
        "marker": marker,
        "tracked_open": open_count,
        "discovered_leftovers": leftovers,
        "quarantined_archived_groups": tracked.quarantined,
        "failure": failure,
    }
    for surface_name in ("async-sdk", "raw-mcp"):
        passed = {
            receipt.operation
            for receipt in receipts
            if receipt.surface == surface_name and receipt.outcome == "PASS"
        }
        summary[surface_name] = f"{len(passed & set(MUTATION_OPERATIONS))}/15"
    print(json.dumps(summary, indent=1))

    ok = (
        failure is None
        and open_count == 0
        and leftovers == 0
        and not tracked.quarantined
        and all(summary[s] == "15/15" for s in ("async-sdk", "raw-mcp"))
    )
    print("WRITE GATE:", "ACCEPT" if ok else "REJECT")
    return 0 if ok else 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
