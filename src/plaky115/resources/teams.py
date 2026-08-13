"""Teams resource: listTeams, getTeam (direct GET for exact IDs)."""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import Team
from plaky115.pagination import DEFAULT_PAGE_SIZE, AsyncPaginator, Page, SyncPaginator
from plaky115.resources._common import (
    Requester,
    RequestOverrides,
    SyncRequester,
    parse_object,
    parse_page,
)


def _list_spec(page: int | None, page_size: int | None) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path="/v1/public/teams",
        query={"page": page, "pageSize": page_size},
        operation_id="listTeams",
    )


def _get_spec(team_id: IdInput) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=f"/v1/public/teams/{id_path_segment(team_id)}",
        operation_id="getTeam",
    )


class AsyncTeamsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Team]:
        data: Any = await self._client.execute(_list_spec(page, page_size), options)
        return parse_page(data, "listTeams", Team)

    async def get(self, team_id: IdInput, *, options: RequestOverrides | None = None) -> Team:
        data: Any = await self._client.execute(_get_spec(team_id), options)
        return parse_object(data, Team)

    def iterate(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[Team]:
        async def fetch(page: int, size: int) -> Page[Team]:
            return await self.list(page=page, page_size=size, options=options)

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        options: RequestOverrides | None = None,
    ) -> list[Team]:
        return await self.iterate(page_size=page_size, limit=limit, options=options).to_list()


class TeamsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Team]:
        data: Any = self._client.execute(_list_spec(page, page_size), options)
        return parse_page(data, "listTeams", Team)

    def get(self, team_id: IdInput, *, options: RequestOverrides | None = None) -> Team:
        data: Any = self._client.execute(_get_spec(team_id), options)
        return parse_object(data, Team)

    def iterate(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[Team]:
        def fetch(page: int, size: int) -> Page[Team]:
            return self.list(page=page, page_size=size, options=options)

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        options: RequestOverrides | None = None,
    ) -> list[Team]:
        return self.iterate(page_size=page_size, limit=limit, options=options).to_list()
