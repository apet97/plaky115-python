# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for getItem: Retrieve an item."""

from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115_mcp.compaction import (
    compact_entity,
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.workflow_models import CanonicalId


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def get_item(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        itemId: Annotated[
            CanonicalId, Field(description="Represents unique item identifier across the system.")
        ],
        expand: Annotated[
            list[
                Literal[
                    "space", "board", "group", "createdBy", "parent", "subscriptions", "fields"
                ]
            ]
            | None,
            Field(
                description="Comma-separated list of relationships to expand into full objects\ninstead of IDs."
            ),
        ] = None,
    ) -> Annotated[CallToolResult, EntityOutput]:
        try:
            result = await client.items.get(
                space_id=spaceId, board_id=boardId, item_id=itemId, expand=expand
            )
            wire = compact_entity(
                result.model_dump(mode="json", by_alias=True, exclude_none=True), "item"
            )
            text = f"getItem: id={wire.get('id')}"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, None)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(
                envelope_wire(internal_error(exc, None)),
                "Internal server error.",
            )

    return ToolSpec(
        name="plaky_get_item",
        title="Get item",
        description="Retrieve an item; it returns the requested result. Requires space ID, board ID, item ID and read scope. Optional filters: expand. This operation is read-only.",
        handler=get_item,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
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
                "expand": {
                    "items": {
                        "enum": [
                            "space",
                            "board",
                            "group",
                            "createdBy",
                            "parent",
                            "subscriptions",
                            "fields",
                        ],
                        "type": "string",
                    },
                    "type": "array",
                    "description": "Comma-separated list of relationships to expand into full objects\ninstead of IDs.",
                },
            },
            "required": ["spaceId", "boardId", "itemId"],
        },
    )
