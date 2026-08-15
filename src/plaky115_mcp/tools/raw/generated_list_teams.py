# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for listTeams: List workspace teams."""

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


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def list_teams(
        page: Annotated[
            StrictInt | None, Field(description="One-based page number.", ge=1)
        ] = None,
        pageSize: Annotated[
            StrictInt | None, Field(description="Positive page size.", ge=1)
        ] = None,
    ) -> Annotated[CallToolResult, PagedOutput]:
        try:
            result = await client.teams.list(page=page, page_size=pageSize)
            entries = [
                entry.model_dump(mode="json", by_alias=True, exclude_none=True)
                for entry in result.data
            ]
            wire = compact_page(entries, result.has_more, "raw")
            text = f"listTeams: {len(entries)} result(s); hasMore={result.has_more}"
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
        name="plaky_list_teams",
        title="List teams",
        description="List workspace teams; it returns a paginated result. Requires no identifiers and read scope. Use page and pageSize to continue the result set.",
        handler=list_teams,
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
                "page": {"type": "integer", "minimum": 1, "description": "One-based page number."},
                "pageSize": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Positive page size.",
                },
            },
            "required": [],
        },
    )
