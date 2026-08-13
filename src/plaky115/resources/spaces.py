"""Spaces resource: listSpaces, getSpace."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import Space
from plaky115.pagination import (
    DEFAULT_PAGE_SIZE,
    AsyncPaginator,
    Page,
    SyncPaginator,
)
from plaky115.resources._common import (
    Requester,
    RequestOverrides,
    SyncRequester,
    expand_values,
    parse_object,
    parse_page,
)


def _list_spec(
    page: int | None, page_size: int | None, expand: Sequence[str] | None
) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path="/v1/public/spaces",
        query={"page": page, "pageSize": page_size, "expand": expand_values(expand)},
        operation_id="listSpaces",
    )


def _get_spec(space_id: IdInput, expand: Sequence[str] | None) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=f"/v1/public/spaces/{id_path_segment(space_id)}",
        query={"expand": expand_values(expand)},
        operation_id="getSpace",
    )


class AsyncSpacesResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Space]:
        data: Any = await self._client.execute(_list_spec(page, page_size, expand), options)
        return parse_page(data, "listSpaces", Space)

    async def get(
        self,
        space_id: IdInput,
        *,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Space:
        data: Any = await self._client.execute(_get_spec(space_id, expand), options)
        return parse_object(data, Space)

    def iterate(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[Space]:
        async def fetch(page: int, size: int) -> Page[Space]:
            return await self.list(page=page, page_size=size, expand=expand, options=options)

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> list[Space]:
        return await self.iterate(
            page_size=page_size, limit=limit, expand=expand, options=options
        ).to_list()


class SpacesResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Space]:
        data: Any = self._client.execute(_list_spec(page, page_size, expand), options)
        return parse_page(data, "listSpaces", Space)

    def get(
        self,
        space_id: IdInput,
        *,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Space:
        data: Any = self._client.execute(_get_spec(space_id, expand), options)
        return parse_object(data, Space)

    def iterate(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[Space]:
        def fetch(page: int, size: int) -> Page[Space]:
            return self.list(page=page, page_size=size, expand=expand, options=options)

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> list[Space]:
        return self.iterate(
            page_size=page_size, limit=limit, expand=expand, options=options
        ).to_list()
