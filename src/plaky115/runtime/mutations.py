"""Durable mutation receipts and attempt tracking.

Ported from sdk/src/runtime/mutations.ts at the pinned source
(docs/port/spec-transport.md, docs/port/spec-helpers.md). Receipts are
immutable, redacted, and conservative: any failure after request dispatch
is recorded as ambiguous with may_have_committed=True.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from plaky115.runtime.redaction import bound_text

MutationReceiptStatus = Literal["planned", "request-started", "completed", "failed", "ambiguous"]
MutationPhase = Literal["preflight", "request", "response", "completed"]

MAX_MUTATION_TEXT_LENGTH = 1024
_OPERATION_TEXT_LIMIT = 256
_TARGET_TEXT_LIMIT = 128
_ERROR_NAME_LIMIT = 128


@dataclass(frozen=True)
class MutationErrorSummary:
    name: str
    message: str


@dataclass(frozen=True)
class MutationReceipt:
    operation: str
    index: int
    status: MutationReceiptStatus
    attempted: bool
    may_have_committed: bool
    phase: MutationPhase
    target_ids: dict[str, str] = field(default_factory=lambda: {})
    error: MutationErrorSummary | None = None


def mutation_error_summary(error: BaseException) -> MutationErrorSummary:
    name = type(error).__name__ or "Error"
    message = str(error) or "Mutation failed."
    return MutationErrorSummary(
        name=bound_text(name, _ERROR_NAME_LIMIT),
        message=bound_text(message, MAX_MUTATION_TEXT_LENGTH),
    )


def new_receipt(operation: str, index: int, target_ids: dict[str, str]) -> MutationReceipt:
    return MutationReceipt(
        operation=bound_text(operation, _OPERATION_TEXT_LIMIT),
        index=index,
        status="planned",
        attempted=False,
        may_have_committed=False,
        phase="preflight",
        target_ids={
            bound_text(k, _TARGET_TEXT_LIMIT): bound_text(str(v), _TARGET_TEXT_LIMIT)
            for k, v in target_ids.items()
        },
    )


def transition_receipt(
    receipt: MutationReceipt,
    status: MutationReceiptStatus,
    phase: MutationPhase,
    error: BaseException | None = None,
) -> MutationReceipt:
    return replace(
        receipt,
        status=status,
        phase=phase,
        attempted=status in ("request-started", "completed", "ambiguous"),
        may_have_committed=status in ("ambiguous", "request-started"),
        error=mutation_error_summary(error) if error is not None else receipt.error,
    )


class AttemptTracker:
    """Invocation-local mutation attempt state.

    Never global, shared, cached, or serialized directly. One tracker per
    tool call or workflow write.
    """

    def __init__(self, operation: str, target_ids: dict[str, str] | None = None) -> None:
        self._receipt = new_receipt(operation, 0, target_ids or {})

    @property
    def receipt(self) -> MutationReceipt:
        return self._receipt

    @property
    def attempted(self) -> bool:
        return self._receipt.attempted

    @property
    def may_have_committed(self) -> bool:
        return self._receipt.may_have_committed

    @property
    def phase(self) -> MutationPhase:
        return self._receipt.phase

    def request_started(self) -> None:
        self._receipt = transition_receipt(self._receipt, "request-started", "request")

    def completed(self) -> None:
        self._receipt = transition_receipt(self._receipt, "completed", "completed")

    def ambiguous(self, error: BaseException) -> None:
        self._receipt = transition_receipt(self._receipt, "ambiguous", "response", error)
