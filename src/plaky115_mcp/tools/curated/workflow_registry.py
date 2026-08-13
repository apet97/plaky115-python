"""Curated workflow implementations and registry (eleven workflow IDs)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from mcp.server.mcpserver import Context

from plaky115.async_client import AsyncPlakyClient
from plaky115.runtime.chunks import PageCursor
from plaky115.runtime.mutations import AttemptTracker
from plaky115.runtime.upload import Base64UploadInput
from plaky115.workflows.bulk import async_bulk_update_items
from plaky115.workflows.export import async_read_item_export_chunk
from plaky115.workflows.search import async_search_items_detailed
from plaky115.workflows.workspace import async_workspace_map
from plaky115_mcp.compaction import compact_entity
from plaky115_mcp.errors import receipt_model
from plaky115_mcp.tools.curated.plan_mutation import normalize_for_operation, plan_wire

READ_WORKFLOW_IDS = ("workspace.map", "items.search", "comments.thread", "export.items")
MUTATION_WORKFLOW_IDS = (
    "items.create",
    "items.updateFields",
    "comments.add",
    "itemGroups.create",
    "itemGroups.update",
    "itemFiles.upload",
    "itemFiles.update",
)
WORKFLOW_IDS = READ_WORKFLOW_IDS + MUTATION_WORKFLOW_IDS


def _board_ref(board: Any) -> Any:
    if isinstance(board, dict):
        record = cast("dict[str, Any]", board)
        return {"id": record.get("id"), "title": record.get("title")}
    return board


def _cursor(args: dict[str, Any]) -> PageCursor | None:
    raw = args.get("cursor")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("cursor must be an object with page and index")
    return PageCursor(page=int(raw.get("page", 1)), index=int(raw.get("index", 0)))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]


async def _run_workspace_map(
    client: AsyncPlakyClient, args: dict[str, Any], ctx: Context | None
) -> tuple[str, dict[str, Any]]:
    tree = await async_workspace_map(
        client,
        max_items=int(args.get("maxItems", 200)),
        max_bytes=int(args.get("maxBytes", 65536)),
    )
    compact = [
        {
            "id": entry["id"],
            "title": entry["title"],
            "boards": [_board_ref(b) for b in entry["boards"]],
        }
        for entry in tree
    ]
    return f"workspace.map: {len(compact)} space(s)", {"data": compact}


async def _run_items_search(
    client: AsyncPlakyClient, args: dict[str, Any], ctx: Context | None
) -> tuple[str, dict[str, Any]]:
    async def progress(scanned: int, limit: int) -> None:
        if ctx is not None:
            await ctx.report_progress(scanned, limit)

    result = await async_search_items_detailed(
        client,
        space=args["spaceId"],
        board=args["boardId"],
        query=str(args.get("query", "")),
        limit=int(args.get("limit", 200)),
        cursor=_cursor(args),
        on_progress=progress,
    )
    wire: dict[str, Any] = {
        "data": [
            compact_entity(item.model_dump(mode="json", by_alias=True, exclude_none=True), "item")
            for item in result.data
        ],
        "scanned": result.scanned,
        "matched": result.matched,
        "complete": result.complete,
        "truncated": result.truncated,
    }
    if result.continuation is not None:
        wire["continuation"] = {
            "page": result.continuation.page,
            "index": result.continuation.index,
        }
    return f"items.search: {result.matched} match(es) in {result.scanned} scanned", wire


async def _run_comments_thread(
    client: AsyncPlakyClient, args: dict[str, Any], ctx: Context | None
) -> tuple[str, dict[str, Any]]:
    limit = int(args.get("limit", 100))
    page = await client.comments.list(
        space_id=args["spaceId"], board_id=args["boardId"], item_id=args["itemId"]
    )
    comments = [
        compact_entity(
            comment.model_dump(mode="json", by_alias=True, exclude_none=True), "comment"
        )
        for comment in page.data[:limit]
    ]
    return (
        f"comments.thread: {len(comments)} comment(s)",
        {"data": comments, "truncated": len(page.data) > limit},
    )


async def _run_export_items(
    client: AsyncPlakyClient, args: dict[str, Any], ctx: Context | None
) -> tuple[str, dict[str, Any]]:
    export_format = str(args.get("format", "jsonl"))
    if export_format not in ("jsonl", "csv"):
        raise ValueError("format must be jsonl or csv")
    csv_safety = str(args.get("csvSafety", "spreadsheet"))
    if csv_safety not in ("spreadsheet", "raw"):
        raise ValueError("csvSafety must be spreadsheet or raw")
    if ctx is not None:
        await ctx.report_progress(0, 1)
    chunk = await async_read_item_export_chunk(
        client,
        space=args["spaceId"],
        board=args["boardId"],
        format=export_format,  # type: ignore[arg-type]
        csv_safety=csv_safety,  # type: ignore[arg-type]
        max_items=int(args.get("maxItems", 100)),
        max_bytes=int(args.get("maxBytes", 65536)),
        cursor=_cursor(args),
        include_header=bool(args.get("includeHeader", True)),
    )
    if ctx is not None:
        await ctx.report_progress(1, 1)
    wire: dict[str, Any] = {
        "format": chunk.format,
        "body": chunk.body,
        "returned": chunk.returned,
        "bytes": chunk.bytes,
        "complete": chunk.complete,
        "truncated": chunk.truncated,
    }
    if chunk.next_cursor is not None:
        wire["continuation"] = {
            "page": chunk.next_cursor.page,
            "index": chunk.next_cursor.index,
        }
    return f"export.items: {chunk.returned} item(s), {chunk.bytes} bytes", wire


ReadRunner = Callable[
    [AsyncPlakyClient, dict[str, Any], "Context | None"],
    Awaitable[tuple[str, dict[str, Any]]],
]

READ_RUNNERS: dict[str, ReadRunner] = {
    "workspace.map": _run_workspace_map,
    "items.search": _run_items_search,
    "comments.thread": _run_comments_thread,
    "export.items": _run_export_items,
}

# Mutation workflows: (plan operation, executor)
_MUTATION_PLAN_OPERATION: dict[str, str] = {
    "items.create": "createItem",
    "items.updateFields": "updateItemFields",
    "comments.add": "createItemComment",
    "itemGroups.create": "createItemGroup",
    "itemGroups.update": "updateItemGroup",
    "itemFiles.upload": "uploadItemFile",
    "itemFiles.update": "updateItemFile",
}


async def run_mutation_workflow(
    client: AsyncPlakyClient,
    workflow: str,
    args: dict[str, Any],
    *,
    dry_run: bool,
    ctx: Context | None,
    trackers_out: list[AttemptTracker] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Validate, then (when enabled) execute exactly one mutation workflow.

    The tracker is appended to trackers_out before dispatch so a failure
    raised mid-write still reaches the caller's error envelope.
    """
    operation = _MUTATION_PLAN_OPERATION[workflow]
    body = args.get("body")
    if not isinstance(body, dict):
        raise TypeError("body must be a plain object")
    body_dict: dict[str, Any] = dict(body)  # pyright: ignore[reportUnknownArgumentType]

    if workflow == "items.updateFields" and isinstance(args.get("updates"), list):
        # Bulk form: one or many updates with durable per-item receipts.
        raise ValueError("use the updates argument only without body")

    plan = normalize_for_operation(
        operation,
        args["spaceId"],
        args["boardId"],
        body_dict,
        args.get("itemId"),
        args.get("itemCommentId"),
        args.get("itemGroupId"),
        args.get("itemFileId"),
    )
    if dry_run:
        return f"{workflow}: dry-run validated; no write performed", plan_wire(plan)

    # All local preparation happens before request_started so a preflight
    # failure never reports may_have_committed=True.
    prepared_upload = None
    if workflow == "itemFiles.upload":
        from plaky115.runtime.upload import normalize_upload

        prepared_upload = normalize_upload(
            Base64UploadInput(
                file_base64=str(body_dict.get("fileBase64", "")),
                file_name=str(body_dict.get("fileName", "")),
                content_type=(
                    str(body_dict["contentType"])
                    if body_dict.get("contentType") is not None
                    else None
                ),
            )
        )

    tracker = AttemptTracker(operation, dict(plan.target_ids))
    if trackers_out is not None:
        trackers_out.append(tracker)
    if ctx is not None:
        await ctx.report_progress(0, 1)
    tracker.request_started()
    if workflow == "items.create":
        result = await client.items.create(
            space_id=args["spaceId"], board_id=args["boardId"], body=dict(plan.body)
        )
    elif workflow == "items.updateFields":
        result = await client.items.update_fields(
            space_id=args["spaceId"],
            board_id=args["boardId"],
            item_id=args["itemId"],
            body=dict(plan.body),
        )
    elif workflow == "comments.add":
        result = await client.comments.create(
            space_id=args["spaceId"],
            board_id=args["boardId"],
            item_id=args["itemId"],
            body=dict(plan.body),
        )
    elif workflow == "itemGroups.create":
        result = await client.item_groups.create(
            space_id=args["spaceId"], board_id=args["boardId"], body=dict(plan.body)
        )
    elif workflow == "itemGroups.update":
        result = await client.item_groups.update(
            space_id=args["spaceId"],
            board_id=args["boardId"],
            item_group_id=args["itemGroupId"],
            body=dict(plan.body),
        )
    elif workflow == "itemFiles.upload":
        assert prepared_upload is not None
        result = await client.item_files.upload(
            space_id=args["spaceId"],
            board_id=args["boardId"],
            item_id=args["itemId"],
            file=prepared_upload.data,
            file_name=prepared_upload.file_name,
            content_type=prepared_upload.media_type,
        )
    else:  # itemFiles.update
        result = await client.item_files.update(
            space_id=args["spaceId"],
            board_id=args["boardId"],
            item_id=args["itemId"],
            item_file_id=args["itemFileId"],
            body=dict(plan.body),
        )
    tracker.completed()
    if ctx is not None:
        await ctx.report_progress(1, 1)
    result_any = cast("Any", result)
    entity: dict[str, Any] = (
        result_any.model_dump(mode="json", by_alias=True, exclude_none=True)
        if hasattr(result_any, "model_dump")
        else {"ok": True}
    )
    wire = {
        "operation": operation,
        "result": compact_entity(entity, "raw"),
        "receipt": receipt_model(tracker.receipt).model_dump(
            mode="json", by_alias=True, exclude_none=True
        ),
    }
    return f"{workflow}: completed", wire


async def run_bulk_update(
    client: AsyncPlakyClient,
    args: dict[str, Any],
    *,
    dry_run: bool,
    ctx: Context | None,
) -> tuple[str, dict[str, Any]]:
    async def progress(done: int, total: int) -> None:
        if ctx is not None:
            await ctx.report_progress(done, total)

    receipts = await async_bulk_update_items(
        client,
        space=args["spaceId"],
        board=args["boardId"],
        updates=args["updates"],
        dry_run=dry_run,
        on_progress=progress,
    )
    wire = {
        "dryRun": dry_run,
        "receipts": [
            receipt_model(r).model_dump(mode="json", by_alias=True, exclude_none=True)
            for r in receipts
        ],
    }
    if dry_run:
        return f"items.updateFields: dry-run validated {len(receipts)} update(s)", wire
    completed = sum(1 for r in receipts if r.status == "completed")
    return f"items.updateFields: {completed}/{len(receipts)} completed", wire
