"""Response-model compatibility layer over the generated schemas.

Friendly names map onto the generated OpenAPI models. Comment adds the
deprecated read-only ``text`` property mirroring the API ``content`` field.
"""

from __future__ import annotations

from typing import cast

from plaky115.models.generated import (
    BoardResponse,
    CommentResponse,
    FolderResponse,
    ItemAttributeDefinition,
    ItemFieldResponse,
    ItemFileDownloadResponse,
    ItemFileResponse,
    ItemGroupResponse,
    ItemResponse,
    ReactionPutResponse,
    ReactionResponse,
    ShortUserResponse,
    SpaceResponse,
    TeamResponse,
    TeamShortResponse,
    UserResponse,
)
from plaky115.models.generated import (
    Reaction as ReactionDetail,
)

# Friendly aliases: generated response models are the single source of shape.
Space = SpaceResponse
Board = BoardResponse
Item = ItemResponse
ItemField = ItemFieldResponse
Field = ItemAttributeDefinition
Folder = FolderResponse
ItemGroup = ItemGroupResponse
ItemFile = ItemFileResponse
ItemFileDownload = ItemFileDownloadResponse
User = UserResponse
ShortUser = ShortUserResponse
Team = TeamResponse
TeamShort = TeamShortResponse
Reaction = ReactionResponse
ReactionReplaceResult = ReactionPutResponse

__all__ = [
    "Board",
    "Comment",
    "Field",
    "Folder",
    "Item",
    "ItemField",
    "ItemFile",
    "ItemFileDownload",
    "ItemGroup",
    "Reaction",
    "ReactionDetail",
    "ReactionReplaceResult",
    "ShortUser",
    "Space",
    "Team",
    "TeamShort",
    "User",
    "field_label",
]


class Comment(CommentResponse):
    """Comment response with the deprecated ``text`` compatibility property."""

    @property
    def text(self) -> str | None:
        """Deprecated: read-only mirror of ``content``. Use ``content``."""
        return self.content


def field_label(field: object) -> str:
    """Human label for a field definition: name, then title, then key."""
    for attribute in ("name", "title", "key"):
        value: object = None
        if isinstance(field, dict):
            value = cast("dict[str, object]", field).get(attribute)
        else:
            value = getattr(field, attribute, None)
        if isinstance(value, str) and value:
            return value
    return ""
