"""plaky_execute_mutation_workflow: discriminated mutation dispatcher.

Mutation workflows default to dry-run. A live write happens only when
dryRun is explicitly false, performs exactly one network attempt per
target, and returns durable attempt receipts.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError, PlakyPartialMutationError
from plaky115_mcp.compaction import error_result, make_result
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error, usage_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.tools.curated.workflow_registry import (
    MUTATION_WORKFLOW_IDS,
    run_bulk_update,
    run_mutation_workflow,
)


def build_execute_mutation_workflow(client: AsyncPlakyClient) -> ToolSpec:
    async def plaky_execute_mutation_workflow(
        workflow: str,
        args: dict[str, Any],
        ctx: Context,  # type: ignore[type-arg]
        dryRun: bool = True,
    ) -> Annotated[CallToolResult, EntityOutput]:
        tracker = None
        try:
            if workflow not in MUTATION_WORKFLOW_IDS:
                envelope = usage_error(
                    f"workflow must be one of {', '.join(MUTATION_WORKFLOW_IDS)}"
                )
                return error_result(envelope_wire(envelope), "Unknown mutation workflow.")
            if workflow == "items.updateFields" and isinstance(args.get("updates"), list):
                text, wire = await run_bulk_update(client, args, dry_run=dryRun, ctx=ctx)
                return make_result(text=text, structured=wire)
            text, wire, trackers = await run_mutation_workflow(
                client, workflow, args, dry_run=dryRun, ctx=ctx
            )
            tracker = trackers[0] if trackers else None
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            # A cancelled modern MCP request is not answered; never return
            # an ambiguous receipt for it.
            raise
        except PlakyPartialMutationError as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except (PlakyError, ValueError, TypeError, KeyError) as exc:
            return error_result(envelope_wire(error_envelope(exc, tracker)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_execute_mutation_workflow",
        title="Execute mutation workflow",
        description=(
            "Run one curated mutation workflow (items.create, "
            "items.updateFields, comments.add, itemGroups.create, "
            "itemGroups.update, itemFiles.upload, itemFiles.update). "
            "Dry-run by default; set dryRun=false to perform exactly one "
            "write per target with durable attempt receipts."
        ),
        handler=plaky_execute_mutation_workflow,
        scopes=frozenset({"read", "write"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
        kind="curated",
    )
