"""Bulk item field updates with durable, immutable receipts.

Ported from sdk/src/workflows bulkUpdateItems at the pinned source
(docs/port/spec-helpers.md §8.4). Completed items are never repeated; any
post-dispatch failure is conservatively ambiguous.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from plaky115.errors import PlakyPartialMutationError
from plaky115.ids import id_path_segment
from plaky115.resolvers import (
    EntityRef,
    _canonical_id,  # pyright: ignore[reportPrivateUsage]
    _entity_value,  # pyright: ignore[reportPrivateUsage]
    async_resolve_space_and_board,
    resolve_space_and_board,
)
from plaky115.resources._common import RequestOverrides
from plaky115.runtime.mutations import MutationReceipt, new_receipt, transition_receipt

if TYPE_CHECKING:
    from plaky115.async_client import AsyncPlakyClient
    from plaky115.client import PlakyClient

__all__ = ["async_bulk_update_items", "bulk_update_items"]


def _validate_updates(updates: Any) -> list[str]:
    if not isinstance(updates, list | tuple):
        raise TypeError("updates must be an array")
    item_ids: list[str] = []
    for index, entry in enumerate(cast("Sequence[Any]", updates)):
        if not isinstance(entry, Mapping):
            raise TypeError(f"updates[{index}] must be an object")
        record = cast("Mapping[str, Any]", entry)
        item_id = record.get("item_id", record.get("itemId"))
        if not isinstance(item_id, int | str) or isinstance(item_id, bool):
            raise TypeError(f"updates[{index}].itemId must be a number or decimal string")
        body = record.get("body")
        if not isinstance(body, Mapping):
            raise TypeError(f"updates[{index}].body must be a plain object")
        item_ids.append(id_path_segment(item_id))
    return item_ids


def _resolved_id(entity: Any, label: str) -> str:
    value = _entity_value(entity, "id")
    if value is None:
        raise ValueError(f"{label} resolver returned no ID")
    return _canonical_id(value)


async def async_bulk_update_items(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    updates: Sequence[Mapping[str, Any]],
    dry_run: bool = False,
    throw_on_error: bool = False,
    on_progress: Callable[[int, int], Awaitable[None] | None] | None = None,
    options: RequestOverrides | None = None,
) -> tuple[MutationReceipt, ...]:
    item_ids = _validate_updates(updates)
    resolution_options = replace(options, on_dispatch=None) if options is not None else None
    resolved_space, resolved_board = await async_resolve_space_and_board(
        client, space=space, board=board, options=resolution_options
    )
    space_id = _resolved_id(resolved_space, "space")
    board_id = _resolved_id(resolved_board, "board")

    receipts = [
        new_receipt(
            "items.updateFields",
            index,
            {"spaceId": space_id, "boardId": board_id, "itemId": item_id},
        )
        for index, item_id in enumerate(item_ids)
    ]
    for index, item_id in enumerate(item_ids):
        receipts[index] = transition_receipt(receipts[index], "planned", "preflight")
        if dry_run:
            await _report(on_progress, receipts, index, len(item_ids))
            continue
        item_options = replace(
            options or RequestOverrides(),
            on_dispatch=_compose_dispatch_callback(
                options.on_dispatch if options is not None else None, receipts, index
            ),
        )
        try:
            await client.items.update_fields(
                space_id=space_id,
                board_id=board_id,
                item_id=item_id,
                body=dict(updates[index]["body"]),
                options=item_options,
            )
        except Exception as error:
            status = "ambiguous" if receipts[index].attempted else "failed"
            phase = "response" if receipts[index].attempted else "preflight"
            receipts[index] = transition_receipt(receipts[index], status, phase, error)
            if throw_on_error:
                raise PlakyPartialMutationError(
                    "Bulk item update has an unconfirmed mutation outcome.",
                    receipts=tuple(receipts),
                    failed_index=index,
                ) from error
        else:
            receipts[index] = transition_receipt(receipts[index], "completed", "completed")
        await _report(on_progress, receipts, index, len(item_ids))
    return tuple(receipts)


async def _report(
    on_progress: Callable[[int, int], Awaitable[None] | None] | None,
    receipts: list[MutationReceipt],
    index: int,
    total: int,
) -> None:
    if on_progress is None:
        return
    try:
        result = on_progress(index + 1, total)
        if result is not None and hasattr(result, "__await__"):
            await result
    except Exception as error:
        raise PlakyPartialMutationError(
            "Bulk item update progress reporting failed.",
            receipts=tuple(receipts),
            failed_index=index,
        ) from error


def bulk_update_items(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    updates: Sequence[Mapping[str, Any]],
    dry_run: bool = False,
    throw_on_error: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
    options: RequestOverrides | None = None,
) -> tuple[MutationReceipt, ...]:
    item_ids = _validate_updates(updates)
    resolution_options = replace(options, on_dispatch=None) if options is not None else None
    resolved_space, resolved_board = resolve_space_and_board(
        client, space=space, board=board, options=resolution_options
    )
    space_id = _resolved_id(resolved_space, "space")
    board_id = _resolved_id(resolved_board, "board")

    receipts = [
        new_receipt(
            "items.updateFields",
            index,
            {"spaceId": space_id, "boardId": board_id, "itemId": item_id},
        )
        for index, item_id in enumerate(item_ids)
    ]
    for index, item_id in enumerate(item_ids):
        if dry_run:
            _report_sync(on_progress, receipts, index, len(item_ids))
            continue
        item_options = replace(
            options or RequestOverrides(),
            on_dispatch=_compose_dispatch_callback(
                options.on_dispatch if options is not None else None, receipts, index
            ),
        )
        try:
            client.items.update_fields(
                space_id=space_id,
                board_id=board_id,
                item_id=item_id,
                body=dict(updates[index]["body"]),
                options=item_options,
            )
        except Exception as error:
            status = "ambiguous" if receipts[index].attempted else "failed"
            phase = "response" if receipts[index].attempted else "preflight"
            receipts[index] = transition_receipt(receipts[index], status, phase, error)
            if throw_on_error:
                raise PlakyPartialMutationError(
                    "Bulk item update has an unconfirmed mutation outcome.",
                    receipts=tuple(receipts),
                    failed_index=index,
                ) from error
        else:
            receipts[index] = transition_receipt(receipts[index], "completed", "completed")
        _report_sync(on_progress, receipts, index, len(item_ids))
    return tuple(receipts)


def _report_sync(
    on_progress: Callable[[int, int], None] | None,
    receipts: list[MutationReceipt],
    index: int,
    total: int,
) -> None:
    if on_progress is None:
        return
    try:
        on_progress(index + 1, total)
    except Exception as error:
        raise PlakyPartialMutationError(
            "Bulk item update progress reporting failed.",
            receipts=tuple(receipts),
            failed_index=index,
        ) from error


def _mark_dispatched(receipts: list[MutationReceipt], index: int) -> None:
    receipts[index] = transition_receipt(receipts[index], "request-started", "request")


def _compose_dispatch_callback(
    caller_callback: Callable[[], None] | None,
    receipts: list[MutationReceipt],
    index: int,
) -> Callable[[], None]:
    def on_dispatch() -> None:
        if caller_callback is not None:
            caller_callback()
        _mark_dispatched(receipts, index)

    return on_dispatch
