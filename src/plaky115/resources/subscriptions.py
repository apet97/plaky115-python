"""Item subscriptions resource: getSubscriptions and overrideSubscriptions.

``replace`` sets the complete subscriber list: users and teams left out are
unsubscribed. To choose subscribers when creating an item, send
``subscribedUserIds`` / ``subscribedTeamIds`` on ``items.create`` instead;
they replace the default subscriber (the creator) in the same request.
"""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import ItemSubscriptions
from plaky115.resources._common import (
    BodyInput,
    Requester,
    RequestOverrides,
    SyncRequester,
    body_as_dict,
    parse_object,
    with_idempotency,
)


def _path(space_id: IdInput, board_id: IdInput, item_id: IdInput) -> str:
    return (
        f"/v1/public/spaces/{id_path_segment(space_id)}"
        f"/boards/{id_path_segment(board_id)}"
        f"/items/{id_path_segment(item_id)}/subscriptions"
    )


def _get_spec(space_id: IdInput, board_id: IdInput, item_id: IdInput) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=_path(space_id, board_id, item_id),
        operation_id="getSubscriptions",
    )


def _replace_spec(
    space_id: IdInput, board_id: IdInput, item_id: IdInput, body: BodyInput
) -> RequestSpec:
    return RequestSpec(
        method="PUT",
        path=_path(space_id, board_id, item_id),
        body=body_as_dict(body),
        response_type="void",
        operation_id="overrideSubscriptions",
    )


class AsyncSubscriptionsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemSubscriptions:
        data: Any = await self._client.execute(_get_spec(space_id, board_id, item_id), options)
        return parse_object(data, ItemSubscriptions)

    async def replace(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        await self._client.execute(
            _replace_spec(space_id, board_id, item_id, body),
            with_idempotency(options, idempotency_key),
        )


class SubscriptionsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemSubscriptions:
        data: Any = self._client.execute(_get_spec(space_id, board_id, item_id), options)
        return parse_object(data, ItemSubscriptions)

    def replace(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        self._client.execute(
            _replace_spec(space_id, board_id, item_id, body),
            with_idempotency(options, idempotency_key),
        )
