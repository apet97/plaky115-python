"""Branded ID types and canonicalization.

Path IDs are canonical non-negative signed-int64 decimals; malformed IDs
fail before any network I/O. Field keys are ordinary validated strings and
use path encoding, not int64 validation. Ported from sdk/src/client/path.ts
at the pinned source (see docs/port/spec-helpers.md).
"""

from __future__ import annotations

import re
from typing import NewType
from urllib.parse import quote

SpaceId = NewType("SpaceId", str)
BoardId = NewType("BoardId", str)
ItemId = NewType("ItemId", str)
CommentId = NewType("CommentId", str)
FieldKey = NewType("FieldKey", str)
UserId = NewType("UserId", str)
TeamId = NewType("TeamId", str)
ItemGroupId = NewType("ItemGroupId", str)
ItemFileId = NewType("ItemFileId", str)
FolderId = NewType("FolderId", str)

INT64_MAX = 9223372036854775807

_CANONICAL_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*)$")

IdInput = int | str

_NUMBER_ID_MESSAGE = (
    "ID numbers must be non-negative safe integers; use a decimal string for larger int64 IDs"
)
_STRING_ID_MESSAGE = "IDs must be canonical non-negative signed int64 decimal strings"


def id_path_segment(value: IdInput) -> str:
    """Canonicalize one path ID; raises ValueError before any I/O."""
    if isinstance(value, bool):
        raise ValueError(_STRING_ID_MESSAGE)
    if isinstance(value, int):
        if value < 0 or value > INT64_MAX:
            raise ValueError(_NUMBER_ID_MESSAGE)
        return str(value)
    if not isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError(_STRING_ID_MESSAGE)
    if not _CANONICAL_DECIMAL.fullmatch(value) or int(value) > INT64_MAX:
        raise ValueError(_STRING_ID_MESSAGE)
    return value


def as_space_id(value: IdInput) -> SpaceId:
    return SpaceId(id_path_segment(value))


def as_board_id(value: IdInput) -> BoardId:
    return BoardId(id_path_segment(value))


def as_item_id(value: IdInput) -> ItemId:
    return ItemId(id_path_segment(value))


def as_comment_id(value: IdInput) -> CommentId:
    return CommentId(id_path_segment(value))


def as_user_id(value: IdInput) -> UserId:
    return UserId(id_path_segment(value))


def as_team_id(value: IdInput) -> TeamId:
    return TeamId(id_path_segment(value))


def as_item_group_id(value: IdInput) -> ItemGroupId:
    return ItemGroupId(id_path_segment(value))


def as_item_file_id(value: IdInput) -> ItemFileId:
    return ItemFileId(id_path_segment(value))


def as_folder_id(value: IdInput) -> FolderId:
    return FolderId(id_path_segment(value))


def as_field_key(value: str) -> FieldKey:
    """Field keys are ordinary strings; path-encoded rather than int64-checked."""
    if not isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError("itemFieldKey must be a string")
    if not value:
        raise ValueError("itemFieldKey must be non-empty")
    return FieldKey(value)


def encode_path_segment(value: str) -> str:
    """Percent-encode one URL path segment (encodeURIComponent semantics)."""
    return quote(value, safe="-_.!~*'()")
