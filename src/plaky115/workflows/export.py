"""Item export (JSONL/CSV) and bounded chunk readers.

Ported from sdk/src/workflows exportItems / readItemChunk /
readItemExportChunk and their iterators at the pinned source
(docs/port/spec-helpers.md §8.5-8.6).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from plaky115.errors import PlakyMaterializationLimitError
from plaky115.resolvers import (
    EntityRef,
    _canonical_id,  # pyright: ignore[reportPrivateUsage]
    _entity_value,  # pyright: ignore[reportPrivateUsage]
    async_resolve_space_and_board,
    resolve_space_and_board,
)
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.chunks import (
    DEFAULT_CHUNK_MAX_BYTES,
    DEFAULT_CHUNK_MAX_ITEMS,
    MAX_MATERIALIZED_BYTES,
    MAX_MATERIALIZED_ITEMS,
    BoundedChunk,
    PageCursor,
    assert_materialized_collection,
    read_paged_chunk,
    sync_read_paged_chunk,
    utf8_byte_length,
)
from plaky115.workflows.csv import (
    CsvSafety,
    CsvSchema,
    create_items_csv_schema,
    render_item_row,
    render_items_csv,
    render_items_csv_chunk,
)

if TYPE_CHECKING:
    from plaky115.async_client import AsyncPlakyClient
    from plaky115.client import PlakyClient

__all__ = [
    "ExportFormat",
    "ItemExportChunk",
    "async_export_items",
    "async_iterate_item_chunks",
    "async_iterate_item_export_chunks",
    "async_read_item_chunk",
    "async_read_item_export_chunk",
    "export_items",
    "iterate_item_chunks",
    "iterate_item_export_chunks",
    "read_item_chunk",
    "read_item_export_chunk",
]

ExportFormat = Literal["jsonl", "csv"]


@dataclass(frozen=True)
class ItemExportChunk:
    format: ExportFormat
    body: str
    scanned: int
    returned: int
    bytes: int
    complete: bool
    truncated: bool
    next_cursor: PageCursor | None = None


def _validate_bound(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative safe integer.")
    return value


def _item_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return item.model_dump(by_alias=True, exclude_none=True)
    return dict(item)


def _json_line(item: Any) -> str:
    return json.dumps(_item_dict(item), separators=(",", ":"), ensure_ascii=False, default=str)


def _render_jsonl(items: list[Any], max_bytes: int) -> str:
    output_bytes = 0
    lines: list[str] = []
    for index, item in enumerate(items):
        line = _json_line(item)
        separator = 1 if index > 0 else 0
        line_bytes = utf8_byte_length(line)
        if output_bytes + separator + line_bytes > max_bytes:
            raise PlakyMaterializationLimitError("bytes", max_bytes)
        output_bytes += separator + line_bytes
        lines.append(line)
    return "\n".join(lines)


def _render_csv_full(items: list[Any], safety: CsvSafety, max_bytes: int) -> str:
    output = render_items_csv([_item_dict(item) for item in items], safety)
    if utf8_byte_length(output) > max_bytes:
        raise PlakyMaterializationLimitError("bytes", max_bytes)
    return output


async def async_export_items(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    format: ExportFormat = "jsonl",
    csv_safety: CsvSafety = "spreadsheet",
    max_items: int = MAX_MATERIALIZED_ITEMS,
    max_bytes: int = MAX_MATERIALIZED_BYTES,
    options: RequestOverrides | None = None,
) -> str:
    _validate_bound(max_items, "maxItems")
    _validate_bound(max_bytes, "maxBytes")
    space_id, board_id = await _async_ids(client, space, board, options)
    items = await client.items.list_all(
        space_id=space_id, board_id=board_id, limit=max_items + 1, options=options
    )
    assert_materialized_collection([_item_dict(i) for i in items], max_items, max_bytes)
    if format == "jsonl":
        return _render_jsonl(list(items), max_bytes)
    return _render_csv_full(list(items), csv_safety, max_bytes)


def export_items(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    format: ExportFormat = "jsonl",
    csv_safety: CsvSafety = "spreadsheet",
    max_items: int = MAX_MATERIALIZED_ITEMS,
    max_bytes: int = MAX_MATERIALIZED_BYTES,
    options: RequestOverrides | None = None,
) -> str:
    _validate_bound(max_items, "maxItems")
    _validate_bound(max_bytes, "maxBytes")
    space_id, board_id = _sync_ids(client, space, board, options)
    items = client.items.list_all(
        space_id=space_id, board_id=board_id, limit=max_items + 1, options=options
    )
    assert_materialized_collection([_item_dict(i) for i in items], max_items, max_bytes)
    if format == "jsonl":
        return _render_jsonl(list(items), max_bytes)
    return _render_csv_full(list(items), csv_safety, max_bytes)


async def _async_ids(
    client: AsyncPlakyClient,
    space: EntityRef,
    board: EntityRef,
    options: RequestOverrides | None,
) -> tuple[str, str]:
    resolved_space, resolved_board = await async_resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    return (
        _canonical_id(_entity_value(resolved_space, "id")),
        _canonical_id(_entity_value(resolved_board, "id")),
    )


def _sync_ids(
    client: PlakyClient,
    space: EntityRef,
    board: EntityRef,
    options: RequestOverrides | None,
) -> tuple[str, str]:
    resolved_space, resolved_board = resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    return (
        _canonical_id(_entity_value(resolved_space, "id")),
        _canonical_id(_entity_value(resolved_board, "id")),
    )


async def async_read_item_chunk(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    cursor: PageCursor | None = None,
    options: RequestOverrides | None = None,
) -> BoundedChunk[Any]:
    space_id, board_id = await _async_ids(client, space, board, options)

    async def fetch(page: int, size: int) -> dict[str, Any]:
        result = await client.items.list(
            space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
        )
        return {"data": list(result.data), "hasMore": result.has_more}

    return await read_paged_chunk(
        fetch,
        page_size=page_size,
        max_items=max_items,
        max_bytes=max_bytes,
        cursor=cursor,
        serialize=_json_line,
    )


async def async_iterate_item_chunks(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    options: RequestOverrides | None = None,
) -> AsyncIterator[BoundedChunk[Any]]:
    cursor: PageCursor | None = None
    while True:
        chunk = await async_read_item_chunk(
            client,
            space=space,
            board=board,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=cursor,
            options=options,
        )
        yield chunk
        if chunk.next_cursor is None:
            return
        cursor = chunk.next_cursor


def read_item_chunk(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    cursor: PageCursor | None = None,
    options: RequestOverrides | None = None,
) -> BoundedChunk[Any]:
    space_id, board_id = _sync_ids(client, space, board, options)

    def fetch(page: int, size: int) -> dict[str, Any]:
        result = client.items.list(
            space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
        )
        return {"data": list(result.data), "hasMore": result.has_more}

    return sync_read_paged_chunk(
        fetch,
        page_size=page_size,
        max_items=max_items,
        max_bytes=max_bytes,
        cursor=cursor,
        serialize=_json_line,
    )


def iterate_item_chunks(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    options: RequestOverrides | None = None,
) -> Iterator[BoundedChunk[Any]]:
    cursor: PageCursor | None = None
    while True:
        chunk = read_item_chunk(
            client,
            space=space,
            board=board,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=cursor,
            options=options,
        )
        yield chunk
        if chunk.next_cursor is None:
            return
        cursor = chunk.next_cursor


@dataclass
class _CsvState:
    schema: CsvSchema
    header: str
    seed_page: dict[str, Any]
    seed_page_number: int


async def _async_csv_state(
    client: AsyncPlakyClient,
    space_id: str,
    board_id: str,
    page: int,
    page_size: int,
    safety: CsvSafety,
    options: RequestOverrides | None,
) -> _CsvState:
    board = await client.boards.get(space_id=space_id, board_id=board_id, options=options)
    definitions = _entity_value(board, "fields")
    listing = await client.items.list(
        space_id=space_id, board_id=board_id, page=page, page_size=page_size, options=options
    )
    seed = {"data": [_item_dict(i) for i in listing.data], "hasMore": listing.has_more}
    definition_dicts = (
        [_item_dict(d) for d in cast("list[Any]", definitions)]
        if isinstance(definitions, list)
        else None
    )
    schema = create_items_csv_schema(cast("list[dict[str, Any]]", seed["data"]), definition_dicts)
    header = render_items_csv_chunk([], safety, schema, include_header=True)
    return _CsvState(schema=schema, header=header, seed_page=seed, seed_page_number=page)


async def async_read_item_export_chunk(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    format: ExportFormat = "jsonl",
    csv_safety: CsvSafety = "spreadsheet",
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    cursor: PageCursor | None = None,
    include_header: bool = True,
    options: RequestOverrides | None = None,
) -> ItemExportChunk:
    space_id, board_id = await _async_ids(client, space, board, options)

    if format == "jsonl":

        async def fetch(page: int, size: int) -> dict[str, Any]:
            result = await client.items.list(
                space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
            )
            return {"data": [_item_dict(i) for i in result.data], "hasMore": result.has_more}

        chunk = await read_paged_chunk(
            fetch,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=cursor,
            serialize=lambda item: _json_line(item) + "\n",
        )
        body = "".join(_json_line(item) + "\n" for item in chunk.data)
        return ItemExportChunk(
            format="jsonl",
            body=body,
            scanned=chunk.scanned,
            returned=chunk.returned,
            bytes=chunk.bytes,
            complete=chunk.complete,
            truncated=chunk.truncated,
            next_cursor=chunk.next_cursor,
        )

    state = await _async_csv_state(
        client,
        space_id,
        board_id,
        cursor.page if cursor is not None else 1,
        page_size,
        csv_safety,
        options,
    )
    header_bytes = utf8_byte_length(state.header) if include_header else 0
    if header_bytes > max_bytes:
        raise PlakyMaterializationLimitError("bytes", max_bytes)

    async def fetch_csv(page: int, size: int) -> dict[str, Any]:
        if page == state.seed_page_number:
            return state.seed_page
        result = await client.items.list(
            space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
        )
        return {"data": [_item_dict(i) for i in result.data], "hasMore": result.has_more}

    chunk = await read_paged_chunk(
        fetch_csv,
        page_size=page_size,
        max_items=max_items,
        max_bytes=max_bytes - header_bytes,
        cursor=cursor,
        serialize=lambda item: render_item_row(item, csv_safety, state.schema) + "\n",
    )
    rows = "".join(render_item_row(item, csv_safety, state.schema) + "\n" for item in chunk.data)
    if chunk.returned == 0 and chunk.complete and include_header:
        body = ""
    else:
        body = (state.header if include_header else "") + rows
    return ItemExportChunk(
        format="csv",
        body=body,
        scanned=chunk.scanned,
        returned=chunk.returned,
        bytes=utf8_byte_length(body),
        complete=chunk.complete,
        truncated=chunk.truncated,
        next_cursor=chunk.next_cursor,
    )


async def async_iterate_item_export_chunks(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    format: ExportFormat = "jsonl",
    csv_safety: CsvSafety = "spreadsheet",
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    options: RequestOverrides | None = None,
) -> AsyncIterator[ItemExportChunk]:
    cursor: PageCursor | None = None
    first = True
    while True:
        chunk = await async_read_item_export_chunk(
            client,
            space=space,
            board=board,
            format=format,
            csv_safety=csv_safety,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=cursor,
            include_header=first,
            options=options,
        )
        yield chunk
        first = False
        if chunk.next_cursor is None:
            return
        cursor = chunk.next_cursor


def read_item_export_chunk(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    format: ExportFormat = "jsonl",
    csv_safety: CsvSafety = "spreadsheet",
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    cursor: PageCursor | None = None,
    include_header: bool = True,
    options: RequestOverrides | None = None,
) -> ItemExportChunk:
    space_id, board_id = _sync_ids(client, space, board, options)

    if format == "jsonl":

        def fetch(page: int, size: int) -> dict[str, Any]:
            result = client.items.list(
                space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
            )
            return {"data": [_item_dict(i) for i in result.data], "hasMore": result.has_more}

        chunk = sync_read_paged_chunk(
            fetch,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=cursor,
            serialize=lambda item: _json_line(item) + "\n",
        )
        body = "".join(_json_line(item) + "\n" for item in chunk.data)
        return ItemExportChunk(
            format="jsonl",
            body=body,
            scanned=chunk.scanned,
            returned=chunk.returned,
            bytes=chunk.bytes,
            complete=chunk.complete,
            truncated=chunk.truncated,
            next_cursor=chunk.next_cursor,
        )

    board_model = client.boards.get(space_id=space_id, board_id=board_id, options=options)
    definitions = _entity_value(board_model, "fields")
    seed_page_number = cursor.page if cursor is not None else 1
    listing = client.items.list(
        space_id=space_id,
        board_id=board_id,
        page=seed_page_number,
        page_size=page_size,
        options=options,
    )
    seed = {"data": [_item_dict(i) for i in listing.data], "hasMore": listing.has_more}
    definition_dicts = (
        [_item_dict(d) for d in cast("list[Any]", definitions)]
        if isinstance(definitions, list)
        else None
    )
    schema = create_items_csv_schema(cast("list[dict[str, Any]]", seed["data"]), definition_dicts)
    header = render_items_csv_chunk([], csv_safety, schema, include_header=True)
    header_bytes = utf8_byte_length(header) if include_header else 0
    if header_bytes > max_bytes:
        raise PlakyMaterializationLimitError("bytes", max_bytes)

    def fetch_csv(page: int, size: int) -> dict[str, Any]:
        if page == seed_page_number:
            return seed
        result = client.items.list(
            space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
        )
        return {"data": [_item_dict(i) for i in result.data], "hasMore": result.has_more}

    chunk = sync_read_paged_chunk(
        fetch_csv,
        page_size=page_size,
        max_items=max_items,
        max_bytes=max_bytes - header_bytes,
        cursor=cursor,
        serialize=lambda item: render_item_row(item, csv_safety, schema) + "\n",
    )
    rows = "".join(render_item_row(item, csv_safety, schema) + "\n" for item in chunk.data)
    if chunk.returned == 0 and chunk.complete and include_header:
        body = ""
    else:
        body = (header if include_header else "") + rows
    return ItemExportChunk(
        format="csv",
        body=body,
        scanned=chunk.scanned,
        returned=chunk.returned,
        bytes=utf8_byte_length(body),
        complete=chunk.complete,
        truncated=chunk.truncated,
        next_cursor=chunk.next_cursor,
    )


def iterate_item_export_chunks(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    format: ExportFormat = "jsonl",
    csv_safety: CsvSafety = "spreadsheet",
    page_size: int = 100,
    max_items: int = DEFAULT_CHUNK_MAX_ITEMS,
    max_bytes: int = DEFAULT_CHUNK_MAX_BYTES,
    options: RequestOverrides | None = None,
) -> Iterator[ItemExportChunk]:
    cursor: PageCursor | None = None
    first = True
    while True:
        chunk = read_item_export_chunk(
            client,
            space=space,
            board=board,
            format=format,
            csv_safety=csv_safety,
            page_size=page_size,
            max_items=max_items,
            max_bytes=max_bytes,
            cursor=cursor,
            include_header=first,
            options=options,
        )
        yield chunk
        first = False
        if chunk.next_cursor is None:
            return
        cursor = chunk.next_cursor
