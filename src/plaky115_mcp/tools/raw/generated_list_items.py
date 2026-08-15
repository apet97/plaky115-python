# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for listItems: List board items."""

from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field, StrictInt

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115_mcp.compaction import (
    compact_page,
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import PagedOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.workflow_models import CanonicalId


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def list_items(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        boardViewId: Annotated[
            CanonicalId | None,
            Field(description="Represents unique board view identifier across the system."),
        ] = None,
        parentId: Annotated[
            CanonicalId | None,
            Field(description="Represents unique item identifier across the system."),
        ] = None,
        subitemsBehaviour: Annotated[
            Literal["INCLUDE", "EXCLUDE", "EMBED"] | None,
            Field(
                description="Indicates how subitems are treated in the response. By default subitems will be included.\nThis flag is not applicable when **parentId** is set.\n\n**Options:**\n* **INCLUDE**: Includes subitems in the top level response.\n* **EXCLUDE**: Excludes subitems from the top level response.\n* **EMBED**: Excludes from top level and embeds into each parent with sorts and filters applied.\n"
            ),
        ] = None,
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
        page: Annotated[
            StrictInt | None, Field(description="One-based page number.", ge=1)
        ] = None,
        pageSize: Annotated[
            StrictInt | None, Field(description="Positive page size.", ge=1)
        ] = None,
    ) -> Annotated[CallToolResult, PagedOutput]:
        try:
            result = await client.items.list(
                space_id=spaceId,
                board_id=boardId,
                board_view_id=boardViewId,
                parent_id=parentId,
                subitems_behaviour=subitemsBehaviour,
                expand=expand,
                page=page,
                page_size=pageSize,
            )
            entries = [
                entry.model_dump(mode="json", by_alias=True, exclude_none=True)
                for entry in result.data
            ]
            wire = compact_page(entries, result.has_more, "item")
            text = f"listItems: {len(entries)} result(s); hasMore={result.has_more}"
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
        name="plaky_list_items",
        title="List board items",
        description="List board items; it returns a paginated result. Requires space ID, board ID and read scope. Optional filters: board view ID, parent ID, subitems behaviour, expand. Use page and pageSize to continue the result set.",
        handler=list_items,
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
                "boardViewId": {
                    "oneOf": [
                        {
                            "type": "integer",
                            "format": "int64",
                            "minimum": 0,
                            "maximum": 9223372036854775807,
                        },
                        {"type": "string", "pattern": "^(0|[1-9][0-9]*)$", "maxLength": 19},
                    ],
                    "description": "Represents unique board view identifier across the system.",
                },
                "parentId": {
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
                "subitemsBehaviour": {
                    "default": "INCLUDE",
                    "enum": ["INCLUDE", "EXCLUDE", "EMBED"],
                    "type": "string",
                    "description": "Indicates how subitems are treated in the response. By default subitems will be included.\nThis flag is not applicable when **parentId** is set.\n\n**Options:**\n* **INCLUDE**: Includes subitems in the top level response.\n* **EXCLUDE**: Excludes subitems from the top level response.\n* **EMBED**: Excludes from top level and embeds into each parent with sorts and filters applied.\n",
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
                "page": {"type": "integer", "minimum": 1, "description": "One-based page number."},
                "pageSize": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Positive page size.",
                },
            },
            "required": ["spaceId", "boardId"],
        },
    )
