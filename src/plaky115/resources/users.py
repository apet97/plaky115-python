"""Users resource: listUsers (emails as repeated keys), getCurrentUser."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from plaky115.http import RequestSpec
from plaky115.models import User
from plaky115.pagination import DEFAULT_PAGE_SIZE, AsyncPaginator, Page, SyncPaginator
from plaky115.resources._common import (
    Requester,
    RequestOverrides,
    SyncRequester,
    parse_object,
    parse_page,
)


def _list_spec(
    page: int | None,
    page_size: int | None,
    emails: Sequence[str] | None,
    status: str | None,
    type_: str | None,
) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path="/v1/public/users",
        query={
            "page": page,
            "pageSize": page_size,
            "emails": list(emails) if emails else None,
            "status": status,
            "type": type_,
        },
        operation_id="listUsers",
    )


_ME_SPEC = RequestSpec(method="GET", path="/v1/public/users/me", operation_id="getCurrentUser")


class AsyncUsersResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        emails: Sequence[str] | None = None,
        status: str | None = None,
        type: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[User]:
        data: Any = await self._client.execute(
            _list_spec(page, page_size, emails, status, type), options
        )
        return parse_page(data, "listUsers", User)

    async def me(self, *, options: RequestOverrides | None = None) -> User:
        data: Any = await self._client.execute(_ME_SPEC, options)
        return parse_object(data, User)

    def iterate(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        emails: Sequence[str] | None = None,
        status: str | None = None,
        type: str | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[User]:
        async def fetch(page: int, size: int) -> Page[User]:
            return await self.list(
                page=page,
                page_size=size,
                emails=emails,
                status=status,
                type=type,
                options=options,
            )

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        emails: Sequence[str] | None = None,
        status: str | None = None,
        type: str | None = None,
        options: RequestOverrides | None = None,
    ) -> list[User]:
        return await self.iterate(
            page_size=page_size,
            limit=limit,
            emails=emails,
            status=status,
            type=type,
            options=options,
        ).to_list()


class UsersResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        emails: Sequence[str] | None = None,
        status: str | None = None,
        type: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[User]:
        data: Any = self._client.execute(
            _list_spec(page, page_size, emails, status, type), options
        )
        return parse_page(data, "listUsers", User)

    def me(self, *, options: RequestOverrides | None = None) -> User:
        data: Any = self._client.execute(_ME_SPEC, options)
        return parse_object(data, User)

    def iterate(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        emails: Sequence[str] | None = None,
        status: str | None = None,
        type: str | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[User]:
        def fetch(page: int, size: int) -> Page[User]:
            return self.list(
                page=page,
                page_size=size,
                emails=emails,
                status=status,
                type=type,
                options=options,
            )

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        emails: Sequence[str] | None = None,
        status: str | None = None,
        type: str | None = None,
        options: RequestOverrides | None = None,
    ) -> list[User]:
        return self.iterate(
            page_size=page_size,
            limit=limit,
            emails=emails,
            status=status,
            type=type,
            options=options,
        ).to_list()
