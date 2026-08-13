"""Entity resolvers: exact IDs use direct GETs; text uses one bounded list.

Ported from sdk/src/resolvers/index.ts at the pinned source
(docs/port/spec-helpers.md §7). Resolver-local errors use the pseudo-origin
``plaky115://resolver`` so they can never be mistaken for API responses.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from plaky115.errors import PlakyAmbiguousMatchError, PlakyNotFoundError
from plaky115.ids import INT64_MAX
from plaky115.models import Board, Item, ItemFile, ItemGroup, Space, Team, User
from plaky115.resources._common import RequestOverrides

if TYPE_CHECKING:
    from plaky115.async_client import AsyncPlakyClient
    from plaky115.client import PlakyClient

__all__ = [
    "EntityRef",
    "async_resolve_board",
    "async_resolve_item",
    "async_resolve_item_file_on_item",
    "async_resolve_item_group_in_board",
    "async_resolve_items_in_board",
    "async_resolve_space",
    "async_resolve_space_and_board",
    "async_resolve_team",
    "async_resolve_user",
    "resolve_board",
    "resolve_item",
    "resolve_item_file_on_item",
    "resolve_item_group_in_board",
    "resolve_items_in_board",
    "resolve_space",
    "resolve_space_and_board",
    "resolve_team",
    "resolve_user",
]

EntityRef = int | str | Mapping[str, Any] | Any

RESOLVER_URL = "plaky115://resolver"

_SELECTOR_FIELDS = ("title", "name", "email")
_MATCH_FIELDS = ("title", "name", "email")


def _canonical_id(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("identifier must be a canonical non-negative decimal string")
    if isinstance(value, int):
        if value < 0 or value > INT64_MAX:
            raise ValueError(
                "identifier must be a safe non-negative integer; "
                "pass larger identifiers as decimal strings"
            )
        return str(value)
    if isinstance(value, str):
        if not value.isdigit() or (value != "0" and value.startswith("0")):
            raise ValueError("identifier must be a canonical non-negative decimal string")
        if int(value) > INT64_MAX:
            raise ValueError("identifier exceeds signed int64 range")
        return value
    raise ValueError("identifier must be a canonical non-negative decimal string")


@dataclass(frozen=True)
class _RefMatch:
    id: str | None = None
    needle: str | None = None
    field: str | None = None


def _as_id(ref: EntityRef) -> _RefMatch:
    if isinstance(ref, bool):
        return _RefMatch()
    if isinstance(ref, int):
        return _RefMatch(id=_canonical_id(ref))
    if isinstance(ref, str):
        if ref.isdigit():
            return _RefMatch(id=_canonical_id(ref))
        return _RefMatch(needle=ref.lower())
    record: Mapping[str, Any] | None = (
        cast("Mapping[str, Any]", ref) if isinstance(ref, Mapping) else None
    )
    if record is None:
        value: Any = getattr(cast(object, ref), "id", None)
        if value is not None:
            return _RefMatch(id=_canonical_id(value))
        return _RefMatch()
    if record.get("id") is not None:
        # ID is authoritative; sibling labels are ignored.
        return _RefMatch(id=_canonical_id(record["id"]))
    selectors = [f for f in _SELECTOR_FIELDS if record.get(f) is not None]
    if len(selectors) > 1:
        raise TypeError(f"entity reference selectors conflict: {', '.join(selectors)}")
    if len(selectors) == 1:
        field = selectors[0]
        value = record[field]
        if not isinstance(value, str) or not value:
            raise TypeError(f"{field} selector must be a non-empty string")
        return _RefMatch(needle=value.lower(), field=field)
    return _RefMatch()


def _local_not_found(message: str) -> PlakyNotFoundError:
    return PlakyNotFoundError(message, status=404, method="LOCAL", url=RESOLVER_URL, headers={})


def _entity_value(entity: Any, field: str) -> Any:
    if isinstance(entity, Mapping):
        return cast(Mapping[str, Any], entity).get(field)
    return getattr(entity, field, None)


def _pick(items: Sequence[Any], match: _RefMatch, label: str) -> Any:
    if match.id is not None:
        for item in items:
            item_id = _entity_value(item, "id")
            if item_id is not None and _canonical_id(item_id) == match.id:
                return item
        raise _local_not_found(f"{label} not found: id={match.id}")
    if match.needle:
        fields = (match.field,) if match.field else _MATCH_FIELDS
        candidates = [
            item
            for item in items
            if any(
                isinstance(_entity_value(item, f), str)
                and match.needle in cast(str, _entity_value(item, f)).lower()
                for f in fields
            )
        ]
        if not candidates:
            raise _local_not_found(f"{label} not found: {match.needle}")
        if len(candidates) > 1:
            raise PlakyAmbiguousMatchError(
                f"{label} ambiguous: {match.needle}", candidates, len(candidates)
            )
        return candidates[0]
    raise _local_not_found(f"{label}: empty ref")


# ----------------------------------------------------------------------------
# Async resolvers
# ----------------------------------------------------------------------------


async def async_resolve_space(
    client: AsyncPlakyClient, ref: EntityRef, options: RequestOverrides | None = None
) -> Space:
    match = _as_id(ref)
    if match.id is not None:
        try:
            result = await client.spaces.get(match.id, options=options)
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"space not found: id={match.id}") from exc
        return _pick([result], match, "space")
    return _pick(await client.spaces.list_all(options=options), match, "space")


async def async_resolve_space_and_board(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    options: RequestOverrides | None = None,
) -> tuple[Space, Board]:
    resolved_space = await async_resolve_space(client, space, options)
    space_id = _canonical_id(_entity_value(resolved_space, "id"))
    match = _as_id(board)
    if match.id is not None:
        try:
            result = await client.boards.get(space_id=space_id, board_id=match.id, options=options)
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"board not found: id={match.id}") from exc
        return resolved_space, _pick([result], match, "board")
    boards = await client.boards.list_all(space_id=space_id, options=options)
    return resolved_space, _pick(boards, match, "board")


async def async_resolve_board(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    options: RequestOverrides | None = None,
) -> Board:
    _, resolved = await async_resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    return resolved


async def async_resolve_user(
    client: AsyncPlakyClient, ref: EntityRef, options: RequestOverrides | None = None
) -> User:
    # There is no user GET endpoint; even exact IDs resolve from the list.
    return _pick(await client.users.list_all(options=options), _as_id(ref), "user")


async def async_resolve_team(
    client: AsyncPlakyClient, ref: EntityRef, options: RequestOverrides | None = None
) -> Team:
    match = _as_id(ref)
    if match.id is not None:
        try:
            result = await client.teams.get(match.id, options=options)
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"team not found: id={match.id}") from exc
        return _pick([result], match, "team")
    return _pick(await client.teams.list_all(options=options), match, "team")


async def async_resolve_item(
    client: AsyncPlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    item: EntityRef,
    options: RequestOverrides | None = None,
) -> Item:
    resolved_space, resolved_board = await async_resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    space_id = _canonical_id(_entity_value(resolved_space, "id"))
    board_id = _canonical_id(_entity_value(resolved_board, "id"))
    resolved = await async_resolve_items_in_board(
        client, space_id=space_id, board_id=board_id, items=[item], options=options
    )
    return resolved[0]


async def async_resolve_items_in_board(
    client: AsyncPlakyClient,
    *,
    space_id: int | str,
    board_id: int | str,
    items: Sequence[EntityRef],
    options: RequestOverrides | None = None,
) -> list[Item]:
    refs = [_as_id(item) for item in items]
    if refs and all(ref.id is not None for ref in refs):
        # All exact IDs: concurrent direct GETs, order preserved.
        async def get_one(item_id: str) -> Any:
            try:
                result = await client.items.get(
                    space_id=space_id, board_id=board_id, item_id=item_id, options=options
                )
            except PlakyNotFoundError as exc:
                if exc.url == RESOLVER_URL:
                    raise
                raise _local_not_found(f"item not found: id={item_id}") from exc
            return _pick([result], _RefMatch(id=item_id), "item")

        return list(await asyncio.gather(*(get_one(cast(str, ref.id)) for ref in refs)))
    listing = await client.items.list_all(space_id=space_id, board_id=board_id, options=options)
    return [_pick(listing, ref, "item") for ref in refs]


async def async_resolve_item_group_in_board(
    client: AsyncPlakyClient,
    *,
    space_id: int | str,
    board_id: int | str,
    item_group: EntityRef,
    options: RequestOverrides | None = None,
) -> ItemGroup:
    match = _as_id(item_group)
    if match.id is not None:
        try:
            result = await client.item_groups.get(
                space_id=space_id, board_id=board_id, item_group_id=match.id, options=options
            )
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"item group not found: id={match.id}") from exc
        return _pick([result], match, "item group")
    groups = await client.item_groups.list_all(
        space_id=space_id, board_id=board_id, options=options
    )
    return _pick(groups, match, "item group")


async def async_resolve_item_file_on_item(
    client: AsyncPlakyClient,
    *,
    space_id: int | str,
    board_id: int | str,
    item_id: int | str,
    item_file: EntityRef,
    options: RequestOverrides | None = None,
) -> ItemFile:
    match = _as_id(item_file)
    if match.id is not None:
        try:
            result = await client.item_files.get(
                space_id=space_id,
                board_id=board_id,
                item_id=item_id,
                item_file_id=match.id,
                options=options,
            )
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"item file not found: id={match.id}") from exc
        return _pick([result], match, "item file")
    files = await client.item_files.list(
        space_id=space_id, board_id=board_id, item_id=item_id, options=options
    )
    return _pick(files, match, "item file")


# ----------------------------------------------------------------------------
# Sync resolvers
# ----------------------------------------------------------------------------


def resolve_space(
    client: PlakyClient, ref: EntityRef, options: RequestOverrides | None = None
) -> Space:
    match = _as_id(ref)
    if match.id is not None:
        try:
            result = client.spaces.get(match.id, options=options)
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"space not found: id={match.id}") from exc
        return _pick([result], match, "space")
    return _pick(client.spaces.list_all(options=options), match, "space")


def resolve_space_and_board(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    options: RequestOverrides | None = None,
) -> tuple[Space, Board]:
    resolved_space = resolve_space(client, space, options)
    space_id = _canonical_id(_entity_value(resolved_space, "id"))
    match = _as_id(board)
    if match.id is not None:
        try:
            result = client.boards.get(space_id=space_id, board_id=match.id, options=options)
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"board not found: id={match.id}") from exc
        return resolved_space, _pick([result], match, "board")
    boards = client.boards.list_all(space_id=space_id, options=options)
    return resolved_space, _pick(boards, match, "board")


def resolve_board(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    options: RequestOverrides | None = None,
) -> Board:
    return resolve_space_and_board(client, space=space, board=board, options=options)[1]


def resolve_user(
    client: PlakyClient, ref: EntityRef, options: RequestOverrides | None = None
) -> User:
    return _pick(client.users.list_all(options=options), _as_id(ref), "user")


def resolve_team(
    client: PlakyClient, ref: EntityRef, options: RequestOverrides | None = None
) -> Team:
    match = _as_id(ref)
    if match.id is not None:
        try:
            result = client.teams.get(match.id, options=options)
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"team not found: id={match.id}") from exc
        return _pick([result], match, "team")
    return _pick(client.teams.list_all(options=options), match, "team")


def resolve_item(
    client: PlakyClient,
    *,
    space: EntityRef,
    board: EntityRef,
    item: EntityRef,
    options: RequestOverrides | None = None,
) -> Item:
    resolved_space, resolved_board = resolve_space_and_board(
        client, space=space, board=board, options=options
    )
    space_id = _canonical_id(_entity_value(resolved_space, "id"))
    board_id = _canonical_id(_entity_value(resolved_board, "id"))
    return resolve_items_in_board(
        client, space_id=space_id, board_id=board_id, items=[item], options=options
    )[0]


def resolve_items_in_board(
    client: PlakyClient,
    *,
    space_id: int | str,
    board_id: int | str,
    items: Sequence[EntityRef],
    options: RequestOverrides | None = None,
) -> list[Item]:
    refs = [_as_id(item) for item in items]
    if refs and all(ref.id is not None for ref in refs):
        out: list[Item] = []
        for ref in refs:
            item_id = cast(str, ref.id)
            try:
                result = client.items.get(
                    space_id=space_id, board_id=board_id, item_id=item_id, options=options
                )
            except PlakyNotFoundError as exc:
                if exc.url == RESOLVER_URL:
                    raise
                raise _local_not_found(f"item not found: id={item_id}") from exc
            out.append(_pick([result], ref, "item"))
        return out
    listing = client.items.list_all(space_id=space_id, board_id=board_id, options=options)
    return [_pick(listing, ref, "item") for ref in refs]


def resolve_item_group_in_board(
    client: PlakyClient,
    *,
    space_id: int | str,
    board_id: int | str,
    item_group: EntityRef,
    options: RequestOverrides | None = None,
) -> ItemGroup:
    match = _as_id(item_group)
    if match.id is not None:
        try:
            result = client.item_groups.get(
                space_id=space_id, board_id=board_id, item_group_id=match.id, options=options
            )
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"item group not found: id={match.id}") from exc
        return _pick([result], match, "item group")
    groups = client.item_groups.list_all(space_id=space_id, board_id=board_id, options=options)
    return _pick(groups, match, "item group")


def resolve_item_file_on_item(
    client: PlakyClient,
    *,
    space_id: int | str,
    board_id: int | str,
    item_id: int | str,
    item_file: EntityRef,
    options: RequestOverrides | None = None,
) -> ItemFile:
    match = _as_id(item_file)
    if match.id is not None:
        try:
            result = client.item_files.get(
                space_id=space_id,
                board_id=board_id,
                item_id=item_id,
                item_file_id=match.id,
                options=options,
            )
        except PlakyNotFoundError as exc:
            if exc.url == RESOLVER_URL:
                raise
            raise _local_not_found(f"item file not found: id={match.id}") from exc
        return _pick([result], match, "item file")
    files = client.item_files.list(
        space_id=space_id, board_id=board_id, item_id=item_id, options=options
    )
    return _pick(files, match, "item file")
