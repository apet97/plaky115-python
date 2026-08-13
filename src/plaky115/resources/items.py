"""Items resource: list, create, subitems, get, delete, field updates.

Seven exact expand values; dry-run for create/update-fields; writes make a
single network attempt.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, encode_path_segment, id_path_segment
from plaky115.models import Item
from plaky115.pagination import DEFAULT_PAGE_SIZE, AsyncPaginator, Page, SyncPaginator
from plaky115.resources._common import (
    BodyInput,
    Requester,
    RequestOverrides,
    SyncRequester,
    body_as_dict,
    expand_values,
    parse_object,
    parse_page,
    with_idempotency,
)
from plaky115.workflows.mutation_plans import (
    DryRunPlan,
    normalize_item_create_plan,
    normalize_item_update_fields_plan,
    plan_to_dry_run,
)


def _base(space_id: IdInput, board_id: IdInput) -> str:
    return f"/v1/public/spaces/{id_path_segment(space_id)}/boards/{id_path_segment(board_id)}"


def _list_spec(
    space_id: IdInput,
    board_id: IdInput,
    page: int | None,
    page_size: int | None,
    expand: Sequence[str] | None,
    board_view_id: IdInput | None,
    parent_id: IdInput | None,
    subitems_behaviour: str | None,
) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=f"{_base(space_id, board_id)}/items",
        query={
            "page": page,
            "pageSize": page_size,
            "expand": expand_values(expand),
            "boardViewId": None if board_view_id is None else id_path_segment(board_view_id),
            "parentId": None if parent_id is None else id_path_segment(parent_id),
            "subitemsBehaviour": subitems_behaviour,
        },
        operation_id="listItems",
    )


def _item_path(space_id: IdInput, board_id: IdInput, item_id: IdInput) -> str:
    return f"{_base(space_id, board_id)}/items/{id_path_segment(item_id)}"


class AsyncItemsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        expand: Sequence[str] | None = None,
        board_view_id: IdInput | None = None,
        parent_id: IdInput | None = None,
        subitems_behaviour: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Item]:
        spec = _list_spec(
            space_id,
            board_id,
            page,
            page_size,
            expand,
            board_view_id,
            parent_id,
            subitems_behaviour,
        )
        data: Any = await self._client.execute(spec, options)
        return parse_page(data, "listItems", Item)

    async def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Item:
        spec = RequestSpec(
            method="GET",
            path=_item_path(space_id, board_id, item_id),
            query={"expand": expand_values(expand)},
            operation_id="getItem",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_object(data, Item)

    async def list_subitems(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Item]:
        spec = RequestSpec(
            method="GET",
            path=f"{_item_path(space_id, board_id, item_id)}/sub-items",
            query={"page": page, "pageSize": page_size, "expand": expand_values(expand)},
            operation_id="listSubitems",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_page(data, "listSubitems", Item)

    async def create(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        body: BodyInput,
        dry_run: bool = False,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Item | DryRunPlan:
        plan = normalize_item_create_plan(
            space_id=space_id, board_id=board_id, body=body_as_dict(body)
        )
        if dry_run:
            return plan_to_dry_run(plan)
        spec = RequestSpec(
            method="POST",
            path=f"{_base(space_id, board_id)}/items",
            body=dict(plan.body),
            operation_id="createItem",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Item)

    async def update_field(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_field_key: str,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Item:
        spec = RequestSpec(
            method="PATCH",
            path=(
                f"{_item_path(space_id, board_id, item_id)}/fields/"
                f"{encode_path_segment(item_field_key)}"
            ),
            body=body_as_dict(body),
            operation_id="updateItemField",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Item)

    async def update_fields(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        body: BodyInput,
        dry_run: bool = False,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Item | DryRunPlan:
        plan = normalize_item_update_fields_plan(
            space_id=space_id, board_id=board_id, item_id=item_id, body=body_as_dict(body)
        )
        if dry_run:
            return plan_to_dry_run(plan)
        spec = RequestSpec(
            method="PATCH",
            path=f"{_item_path(space_id, board_id, item_id)}/fields",
            body=dict(plan.body),
            operation_id="updateItemFields",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Item)

    async def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=_item_path(space_id, board_id, item_id),
            response_type="void",
            operation_id="deleteItem",
        )
        await self._client.execute(spec, with_idempotency(options, idempotency_key))

    def iterate(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[Item]:
        async def fetch(page: int, size: int) -> Page[Item]:
            return await self.list(
                space_id=space_id,
                board_id=board_id,
                page=page,
                page_size=size,
                expand=expand,
                options=options,
            )

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> list[Item]:
        return await self.iterate(
            space_id=space_id,
            board_id=board_id,
            page_size=page_size,
            limit=limit,
            expand=expand,
            options=options,
        ).to_list()


class ItemsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        expand: Sequence[str] | None = None,
        board_view_id: IdInput | None = None,
        parent_id: IdInput | None = None,
        subitems_behaviour: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Item]:
        spec = _list_spec(
            space_id,
            board_id,
            page,
            page_size,
            expand,
            board_view_id,
            parent_id,
            subitems_behaviour,
        )
        data: Any = self._client.execute(spec, options)
        return parse_page(data, "listItems", Item)

    def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Item:
        spec = RequestSpec(
            method="GET",
            path=_item_path(space_id, board_id, item_id),
            query={"expand": expand_values(expand)},
            operation_id="getItem",
        )
        data: Any = self._client.execute(spec, options)
        return parse_object(data, Item)

    def list_subitems(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        page: int | None = None,
        page_size: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> Page[Item]:
        spec = RequestSpec(
            method="GET",
            path=f"{_item_path(space_id, board_id, item_id)}/sub-items",
            query={"page": page, "pageSize": page_size, "expand": expand_values(expand)},
            operation_id="listSubitems",
        )
        data: Any = self._client.execute(spec, options)
        return parse_page(data, "listSubitems", Item)

    def create(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        body: BodyInput,
        dry_run: bool = False,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Item | DryRunPlan:
        plan = normalize_item_create_plan(
            space_id=space_id, board_id=board_id, body=body_as_dict(body)
        )
        if dry_run:
            return plan_to_dry_run(plan)
        spec = RequestSpec(
            method="POST",
            path=f"{_base(space_id, board_id)}/items",
            body=dict(plan.body),
            operation_id="createItem",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Item)

    def update_field(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_field_key: str,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Item:
        spec = RequestSpec(
            method="PATCH",
            path=(
                f"{_item_path(space_id, board_id, item_id)}/fields/"
                f"{encode_path_segment(item_field_key)}"
            ),
            body=body_as_dict(body),
            operation_id="updateItemField",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Item)

    def update_fields(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        body: BodyInput,
        dry_run: bool = False,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Item | DryRunPlan:
        plan = normalize_item_update_fields_plan(
            space_id=space_id, board_id=board_id, item_id=item_id, body=body_as_dict(body)
        )
        if dry_run:
            return plan_to_dry_run(plan)
        spec = RequestSpec(
            method="PATCH",
            path=f"{_item_path(space_id, board_id, item_id)}/fields",
            body=dict(plan.body),
            operation_id="updateItemFields",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Item)

    def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=_item_path(space_id, board_id, item_id),
            response_type="void",
            operation_id="deleteItem",
        )
        self._client.execute(spec, with_idempotency(options, idempotency_key))

    def iterate(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[Item]:
        def fetch(page: int, size: int) -> Page[Item]:
            return self.list(
                space_id=space_id,
                board_id=board_id,
                page=page,
                page_size=size,
                expand=expand,
                options=options,
            )

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        limit: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        expand: Sequence[str] | None = None,
        options: RequestOverrides | None = None,
    ) -> list[Item]:
        return self.iterate(
            space_id=space_id,
            board_id=board_id,
            page_size=page_size,
            limit=limit,
            expand=expand,
            options=options,
        ).to_list()
