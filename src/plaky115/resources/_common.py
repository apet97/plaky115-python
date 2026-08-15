"""Shared pure helpers for resource implementations.

Response-root validation and model parsing are identical for the sync and
async resource classes; only the network executor differs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from plaky115.http import RequestSpec
from plaky115.pagination import Page, assert_array_result, assert_paged_result

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class RequestOverrides:
    """Per-call request overrides accepted by every resource method."""

    timeout: float | None = None
    headers: Mapping[str, str] | None = None
    idempotency_key: str | None = None
    max_retries: int | None = None
    max_response_bytes: int | None = None
    on_dispatch: Callable[[], None] | None = None


class Requester(Protocol):
    """The async client seam every async resource depends on."""

    async def execute(self, spec: RequestSpec, options: RequestOverrides | None) -> Any: ...


class SyncRequester(Protocol):
    """The sync client seam every sync resource depends on."""

    def execute(self, spec: RequestSpec, options: RequestOverrides | None) -> Any: ...


def parse_page(data: Any, operation_id: str, model: type[ModelT]) -> Page[ModelT]:
    checked = assert_paged_result(data, operation_id)
    return Page[model].model_validate(checked)  # type: ignore[valid-type]


def parse_array(data: Any, operation_id: str, model: type[ModelT]) -> list[ModelT]:
    checked = assert_array_result(data, operation_id)
    return [model.model_validate(entry) for entry in checked]


def parse_object(data: Any, model: type[ModelT]) -> ModelT:
    return model.model_validate(data)


def expand_values(expand: Sequence[str] | None) -> list[str] | None:
    if expand is None:
        return None
    return [str(value) for value in expand]


BodyInput = Mapping[str, Any] | BaseModel


def body_as_dict(body: BodyInput) -> dict[str, Any]:
    if isinstance(body, BaseModel):
        return body.model_dump(by_alias=True, exclude_none=True)
    return dict(body)


def with_idempotency(
    options: RequestOverrides | None, idempotency_key: str | None
) -> RequestOverrides | None:
    """Attach a method-level idempotency key when the method supplies one."""
    if idempotency_key is None:
        return options
    if options is None:
        return RequestOverrides(idempotency_key=idempotency_key)
    return replace(options, idempotency_key=idempotency_key)
