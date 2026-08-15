"""plaky_board_view: read-only board snapshot for the Board View MCP App.

The tool returns the board's columns, groups, label palettes, and a bounded
page of shaped items. Hosts that negotiated MCP Apps render the linked
`ui://` template; every other host can use the structured JSON directly.
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, cast

from mcp.types import CallToolResult, ToolAnnotations

from plaky115.async_client import AsyncPlakyClient
from plaky115.errors import PlakyError
from plaky115.pagination import DEFAULT_PAGE_SIZE
from plaky115.resolvers import async_resolve_space_and_board
from plaky115_mcp.apps import BOARD_VIEW_URI
from plaky115_mcp.compaction import error_result, make_result
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.outputs import BoardViewOutput
from plaky115_mcp.registry import ToolSpec

MAX_ITEMS = 500
_ITEM_BYTE_BUDGET = 112 * 1024
_TEXT_VALUE_LIMIT = 200
_LABEL_TYPES = ("STATUS", "TAG")


def _dump(entity: Any) -> dict[str, Any]:
    if hasattr(entity, "model_dump"):
        return entity.model_dump(mode="json", by_alias=True, exclude_none=True)
    return dict(entity)


def _nested_id(value: Any) -> Any:
    if isinstance(value, dict):
        return cast("dict[str, Any]", value).get("id")
    return value


def _person_name(entry: dict[str, Any]) -> Any:
    return entry.get("name") or entry.get("title") or entry.get("id")


def _shape_value(field_type: str | None, value: Any) -> Any:
    """Compact one item-field value; accepts both short and expanded forms."""
    if value is None:
        return None
    if field_type == "STATUS":
        return cast("dict[str, Any]", value).get("key") if isinstance(value, dict) else value
    if field_type == "TAG":
        entries = cast("list[Any]", value) if isinstance(value, list) else [value]
        return [
            cast("dict[str, Any]", e).get("key") if isinstance(e, dict) else e for e in entries
        ]
    if field_type == "PERSON":
        names: list[Any] = []
        for entry in _flatten_person(value):
            if isinstance(entry, dict):
                names.append(_person_name(cast("dict[str, Any]", entry)))
            else:
                names.append(entry)
        return names
    if isinstance(value, str) and len(value) > _TEXT_VALUE_LIMIT:
        return value[: _TEXT_VALUE_LIMIT - 1] + "…"
    return value


def _flatten_person(value: Any) -> list[Any]:
    """Person values arrive as an object holding user/team lists; flatten it."""
    if isinstance(value, dict):
        record = cast("dict[str, Any]", value)
        if not (record.get("name") or record.get("title")):
            flattened: list[Any] = []
            for nested in record.values():
                if isinstance(nested, list):
                    flattened.extend(cast("list[Any]", nested))
                elif nested is not None:
                    flattened.append(nested)
            return flattened
    if isinstance(value, list):
        return cast("list[Any]", value)
    return [value]


def _columns_and_labels(
    fields: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    columns: list[dict[str, Any]] = []
    labels: dict[str, dict[str, dict[str, Any]]] = {}
    for field in fields:
        key = field.get("key")
        if not key:
            continue
        field_type = field.get("type")
        columns.append({"key": key, "title": field.get("name") or key, "type": field_type})
        if field_type in _LABEL_TYPES:
            palette: dict[str, dict[str, Any]] = {}
            configuration = cast("dict[str, Any]", field.get("configuration") or {})
            for value in cast("list[dict[str, Any]]", configuration.get("values") or []):
                value_key = value.get("key")
                if value_key:
                    # An untitled label is Plaky's "unset" state; keep the
                    # title empty so the widget renders no pill for it.
                    palette[value_key] = {
                        "title": value.get("title") or "",
                        "color": value.get("color"),
                    }
            labels[key] = palette
    return columns, labels


def _shape_item(item: dict[str, Any], types_by_key: dict[str, str | None]) -> dict[str, Any]:
    shaped_fields: dict[str, Any] = {}
    for field in cast("list[dict[str, Any]]", item.get("fields") or []):
        key = field.get("key")
        if key:
            shaped_fields[key] = _shape_value(types_by_key.get(key), field.get("value"))
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "groupId": _nested_id(item.get("group")),
        "fields": shaped_fields,
    }


def build_board_view(client: AsyncPlakyClient) -> ToolSpec:
    async def plaky_board_view(
        spaceId: int | str,
        board: int | str,
    ) -> Annotated[CallToolResult, BoardViewOutput]:
        try:
            space, resolved = await async_resolve_space_and_board(
                client, space=spaceId, board=board
            )
            board_wire = _dump(resolved)
            space_id = _dump(space)["id"]
            board_id = board_wire["id"]
            if board_wire.get("fields") is None:
                board_wire = _dump(await client.boards.get(space_id=space_id, board_id=board_id))
            columns, labels = _columns_and_labels(board_wire.get("fields") or [])
            types_by_key = {c["key"]: c["type"] for c in columns}

            items: list[dict[str, Any]] = []
            used_bytes = 0
            truncated = False
            has_more = False
            page = 1
            while len(items) < MAX_ITEMS and not truncated:
                listing = await client.items.list(
                    space_id=space_id,
                    board_id=board_id,
                    page=page,
                    page_size=DEFAULT_PAGE_SIZE,
                    expand=["fields"],
                )
                for entry in listing.data:
                    shaped = _shape_item(_dump(entry), types_by_key)
                    size = len(json.dumps(shaped, ensure_ascii=False).encode("utf-8"))
                    if used_bytes + size > _ITEM_BYTE_BUDGET or len(items) >= MAX_ITEMS:
                        truncated = True
                        break
                    items.append(shaped)
                    used_bytes += size
                has_more = listing.has_more
                if not listing.has_more:
                    break
                page += 1
            truncated = truncated or (len(items) >= MAX_ITEMS and has_more)

            groups = cast("list[dict[str, Any]]", board_wire.get("groups") or [])
            structured: dict[str, Any] = {
                "board": {"id": board_id, "title": board_wire.get("title")},
                "space": {"id": space_id},
                "columns": columns,
                "labels": labels,
                "groups": [
                    {"id": g.get("id"), "title": g.get("title"), "color": g.get("color")}
                    for g in groups
                ],
                "items": items,
                "itemCount": len(items),
                "hasMore": has_more or truncated,
                "truncated": truncated,
            }
            suffix = " (truncated)" if truncated else ""
            return make_result(
                text=(f"plaky_board_view: {board_wire.get('title')} — {len(items)} items{suffix}"),
                structured=structured,
            )
        except asyncio.CancelledError:
            raise
        except (PlakyError, ValueError, TypeError) as exc:
            return error_result(envelope_wire(error_envelope(exc)), str(exc))
        except Exception as exc:
            return error_result(envelope_wire(internal_error(exc)), "Internal server error.")

    return ToolSpec(
        name="plaky_board_view",
        title="Board view",
        description=(
            "Read-only board snapshot for the Board View app: columns from the "
            "board's field definitions, groups, status/tag label colors, and up "
            f"to {MAX_ITEMS} shaped items. Hosts with MCP Apps support render "
            "an interactive table; the structured JSON is complete on its own."
        ),
        handler=plaky_board_view,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        kind="curated",
        meta={"ui": {"resourceUri": BOARD_VIEW_URI}},
    )
