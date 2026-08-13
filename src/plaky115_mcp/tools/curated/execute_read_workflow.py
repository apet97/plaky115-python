"""plaky_execute_read_workflow: discriminated read-only workflow dispatcher."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115_mcp.compaction import error_result, make_result
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error, usage_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.tools.curated.workflow_registry import READ_RUNNERS, READ_WORKFLOW_IDS


def build_execute_read_workflow(client: AsyncPlakyClient) -> ToolSpec:
    async def plaky_execute_read_workflow(
        workflow: str,
        args: dict[str, Any],
        ctx: Context,  # type: ignore[type-arg]
    ) -> Annotated[CallToolResult, EntityOutput]:
        try:
            runner = READ_RUNNERS.get(workflow)
            if runner is None:
                envelope = usage_error(f"workflow must be one of {', '.join(READ_WORKFLOW_IDS)}")
                return error_result(envelope_wire(envelope), "Unknown read workflow.")
            text, wire = await runner(client, args, ctx)
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError, KeyError) as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_execute_read_workflow",
        title="Execute read workflow",
        description=(
            "Run one read-only curated workflow: workspace.map, items.search, "
            "comments.thread, or export.items. Mutations are never reachable "
            "through this dispatcher."
        ),
        handler=plaky_execute_read_workflow,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="curated",
    )
