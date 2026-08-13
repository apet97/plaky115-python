"""Mutation plan normalizers.

Ported from sdk/src/workflows/mutation-plans.ts at the pinned source
(docs/port/spec-helpers.md §5). Every normalizer validates locally, before
any network access, and returns an immutable plan with exactly one write.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, cast

from plaky115.ids import id_path_segment
from plaky115.runtime.upload import (
    MAX_UPLOAD_BYTES_HARD_CEILING,
    Base64UploadInput,
    NormalizedUpload,
    UploadMetadata,
    normalize_upload,
    validate_binary_upload,
    validate_upload_file_name,
)

_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class UploadDigest:
    file_name: str
    media_type: str
    decoded_bytes: int
    sha256: str | None = None


@dataclass(frozen=True)
class NormalizedMutationPlan:
    version: int
    operation_id: str
    target_ids: MappingProxyType[str, str]
    body: MappingProxyType[str, Any]
    write_count: int
    requires_live_resolution: bool
    upload: UploadDigest | None = None


@dataclass(frozen=True)
class DryRunPlan:
    """User-facing dry-run result: what one write would send, unexecuted."""

    dry_run: bool
    operation: str
    payload: dict[str, Any]
    target_ids: dict[str, str]
    write_count: int
    requires_live_resolution: bool


def plan_to_dry_run(plan: NormalizedMutationPlan) -> DryRunPlan:
    return DryRunPlan(
        dry_run=True,
        operation=plan.operation_id,
        payload={**dict(plan.target_ids), "body": dict(plan.body)},
        target_ids=dict(plan.target_ids),
        write_count=plan.write_count,
        requires_live_resolution=plan.requires_live_resolution,
    )


def _plain_body(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be a plain object")
    return cast(dict[str, Any], value)


def _canonical_id(value: Any, label: str) -> str:
    if not isinstance(value, int | str) or isinstance(value, bool):
        raise TypeError(f"{label} must be a number or decimal string")
    try:
        return id_path_segment(value)
    except ValueError as exc:
        raise TypeError(f"{label}: {exc}") from None


def _require_string(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"body.{key} must be a non-empty string")
    return value


def _optional_string(body: dict[str, Any], key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"body.{key} must be a non-empty string when provided")
    return value


def _require_color(body: dict[str, Any]) -> str:
    value = body.get("color")
    if not isinstance(value, str) or not _COLOR.fullmatch(value):
        raise TypeError("body.color must be a six-digit RGB hexadecimal color")
    return value


def _plan(
    operation_id: str,
    target_ids: dict[str, str],
    body: dict[str, Any],
    *,
    requires_live_resolution: bool = False,
    upload: UploadDigest | None = None,
) -> NormalizedMutationPlan:
    return NormalizedMutationPlan(
        version=1,
        operation_id=operation_id,
        target_ids=MappingProxyType(dict(target_ids)),
        body=MappingProxyType(dict(body)),
        write_count=1,
        requires_live_resolution=requires_live_resolution,
        upload=upload,
    )


def normalize_item_create_plan(
    *, space_id: int | str, board_id: int | str, body: Any
) -> NormalizedMutationPlan:
    payload = dict(_plain_body(body, "body"))
    if payload.get("groupId") is not None and payload.get("groupTitle") is not None:
        raise TypeError("body.groupId and body.groupTitle cannot both be provided")
    if payload.get("groupId") is not None:
        payload["groupId"] = _canonical_id(payload["groupId"], "body.groupId")
    if payload.get("parentId") is not None:
        payload["parentId"] = _canonical_id(payload["parentId"], "body.parentId")
    group_title = payload.get("groupTitle")
    if group_title is not None and (not isinstance(group_title, str) or not group_title.strip()):
        raise TypeError("body.groupTitle must be a non-empty string")
    return _plan(
        "createItem",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
        },
        payload,
        requires_live_resolution=group_title is not None,
    )


def normalize_item_update_fields_plan(
    *, space_id: int | str, board_id: int | str, item_id: int | str, body: Any
) -> NormalizedMutationPlan:
    payload = _plain_body(body, "body")
    return _plan(
        "updateItemFields",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
            "itemId": _canonical_id(item_id, "itemId"),
        },
        payload,
    )


def normalize_comment_plan(
    *,
    space_id: int | str,
    board_id: int | str,
    item_id: int | str,
    body: Any,
    item_comment_id: int | str | None = None,
    operation_id: str = "createItemComment",
) -> NormalizedMutationPlan:
    payload = _plain_body(body, "body")
    _require_string(payload, "text")
    target_ids = {
        "spaceId": _canonical_id(space_id, "spaceId"),
        "boardId": _canonical_id(board_id, "boardId"),
        "itemId": _canonical_id(item_id, "itemId"),
    }
    if item_comment_id is not None:
        target_ids["itemCommentId"] = _canonical_id(item_comment_id, "itemCommentId")
    return _plan(operation_id, target_ids, payload)


def normalize_item_group_create_plan(
    *, space_id: int | str, board_id: int | str, body: Any
) -> NormalizedMutationPlan:
    payload = _plain_body(body, "body")
    _require_string(payload, "title")
    _require_color(payload)
    _optional_string(payload, "ranking")
    return _plan(
        "createItemGroup",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
        },
        payload,
    )


def normalize_item_group_update_plan(
    *, space_id: int | str, board_id: int | str, item_group_id: int | str, body: Any
) -> NormalizedMutationPlan:
    payload = _plain_body(body, "body")
    _require_string(payload, "title")
    _require_string(payload, "ranking")
    _require_color(payload)
    return _plan(
        "updateItemGroup",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
            "itemGroupId": _canonical_id(item_group_id, "itemGroupId"),
        },
        payload,
    )


def normalize_item_file_update_plan(
    *,
    space_id: int | str,
    board_id: int | str,
    item_id: int | str,
    item_file_id: int | str,
    body: Any,
) -> NormalizedMutationPlan:
    payload = _plain_body(body, "body")
    validate_upload_file_name(cast(str, payload.get("name")))
    return _plan(
        "updateItemFile",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
            "itemId": _canonical_id(item_id, "itemId"),
            "itemFileId": _canonical_id(item_file_id, "itemFileId"),
        },
        payload,
    )


@dataclass(frozen=True)
class NormalizedUploadPlan:
    plan: NormalizedMutationPlan
    upload: NormalizedUpload = field(compare=False)


def normalize_base64_upload_plan(
    *,
    space_id: int | str,
    board_id: int | str,
    item_id: int | str,
    upload: Base64UploadInput,
    max_bytes: int = MAX_UPLOAD_BYTES_HARD_CEILING,
) -> NormalizedUploadPlan:
    """Normalize an MCP-style base64 upload. Base64 is never echoed in the plan."""
    normalized = normalize_upload(upload, max_bytes)
    plan = _plan(
        "uploadItemFile",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
            "itemId": _canonical_id(item_id, "itemId"),
        },
        {},
        upload=UploadDigest(
            file_name=normalized.file_name,
            media_type=normalized.media_type,
            decoded_bytes=normalized.decoded_bytes,
            sha256=normalized.sha256,
        ),
    )
    return NormalizedUploadPlan(plan=plan, upload=normalized)


def normalize_binary_upload_plan(
    *,
    space_id: int | str,
    board_id: int | str,
    item_id: int | str,
    file: bytes | bytearray | memoryview,
    file_name: str | None = None,
    content_type: str | None = None,
) -> tuple[NormalizedMutationPlan, UploadMetadata]:
    """Normalize an SDK binary upload (bytes, explicit filename)."""
    metadata = validate_binary_upload(file, file_name, content_type)
    plan = _plan(
        "uploadItemFile",
        {
            "spaceId": _canonical_id(space_id, "spaceId"),
            "boardId": _canonical_id(board_id, "boardId"),
            "itemId": _canonical_id(item_id, "itemId"),
        },
        {},
        upload=UploadDigest(
            file_name=metadata.file_name,
            media_type=metadata.media_type,
            decoded_bytes=metadata.decoded_bytes,
        ),
    )
    return plan, metadata
