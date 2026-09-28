# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for overrideSubscriptions: Replace item subscribers."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.models.generated import ItemSubscriptionRequest
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.mutations import AttemptTracker
from plaky115_mcp.compaction import (
    error_result,
    make_result,
)
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import OkOutput
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.workflow_models import CanonicalId


def build_tool(client: AsyncPlakyClient) -> ToolSpec:
    async def override_subscriptions(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        itemId: Annotated[
            CanonicalId, Field(description="Represents unique item identifier across the system.")
        ],
        body: ItemSubscriptionRequest,
    ) -> Annotated[CallToolResult, OkOutput]:
        tracker = AttemptTracker(
            "overrideSubscriptions",
            {"spaceId": str(spaceId), "boardId": str(boardId), "itemId": str(itemId)},
        )
        try:
            result = await client.subscriptions.replace(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                body=body,
                options=RequestOverrides(on_dispatch=tracker.request_started),
            )
            tracker.completed()
            del result
            wire = {"ok": True}
            text = "overrideSubscriptions: ok"
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
        name="plaky_replace_item_subscriptions",
        title="Replace item subscribers",
        description="Replace item subscribers; it performs the requested change. Requires space ID, board ID, item ID and write scope. This performs a live write with no dry-run; if a failure is ambiguous, inspect the receipt and do not repeat blindly.",
        handler=override_subscriptions,
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
                "body": {
                    "description": "Represents a request to manage item subscriptions.",
                    "properties": {
                        "teamIds": {
                            "anyOf": [
                                {
                                    "description": "List of team IDs to process.",
                                    "example": [10, 11],
                                    "items": {
                                        "anyOf": [
                                            {
                                                "type": "integer",
                                                "format": "int64",
                                                "minimum": 0,
                                                "maximum": 9223372036854775807,
                                            },
                                            {
                                                "type": "string",
                                                "pattern": "^(0|[1-9][0-9]*)$",
                                                "maxLength": 19,
                                            },
                                        ]
                                    },
                                    "type": "array",
                                },
                                {"type": "null"},
                            ]
                        },
                        "userIds": {
                            "anyOf": [
                                {
                                    "description": "List of user IDs to process.",
                                    "example": [1, 2, 3],
                                    "items": {
                                        "anyOf": [
                                            {
                                                "type": "integer",
                                                "format": "int64",
                                                "minimum": 0,
                                                "maximum": 9223372036854775807,
                                            },
                                            {
                                                "type": "string",
                                                "pattern": "^(0|[1-9][0-9]*)$",
                                                "maxLength": 19,
                                            },
                                        ]
                                    },
                                    "type": "array",
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                    "type": "object",
                    "additionalProperties": False,
                },
            },
            "required": ["spaceId", "boardId", "itemId", "body"],
        },
    )
