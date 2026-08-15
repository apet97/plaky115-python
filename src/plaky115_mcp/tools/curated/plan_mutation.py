"""plaky_plan_mutation: validate and normalize one mutation without executing."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.errors import PlakyError
from plaky115.runtime.upload import Base64UploadInput
from plaky115.workflows.mutation_plans import (
    NormalizedMutationPlan,
    normalize_base64_upload_plan,
    normalize_comment_plan,
    normalize_item_create_plan,
    normalize_item_file_update_plan,
    normalize_item_group_create_plan,
    normalize_item_group_update_plan,
    normalize_item_update_fields_plan,
)
from plaky115_mcp.compaction import error_result, make_result
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import PlanMutationOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.workflow_models import PLAN_MUTATION_SCHEMA, CanonicalId, validate_plan_mutation


def plan_wire(plan: NormalizedMutationPlan) -> dict[str, Any]:
    wire: dict[str, Any] = {
        "dryRun": True,
        "operation": plan.operation_id,
        "targetIds": dict(plan.target_ids),
        "body": dict(plan.body),
        "writeCount": plan.write_count,
        "requiresLiveResolution": plan.requires_live_resolution,
    }
    if plan.upload is not None:
        wire["upload"] = {
            "fileName": plan.upload.file_name,
            "mediaType": plan.upload.media_type,
            "decodedBytes": plan.upload.decoded_bytes,
            "sha256": plan.upload.sha256,
        }
    return wire


def normalize_for_operation(
    operation: str,
    space_id: int | str,
    board_id: int | str,
    body: dict[str, Any],
    item_id: int | str | None,
    item_comment_id: int | str | None,
    item_group_id: int | str | None,
    item_file_id: int | str | None,
) -> NormalizedMutationPlan:
    if operation == "createItem":
        return normalize_item_create_plan(space_id=space_id, board_id=board_id, body=body)
    if operation == "updateItemFields":
        if item_id is None:
            raise ValueError("updateItemFields requires itemId")
        return normalize_item_update_fields_plan(
            space_id=space_id, board_id=board_id, item_id=item_id, body=body
        )
    if operation in ("createItemComment", "updateItemComment"):
        if item_id is None:
            raise ValueError(f"{operation} requires itemId")
        if operation == "updateItemComment" and item_comment_id is None:
            raise ValueError("updateItemComment requires itemCommentId")
        return normalize_comment_plan(
            space_id=space_id,
            board_id=board_id,
            item_id=item_id,
            item_comment_id=item_comment_id if operation == "updateItemComment" else None,
            body=body,
            operation_id=operation,
        )
    if operation == "createItemGroup":
        return normalize_item_group_create_plan(space_id=space_id, board_id=board_id, body=body)
    if operation == "updateItemGroup":
        if item_group_id is None:
            raise ValueError("updateItemGroup requires itemGroupId")
        return normalize_item_group_update_plan(
            space_id=space_id, board_id=board_id, item_group_id=item_group_id, body=body
        )
    if operation == "updateItemFile":
        if item_id is None or item_file_id is None:
            raise ValueError("updateItemFile requires itemId and itemFileId")
        return normalize_item_file_update_plan(
            space_id=space_id,
            board_id=board_id,
            item_id=item_id,
            item_file_id=item_file_id,
            body=body,
        )
    if item_id is None:
        raise ValueError("uploadItemFile requires itemId")
    upload = Base64UploadInput(
        file_base64=str(body.get("fileBase64", "")),
        file_name=str(body.get("fileName", "")),
        content_type=(str(body["contentType"]) if body.get("contentType") is not None else None),
    )
    normalized = normalize_base64_upload_plan(
        space_id=space_id, board_id=board_id, item_id=item_id, upload=upload
    )
    return normalized.plan


def build_plan_mutation() -> ToolSpec:
    async def plaky_plan_mutation(
        operation: str,
        spaceId: CanonicalId,
        boardId: CanonicalId,
        body: dict[str, Any],
        itemId: CanonicalId | None = None,
        itemCommentId: CanonicalId | None = None,
        itemGroupId: CanonicalId | None = None,
        itemFileId: CanonicalId | None = None,
    ) -> Annotated[CallToolResult, PlanMutationOutput]:
        try:
            values: dict[str, Any] = {
                "operation": operation,
                "spaceId": spaceId,
                "boardId": boardId,
                "body": body,
            }
            for name, value in (
                ("itemId", itemId),
                ("itemCommentId", itemCommentId),
                ("itemGroupId", itemGroupId),
                ("itemFileId", itemFileId),
            ):
                if value is not None:
                    values[name] = value
            validated = validate_plan_mutation(values)
            plan = normalize_for_operation(
                validated["operation"],
                validated["spaceId"],
                validated["boardId"],
                validated["body"],
                validated.get("itemId"),
                validated.get("itemCommentId"),
                validated.get("itemGroupId"),
                validated.get("itemFileId"),
            )
            wire = plan_wire(plan)
            # Base64 content never appears in plan output.
            return make_result(
                text=(
                    f"plaky_plan_mutation: {validated['operation']} validated; no write performed"
                ),
                structured=wire,
            )
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_plan_mutation",
        title="Plan mutation",
        description=(
            "Validate and normalize one mutation locally without executing "
            "it. Returns the exact write that would be sent (one write, "
            "canonical target IDs); uploads report metadata and SHA-256 only."
        ),
        handler=plaky_plan_mutation,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        kind="curated",
        parameters=PLAN_MUTATION_SCHEMA,
    )
