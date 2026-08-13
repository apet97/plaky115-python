"""plaky_workspace_context: bounded compact workspace context."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, cast

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.workflows.workspace import async_workspace_map
from plaky115_mcp.compaction import error_result, make_result
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import ListOutput
from plaky115_mcp.registry import ToolSpec


def _board_ref(board: Any) -> Any:
    if isinstance(board, dict):
        record = cast("dict[str, Any]", board)
        return {"id": record.get("id"), "title": record.get("title")}
    return board


def build_workspace_context(client: AsyncPlakyClient) -> ToolSpec:
    async def plaky_workspace_context(
        maxItems: int = 200,
        maxBytes: int = 65536,
    ) -> Annotated[CallToolResult, ListOutput]:
        try:
            tree = await async_workspace_map(client, max_items=maxItems, max_bytes=maxBytes)
            compact = [
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "boards": [_board_ref(b) for b in entry["boards"]],
                }
                for entry in tree
            ]
            return make_result(
                text=f"plaky_workspace_context: {len(compact)} space(s)",
                structured={"data": compact},
            )
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_workspace_context",
        title="Workspace context",
        description=(
            "Return a bounded, compact tree of the workspace's spaces and "
            "boards (IDs and titles only) for orientation before other calls."
        ),
        handler=plaky_workspace_context,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="curated",
    )
