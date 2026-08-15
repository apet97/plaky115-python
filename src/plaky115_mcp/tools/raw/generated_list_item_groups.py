# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for listItemGroups: List board item groups."""

from __future__ import annotations

import asyncio
from typing import Annotated

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
    async def list_item_groups(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        page: Annotated[
            StrictInt | None, Field(description="One-based page number.", ge=1)
        ] = None,
        pageSize: Annotated[
            StrictInt | None, Field(description="Positive page size.", ge=1)
        ] = None,
    ) -> Annotated[CallToolResult, PagedOutput]:
        try:
            result = await client.item_groups.list(
                space_id=spaceId, board_id=boardId, page=page, page_size=pageSize
            )
            entries = [
                entry.model_dump(mode="json", by_alias=True, exclude_none=True)
                for entry in result.data
            ]
            wire = compact_page(entries, result.has_more, "itemGroup")
            text = f"listItemGroups: {len(entries)} result(s); hasMore={result.has_more}"
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
        name="plaky_list_item_groups",
        title="List item groups",
        description="List board item groups; it returns a paginated result. Requires space ID, board ID and read scope. Use page and pageSize to continue the result set.",
        handler=list_item_groups,
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
