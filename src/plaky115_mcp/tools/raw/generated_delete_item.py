# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for deleteItem: Delete an item."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.runtime.mutations import AttemptTracker
from plaky115_mcp.compaction import (
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import OkOutput
from plaky115_mcp.registry import ToolSpec


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def delete_item(
        spaceId: int | str,
        boardId: int | str,
        itemId: int | str,
    ) -> Annotated[CallToolResult, OkOutput]:
        tracker = AttemptTracker(
            "deleteItem", {"spaceId": str(spaceId), "boardId": str(boardId), "itemId": str(itemId)}
        )
        try:
            tracker.request_started()
            result = await client.items.delete(space_id=spaceId, board_id=boardId, item_id=itemId)
            tracker.completed()
            del result
            wire = {"ok": True}
            text = "deleteItem: ok"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, tracker)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_delete_item",
        title="Delete item",
        description="Delete an item",
        handler=delete_item,
        scopes=frozenset({"write", "destructive"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="raw",
    )
