# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for updateItemComment: Update item comment."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.runtime.mutations import AttemptTracker
from plaky115_mcp.compaction import (
    compact_entity,
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def update_item_comment(
        spaceId: int | str,
        boardId: int | str,
        itemId: int | str,
        itemCommentId: int | str,
        body: dict[str, Any],
    ) -> Annotated[CallToolResult, EntityOutput]:
        tracker = AttemptTracker(
            "updateItemComment",
            {
                "spaceId": str(spaceId),
                "boardId": str(boardId),
                "itemId": str(itemId),
                "itemCommentId": str(itemCommentId),
            },
        )
        try:
            tracker.request_started()
            result = await client.comments.update(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                item_comment_id=itemCommentId,
                body=body,
            )
            tracker.completed()
            wire = compact_entity(
                result.model_dump(mode="json", by_alias=True, exclude_none=True), "comment"
            )
            text = f"updateItemComment: id={wire.get('id')}"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, tracker)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_update_item_comment",
        title="Update item comment",
        description="Update item comment",
        handler=update_item_comment,
        scopes=frozenset({"write"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="raw",
    )
