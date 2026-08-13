# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for listSubitems: List subitems."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations

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
    async def list_subitems(
        spaceId: int | str,
        boardId: int | str,
        itemId: int | str,
        expand: list[str] | None = None,
        page: int | None = None,
        pageSize: int | None = None,
    ) -> Annotated[CallToolResult, PagedOutput]:
        try:
            result = await client.items.list_subitems(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                expand=expand,
                page=page,
                page_size=pageSize,
            )
            entries = [entry.model_dump(by_alias=True, exclude_none=True) for entry in result.data]
            wire = compact_page(entries, result.has_more, "item")
            text = f"listSubitems: {len(entries)} result(s); hasMore={result.has_more}"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, None)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_list_subitems",
        title="List subitems",
        description="List subitems",
        handler=list_subitems,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="raw",
    )
