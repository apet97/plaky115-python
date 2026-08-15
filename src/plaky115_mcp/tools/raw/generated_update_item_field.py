# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for updateItemField: Update one item field."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field, StrictStr

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.models.generated import FieldValueChangeRequest
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.mutations import AttemptTracker
from plaky115_mcp.compaction import (
    compact_entity,
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.workflow_models import CanonicalId


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def update_item_field(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        itemId: Annotated[
            CanonicalId, Field(description="Represents unique item identifier across the system.")
        ],
        itemFieldKey: Annotated[StrictStr, Field(description="Represents key of the field.")],
        body: FieldValueChangeRequest,
    ) -> Annotated[CallToolResult, EntityOutput]:
        tracker = AttemptTracker(
            "updateItemField",
            {
                "spaceId": str(spaceId),
                "boardId": str(boardId),
                "itemId": str(itemId),
                "itemFieldKey": str(itemFieldKey),
            },
        )
        try:
            result = await client.items.update_field(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                item_field_key=itemFieldKey,
                body=body,
                options=RequestOverrides(on_dispatch=tracker.request_started),
            )
            tracker.completed()
            wire = compact_entity(
                result.model_dump(mode="json", by_alias=True, exclude_none=True), "item"
            )
            text = f"updateItemField: id={wire.get('id')}"
            return make_result(text=text, structured=wire)
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc, tracker)), str(exc))
        except Exception as exc:  # controlled internal-error path
            return error_result(
                envelope_wire(internal_error(exc, tracker)),
                "Internal server error.",
            )

    return ToolSpec(
        name="plaky_update_item_field",
        title="Update item field",
        description="Update one item field; it performs the requested change. Requires space ID, board ID, item ID, item field key and write scope. This performs a live write with no dry-run; if a failure is ambiguous, inspect the receipt and do not repeat blindly.",
        handler=update_item_field,
        scopes=frozenset({"write"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
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
                "itemId": {
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
                "itemFieldKey": {"type": "string", "description": "Represents key of the field."},
                "body": {
                    "description": "Represents request for item field value change.",
                    "properties": {
                        "value": {
                            "anyOf": [
                                {
                                    "description": 'Represents item field value. Field value differs per type and for some types it can be specified in multiple ways.\n\n| Type | Examples (Key / Title) |\n| :--- | :--- |\n| **String** | `{"value" : "test"}`|\n| **Rich Text** | `{"value" : "some rich text"}`\n| **Number** | `{"value" : 13.4}` |\n| **Date** | `{"value" : "2017-06-02T18:10:15.254Z"}` |\n| **Timeline** | `{"value" : {"start" : "2026-01-02T18:10:15.254Z", "end": "2026-02-02T18:10:15.254Z"}}` |\n| **Status** | `{"value" : "1"}`, `{"value" : "To do"}` |\n| **Tag** | `{"value" : ["1", "2"]}`, `{"value" : ["Product", "HR"]}` |\n| **Link** | `{"value" : "https://www.google.com"}`, `{"value" : {"url" : "https://www.google.com", "displayText" : "Google"}}`  |\n| **Person** | `{"value": {"users" : [{"id" : "1"}, {"email" : "test@gmail.com"}], "teams": [{"id" : 1}, {"title" : "Backend Team"}]}}`|\n',
                                    "example": {"value": "To do"},
                                },
                                {"type": "null"},
                            ]
                        }
                    },
                    "type": "object",
                    "additionalProperties": False,
                },
            },
            "required": ["spaceId", "boardId", "itemId", "itemFieldKey", "body"],
        },
    )
