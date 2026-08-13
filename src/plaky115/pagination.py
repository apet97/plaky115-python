"""Strict page-root validation and pagination primitives.

Ported from sdk/src/runtime/pagination.ts at the pinned source.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel
from pydantic import Field as PydanticField

from plaky115.errors import PlakyResponseContractError

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 100
MAX_PAGES = 10_000


class Page(BaseModel, Generic[T]):
    """One page of results with the strict {data, hasMore} root."""

    data: list[T]
    has_more: bool = PydanticField(alias="hasMore")

    model_config = {"populate_by_name": True, "frozen": True}


def assert_paged_result(value: Any, operation_id: str) -> dict[str, Any]:
    """Validate the strict paged root: {"data": [...], "hasMore": bool}."""
    if not isinstance(value, dict):
        raise PlakyResponseContractError(operation_id, "/")
    record = cast(dict[str, Any], value)
    if "data" not in record:
        raise PlakyResponseContractError(operation_id, "/data")
    data = record["data"]
    if not isinstance(data, list):
        raise PlakyResponseContractError(operation_id, "/data")
    if "hasMore" not in record:
        raise PlakyResponseContractError(operation_id, "/hasMore")
    has_more = record["hasMore"]
    if not isinstance(has_more, bool):
        raise PlakyResponseContractError(operation_id, "/hasMore")
    if len(cast(list[Any], data)) == 0 and has_more is True:
        # An empty page may not claim more results; it would loop forever.
        raise PlakyResponseContractError(operation_id, "/hasMore")
    return record


def assert_array_result(value: Any, operation_id: str) -> list[Any]:
    """Validate a bare-array response root."""
    if not isinstance(value, list):
        raise PlakyResponseContractError(operation_id, "/")
    return cast(list[Any], value)


def _validate_page_size(page_size: int) -> None:
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
        raise ValueError("pageSize must be a positive integer.")


def _validate_limit(limit: int | None) -> None:
    if limit is None:
        return
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a non-negative integer.")


PageFetcher = Callable[[int, int], Awaitable[Page[T]]]
SyncPageFetcher = Callable[[int, int], Page[T]]


class AsyncPaginator(Generic[T]):
    """Async iterator over paged results with first_page/pages/to_list.

    The fetcher receives (page, page_size); pages are 1-based. Iteration
    never fetches past the last consumed item and stops at the 10,000-page
    safety valve.
    """

    def __init__(
        self,
        fetcher: PageFetcher[T],
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
    ) -> None:
        _validate_page_size(page_size)
        _validate_limit(limit)
        self._fetcher = fetcher
        self._page_size = page_size
        self._limit = limit
        self._page = 1
        self._buffer: list[T] = []
        self._buffer_index = 0
        self._done = False
        self._yielded = 0

    def __aiter__(self) -> AsyncPaginator[T]:
        return self

    async def _fetch(self, page: int) -> Page[T]:
        if page > MAX_PAGES:
            raise ValueError(f"Pagination exceeded {MAX_PAGES} pages.")
        return await self._fetcher(page, self._page_size)

    async def __anext__(self) -> T:
        if self._limit is not None and self._yielded >= self._limit:
            raise StopAsyncIteration
        while self._buffer_index >= len(self._buffer) and not self._done:
            result = await self._fetch(self._page)
            self._page += 1
            self._buffer = list(result.data)
            self._buffer_index = 0
            self._done = not result.has_more
        if self._buffer_index >= len(self._buffer):
            raise StopAsyncIteration
        item = self._buffer[self._buffer_index]
        self._buffer_index += 1
        self._yielded += 1
        return item

    async def first_page(self) -> Page[T]:
        """Fetch page 1 fresh without advancing this iterator."""
        return await self._fetcher(1, self._page_size)

    async def pages(self) -> AsyncIterator[Page[T]]:
        """Independent page-by-page iteration; ignores the item limit."""
        page = 1
        while True:
            if page > MAX_PAGES:
                raise ValueError(f"Pagination exceeded {MAX_PAGES} pages.")
            result = await self._fetcher(page, self._page_size)
            yield result
            if not result.has_more:
                return
            page += 1

    async def to_list(self, limit: int | None = None) -> list[T]:
        """Materialize items with an optional additional client-side limit."""
        _validate_limit(limit)
        bounds = [b for b in (self._limit, limit) if b is not None]
        maximum = min(bounds) if bounds else None
        out: list[T] = []
        page = 1
        while maximum is None or len(out) < maximum:
            if page > MAX_PAGES:
                raise ValueError(f"Pagination exceeded {MAX_PAGES} pages.")
            result = await self._fetcher(page, self._page_size)
            remaining = None if maximum is None else maximum - len(out)
            out.extend(result.data if remaining is None else result.data[:remaining])
            if not result.has_more:
                break
            page += 1
        return out


class SyncPaginator(Generic[T]):
    """Sync twin of AsyncPaginator."""

    def __init__(
        self,
        fetcher: SyncPageFetcher[T],
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
    ) -> None:
        _validate_page_size(page_size)
        _validate_limit(limit)
        self._fetcher = fetcher
        self._page_size = page_size
        self._limit = limit
        self._page = 1
        self._buffer: list[T] = []
        self._buffer_index = 0
        self._done = False
        self._yielded = 0

    def __iter__(self) -> SyncPaginator[T]:
        return self

    def _fetch(self, page: int) -> Page[T]:
        if page > MAX_PAGES:
            raise ValueError(f"Pagination exceeded {MAX_PAGES} pages.")
        return self._fetcher(page, self._page_size)

    def __next__(self) -> T:
        if self._limit is not None and self._yielded >= self._limit:
            raise StopIteration
        while self._buffer_index >= len(self._buffer) and not self._done:
            result = self._fetch(self._page)
            self._page += 1
            self._buffer = list(result.data)
            self._buffer_index = 0
            self._done = not result.has_more
        if self._buffer_index >= len(self._buffer):
            raise StopIteration
        item = self._buffer[self._buffer_index]
        self._buffer_index += 1
        self._yielded += 1
        return item

    def first_page(self) -> Page[T]:
        return self._fetcher(1, self._page_size)

    def pages(self) -> Iterator[Page[T]]:
        page = 1
        while True:
            if page > MAX_PAGES:
                raise ValueError(f"Pagination exceeded {MAX_PAGES} pages.")
            result = self._fetcher(page, self._page_size)
            yield result
            if not result.has_more:
                return
            page += 1

    def to_list(self, limit: int | None = None) -> list[T]:
        _validate_limit(limit)
        bounds = [b for b in (self._limit, limit) if b is not None]
        maximum = min(bounds) if bounds else None
        out: list[T] = []
        page = 1
        while maximum is None or len(out) < maximum:
            if page > MAX_PAGES:
                raise ValueError(f"Pagination exceeded {MAX_PAGES} pages.")
            result = self._fetcher(page, self._page_size)
            remaining = None if maximum is None else maximum - len(out)
            out.extend(result.data if remaining is None else result.data[:remaining])
            if not result.has_more:
                break
            page += 1
        return out


# Functional aliases matching the pinned source's paginate export.
def paginate(
    fetcher: SyncPageFetcher[T],
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    limit: int | None = None,
) -> SyncPaginator[T]:
    return SyncPaginator(fetcher, page_size=page_size, limit=limit)


def async_paginate(
    fetcher: PageFetcher[T],
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    limit: int | None = None,
) -> AsyncPaginator[T]:
    return AsyncPaginator(fetcher, page_size=page_size, limit=limit)
