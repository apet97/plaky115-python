"""Deterministic, spreadsheet-safe CSV rendering for item exports.

Ported from sdk/src/workflows/internal/csv.ts at the pinned source
(docs/port/spec-helpers.md §9). Output is byte-identical to the source for
the golden fixtures in tests/fixtures/export.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

CsvSafety = Literal["spreadsheet", "raw"]

_FORMULA_STARTERS = ("=", "+", "-", "@")


def field_label(field: Mapping[str, Any]) -> str:
    """Prefer name, then title, then key; empty string means unlabelled."""
    for key in ("name", "title", "key"):
        value = field.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def canonical_json(value: Any) -> str:
    """Deterministic nested JSON: sorted object keys, no spaces."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int | float):
        if isinstance(value, float) and not math.isfinite(value):
            return "null"
        return json.dumps(value)
    if isinstance(value, list | tuple):
        seq = cast("Sequence[Any]", value)
        return "[" + ",".join(canonical_json(v) for v in seq) + "]"
    if isinstance(value, Mapping):
        record = cast("Mapping[str, Any]", value)
        keys = sorted(record.keys())
        parts = [
            f"{json.dumps(str(key), ensure_ascii=False)}:{canonical_json(record[key])}"
            for key in keys
        ]
        return "{" + ",".join(parts) + "}"
    return json.dumps(str(value), ensure_ascii=False)


def protect_spreadsheet_string(value: str) -> str:
    if value == "":
        return value
    if value[0] in ("\t", "\r", "\n"):
        return "'" + value
    stripped = re.sub(r"^[ \t]+", "", value)
    if stripped and stripped[0] in _FORMULA_STARTERS:
        return "'" + value
    return value


def format_cell(value: Any, safety: CsvSafety) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return protect_spreadsheet_string(value) if safety == "spreadsheet" else value
    if isinstance(value, int | float):
        if isinstance(value, float) and not math.isfinite(value):
            return "null"
        return json.dumps(value)
    return canonical_json(value)


def quote_csv(value: str) -> str:
    if re.search(r'[",\r\n]', value) or re.match(r"^\s", value):
        return '"' + value.replace('"', '""') + '"'
    return value


@dataclass(frozen=True)
class _Descriptor:
    identity: str
    label: str
    key: str | None = None
    missing_index: int | None = None
    column: str = ""


@dataclass(frozen=True)
class CsvSchema:
    top_keys: tuple[str, ...]
    descriptors: tuple[_Descriptor, ...]

    @property
    def header(self) -> list[str]:
        return [*self.top_keys, *(d.column for d in self.descriptors)]


def _collect_descriptors(
    registry: dict[str, _Descriptor],
    fields: Any,
) -> None:
    if not isinstance(fields, list):
        return
    missing_occurrence = 0
    for field in cast("list[Any]", fields):
        if not isinstance(field, Mapping):
            continue
        record = cast("Mapping[str, Any]", field)
        label = field_label(record)
        if not label:
            continue
        key = record.get("key")
        if isinstance(key, str) and key:
            identity = f"key:{key}"
        else:
            missing_occurrence += 1
            identity = f"missing:{label}:{missing_occurrence}"
            key = None
        if identity not in registry:
            registry[identity] = _Descriptor(identity=identity, label=label, key=key)


def create_items_csv_schema(
    items: Sequence[Mapping[str, Any]],
    definitions: Any = None,
) -> CsvSchema:
    top_keys = sorted({key for item in items for key in item if key != "fields"})
    registry: dict[str, _Descriptor] = {}
    _collect_descriptors(registry, definitions)
    for item in items:
        _collect_descriptors(registry, item.get("fields"))
    return _finalize(top_keys, list(registry.values()))


def _finalize(top_keys: list[str], descriptors: list[_Descriptor]) -> CsvSchema:
    ordered = sorted(descriptors, key=lambda d: (d.label, d.identity))
    missing_index = 0
    with_indices: list[_Descriptor] = []
    for descriptor in ordered:
        if descriptor.key is None:
            missing_index += 1
            with_indices.append(
                _Descriptor(
                    identity=descriptor.identity,
                    label=descriptor.label,
                    key=None,
                    missing_index=missing_index,
                )
            )
        else:
            with_indices.append(descriptor)

    label_counts: dict[str, int] = {}
    for descriptor in with_indices:
        label_counts[descriptor.label] = label_counts.get(descriptor.label, 0) + 1

    used = set(top_keys)
    final: list[_Descriptor] = []
    for descriptor in with_indices:
        collides = descriptor.label in top_keys or label_counts[descriptor.label] > 1
        if collides:
            if descriptor.key is not None:
                base = f"{descriptor.label} [{descriptor.key}]"
            else:
                base = f"{descriptor.label} [#{descriptor.missing_index}]"
        else:
            base = descriptor.label
        column = base
        suffix = 0
        while column in used:
            suffix += 1
            column = f"{base} [#{suffix}]"
        used.add(column)
        final.append(
            _Descriptor(
                identity=descriptor.identity,
                label=descriptor.label,
                key=descriptor.key,
                missing_index=descriptor.missing_index,
                column=column,
            )
        )
    return CsvSchema(top_keys=tuple(top_keys), descriptors=tuple(final))


def _collect_field_values(item: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    fields = item.get("fields")
    if not isinstance(fields, list):
        return values
    missing_occurrence = 0
    for field in cast("list[Any]", fields):
        if not isinstance(field, Mapping):
            continue
        record = cast("Mapping[str, Any]", field)
        label = field_label(record)
        if not label:
            continue
        key = record.get("key")
        if isinstance(key, str) and key:
            identity = f"key:{key}"
        else:
            missing_occurrence += 1
            identity = f"missing:{label}:{missing_occurrence}"
        if identity not in values:
            values[identity] = record.get("value")
    return values


def render_item_row(item: Mapping[str, Any], safety: CsvSafety, schema: CsvSchema) -> str:
    field_values = _collect_field_values(item)
    cells = [format_cell(item.get(key), safety) for key in schema.top_keys]
    cells.extend(format_cell(field_values.get(d.identity), safety) for d in schema.descriptors)
    return ",".join(quote_csv(cell) for cell in cells)


def render_items_csv_chunk(
    items: Sequence[Mapping[str, Any]],
    safety: CsvSafety,
    schema: CsvSchema,
    include_header: bool,
) -> str:
    if not items and not include_header:
        return ""
    lines: list[str] = []
    if include_header:
        lines.append(",".join(quote_csv(cell) for cell in schema.header))
    lines.extend(render_item_row(item, safety, schema) for item in items)
    return "\n".join(lines) + "\n"


def render_items_csv(
    items: Sequence[Mapping[str, Any]],
    safety: CsvSafety = "spreadsheet",
    definitions: Any = None,
) -> str:
    if not items:
        return ""
    schema = create_items_csv_schema(items, definitions)
    return render_items_csv_chunk(items, safety, schema, include_header=True)
