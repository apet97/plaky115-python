"""Boards resource: listBoards, getBoard. Always scoped by space_id."""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import Board
from plaky115.pagination import DEFAULT_PAGE_SIZE, AsyncPaginator, Page, SyncPaginator
from plaky115.resources._common import (
    Requester,
    RequestOverrides,
    SyncRequester,
    parse_object,
    parse_page,
)


def _list_spec(space_id: IdInput, page: int | None, page_size: int | None) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=f"/v1/public/spaces/{id_path_segment(space_id)}/boards",
        query={"page": page, "pageSize": page_size},
        operation_id="listBoards",
    )


def _get_spec(space_id: IdInput, board_id: IdInput) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=f"/v1/public/spaces/{id_path_segment(space_id)}/boards/{id_path_segment(board_id)}",
        operation_id="getBoard",
    )


class AsyncBoardsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        space_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Board]:
        data: Any = await self._client.execute(_list_spec(space_id, page, page_size), options)
        return parse_page(data, "listBoards", Board)

    async def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> Board:
        data: Any = await self._client.execute(_get_spec(space_id, board_id), options)
        return parse_object(data, Board)

    def iterate(
        self,
        *,
        space_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[Board]:
        async def fetch(page: int, size: int) -> Page[Board]:
            return await self.list(space_id=space_id, page=page, page_size=size, options=options)

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        space_id: IdInput,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        options: RequestOverrides | None = None,
    ) -> list[Board]:
        return await self.iterate(
            space_id=space_id, page_size=page_size, limit=limit, options=options
        ).to_list()


class BoardsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        space_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Board]:
        data: Any = self._client.execute(_list_spec(space_id, page, page_size), options)
        return parse_page(data, "listBoards", Board)

    def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> Board:
        data: Any = self._client.execute(_get_spec(space_id, board_id), options)
        return parse_object(data, Board)

    def iterate(
        self,
        *,
        space_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[Board]:
        def fetch(page: int, size: int) -> Page[Board]:
            return self.list(space_id=space_id, page=page, page_size=size, options=options)

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        space_id: IdInput,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        options: RequestOverrides | None = None,
    ) -> list[Board]:
        return self.iterate(
            space_id=space_id, page_size=page_size, limit=limit, options=options
        ).to_list()
