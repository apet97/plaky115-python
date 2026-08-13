# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for archiveItemGroup: Archive an item group."""

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
    async def archive_item_group(
        spaceId: int | str,
        boardId: int | str,
        itemGroupId: int | str,
    ) -> Annotated[CallToolResult, OkOutput]:
        tracker = AttemptTracker(
            "archiveItemGroup",
            {"spaceId": str(spaceId), "boardId": str(boardId), "itemGroupId": str(itemGroupId)},
        )
        try:
            tracker.request_started()
            result = await client.item_groups.archive(
                space_id=spaceId, board_id=boardId, item_group_id=itemGroupId
            )
            tracker.completed()
            del result
            wire = {"ok": True}
            text = "archiveItemGroup: ok"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, tracker)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_archive_item_group",
        title="Archive item group",
        description="Archive an item group",
        handler=archive_item_group,
        scopes=frozenset({"write", "destructive"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="raw",
    )
