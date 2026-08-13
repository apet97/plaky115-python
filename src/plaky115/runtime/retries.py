"""Generic read-only retry helper.

Ported from sdk/src/runtime/retries.ts at the pinned source. Only
explicitly retry-safe read operations may use this; it refuses any other
kind and never becomes a write-retry mechanism.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from plaky115.errors import PlakyApiError, PlakyError, PlakyRateLimitError

T = TypeVar("T")

_RETRY_AFTER_CAP_MS = 60_000
_JITTER_MS = 100


def _validate(value: float, name: str, integer: bool) -> None:
    bad = (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or value != value
        or value in (float("inf"), float("-inf"))
        or value < 0
        or (integer and not float(value).is_integer())
    )
    if bad:
        kind = " integer" if integer else " number"
        raise ValueError(f"{name} must be a finite non-negative{kind}")


def default_retryable(error: BaseException) -> bool:
    if isinstance(error, PlakyRateLimitError):
        return True
    return isinstance(error, PlakyApiError) and 500 <= error.status <= 599


def _wait_ms(error: BaseException, attempt: int, base_delay_ms: float) -> float:
    retry_after: float | None = None
    if isinstance(error, PlakyRateLimitError) and error.retry_after_ms is not None:
        retry_after = error.retry_after_ms
    if retry_after is not None and retry_after > 0:
        wait = min(retry_after, _RETRY_AFTER_CAP_MS)
    else:
        wait = base_delay_ms * (2**attempt)
    return wait + random.random() * _JITTER_MS


def _check_args(kind: str, max_retries: int, base_delay_ms: float) -> None:
    if kind != "read":
        raise PlakyError("withRetries only supports kind=read")
    _validate(max_retries, "maxRetries", integer=True)
    _validate(base_delay_ms, "baseDelayMs", integer=False)


def with_retries(
    fn: Callable[[], T],
    *,
    kind: str = "read",
    max_retries: int = 2,
    base_delay_ms: float = 250,
    is_retryable: Callable[[BaseException], bool] = default_retryable,
) -> T:
    """Run a read-only callable with bounded retries (sync)."""
    _check_args(kind, max_retries, base_delay_ms)
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as error:
            if attempt >= max_retries or not is_retryable(error):
                raise
            time.sleep(_wait_ms(error, attempt, base_delay_ms) / 1000)
            attempt += 1


async def async_with_retries(
    fn: Callable[[], Awaitable[Any]],
    *,
    kind: str = "read",
    max_retries: int = 2,
    base_delay_ms: float = 250,
    is_retryable: Callable[[BaseException], bool] = default_retryable,
) -> Any:
    """Run a read-only coroutine factory with bounded retries (async)."""
    _check_args(kind, max_retries, base_delay_ms)
    attempt = 0
    while True:
        try:
            return await fn()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if attempt >= max_retries or not is_retryable(error):
                raise
            await asyncio.sleep(_wait_ms(error, attempt, base_delay_ms) / 1000)
            attempt += 1
