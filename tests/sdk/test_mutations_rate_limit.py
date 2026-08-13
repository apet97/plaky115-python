"""Mutation receipt and rate-limit tracker gates (spec-transport §10, spec-helpers §5)."""

import dataclasses

import pytest

from plaky115.errors import PlakyPartialMutationError
from plaky115.idempotency import (
    new_idempotency_key,
    resolve_explicit_idempotency_key,
    resolve_idempotency_key,
)
from plaky115.runtime.mutations import (
    AttemptTracker,
    mutation_error_summary,
    new_receipt,
    transition_receipt,
)
from plaky115.runtime.rate_limit import RateLimitTracker


def test_receipt_lifecycle_and_conservative_flags() -> None:
    receipt = new_receipt("items.updateFields", 0, {"spaceId": "1", "itemId": "2"})
    assert receipt.status == "planned"
    assert receipt.attempted is False
    assert receipt.may_have_committed is False
    assert receipt.phase == "preflight"

    started = transition_receipt(receipt, "request-started", "request")
    assert started.attempted is True
    assert started.may_have_committed is True  # in-flight is conservative

    done = transition_receipt(started, "completed", "completed")
    assert done.attempted is True
    assert done.may_have_committed is False

    failed = transition_receipt(started, "ambiguous", "response", RuntimeError("x plk_key y"))
    assert failed.may_have_committed is True
    assert failed.error is not None
    assert "plk_key" not in failed.error.message


def test_receipts_are_immutable() -> None:
    receipt = new_receipt("op", 0, {})
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.status = "completed"  # type: ignore[misc]


def test_error_summary_bounded_and_redacted() -> None:
    summary = mutation_error_summary(RuntimeError("plk_secret " + "m" * 3000))
    assert summary.name == "RuntimeError"
    assert len(summary.message) <= 1024
    assert "plk_secret" not in summary.message


def test_error_summary_defaults() -> None:
    summary = mutation_error_summary(RuntimeError())
    assert summary.message == "Mutation failed."


def test_attempt_tracker_flow() -> None:
    tracker = AttemptTracker("createItem", {"spaceId": "1"})
    assert not tracker.attempted
    tracker.request_started()
    assert tracker.attempted and tracker.may_have_committed
    tracker.completed()
    assert tracker.attempted and not tracker.may_have_committed

    failing = AttemptTracker("createItem")
    failing.request_started()
    failing.ambiguous(TimeoutError("late"))
    assert failing.may_have_committed
    assert failing.receipt.error is not None


def test_partial_mutation_error_carries_receipts() -> None:
    receipts = (new_receipt("op", 0, {}),)
    error = PlakyPartialMutationError("failed", receipts=receipts, failed_index=0)
    assert error.receipts == receipts
    assert error.failed_index == 0


def test_idempotency_helpers() -> None:
    key = new_idempotency_key()
    assert key.startswith("idmp_")
    assert resolve_explicit_idempotency_key(None, None) is None
    assert resolve_explicit_idempotency_key("a", "b") == "a"
    assert resolve_explicit_idempotency_key(None, "b") == "b"
    generated = resolve_idempotency_key(None, None, prefix="bulk")
    assert generated.startswith("bulk_")


def test_rate_limit_tracker_windows() -> None:
    tracker = RateLimitTracker()
    assert tracker.estimated_remaining(now=0.0) == 200
    for i in range(200):
        tracker.record(now=float(i % 50))
    assert tracker.would_throttle(now=50.0)
    assert tracker.seconds_until_next_slot(now=50.0) > 0
    # Entries age out of the rolling window.
    assert tracker.estimated_remaining(now=1000.0) == 200
    assert tracker.seconds_until_next_slot(now=1000.0) == 0.0


def test_rate_limit_server_headers_win() -> None:
    tracker = RateLimitTracker()
    tracker.observe(
        {"X-RateLimit-Limit": "200", "X-RateLimit-Remaining": "3"},
        now=0.0,
    )
    assert tracker.last.limit == 200
    assert tracker.last.remaining == 3
    assert tracker.estimated_remaining(now=0.0) == 3
    tracker.observe({}, now=1.0)  # snapshot replaced wholesale
    assert tracker.last.remaining is None
    tracker.reset()
    assert tracker.estimated_remaining(now=1.0) == 200
