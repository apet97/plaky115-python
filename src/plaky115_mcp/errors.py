"""MCP error envelope and domain-failure adapter.

Known failures return is_error=True with the wire-compatible envelope from
the pinned source (plan section 10.6). Cancellation is always re-raised.
Unknown programmer errors are redacted, logged to stderr with a correlation
ID, and converted through one controlled internal-error path.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from plaky115.errors import (
    PlakyAmbiguousMatchError,
    PlakyApiError,
    PlakyCancelledError,
    PlakyConnectionError,
    PlakyDecodeError,
    PlakyError,
    PlakyOutputLimitError,
    PlakyPartialMutationError,
    PlakyRateLimitError,
    PlakyResponseTooLargeError,
    PlakyTimeoutError,
    UploadValidationError,
)
from plaky115.runtime.mutations import AttemptTracker, MutationReceipt
from plaky115.runtime.redaction import presentation_text

logger = logging.getLogger("plaky115_mcp")


class ReceiptModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operation: str
    index: int
    status: str
    attempted: bool
    may_have_committed: bool = Field(alias="mayHaveCommitted")
    phase: str
    target_ids: dict[str, str] = Field(alias="targetIds", default_factory=lambda: {})
    error: dict[str, str] | None = None


class ErrorDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: str
    name: str
    message: str
    retryable: bool
    status: int | None = None
    code: str | int | None = None
    request_id: str | None = Field(alias="requestId", default=None)
    retry_after_ms: float | None = Field(alias="retryAfterMs", default=None)
    attempted: bool | None = None
    may_have_committed: bool | None = Field(alias="mayHaveCommitted", default=None)
    phase: str | None = None
    receipts: list[ReceiptModel] = Field(default_factory=lambda: [])


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


def receipt_model(receipt: MutationReceipt) -> ReceiptModel:
    return ReceiptModel(
        operation=receipt.operation,
        index=receipt.index,
        status=receipt.status,
        attempted=receipt.attempted,
        mayHaveCommitted=receipt.may_have_committed,
        phase=receipt.phase,
        targetIds=dict(receipt.target_ids),
        error=(
            {"name": receipt.error.name, "message": receipt.error.message}
            if receipt.error is not None
            else None
        ),
    )


def _category(error: BaseException) -> tuple[str, bool]:
    """Map a domain failure to (category, retryable)."""
    if isinstance(error, PlakyRateLimitError):
        return "api", True
    if isinstance(error, PlakyApiError):
        return "api", 500 <= error.status <= 599
    if isinstance(error, PlakyTimeoutError):
        return "timeout", True
    if isinstance(error, PlakyConnectionError):
        return "connection", True
    if isinstance(error, PlakyDecodeError):
        return "decode", False
    if isinstance(error, PlakyCancelledError):
        return "abort", False
    if isinstance(error, UploadValidationError | ValueError | TypeError):
        return "validation", False
    if isinstance(error, PlakyOutputLimitError | PlakyResponseTooLargeError):
        return "usage", False
    if isinstance(error, PlakyAmbiguousMatchError | PlakyPartialMutationError | PlakyError):
        return "plaky", False
    return "plaky", False


def error_envelope(
    error: BaseException,
    tracker: AttemptTracker | None = None,
    receipts: tuple[MutationReceipt, ...] | None = None,
) -> ErrorEnvelope:
    """Build the structured error envelope for a known domain failure."""
    if isinstance(error, asyncio.CancelledError):  # pragma: no cover - guarded upstream
        raise error
    if tracker is not None and tracker.receipt.status == "request-started":
        # A failure after dispatch is conservatively ambiguous.
        tracker.ambiguous(error)
    category, retryable = _category(error)
    detail = ErrorDetail(
        category=category,
        name=type(error).__name__,
        message=presentation_text(str(error) or "Unknown error."),
        retryable=retryable,
        attempted=tracker.attempted if tracker is not None else False,
        mayHaveCommitted=tracker.may_have_committed if tracker is not None else False,
        phase=tracker.phase if tracker is not None else "preflight",
    )
    if isinstance(error, PlakyApiError):
        detail.status = error.status
        if error.code is not None:
            detail.code = error.code
        if error.request_id is not None:
            detail.request_id = error.request_id
        if error.retry_after_ms is not None:
            detail.retry_after_ms = error.retry_after_ms
    if isinstance(error, PlakyPartialMutationError):
        detail.receipts = [receipt_model(r) for r in error.receipts]
    elif receipts:
        detail.receipts = [receipt_model(r) for r in receipts]
    return ErrorEnvelope(error=detail)


def usage_error(message: str) -> ErrorEnvelope:
    return ErrorEnvelope(
        error=ErrorDetail(
            category="usage",
            name="UsageError",
            message=presentation_text(message),
            retryable=False,
            attempted=False,
            mayHaveCommitted=False,
            phase="preflight",
        )
    )


def internal_error(error: BaseException) -> ErrorEnvelope:
    """Redact and log an unexpected programmer error with a correlation ID."""
    correlation_id = uuid.uuid4().hex[:12]
    logger.error(
        "internal error [%s]: %s: %s",
        correlation_id,
        type(error).__name__,
        presentation_text(str(error)),
    )
    return ErrorEnvelope(
        error=ErrorDetail(
            category="plaky",
            name="InternalError",
            message=f"Internal server error (correlation {correlation_id}).",
            retryable=False,
            attempted=False,
            mayHaveCommitted=False,
            phase="preflight",
        )
    )


def envelope_wire(envelope: ErrorEnvelope) -> dict[str, Any]:
    return envelope.model_dump(by_alias=True, exclude_none=True)
