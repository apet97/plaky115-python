# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for replaceCommentReactions: Replace comment reactions."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.models.generated import ReactionPutRequest
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
    async def replace_comment_reactions(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        itemId: Annotated[
            CanonicalId, Field(description="Represents unique item identifier across the system.")
        ],
        itemCommentId: Annotated[
            CanonicalId,
            Field(description="Represents unique item comment identifier across the system."),
        ],
        body: ReactionPutRequest,
    ) -> Annotated[CallToolResult, EntityOutput]:
        tracker = AttemptTracker(
            "replaceCommentReactions",
            {
                "spaceId": str(spaceId),
                "boardId": str(boardId),
                "itemId": str(itemId),
                "itemCommentId": str(itemCommentId),
            },
        )
        try:
            result = await client.reactions.replace(
                space_id=spaceId,
                board_id=boardId,
                item_id=itemId,
                item_comment_id=itemCommentId,
                body=body,
                options=RequestOverrides(on_dispatch=tracker.request_started),
            )
            tracker.completed()
            wire = compact_entity(
                result.model_dump(mode="json", by_alias=True, exclude_none=True), "raw"
            )
            text = f"replaceCommentReactions: id={wire.get('id')}"
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
        name="plaky_replace_comment_reactions",
        title="Replace comment reactions",
        description="Replace comment reactions; it performs the requested change. Requires space ID, board ID, item ID, item comment ID and write scope. This performs a live write with no dry-run; if a failure is ambiguous, inspect the receipt and do not repeat blindly.",
        handler=replace_comment_reactions,
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
                "itemCommentId": {
                    "oneOf": [
                        {
                            "type": "integer",
                            "format": "int64",
                            "minimum": 0,
                            "maximum": 9223372036854775807,
                        },
                        {"type": "string", "pattern": "^(0|[1-9][0-9]*)$", "maxLength": 19},
                    ],
                    "description": "Represents unique item comment identifier across the system.",
                },
                "body": {
                    "description": "Represents request for adding/removing authenticated user's comment reaction(s).",
                    "properties": {
                        "reactions": {
                            "description": "You can leave multiple reactions, it's overriding the current ones that you've left,\nleave empty to remove them.\n",
                            "items": {"$ref": "#/$defs/Reaction"},
                            "type": "array",
                            "uniqueItems": True,
                        }
                    },
                    "required": ["reactions"],
                    "type": "object",
                    "additionalProperties": False,
                },
            },
            "required": ["spaceId", "boardId", "itemId", "itemCommentId", "body"],
            "$defs": {
                "Reaction": {
                    "properties": {
                        "value": {
                            "description": 'A code representing an emoji, like "1f44d" (thumbs up) or "2705" (checkmark button).\nYou\'ll see there are variations on how an emoji could be represented, we need a unicode representation\nwithout "U+" prefix. For example, the unicode for "thumbs up" is "U+1F44D", so take it after the plus\nsign (letter case doesn\'t matter).\n',
                            "example": "1f44d",
                            "minLength": 1,
                            "type": "string",
                        }
                    },
                    "required": ["value"],
                    "type": "object",
                }
            },
        },
    )
