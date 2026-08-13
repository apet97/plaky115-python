"""Hand-written common models and exact public enums (plan section 7.3)."""

from __future__ import annotations

from enum import StrEnum


class SpaceExpand(StrEnum):
    BOARD = "board"


class ItemExpand(StrEnum):
    SPACE = "space"
    BOARD = "board"
    GROUP = "group"
    CREATED_BY = "createdBy"
    PARENT = "parent"
    SUBSCRIPTIONS = "subscriptions"
    FIELDS = "fields"


class SubitemsBehaviour(StrEnum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    EMBED = "EMBED"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"


class UserType(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"
