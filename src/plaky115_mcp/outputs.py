"""Structured output models shared by generated and curated tools.

Every tool advertises Annotated[CallToolResult, <RootModel union>] so both
the success and the error envelope validate against the published output
schema, while handlers return the direct CallToolResult form.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel

from plaky115_mcp.errors import ErrorEnvelope


class PagedSuccess(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    data: list[Any]
    has_more: bool = Field(alias="hasMore")


class ListSuccess(BaseModel):
    """Bare-array API roots are presented as a documented data envelope."""

    data: list[Any]


class OkSuccess(BaseModel):
    ok: bool


# Every possible result is a JSON object; the explicit top-level
# "type": "object" keeps the schema valid for legacy (2025-11-25) hosts,
# which reject bare anyOf output schemas.
_OBJECT_SCHEMA = ConfigDict(json_schema_extra={"type": "object"})


class PagedOutput(RootModel[PagedSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class ListOutput(RootModel[ListSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class OkOutput(RootModel[OkSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class EntityOutput(RootModel[ErrorEnvelope | dict[str, Any]]):
    model_config = _OBJECT_SCHEMA
