# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""Raw MCP tool for createItem: Create an item."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, cast

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.models.generated import ItemCreateRequest
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
    async def create_item(
        spaceId: Annotated[
            CanonicalId, Field(description="Represents unique space identifier across the system.")
        ],
        boardId: Annotated[
            CanonicalId, Field(description="Represents unique board identifier across the system.")
        ],
        body: ItemCreateRequest,
    ) -> Annotated[CallToolResult, EntityOutput]:
        tracker = AttemptTracker("createItem", {"spaceId": str(spaceId), "boardId": str(boardId)})
        try:
            result = cast(
                "Any",
                await client.items.create(
                    space_id=spaceId,
                    board_id=boardId,
                    body=body,
                    options=RequestOverrides(on_dispatch=tracker.request_started),
                ),
            )
            tracker.completed()
            wire = compact_entity(
                result.model_dump(mode="json", by_alias=True, exclude_none=True), "item"
            )
            text = f"createItem: id={wire.get('id')}"
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
        name="plaky_create_item",
        title="Create item",
        description="Create an item; it performs the requested change. Requires space ID, board ID and write scope. This performs a live write with no dry-run; if a failure is ambiguous, inspect the receipt and do not repeat blindly.",
        handler=create_item,
        scopes=frozenset({"write"}),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
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
                "body": {
                    "description": "Represents item create request.",
                    "properties": {
                        "fields": {
                            "anyOf": [
                                {
                                    "additionalProperties": {},
                                    "description": 'Represents item field values added to the item. If it is omitted then item will be created with default values. Field can be\nspecified by it\'s key or by it\'s title. Field value differs per type and for some types it can be specified in multiple ways.\n\n| Type | Examples (Key / Title) |\n| :--- | :--- |\n| **String** | `{"string-1" : "test"}` <br> `{"String Field Title" : "test"}` |\n| **Rich Text** | `{"rich_text-1" : "some rich text"}` <br> `{"Description" : "some rich text"}` |\n| **Number** | `{"number-1" : 13.4}` <br> `{"Price" : 13.4}` |\n| **Date** | `{"date_time-1" : "2017-06-02T18:10:15.254Z"}` <br> `{"Date" : "2017-06-02T18:10:15.254Z"}` |\n| **Timeline** | `{"timeline-1" : {"start" : "2026-01-02T18:10:15.254Z", "end": "2026-02-02T18:10:15.254Z"}}` <br> `{"Timeline" : {"start" : "2026-01-02T18:10:15.254Z", "end": "2026-02-02T18:10:15.254Z"}}` |\n| **Status** | `{"status-1" : "1"}`, `{"status-1" : "To do"}` <br> `{"Status" : "1"}`, `{"Status" : "To do"}` |\n| **Tag** | `{"tag-1" : ["1", "2"]}`, `{"tag-1" : ["Product", "HR"]}` <br> `{"Department" : ["1", "2"]}`, `{"Department" : ["Product", "HR"]}` |\n| **Link** | `{"link-1" : "https://www.google.com"}` <br> `{"link-1" : {"url" : "https://www.google.com", "displayText" : "Google"}}` <br> `{"Link" : "https://www.google.com"}` |\n| **Person** | `{"person-1": {"users" : [{"id" : "1"}, {"email" : "test@gmail.com"}], "teams": [{"id" : 1}, {"title" : "Backend Team"}]}}` <br> `{"Assignee": {"users" : [{"id" : "1"}, {"email" : "test@gmail.com"}], "teams": [{"id" : 1}, {"title" : "Backend Team"}]}}` |\n',
                                    "example": {
                                        "Description": "Test description",
                                        "Status": "To do",
                                        "number-1": 50,
                                    },
                                    "type": "object",
                                },
                                {"type": "null"},
                            ]
                        },
                        "groupId": {
                            "anyOf": [
                                {
                                    "description": "Represents ID of the item group in which item is created. If it is not specified then **groupTitle** field\nwill be used for determining in which group item is created.",
                                    "example": 1,
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
                                    ],
                                },
                                {"type": "null"},
                            ]
                        },
                        "groupTitle": {
                            "anyOf": [
                                {
                                    "description": "Represents title of the item group in which item is created. If neither **groupId** nor **groupTitle** field is\nnot specified then item will be created in the first group in the board.",
                                    "example": "Backlog",
                                    "type": "string",
                                },
                                {"type": "null"},
                            ]
                        },
                        "parentId": {
                            "anyOf": [
                                {
                                    "description": "Represents ID of the parent under which subitem is created. If it has null value then item is created, if\nit is specified then subitem is created under specified parent.",
                                    "example": 1,
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
                                    ],
                                },
                                {"type": "null"},
                            ]
                        },
                        "title": {
                            "anyOf": [
                                {
                                    "description": "Represents title of the item. If it is not provided then default title be set. Default title for item is New Item and\nfor subitem it is New Subitem.",
                                    "example": "My New Item",
                                    "maxLength": 255,
                                    "type": "string",
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                    "type": "object",
                    "additionalProperties": False,
                },
            },
            "required": ["spaceId", "boardId", "body"],
        },
    )
