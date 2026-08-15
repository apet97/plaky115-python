"""Structured output models shared by generated and curated tools."""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel

from plaky115_mcp.errors import ErrorEnvelope, ReceiptModel

JsonObject: TypeAlias = dict[str, JsonValue]
Identifier: TypeAlias = int | str


class OwnedOutput(BaseModel):
    """Package-owned output objects reject fields that the package did not emit."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PagedSuccess(OwnedOutput):
    data: list[JsonValue]
    has_more: bool = Field(alias="hasMore")


class ListSuccess(OwnedOutput):
    """Bare-array API roots are presented as a documented data envelope."""

    data: list[JsonValue]


class OkSuccess(OwnedOutput):
    ok: bool


class PlanUploadSuccess(OwnedOutput):
    file_name: str = Field(alias="fileName")
    media_type: str = Field(alias="mediaType")
    decoded_bytes: int = Field(alias="decodedBytes")
    sha256: str


class PlanMutationSuccess(OwnedOutput):
    dry_run: Literal[True] = Field(alias="dryRun")
    operation: str
    target_ids: dict[str, str] = Field(alias="targetIds")
    body: JsonObject
    write_count: int = Field(alias="writeCount")
    requires_live_resolution: bool = Field(alias="requiresLiveResolution")
    upload: PlanUploadSuccess | None = None


class CompletedMutationSuccess(OwnedOutput):
    operation: str
    result: JsonObject
    receipt: ReceiptModel


class BulkMutationSuccess(OwnedOutput):
    dry_run: bool = Field(alias="dryRun")
    receipts: list[ReceiptModel]


class BoardReference(OwnedOutput):
    id: Identifier
    title: str | None = None


class WorkspaceMapEntry(OwnedOutput):
    id: Identifier
    title: str | None = None
    boards: list[BoardReference]


class WorkspaceMapSuccess(OwnedOutput):
    data: list[WorkspaceMapEntry]


class Continuation(OwnedOutput):
    page: int
    index: int


class ItemSearchSuccess(OwnedOutput):
    data: list[JsonObject]
    scanned: int
    matched: int
    complete: bool
    truncated: bool
    continuation: Continuation | None = None


class CommentsThreadSuccess(OwnedOutput):
    data: list[JsonObject]
    truncated: bool


class ExportItemsSuccess(OwnedOutput):
    format: Literal["jsonl", "csv"]
    body: str
    returned: int
    bytes: int
    complete: bool
    truncated: bool
    continuation: Continuation | None = None


class BoardColumn(OwnedOutput):
    key: str
    title: str
    type: str | None = None


class BoardLabel(OwnedOutput):
    title: str
    color: str | None = None


class BoardGroup(OwnedOutput):
    id: Identifier | None = None
    title: str | None = None
    color: str | None = None


class BoardItem(OwnedOutput):
    id: Identifier | None = None
    title: str | None = None
    group_id: Identifier | None = Field(alias="groupId", default=None)
    fields: JsonObject


class BoardViewSuccess(OwnedOutput):
    board: BoardReference
    space: BoardReference
    columns: list[BoardColumn]
    labels: dict[str, dict[str, BoardLabel]]
    groups: list[BoardGroup]
    items: list[BoardItem]
    item_count: int = Field(alias="itemCount")
    has_more: bool = Field(alias="hasMore")
    truncated: bool


class DownloadLinkSuccess(OwnedOutput):
    url: str | None = None
    expires_in_seconds: int | str | None = Field(alias="expiresInSeconds", default=None)


# Every possible result is a JSON object; the explicit top-level "type":
# "object" keeps the schema valid for legacy hosts, which reject bare anyOf
# output schemas.
_OBJECT_SCHEMA = ConfigDict(json_schema_extra={"type": "object"})


class PagedOutput(RootModel[PagedSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class ListOutput(RootModel[ListSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class OkOutput(RootModel[OkSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class EntityOutput(RootModel[ErrorEnvelope | JsonObject]):
    """Permissive only for upstream entity fields that the API may extend."""

    model_config = _OBJECT_SCHEMA


class PlanMutationOutput(RootModel[PlanMutationSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class MutationWorkflowOutput(
    RootModel[PlanMutationSuccess | CompletedMutationSuccess | BulkMutationSuccess | ErrorEnvelope]
):
    model_config = _OBJECT_SCHEMA


class ReadWorkflowOutput(
    RootModel[
        WorkspaceMapSuccess
        | ItemSearchSuccess
        | CommentsThreadSuccess
        | ExportItemsSuccess
        | ErrorEnvelope
    ]
):
    model_config = _OBJECT_SCHEMA


class BoardViewOutput(RootModel[BoardViewSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA


class DownloadLinkOutput(RootModel[DownloadLinkSuccess | ErrorEnvelope]):
    model_config = _OBJECT_SCHEMA
