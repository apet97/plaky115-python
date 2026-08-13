"""Reactions resource: replaceCommentReactions.

Reaction values are Unicode codepoint hex strings such as ``1f44d``. An
empty array clears the caller's reactions.
"""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import ReactionReplaceResult
from plaky115.resources._common import (
    BodyInput,
    Requester,
    RequestOverrides,
    SyncRequester,
    body_as_dict,
    parse_object,
    with_idempotency,
)


def _spec(
    space_id: IdInput,
    board_id: IdInput,
    item_id: IdInput,
    item_comment_id: IdInput,
    body: BodyInput,
) -> RequestSpec:
    return RequestSpec(
        method="PUT",
        path=(
            f"/v1/public/spaces/{id_path_segment(space_id)}"
            f"/boards/{id_path_segment(board_id)}"
            f"/items/{id_path_segment(item_id)}"
            f"/comments/{id_path_segment(item_comment_id)}/reactions"
        ),
        body=body_as_dict(body),
        operation_id="replaceCommentReactions",
    )


class AsyncReactionsResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def replace(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_comment_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ReactionReplaceResult:
        data: Any = await self._client.execute(
            _spec(space_id, board_id, item_id, item_comment_id, body),
            with_idempotency(options, idempotency_key),
        )
        return parse_object(data, ReactionReplaceResult)


class ReactionsResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def replace(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_comment_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ReactionReplaceResult:
        data: Any = self._client.execute(
            _spec(space_id, board_id, item_id, item_comment_id, body),
            with_idempotency(options, idempotency_key),
        )
        return parse_object(data, ReactionReplaceResult)
