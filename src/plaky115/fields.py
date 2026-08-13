"""Field-value builders for item creation and updates.

Ported from sdk/src/fields at the pinned source (docs/port/spec-helpers.md
§6). Builders are deliberately thin; the server owns field-type semantics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "field_values",
    "link_field",
    "number_field",
    "omit_none",
    "person_field",
    "status_field",
    "string_field",
    "tag_field",
    "timeline_field",
]


def field_values(values: Mapping[str, Any]) -> dict[str, Any]:
    """Open field-value map keyed by field key or title."""
    return dict(values)


def omit_none(values: Mapping[str, Any]) -> dict[str, Any]:
    """Remove absent optional values (None) from a mapping."""
    return {key: value for key, value in values.items() if value is not None}


def string_field(value: str) -> str:
    return value


def status_field(value: str | int) -> str | int:
    """A status by label or ID."""
    return value


def tag_field(values: Sequence[str | int]) -> list[str | int]:
    """Tags by label or ID."""
    return list(values)


def person_field(
    *,
    users: Sequence[int | Mapping[str, Any]] | None = None,
    teams: Sequence[int | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize user/team references; bare integers become {"id": n}."""

    def normalize(refs: Sequence[int | Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [{"id": ref} if isinstance(ref, int) else dict(ref) for ref in refs]

    out: dict[str, Any] = {}
    if users is not None:
        out["users"] = normalize(users)
    if teams is not None:
        out["teams"] = normalize(teams)
    return out


def timeline_field(*, start: str, end: str) -> dict[str, str]:
    if not start or not end:
        raise ValueError("timelineField: both start and end are required (ISO date strings)")
    return {"start": start, "end": end}


def link_field(*, url: str, text: str | None = None) -> dict[str, str]:
    if not url:
        raise ValueError("linkField: url is required")
    out = {"url": url}
    if text is not None:
        out["text"] = text
    return out


def number_field(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError("numberField: value must be a finite number")
    return value
