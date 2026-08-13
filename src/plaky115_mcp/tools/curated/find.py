"""plaky_find: find entities by exact ID or text reference."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyAmbiguousMatchError, PlakyError
from plaky115.resolvers import (
    async_resolve_item,
    async_resolve_item_file_on_item,
    async_resolve_item_group_in_board,
    async_resolve_space,
    async_resolve_space_and_board,
    async_resolve_team,
    async_resolve_user,
)
from plaky115_mcp.compaction import compact_entity, error_result, make_result
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error, usage_error
from plaky115_mcp.outputs import EntityOutput
from plaky115_mcp.registry import ToolSpec

_KINDS = ("space", "board", "item", "user", "team", "itemGroup", "itemFile")
_COMPACT_BY_KIND = {
    "space": "space",
    "board": "board",
    "item": "item",
    "user": "raw",
    "team": "raw",
    "itemGroup": "itemGroup",
    "itemFile": "itemFile",
}


def build_find(client: AsyncPlakyClient) -> ToolSpec:
    async def plaky_find(
        kind: str,
        query: str,
        spaceId: int | str | None = None,
        boardId: int | str | None = None,
        itemId: int | str | None = None,
    ) -> Annotated[CallToolResult, EntityOutput]:
        try:
            if kind not in _KINDS:
                envelope = usage_error(f"kind must be one of {', '.join(_KINDS)}")
                return error_result(envelope_wire(envelope), "Invalid kind.")
            entity: Any
            if kind == "space":
                entity = await async_resolve_space(client, query)
            elif kind == "board":
                if spaceId is None:
                    envelope = usage_error("board lookup requires spaceId")
                    return error_result(envelope_wire(envelope), "Missing spaceId.")
                _, entity = await async_resolve_space_and_board(client, space=spaceId, board=query)
            elif kind == "item":
                if spaceId is None or boardId is None:
                    envelope = usage_error("item lookup requires spaceId and boardId")
                    return error_result(envelope_wire(envelope), "Missing scope IDs.")
                entity = await async_resolve_item(client, space=spaceId, board=boardId, item=query)
            elif kind == "user":
                entity = await async_resolve_user(client, query)
            elif kind == "team":
                entity = await async_resolve_team(client, query)
            elif kind == "itemGroup":
                if spaceId is None or boardId is None:
                    envelope = usage_error("itemGroup lookup requires spaceId and boardId")
                    return error_result(envelope_wire(envelope), "Missing scope IDs.")
                entity = await async_resolve_item_group_in_board(
                    client, space_id=spaceId, board_id=boardId, item_group=query
                )
            else:
                if spaceId is None or boardId is None or itemId is None:
                    envelope = usage_error("itemFile lookup requires spaceId, boardId, and itemId")
                    return error_result(envelope_wire(envelope), "Missing scope IDs.")
                entity = await async_resolve_item_file_on_item(
                    client,
                    space_id=spaceId,
                    board_id=boardId,
                    item_id=itemId,
                    item_file=query,
                )
            wire = compact_entity(
                entity.model_dump(mode="json", by_alias=True, exclude_none=True)
                if hasattr(entity, "model_dump")
                else dict(entity),
                _COMPACT_BY_KIND[kind],
            )
            return make_result(text=f"plaky_find: {kind} id={wire.get('id')}", structured=wire)
        except asyncio.CancelledError:
            raise
        except PlakyAmbiguousMatchError as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_find",
        title="Find entity",
        description=(
            "Find one space, board, item, user, team, item group, or item "
            "file by exact ID or case-insensitive text. Ambiguous matches "
            "return a structured error listing the candidate count."
        ),
        handler=plaky_find,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="curated",
    )
