"""Strict page-root validation and pagination primitives.

Ported from sdk/src/runtime/pagination.ts at the pinned source.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel

from plaky115.errors import PlakyResponseContractError

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 100
MAX_PAGES = 10_000


class Page(BaseModel, Generic[T]):
    """One page of results with the strict {data, hasMore} root."""

    data: list[T]
    has_more: bool

    model_config = {"populate_by_name": True, "frozen": True}


def assert_paged_result(value: Any, operation_id: str) -> dict[str, Any]:
    """Validate the strict paged root: {"data": [...], "hasMore": bool}."""
    if not isinstance(value, dict):
        raise PlakyResponseContractError(operation_id, "/")
    record = cast(dict[str, Any], value)
    if "data" not in record:
        raise PlakyResponseContractError(operation_id, "/data")
    data = record["data"]
    if not isinstance(data, list):
        raise PlakyResponseContractError(operation_id, "/data")
    if "hasMore" not in record:
        raise PlakyResponseContractError(operation_id, "/hasMore")
    has_more = record["hasMore"]
    if not isinstance(has_more, bool):
        raise PlakyResponseContractError(operation_id, "/hasMore")
    if len(cast(list[Any], data)) == 0 and has_more is True:
        # An empty page may not claim more results; it would loop forever.
        raise PlakyResponseContractError(operation_id, "/hasMore")
    return record


def assert_array_result(value: Any, operation_id: str) -> list[Any]:
    """Validate a bare-array response root."""
    if not isinstance(value, list):
        raise PlakyResponseContractError(operation_id, "/")
    return cast(list[Any], value)
