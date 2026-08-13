"""Bounded chunk reads with exact continuation cursors.

Ported from sdk/src/runtime/chunks.ts at the pinned source
(docs/port/spec-helpers.md). Byte accounting uses UTF-8 encoded bytes of
each serialized item.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from plaky115.errors import (
    PlakyMaterializationLimitError,
    PlakyOutputLimitError,
    PlakyResponseContractError,
)
from plaky115.pagination import assert_paged_result

T = TypeVar("T")

DEFAULT_CHUNK_MAX_ITEMS = 100
DEFAULT_CHUNK_MAX_BYTES = 1_048_576
MAX_MATERIALIZED_ITEMS = 10_000
MAX_MATERIALIZED_BYTES = 16_777_216

MAX_SAFE_INTEGER = 9007199254740991


def utf8_byte_length(value: str) -> int:
    """Length of a string in UTF-8 encoded bytes, not characters."""
    return len(value.encode("utf-8"))


@dataclass(frozen=True)
class PageCursor:
    page: int = 1
    index: int = 0


@dataclass(frozen=True)
class BoundedChunk(Generic[T]):
    data: tuple[T, ...]
    scanned: int
    returned: int
    bytes: int
    complete: bool
    truncated: bool
    next_cursor: PageCursor | None = None


def _validate_positive(value: int, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > MAX_SAFE_INTEGER
    ):
        raise ValueError(f"{name} must be a positive safe integer.")
    return value


def _validate_non_negative(value: int, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_SAFE_INTEGER
    ):
        raise ValueError(f"{name} must be a non-negative safe integer.")
    return value


def normalize_cursor(cursor: PageCursor | None) -> tuple[int, int]:
    page = cursor.page if cursor is not None else 1
    index = cursor.index if cursor is not None else 0
    _validate_positive(page, "cursor.page")
    _validate_non_negative(index, "cursor.index")
    return page, index


def default_serialize(value: Any) -> str:
    import json

    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


PageFetcher = Callable[[int, int], Awaitable[dict[str, Any]]]


async def read_paged_chunk(
    fetcher: PageFetcher,
    *,
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    cursor: PageCursor | None = None,
    serialize: Callable[[Any], str] = default_serialize,
) -> BoundedChunk[Any]:
    """Read one bounded chunk; the cursor resumes at the first omitted item."""
    _validate_positive(page_size, "pageSize")
    _validate_non_negative(max_items, "maxItems")
    _validate_non_negative(max_bytes, "maxBytes")
    if max_items == 0:
        raise PlakyOutputLimitError("items", 0)

    page, index = normalize_cursor(cursor)
    data: list[Any] = []
    total_bytes = 0

    while True:
        raw_page = await fetcher(page, page_size)
        checked = assert_paged_result(raw_page, "boundedChunk")
        items: list[Any] = checked["data"]
        has_more: bool = checked["hasMore"]
        if index > len(items):
            raise PlakyResponseContractError("boundedChunk", "/data")

        while index < len(items):
            if len(data) >= max_items:
                return BoundedChunk(
                    data=tuple(data),
                    scanned=len(data),
                    returned=len(data),
                    bytes=total_bytes,
                    complete=False,
                    truncated=True,
                    next_cursor=PageCursor(page=page, index=index),
                )
            item = items[index]
            item_bytes = utf8_byte_length(serialize(item))
            if total_bytes + item_bytes > max_bytes:
                if len(data) == 0:
                    # A single item larger than the byte budget can never be
                    # returned; skipping it silently would corrupt the export.
                    raise PlakyOutputLimitError("bytes", max_bytes)
                return BoundedChunk(
                    data=tuple(data),
                    scanned=len(data),
                    returned=len(data),
                    bytes=total_bytes,
                    complete=False,
                    truncated=True,
                    next_cursor=PageCursor(page=page, index=index),
                )
            data.append(item)
            total_bytes += item_bytes
            index += 1

        if has_more and (len(data) >= max_items or total_bytes >= max_bytes):
            return BoundedChunk(
                data=tuple(data),
                scanned=len(data),
                returned=len(data),
                bytes=total_bytes,
                complete=False,
                truncated=True,
                next_cursor=PageCursor(page=page + 1, index=0),
            )
        if not has_more:
            return BoundedChunk(
                data=tuple(data),
                scanned=len(data),
                returned=len(data),
                bytes=total_bytes,
                complete=True,
                truncated=False,
                next_cursor=None,
            )
        page += 1
        index = 0


async def iterate_paged_chunks(
    fetcher: PageFetcher,
    *,
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    cursor: PageCursor | None = None,
    serialize: Callable[[Any], str] = default_serialize,
) -> AsyncIterator[BoundedChunk[Any]]:
    """Lazily yield bounded chunks until the collection is exhausted."""
    current = cursor
    while True:
        chunk = await read_paged_chunk(
            fetcher,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=current,
            serialize=serialize,
        )
        yield chunk
        if chunk.next_cursor is None:
            return
        current = chunk.next_cursor


def assert_materialized_collection(
    items: list[Any],
    max_items: int,
    max_bytes: int,
    serialize: Callable[[Any], str] = default_serialize,
) -> None:
    """Guard a fully materialized collection against runaway size."""
    if len(items) > max_items:
        raise PlakyMaterializationLimitError("items", max_items)
    total = 0
    for item in items:
        total += utf8_byte_length(serialize(item))
        if total > max_bytes:
            raise PlakyMaterializationLimitError("bytes", max_bytes)
