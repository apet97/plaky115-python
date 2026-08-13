"""Item comments resource. The API list root is a bare array; the SDK
normalizes it to Page(has_more=False) so iterate/list_all stay useful."""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import Comment
from plaky115.pagination import DEFAULT_PAGE_SIZE, AsyncPaginator, Page, SyncPaginator
from plaky115.resources._common import (
    Requester,
    RequestOverrides,
    SyncRequester,
    body_as_dict,
    parse_array,
    parse_object,
    with_idempotency,
)
from plaky115.workflows.mutation_plans import normalize_comment_plan


def _comments_path(space_id: IdInput, board_id: IdInput, item_id: IdInput) -> str:
    return (
        f"/v1/public/spaces/{id_path_segment(space_id)}"
        f"/boards/{id_path_segment(board_id)}"
        f"/items/{id_path_segment(item_id)}/comments"
    )


def _normalize(data: Any) -> Page[Comment]:
    comments = parse_array(data, "listItemComments", Comment)
    return Page[Comment].model_validate({"data": comments, "hasMore": False})


class AsyncItemCommentsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> Page[Comment]:
        spec = RequestSpec(
            method="GET",
            path=_comments_path(space_id, board_id, item_id),
            operation_id="listItemComments",
        )
        return _normalize(await self._client.execute(spec, options))

    async def create(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        body: Any,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Comment:
        plan = normalize_comment_plan(
            space_id=space_id, board_id=board_id, item_id=item_id, body=body_as_dict(body)
        )
        spec = RequestSpec(
            method="POST",
            path=_comments_path(space_id, board_id, item_id),
            body=dict(plan.body),
            operation_id="createItemComment",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Comment)

    async def update(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_comment_id: IdInput,
        body: Any,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Comment:
        plan = normalize_comment_plan(
            space_id=space_id,
            board_id=board_id,
            item_id=item_id,
            item_comment_id=item_comment_id,
            body=body_as_dict(body),
            operation_id="updateItemComment",
        )
        spec = RequestSpec(
            method="PUT",
            path=(
                f"{_comments_path(space_id, board_id, item_id)}/{id_path_segment(item_comment_id)}"
            ),
            body=dict(plan.body),
            operation_id="updateItemComment",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Comment)

    async def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_comment_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=(
                f"{_comments_path(space_id, board_id, item_id)}/{id_path_segment(item_comment_id)}"
            ),
            response_type="void",
            operation_id="deleteItemComment",
        )
        await self._client.execute(spec, with_idempotency(options, idempotency_key))

    def iterate(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> AsyncPaginator[Comment]:
        async def fetch(page: int, size: int) -> Page[Comment]:
            return await self.list(
                space_id=space_id, board_id=board_id, item_id=item_id, options=options
            )

        return AsyncPaginator(fetch, page_size=page_size, limit=limit)

    async def list_all(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> list[Comment]:
        page = await self.list(
            space_id=space_id, board_id=board_id, item_id=item_id, options=options
        )
        return list(page.data if limit is None else page.data[:limit])


class ItemCommentsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> Page[Comment]:
        spec = RequestSpec(
            method="GET",
            path=_comments_path(space_id, board_id, item_id),
            operation_id="listItemComments",
        )
        return _normalize(self._client.execute(spec, options))

    def create(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        body: Any,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Comment:
        plan = normalize_comment_plan(
            space_id=space_id, board_id=board_id, item_id=item_id, body=body_as_dict(body)
        )
        spec = RequestSpec(
            method="POST",
            path=_comments_path(space_id, board_id, item_id),
            body=dict(plan.body),
            operation_id="createItemComment",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Comment)

    def update(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_comment_id: IdInput,
        body: Any,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> Comment:
        plan = normalize_comment_plan(
            space_id=space_id,
            board_id=board_id,
            item_id=item_id,
            item_comment_id=item_comment_id,
            body=body_as_dict(body),
            operation_id="updateItemComment",
        )
        spec = RequestSpec(
            method="PUT",
            path=(
                f"{_comments_path(space_id, board_id, item_id)}/{id_path_segment(item_comment_id)}"
            ),
            body=dict(plan.body),
            operation_id="updateItemComment",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, Comment)

    def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_comment_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=(
                f"{_comments_path(space_id, board_id, item_id)}/{id_path_segment(item_comment_id)}"
            ),
            response_type="void",
            operation_id="deleteItemComment",
        )
        self._client.execute(spec, with_idempotency(options, idempotency_key))

    def iterate(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> SyncPaginator[Comment]:
        def fetch(page: int, size: int) -> Page[Comment]:
            return self.list(
                space_id=space_id, board_id=board_id, item_id=item_id, options=options
            )

        return SyncPaginator(fetch, page_size=page_size, limit=limit)

    def list_all(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        limit: int | None = None,
        options: RequestOverrides | None = None,
    ) -> list[Comment]:
        page = self.list(space_id=space_id, board_id=board_id, item_id=item_id, options=options)
        return list(page.data if limit is None else page.data[:limit])
