"""Retry policy gates (spec-transport §2)."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from plaky115.runtime.retry_policy import (
    can_retry,
    can_retry_error,
    parse_retry_after,
    retry_delay_ms,
    should_retry_response,
)


def test_only_get_retries() -> None:
    assert can_retry("GET")
    assert can_retry("get")
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert not can_retry(method)


def test_retryable_statuses() -> None:
    assert should_retry_response("GET", 429, 0, 2)
    assert should_retry_response("GET", 500, 0, 2)
    assert should_retry_response("GET", 599, 1, 2)
    for status in (400, 401, 403, 404, 409, 422, 302):
        assert not should_retry_response("GET", status, 0, 2)
    assert not should_retry_response("POST", 500, 0, 2)
    assert not should_retry_response("GET", 500, 2, 2)  # budget exhausted


def test_error_retry_budget() -> None:
    assert can_retry_error("GET", 0, 2)
    assert can_retry_error("GET", 1, 2)
    assert not can_retry_error("GET", 2, 2)
    assert not can_retry_error("POST", 0, 2)


def test_equal_jitter_backoff_bounds() -> None:
    for attempt, capped in ((0, 250), (1, 500), (2, 1000), (40, 60_000)):
        for _ in range(20):
            delay = retry_delay_ms(None, attempt)
            assert capped / 2 <= delay < capped


def test_retry_after_seconds() -> None:
    assert parse_retry_after("2") == 2000
    assert parse_retry_after("2.5") == 2500
    assert parse_retry_after("0") == 0
    assert parse_retry_after("") is None
    assert parse_retry_after(None) is None
    assert parse_retry_after("soon") is None


def test_retry_after_http_date() -> None:
    future = datetime.now(UTC) + timedelta(seconds=30)
    parsed = parse_retry_after(format_datetime(future, usegmt=True))
    assert parsed is not None and 25_000 < parsed <= 31_000
    past = datetime.now(UTC) - timedelta(seconds=30)
    assert parse_retry_after(format_datetime(past, usegmt=True)) == 0


def test_retry_after_clamped_in_delay() -> None:
    assert retry_delay_ms("120", 0) == 60_000  # clamped to cap
    assert retry_delay_ms("0", 0) == 0  # deterministic, bypasses jitter
    assert retry_delay_ms("1", 5) == 1000
