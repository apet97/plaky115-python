"""Bounded workspace map: compact spaces/boards tree.

Ported from sdk/src/workflows workspaceMap at the pinned source
(docs/port/spec-helpers.md §8.1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from plaky115.errors import PlakyMaterializationLimitError
from plaky115.resolvers import _entity_value  # pyright: ignore[reportPrivateUsage]
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.chunks import (
    MAX_MATERIALIZED_BYTES,
    MAX_MATERIALIZED_ITEMS,
    assert_materialized_collection,
    utf8_byte_length,
)

if TYPE_CHECKING:
    from plaky115.async_client import AsyncPlakyClient
    from plaky115.client import PlakyClient

__all__ = ["async_workspace_map", "workspace_map"]


def _validate_bound(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative safe integer.")
    return value


def _entry_bytes(entry: dict[str, Any]) -> int:
    import json

    return utf8_byte_length(json.dumps(entry, separators=(",", ":"), default=str))


def _as_dict(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    return value


def _space_entry(space: Any, boards: list[Any]) -> dict[str, Any]:
    return {
        "id": _entity_value(space, "id"),
        "title": _entity_value(space, "title"),
        "boards": [_as_dict(board) for board in boards],
    }


async def async_workspace_map(
    client: AsyncPlakyClient,
    *,
    max_items: int = MAX_MATERIALIZED_ITEMS,
    max_bytes: int = MAX_MATERIALIZED_BYTES,
    options: RequestOverrides | None = None,
) -> list[dict[str, Any]]:
    _validate_bound(max_items, "maxItems")
    _validate_bound(max_bytes, "maxBytes")
    spaces = await client.spaces.list_all(expand=["board"], limit=max_items + 1, options=options)
    assert_materialized_collection(
        [s.model_dump(by_alias=True, exclude_none=True) for s in spaces], max_items, max_bytes
    )
    out: list[dict[str, Any]] = []
    output_bytes = 0
    for space in spaces:
        boards = _entity_value(space, "boards")
        resolved_boards: list[Any]
        if isinstance(boards, list):
            resolved_boards = list(cast("list[Any]", boards))
        elif _entity_value(space, "id") is not None:
            resolved_boards = list(
                await client.boards.list_all(
                    space_id=str(_entity_value(space, "id")),
                    limit=max_items + 1,
                    options=options,
                )
            )
        else:
            resolved_boards = []
        assert_materialized_collection(
            [_as_dict(b) for b in resolved_boards], max_items, max_bytes
        )
        entry = _space_entry(space, resolved_boards)
        output_bytes += _entry_bytes(entry)
        if output_bytes > max_bytes:
            raise PlakyMaterializationLimitError("bytes", max_bytes)
        out.append(entry)
    return out


def workspace_map(
    client: PlakyClient,
    *,
    max_items: int = MAX_MATERIALIZED_ITEMS,
    max_bytes: int = MAX_MATERIALIZED_BYTES,
    options: RequestOverrides | None = None,
) -> list[dict[str, Any]]:
    _validate_bound(max_items, "maxItems")
    _validate_bound(max_bytes, "maxBytes")
    spaces = client.spaces.list_all(expand=["board"], limit=max_items + 1, options=options)
    assert_materialized_collection(
        [s.model_dump(by_alias=True, exclude_none=True) for s in spaces], max_items, max_bytes
    )
    out: list[dict[str, Any]] = []
    output_bytes = 0
    for space in spaces:
        boards = _entity_value(space, "boards")
        resolved_boards: list[Any]
        if isinstance(boards, list):
            resolved_boards = list(cast("list[Any]", boards))
        elif _entity_value(space, "id") is not None:
            resolved_boards = list(
                client.boards.list_all(
                    space_id=str(_entity_value(space, "id")),
                    limit=max_items + 1,
                    options=options,
                )
            )
        else:
            resolved_boards = []
        assert_materialized_collection(
            [_as_dict(b) for b in resolved_boards], max_items, max_bytes
        )
        entry = _space_entry(space, resolved_boards)
        output_bytes += _entry_bytes(entry)
        if output_bytes > max_bytes:
            raise PlakyMaterializationLimitError("bytes", max_bytes)
        out.append(entry)
    return out
