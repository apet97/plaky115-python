"""Strict, wire-compatible models for curated MCP workflow calls."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    TypeAdapter,
    model_validator,
)
from pydantic.types import StringConstraints

from plaky115.models.generated import (
    CommentRequest,
    FieldValueChangeRequest,
    ItemCreateRequest,
    ItemFileUpdateRequest,
    ItemGroupCreateRequest,
    ItemGroupUpdateRequest,
)

CanonicalId: TypeAlias = (
    Annotated[StrictInt, Field(ge=0, le=9_223_372_036_854_775_807)]
    | Annotated[
        StrictStr,
        StringConstraints(pattern=r"^(0|[1-9][0-9]*)$", max_length=19),
    ]
)
MAX_BULK_UPDATES = 50
MAX_BULK_UPDATES_BYTES = 64 * 1024


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, strict=True)


class Base64UploadBody(StrictModel):
    file_base64: StrictStr = Field(alias="fileBase64")
    file_name: StrictStr = Field(alias="fileName")
    content_type: StrictStr | None = Field(default=None, alias="contentType")


FieldUpdates: TypeAlias = dict[StrictStr, FieldValueChangeRequest]


class Cursor(StrictModel):
    page: StrictInt = Field(default=1, ge=1)
    index: StrictInt = Field(default=0, ge=0)


class WorkspaceMapArgs(StrictModel):
    max_items: StrictInt = Field(default=200, alias="maxItems", ge=1, le=500)
    max_bytes: StrictInt = Field(default=65_536, alias="maxBytes", ge=1, le=131_072)


class ItemsSearchArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    query: StrictStr = ""
    limit: StrictInt = Field(default=200, ge=1, le=500)
    cursor: Cursor | None = None


class CommentsThreadArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    limit: StrictInt = Field(default=100, ge=1, le=500)


class ExportItemsArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    format: Literal["jsonl", "csv"] = "jsonl"
    csv_safety: Literal["spreadsheet", "raw"] = Field(default="spreadsheet", alias="csvSafety")
    max_items: StrictInt = Field(default=100, alias="maxItems", ge=1, le=500)
    max_bytes: StrictInt = Field(default=65_536, alias="maxBytes", ge=1, le=131_072)
    cursor: Cursor | None = None
    include_header: StrictBool = Field(default=True, alias="includeHeader")


class CreateItemArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    body: ItemCreateRequest


class ItemUpdate(StrictModel):
    item_id: CanonicalId = Field(alias="itemId")
    body: FieldUpdates


class UpdateFieldsArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId | None = Field(default=None, alias="itemId")
    body: FieldUpdates | None = None
    updates: list[ItemUpdate] | None = None

    @model_validator(mode="after")
    def validate_form_and_bounds(self) -> UpdateFieldsArgs:
        single = self.item_id is not None and self.body is not None and self.updates is None
        bulk = self.item_id is None and self.body is None and self.updates is not None
        if not single and not bulk:
            raise ValueError("items.updateFields requires itemId and body, or updates")
        if self.updates is not None:
            if not self.updates:
                raise ValueError("updates must contain at least one item")
            if len(self.updates) > MAX_BULK_UPDATES:
                raise ValueError(f"updates must contain at most {MAX_BULK_UPDATES} items")
            size = len(
                json.dumps(
                    [entry.model_dump(by_alias=True, mode="json") for entry in self.updates],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            if size > MAX_BULK_UPDATES_BYTES:
                raise ValueError(f"updates must not exceed {MAX_BULK_UPDATES_BYTES} UTF-8 bytes")
        return self


class AddCommentArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    body: CommentRequest


class CreateItemGroupArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    body: ItemGroupCreateRequest


class UpdateItemGroupArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_group_id: CanonicalId = Field(alias="itemGroupId")
    body: ItemGroupUpdateRequest


class UploadItemFileArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    body: Base64UploadBody


class UpdateItemFileArgs(StrictModel):
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    item_file_id: CanonicalId = Field(alias="itemFileId")
    body: ItemFileUpdateRequest


class ReadWorkspaceMap(StrictModel):
    workflow: Literal["workspace.map"]
    args: WorkspaceMapArgs


class ReadItemsSearch(StrictModel):
    workflow: Literal["items.search"]
    args: ItemsSearchArgs


class ReadCommentsThread(StrictModel):
    workflow: Literal["comments.thread"]
    args: CommentsThreadArgs


class ReadExportItems(StrictModel):
    workflow: Literal["export.items"]
    args: ExportItemsArgs


class MutationCreateItem(StrictModel):
    workflow: Literal["items.create"]
    args: CreateItemArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


class MutationUpdateFields(StrictModel):
    workflow: Literal["items.updateFields"]
    args: UpdateFieldsArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


class MutationAddComment(StrictModel):
    workflow: Literal["comments.add"]
    args: AddCommentArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


class MutationCreateItemGroup(StrictModel):
    workflow: Literal["itemGroups.create"]
    args: CreateItemGroupArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


class MutationUpdateItemGroup(StrictModel):
    workflow: Literal["itemGroups.update"]
    args: UpdateItemGroupArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


class MutationUploadItemFile(StrictModel):
    workflow: Literal["itemFiles.upload"]
    args: UploadItemFileArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


class MutationUpdateItemFile(StrictModel):
    workflow: Literal["itemFiles.update"]
    args: UpdateItemFileArgs
    dry_run: StrictBool = Field(default=True, alias="dryRun")


ReadCallModel: TypeAlias = (
    ReadWorkspaceMap | ReadItemsSearch | ReadCommentsThread | ReadExportItems
)
MutationCallModel: TypeAlias = (
    MutationCreateItem
    | MutationUpdateFields
    | MutationAddComment
    | MutationCreateItemGroup
    | MutationUpdateItemGroup
    | MutationUploadItemFile
    | MutationUpdateItemFile
)
ReadWorkflowCall: TypeAlias = Annotated[
    ReadCallModel,
    Field(discriminator="workflow"),
]
MutationWorkflowCall: TypeAlias = Annotated[
    MutationCallModel,
    Field(discriminator="workflow"),
]


class PlanCreateItem(StrictModel):
    operation: Literal["createItem"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    body: ItemCreateRequest


class PlanUpdateItemFields(StrictModel):
    operation: Literal["updateItemFields"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    body: FieldUpdates


class PlanCreateComment(StrictModel):
    operation: Literal["createItemComment"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    body: CommentRequest


class PlanUpdateComment(StrictModel):
    operation: Literal["updateItemComment"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    item_comment_id: CanonicalId = Field(alias="itemCommentId")
    body: CommentRequest


class PlanCreateItemGroup(StrictModel):
    operation: Literal["createItemGroup"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    body: ItemGroupCreateRequest


class PlanUpdateItemGroup(StrictModel):
    operation: Literal["updateItemGroup"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_group_id: CanonicalId = Field(alias="itemGroupId")
    body: ItemGroupUpdateRequest


class PlanUpdateItemFile(StrictModel):
    operation: Literal["updateItemFile"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    item_file_id: CanonicalId = Field(alias="itemFileId")
    body: ItemFileUpdateRequest


class PlanUploadItemFile(StrictModel):
    operation: Literal["uploadItemFile"]
    space_id: CanonicalId = Field(alias="spaceId")
    board_id: CanonicalId = Field(alias="boardId")
    item_id: CanonicalId = Field(alias="itemId")
    body: Base64UploadBody


PlanMutationModel: TypeAlias = (
    PlanCreateItem
    | PlanUpdateItemFields
    | PlanCreateComment
    | PlanUpdateComment
    | PlanCreateItemGroup
    | PlanUpdateItemGroup
    | PlanUpdateItemFile
    | PlanUploadItemFile
)
PlanMutationCall: TypeAlias = Annotated[PlanMutationModel, Field(discriminator="operation")]

_READ_ADAPTER: TypeAdapter[ReadCallModel] = TypeAdapter(ReadWorkflowCall)
_MUTATION_ADAPTER: TypeAdapter[MutationCallModel] = TypeAdapter(MutationWorkflowCall)
_PLAN_MUTATION_ADAPTER: TypeAdapter[PlanMutationModel] = TypeAdapter(PlanMutationCall)
READ_WORKFLOW_SCHEMA = _READ_ADAPTER.json_schema()
MUTATION_WORKFLOW_SCHEMA = _MUTATION_ADAPTER.json_schema()
PLAN_MUTATION_SCHEMA = _PLAN_MUTATION_ADAPTER.json_schema()
# MCP requires an object root even when a JSON Schema discriminated union uses
# ``oneOf`` at that root. The union and discriminator remain the owner of the
# accepted member shape.
READ_WORKFLOW_SCHEMA["type"] = "object"
MUTATION_WORKFLOW_SCHEMA["type"] = "object"
PLAN_MUTATION_SCHEMA["type"] = "object"
# The root must declare these members as well as each ``oneOf`` branch.
# Otherwise root-level ``additionalProperties: false`` rejects every valid
# branch before the discriminator can select it.
READ_WORKFLOW_SCHEMA["properties"] = {"workflow": {}, "args": {}}
MUTATION_WORKFLOW_SCHEMA["properties"] = {"workflow": {}, "args": {}, "dryRun": {}}
PLAN_MUTATION_SCHEMA["properties"] = {
    "operation": {},
    "spaceId": {},
    "boardId": {},
    "itemId": {},
    "itemCommentId": {},
    "itemGroupId": {},
    "itemFileId": {},
    "body": {},
}
READ_WORKFLOW_SCHEMA["additionalProperties"] = False
MUTATION_WORKFLOW_SCHEMA["additionalProperties"] = False
PLAN_MUTATION_SCHEMA["additionalProperties"] = False


def validate_read_workflow(workflow: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    call = _READ_ADAPTER.validate_python({"workflow": workflow, "args": args})
    return call.workflow, call.args.model_dump(by_alias=True, mode="json", exclude_none=True)


def validate_mutation_workflow(
    workflow: str,
    args: dict[str, Any],
    dry_run: bool,
) -> tuple[str, dict[str, Any], bool]:
    call = _MUTATION_ADAPTER.validate_python(
        {"workflow": workflow, "args": args, "dryRun": dry_run}
    )
    return (
        call.workflow,
        call.args.model_dump(by_alias=True, mode="json", exclude_none=True),
        call.dry_run,
    )


def validate_plan_mutation(values: dict[str, Any]) -> dict[str, Any]:
    call = _PLAN_MUTATION_ADAPTER.validate_python(values)
    return call.model_dump(by_alias=True, mode="json", exclude_none=True)
