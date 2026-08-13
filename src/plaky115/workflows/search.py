"""Item search with nested scalar traversal and exact continuation.

Ported from sdk/src/workflows (searchItemsDetailed / searchItems) at the
pinned source (docs/port/spec-helpers.md §8.2).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from plaky115.resolvers import (
    EntityRef,
    _canonical_id,  # pyright: ignore[reportPrivateUsage]
    _entity_value,  # pyright: ignore[reportPrivateUsage]
    async_resolve_space_and_board,
    resolve_space_and_board,
)
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.chunks import PageCursor

if TYPE_CHECKING:
    from plaky115.async_client import AsyncPlakyClient
    from plaky115.client import PlakyClient

__all__ = [
    "ItemSearchResult",
    "async_search_items",
    "async_search_items_detailed",
    "search_items",
    "search_items_detailed",
]

DEFAULT_SEARCH_LIMIT = 200


@dataclass(frozen=True)
class ItemSearchResult:
    data: tuple[Any, ...]
    scanned: int
    matched: int
    complete: bool
    truncated: bool
    continuation: PageCursor | None = None


def _searchable_scalars(value: Any) -> list[str]:
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, str | int | float):
        return [str(value)]
    if isinstance(value, list | tuple):
        seq = cast("Sequence[Any]", value)
        return [scalar for entry in seq for scalar in _searchable_scalars(entry)]
    if isinstance(value, Mapping):
        record = cast("Mapping[str, Any]", value)
        return [
            scalar for key in sorted(record.keys()) for scalar in _searchable_scalars(record[key])
        ]
    return []


def _item_matches(item: Any, needle: str) -> bool:
    title = _entity_value(item, "title")
    if isinstance(title, str) and needle in title.lower():
        return True
    fields = _entity_value(item, "fields")
    if not isinstance(fields, list):
        return False
    for field in cast("list[Any]", fields):
        value = _entity_value(field, "value") if field is not None else None
        if value is None:
            continue
        if any(needle in scalar.lower() for scalar in _searchable_scalars(value)):
            return True
    return False


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a finite positive integer")


def _validate_cursor(cursor: PageCursor | None) -> tuple[int, int]:
    page = cursor.page if cursor is not None else 1
    index = cursor.index if cursor is not None else 0
    if (
        isinstance(page, bool)
        or not isinstance(page, int)
        or page <= 0
        or isinstance(index, bool)
        or not isinstance(index, int)
        or index < 0
    ):
        raise ValueError("cursor must contain a positive page and non-negative index")
    return page, index


PageFetch = Callable[[int, int], Awaitable[Any]]


async def _search_core(
    fetch_page: PageFetch,
    *,
    query: str,
    limit: int,
    cursor: PageCursor | None,
    on_progress: Callable[[int, int], Awaitable[None] | None] | None,
) -> ItemSearchResult:
    needle = query.lower()
    page, index = _validate_cursor(cursor)
    scanned = 0
    data: list[Any] = []

    while scanned < limit:
        response = await fetch_page(page, min(100, limit - scanned))
        items = list(response.data)
        has_more = response.has_more
        if index > len(items):
            raise ValueError(f"item search cursor index {index} exceeds page {page} length")
        page_items = items[index : index + (limit - scanned)]
        for item in page_items:
            scanned += 1
            if _item_matches(item, needle):
                data.append(item)
        if on_progress is not None:
            result = on_progress(scanned, limit)
            if result is not None and hasattr(result, "__await__"):
                await result
        page_index = index + len(page_items)
        page_has_unconsumed = page_index < len(items)
        if scanned >= limit and (has_more or page_has_unconsumed):
            return ItemSearchResult(
                data=tuple(data),
                scanned=scanned,
                matched=len(data),
                complete=False,
                truncated=True,
                continuation=PageCursor(page=page, index=page_index),
            )
        if not has_more:
            return ItemSearchResult(
                data=tuple(data),
                scanned=scanned,
                matched=len(data),
                complete=True,
                truncated=False,
            )
        if not items:
            raise ValueError(f"item search page {page} was empty while hasMore was true")
        page += 1
        index = 0

    return ItemSearchResult(
        data=tuple(data),
        scanned=scanned,
        matched=len(data),
        complete=False,
        truncated=True,
        continuation=PageCursor(page=page, index=index),
    )


async def async_search_items_detailed(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    cursor: PageCursor | None = None,
    on_progress: Callable[[int, int], Awaitable[None] | None] | None = None,
    options: RequestOverrides | None = None,
) -> ItemSearchResult:
    _validate_limit(limit)
    resolved_space, resolved_board = await async_resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    space_id = _canonical_id(_entity_value(resolved_space, "id"))
    board_id = _canonical_id(_entity_value(resolved_board, "id"))

    async def fetch_page(page: int, page_size: int) -> Any:
        return await client.items.list(
            space_id=space_id,
            board_id=board_id,
            page=page,
            page_size=page_size,
            options=options,
        )

    return await _search_core(
        fetch_page, query=query, limit=limit, cursor=cursor, on_progress=on_progress
    )


async def async_search_items(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    options: RequestOverrides | None = None,
) -> list[Any]:
    """Deprecated: use async_search_items_detailed for continuation metadata."""
    result = await async_search_items_detailed(
        client, space=space, board=board, query=query, limit=limit, options=options
    )
    return list(result.data)


def search_items_detailed(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    cursor: PageCursor | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    options: RequestOverrides | None = None,
) -> ItemSearchResult:
    _validate_limit(limit)
    resolved_space, resolved_board = resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    space_id = _canonical_id(_entity_value(resolved_space, "id"))
    board_id = _canonical_id(_entity_value(resolved_board, "id"))

    needle = query.lower()
    page, index = _validate_cursor(cursor)
    scanned = 0
    data: list[Any] = []

    while scanned < limit:
        response = client.items.list(
            space_id=space_id,
            board_id=board_id,
            page=page,
            page_size=min(100, limit - scanned),
            options=options,
        )
        items = list(response.data)
        has_more = response.has_more
        if index > len(items):
            raise ValueError(f"item search cursor index {index} exceeds page {page} length")
        page_items = items[index : index + (limit - scanned)]
        for item in page_items:
            scanned += 1
            if _item_matches(item, needle):
                data.append(item)
        if on_progress is not None:
            on_progress(scanned, limit)
        page_index = index + len(page_items)
        page_has_unconsumed = page_index < len(items)
        if scanned >= limit and (has_more or page_has_unconsumed):
            return ItemSearchResult(
                data=tuple(data),
                scanned=scanned,
                matched=len(data),
                complete=False,
                truncated=True,
                continuation=PageCursor(page=page, index=page_index),
            )
        if not has_more:
            return ItemSearchResult(
                data=tuple(data),
                scanned=scanned,
                matched=len(data),
                complete=True,
                truncated=False,
            )
        if not items:
            raise ValueError(f"item search page {page} was empty while hasMore was true")
        page += 1
        index = 0

    return ItemSearchResult(
        data=tuple(data),
        scanned=scanned,
        matched=len(data),
        complete=False,
        truncated=True,
        continuation=PageCursor(page=page, index=index),
    )


def search_items(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    options: RequestOverrides | None = None,
) -> list[Any]:
    """Deprecated: use search_items_detailed for continuation metadata."""
    result = search_items_detailed(
        client, space=space, board=board, query=query, limit=limit, options=options
    )
    return list(result.data)
