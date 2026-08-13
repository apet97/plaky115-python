"""plaky_execute_workflow: deprecated mixed read/write compatibility dispatcher.

Available only behind an explicit local compatibility flag and excluded
from every directory-facing catalog because it mixes read and write
behavior. Mutation workflows default to dry-run.
"""

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
from plaky115_mcp.tools.curated.workflow_registry import (
    MUTATION_WORKFLOW_IDS,
    READ_RUNNERS,
    WORKFLOW_IDS,
    run_bulk_update,
    run_mutation_workflow,
)


def build_execute_workflow(client: AsyncPlakyClient) -> ToolSpec:
    async def plaky_execute_workflow(
        workflow: str,
        args: dict[str, Any],
        ctx: Context,  # type: ignore[type-arg]
        dryRun: bool = True,
    ) -> Annotated[CallToolResult, EntityOutput]:
        try:
            if workflow in READ_RUNNERS:
                text, wire = await READ_RUNNERS[workflow](client, args, ctx)
                return make_result(text=text, structured=wire)
            if workflow in MUTATION_WORKFLOW_IDS:
                if workflow == "items.updateFields" and isinstance(args.get("updates"), list):
                    text, wire = await run_bulk_update(client, args, dry_run=dryRun, ctx=ctx)
                    return make_result(text=text, structured=wire)
                text, wire, _ = await run_mutation_workflow(
                    client, workflow, args, dry_run=dryRun, ctx=ctx
                )
                return make_result(text=text, structured=wire)
            envelope = usage_error(f"workflow must be one of {', '.join(WORKFLOW_IDS)}")
            return error_result(envelope_wire(envelope), "Unknown workflow.")
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError, KeyError) as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_execute_workflow",
        title="Execute workflow (deprecated)",
        description=(
            "Deprecated mixed read/write workflow dispatcher kept for local "
            "compatibility only. Prefer plaky_execute_read_workflow and "
            "plaky_execute_mutation_workflow. Mutations default to dry-run."
        ),
        handler=plaky_execute_workflow,
        scopes=frozenset({"read", "write"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
        kind="curated",
        compat_only=True,
    )
