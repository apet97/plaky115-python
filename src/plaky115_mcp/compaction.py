"""Result compaction and the 128 KiB aggregate serialized-result cap.

The UTF-8 canonical JSON encoding of the complete CallToolResult (content,
structuredContent, isError, and _meta) must not exceed 131,072 bytes.
Oversized output becomes a bounded structured usage error that itself fits
the cap.
"""

from __future__ import annotations

import json
from typing import Any, cast

from mcp.types import CallToolResult, TextContent

from plaky115.runtime.redaction import redact
from plaky115_mcp.errors import envelope_wire, usage_error

MAX_RESULT_BYTES = 128 * 1024  # 131_072
MAX_RAW_VALUE_BYTES = 64 * 1024
MAX_TEXT_CHARS = 4_000

_COMPACT_FIELD_LIMIT = 20


def result_bytes(result: CallToolResult) -> int:
    """Canonical UTF-8 size of the complete serialized result."""
    payload = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def make_result(
    *,
    text: str,
    structured: dict[str, Any] | None,
    is_error: bool = False,
) -> CallToolResult:
    """Build a bounded CallToolResult; oversized output degrades to a usage error."""
    safe_text = redact(text)
    if len(safe_text) > MAX_TEXT_CHARS:
        safe_text = safe_text[: MAX_TEXT_CHARS - 1] + "…"
    result = CallToolResult(
        content=[TextContent(type="text", text=safe_text)],
        structured_content=structured,
        is_error=is_error,
    )
    if result_bytes(result) <= MAX_RESULT_BYTES:
        return result
    envelope = envelope_wire(
        usage_error(
            "Result exceeds the 131072-byte serialized limit; narrow the request "
            "or use pagination/continuation arguments."
        )
    )
    return CallToolResult(
        content=[TextContent(type="text", text="Result too large; narrow the request.")],
        structured_content=envelope,
        is_error=True,
    )


def error_result(envelope: dict[str, Any], summary: str) -> CallToolResult:
    return make_result(text=summary, structured=envelope, is_error=True)


def _first_fields(value: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: value[k] for k in keys if k in value and value[k] is not None}


COMPACT_KEYS: dict[str, tuple[str, ...]] = {
    "space": ("id", "title", "kind"),
    "board": ("id", "title", "kind", "ranking"),
    "item": ("id", "title", "archived", "commentCount", "group", "parent"),
    "comment": ("id", "content", "createdBy", "createdAt", "repliesToId"),
    "itemGroup": ("id", "title", "color", "ranking"),
    "itemFile": ("id", "name", "size", "fileType", "extension", "uploadedBy"),
    "downloadLink": ("url", "expiresAt"),
}


def compact_entity(value: dict[str, Any], kind: str) -> dict[str, Any]:
    """Compact one API entity by kind; unknown kinds pass through bounded."""
    keys = COMPACT_KEYS.get(kind)
    if keys is None:
        return dict(list(value.items())[:_COMPACT_FIELD_LIMIT])
    compacted = _first_fields(value, keys)
    # Relationship fields may be full objects; reduce them to their IDs.
    for key in ("group", "parent", "createdBy", "uploadedBy"):
        nested = compacted.get(key)
        if isinstance(nested, dict):
            nested_record = cast("dict[str, Any]", nested)
            compacted[key] = nested_record.get("id")
    return compacted


def _compact_values(data: list[Any], kind: str) -> list[Any]:
    out: list[Any] = []
    for value in data:
        if isinstance(value, dict):
            out.append(compact_entity(cast("dict[str, Any]", value), kind))
        else:
            out.append(value)
    return out


def compact_page(data: list[Any], has_more: bool, kind: str) -> dict[str, Any]:
    return {"data": _compact_values(data, kind), "hasMore": has_more}


def compact_list(data: list[Any], kind: str) -> dict[str, Any]:
    return {"data": _compact_values(data, kind)}
