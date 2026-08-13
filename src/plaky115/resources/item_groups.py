"""Item groups resource. Archive is destructive: the public API has no
unarchive operation."""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import ItemGroup
from plaky115.pagination import DEFAULT_PAGE_SIZE, AsyncPaginator, Page, SyncPaginator
from plaky115.resources._common import (
    BodyInput,
    Requester,
    RequestOverrides,
    SyncRequester,
    body_as_dict,
    parse_object,
    parse_page,
    with_idempotency,
)
from plaky115.workflows.mutation_plans import (
    normalize_item_group_create_plan,
    normalize_item_group_update_plan,
)


def _groups_path(space_id: IdInput, board_id: IdInput) -> str:
    return (
        f"/v1/public/spaces/{id_path_segment(space_id)}"
        f"/boards/{id_path_segment(board_id)}/item-groups"
    )


class AsyncItemGroupsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[ItemGroup]:
        spec = RequestSpec(
            method="GET",
            path=_groups_path(space_id, board_id),
            query={"page": page, "pageSize": page_size},
            operation_id="listItemGroups",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_page(data, "listItemGroups", ItemGroup)

    async def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemGroup:
        spec = RequestSpec(
            method="GET",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}",
            operation_id="getItemGroup",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_object(data, ItemGroup)

    async def create(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemGroup:
        plan = normalize_item_group_create_plan(
            space_id=space_id, board_id=board_id, body=body_as_dict(body)
        )
        spec = RequestSpec(
            method="POST",
            path=_groups_path(space_id, board_id),
            body=dict(plan.body),
            operation_id="createItemGroup",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemGroup)

    async def update(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemGroup:
        plan = normalize_item_group_update_plan(
            space_id=space_id,
            board_id=board_id,
            item_group_id=item_group_id,
            body=body_as_dict(body),
        )
        spec = RequestSpec(
            method="PUT",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}",
            body=dict(plan.body),
            operation_id="updateItemGroup",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemGroup)

    async def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}",
            response_type="void",
            operation_id="deleteItemGroup",
        )
        await self._client.execute(spec, with_idempotency(options, idempotency_key))

    async def archive(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="PUT",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}/archive",
            response_type="void",
            operation_id="archiveItemGroup",
        )
        await self._client.execute(spec, with_idempotency(options, idempotency_key))

    def iterate(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[ItemGroup]:
        async def fetch(page: int, size: int) -> Page[ItemGroup]:
            return await self.list(
                space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
            )

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        options: RequestOverrides | None = None,
    ) -> list[ItemGroup]:
        return await self.iterate(
            space_id=space_id, board_id=board_id, page_size=page_size, limit=limit, options=options
        ).to_list()


class ItemGroupsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[ItemGroup]:
        spec = RequestSpec(
            method="GET",
            path=_groups_path(space_id, board_id),
            query={"page": page, "pageSize": page_size},
            operation_id="listItemGroups",
        )
        data: Any = self._client.execute(spec, options)
        return parse_page(data, "listItemGroups", ItemGroup)

    def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemGroup:
        spec = RequestSpec(
            method="GET",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}",
            operation_id="getItemGroup",
        )
        data: Any = self._client.execute(spec, options)
        return parse_object(data, ItemGroup)

    def create(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemGroup:
        plan = normalize_item_group_create_plan(
            space_id=space_id, board_id=board_id, body=body_as_dict(body)
        )
        spec = RequestSpec(
            method="POST",
            path=_groups_path(space_id, board_id),
            body=dict(plan.body),
            operation_id="createItemGroup",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemGroup)

    def update(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemGroup:
        plan = normalize_item_group_update_plan(
            space_id=space_id,
            board_id=board_id,
            item_group_id=item_group_id,
            body=body_as_dict(body),
        )
        spec = RequestSpec(
            method="PUT",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}",
            body=dict(plan.body),
            operation_id="updateItemGroup",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemGroup)

    def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}",
            response_type="void",
            operation_id="deleteItemGroup",
        )
        self._client.execute(spec, with_idempotency(options, idempotency_key))

    def archive(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_group_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="PUT",
            path=f"{_groups_path(space_id, board_id)}/{id_path_segment(item_group_id)}/archive",
            response_type="void",
            operation_id="archiveItemGroup",
        )
        self._client.execute(spec, with_idempotency(options, idempotency_key))

    def iterate(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[ItemGroup]:
        def fetch(page: int, size: int) -> Page[ItemGroup]:
            return self.list(
                space_id=space_id, board_id=board_id, page=page, page_size=size, options=options
            )

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        options: RequestOverrides | None = None,
    ) -> list[ItemGroup]:
        return self.iterate(
            space_id=space_id, board_id=board_id, page_size=page_size, limit=limit, options=options
        ).to_list()
