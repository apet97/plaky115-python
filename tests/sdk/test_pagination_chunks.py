"""Pagination root and bounded-chunk gates (plan Phase 5)."""

from typing import Any

import pytest

from plaky115.errors import (
    PlakyMaterializationLimitError,
    PlakyOutputLimitError,
    PlakyResponseContractError,
)
from plaky115.pagination import assert_array_result, assert_paged_result
from plaky115.runtime.chunks import (
    DEFAULT_CHUNK_MAX_BYTES,
    DEFAULT_CHUNK_MAX_ITEMS,
    MAX_MATERIALIZED_BYTES,
    MAX_MATERIALIZED_ITEMS,
    BoundedChunk,
    PageCursor,
    assert_materialized_collection,
    iterate_paged_chunks,
    read_paged_chunk,
    utf8_byte_length,
)

pytestmark = pytest.mark.anyio


def test_constants() -> None:
    assert DEFAULT_CHUNK_MAX_ITEMS == 100
    assert DEFAULT_CHUNK_MAX_BYTES == 1_048_576
    assert MAX_MATERIALIZED_ITEMS == 10_000
    assert MAX_MATERIALIZED_BYTES == 16_777_216


@pytest.mark.parametrize(
    ("value", "pointer"),
    [
        (None, "/"),
        ([], "/"),
        ("x", "/"),
        ({}, "/data"),
        ({"data": "not-a-list", "hasMore": False}, "/data"),
        ({"data": []}, "/hasMore"),
        ({"data": [], "hasMore": "yes"}, "/hasMore"),
        ({"data": [], "hasMore": True}, "/hasMore"),  # empty page claiming more
    ],
)
def test_paged_root_rejections(value: Any, pointer: str) -> None:
    with pytest.raises(PlakyResponseContractError) as info:
        assert_paged_result(value, "listSpaces")
    assert info.value.pointer == pointer
    assert str(info.value) == f"Invalid listSpaces response at {pointer}."


def test_paged_root_accepts_valid() -> None:
    assert assert_paged_result({"data": [1], "hasMore": False}, "op")["data"] == [1]
    assert assert_paged_result({"data": [], "hasMore": False}, "op")["hasMore"] is False


def test_array_root() -> None:
    assert assert_array_result([1, 2], "listItemComments") == [1, 2]
    with pytest.raises(PlakyResponseContractError):
        assert_array_result({"data": []}, "listItemComments")


def make_fetcher(pages: list[dict[str, Any]]) -> Any:
    calls: list[int] = []

    async def fetcher(page: int, page_size: int) -> dict[str, Any]:
        calls.append(page)
        return pages[page - 1]

    return fetcher, calls


async def test_chunk_exact_continuation() -> None:
    fetcher, calls = make_fetcher(
        [
            {"data": [1, 2], "hasMore": True},
            {"data": [3], "hasMore": False},
        ]
    )
    first = await read_paged_chunk(fetcher, max_items=1)
    assert first.data == (1,)
    assert first.truncated and not first.complete
    assert first.next_cursor == PageCursor(page=1, index=1)

    rest = await read_paged_chunk(fetcher, cursor=first.next_cursor)
    assert rest.data == (2, 3)
    assert rest.complete and rest.next_cursor is None
    assert calls == [1, 1, 2]  # no duplicate items delivered


async def test_single_oversized_item_raises() -> None:
    fetcher, _ = make_fetcher([{"data": [{"big": "x" * 100}], "hasMore": False}])
    with pytest.raises(PlakyOutputLimitError) as info:
        await read_paged_chunk(fetcher, max_bytes=10)
    assert "Output bytes limit of 10 was reached" in str(info.value)


async def test_zero_max_items_fails_immediately() -> None:
    fetcher, calls = make_fetcher([])
    with pytest.raises(PlakyOutputLimitError):
        await read_paged_chunk(fetcher, max_items=0)
    assert calls == []


async def test_byte_accounting_uses_utf8() -> None:
    assert utf8_byte_length("čšž") == 6
    # Two 6-byte items with an 11-byte budget: only the first fits.
    fetcher, _ = make_fetcher([{"data": ["čš", "žđ"], "hasMore": False}])
    chunk = await read_paged_chunk(fetcher, max_bytes=11)
    # JSON serialization adds quotes: "čš" is 6 chars = 2+4 bytes.
    assert chunk.data == ("čš",)
    assert chunk.next_cursor == PageCursor(page=1, index=1)


async def test_cursor_index_beyond_page_is_contract_error() -> None:
    fetcher, _ = make_fetcher([{"data": [1], "hasMore": False}])
    with pytest.raises(PlakyResponseContractError):
        await read_paged_chunk(fetcher, cursor=PageCursor(page=1, index=5))


async def test_cursor_validation() -> None:
    fetcher, _ = make_fetcher([])
    with pytest.raises(ValueError, match=r"cursor\.page must be a positive safe integer\."):
        await read_paged_chunk(fetcher, cursor=PageCursor(page=0, index=0))
    with pytest.raises(ValueError, match=r"cursor\.index must be a non-negative safe integer\."):
        await read_paged_chunk(fetcher, cursor=PageCursor(page=1, index=-1))


async def test_iterate_chunks_yields_until_complete() -> None:
    fetcher, _calls = make_fetcher(
        [
            {"data": [1, 2, 3], "hasMore": True},
            {"data": [4], "hasMore": False},
        ]
    )
    chunks: list[BoundedChunk[Any]] = []
    async for chunk in iterate_paged_chunks(fetcher, max_items=2):
        chunks.append(chunk)
    assert [c.data for c in chunks] == [(1, 2), (3, 4)]
    assert chunks[-1].complete


async def test_iterate_chunks_close_stops_fetching() -> None:
    fetcher, calls = make_fetcher(
        [
            {"data": [1, 2], "hasMore": True},
            {"data": [3], "hasMore": False},
        ]
    )
    iterator = aiter(iterate_paged_chunks(fetcher, max_items=1))
    first = await anext(iterator)
    assert first.data == (1,)
    await iterator.aclose()  # type: ignore[attr-defined]
    assert calls == [1]


def test_materialized_collection_guards() -> None:
    with pytest.raises(PlakyMaterializationLimitError):
        assert_materialized_collection([1, 2, 3], 2, 10_000)
    with pytest.raises(PlakyMaterializationLimitError):
        assert_materialized_collection([{"k": "x" * 100}], 10, 20)
    assert_materialized_collection([1, 2], 2, 1000)
