# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for uploadItemFile: Upload an item file."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.runtime.mutations import AttemptTracker
from plaky115.runtime.upload import Base64UploadInput, normalize_upload
from plaky115_mcp.compaction import (
    compact_entity,
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def upload_item_file(
        spaceId: int | str,
        boardId: int | str,
        itemId: int | str,
        fileBase64: str,
        fileName: str,
        contentType: str | None = None,
    ) -> Annotated[CallToolResult, EntityOutput]:
        tracker = AttemptTracker(
            "uploadItemFile",
            {"spaceId": str(spaceId), "boardId": str(boardId), "itemId": str(itemId)},
        )
        try:
            upload = normalize_upload(
                Base64UploadInput(
                    file_base64=fileBase64, file_name=fileName, content_type=contentType
                )
            )
            tracker.request_started()
            result = await client.item_files.upload(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                file=upload.data,
                file_name=upload.file_name,
                content_type=upload.media_type,
            )
            tracker.completed()
            wire = compact_entity(result.model_dump(by_alias=True, exclude_none=True), "itemFile")
            text = f"uploadItemFile: id={wire.get('id')}"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, tracker)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_upload_item_file",
        title="Upload item file",
        description="Upload an item file",
        handler=upload_item_file,
        scopes=frozenset({"write"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
        kind="raw",
    )
