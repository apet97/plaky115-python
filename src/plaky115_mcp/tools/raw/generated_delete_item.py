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
from pydantic import Field

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.mutations import AttemptTracker
from plaky115_mcp.compaction import (
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import OkOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.workflow_models import CanonicalId


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def delete_item(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        itemId: Annotated[
            CanonicalId, Field(description="Represents unique item identifier across the system.")
        ],
    ) -> Annotated[CallToolResult, OkOutput]:
        tracker = AttemptTracker(
            "deleteItem", {"spaceId": str(spaceId), "boardId": str(boardId), "itemId": str(itemId)}
        )
        try:
            result = await client.items.delete(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                options=RequestOverrides(on_dispatch=tracker.request_started),
            )
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
            return error_result(
                envelope_wire(internal_error(exc, tracker)),
                "Internal server error.",
            )

    return ToolSpec(
        name="plaky_delete_item",
        title="Delete item",
        description="Delete an item; it performs the requested change. Requires space ID, board ID, item ID and write and destructive scope. This performs a live write with no dry-run; if a failure is ambiguous, inspect the receipt and do not repeat blindly.",
        handler=delete_item,
        scopes=frozenset({"write", "destructive"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="raw",
        parameters={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "spaceId": {
                    "oneOf": [
                        {
                            "type": "integer",
                            "format": "int64",
                            "minimum": 0,
                            "maximum": 9223372036854775807,
                        },
                        {"type": "string", "pattern": "^(0|[1-9][0-9]*)$", "maxLength": 19},
                    ],
                    "description": "Represents unique space identifier across the system.",
                },
                "boardId": {
                    "oneOf": [
                        {
                            "type": "integer",
                            "format": "int64",
                            "minimum": 0,
                            "maximum": 9223372036854775807,
                        },
                        {"type": "string", "pattern": "^(0|[1-9][0-9]*)$", "maxLength": 19},
                    ],
                    "description": "Represents unique board identifier across the system.",
                },
                "itemId": {
                    "oneOf": [
                        {
                            "type": "integer",
                            "format": "int64",
                            "minimum": 0,
                            "maximum": 9223372036854775807,
                        },
                        {"type": "string", "pattern": "^(0|[1-9][0-9]*)$", "maxLength": 19},
                    ],
                    "description": "Represents unique item identifier across the system.",
                },
            },
            "required": ["spaceId", "boardId", "itemId"],
        },
    )
