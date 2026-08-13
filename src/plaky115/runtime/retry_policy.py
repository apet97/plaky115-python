"""GET-only retry policy with equal jitter and bounded Retry-After.

Ported from sdk/src/runtime/internal/retry-policy.ts at the pinned source
(docs/port/spec-transport.md). Writes never retry, with or without an
idempotency key.
"""

from __future__ import annotations

import random
from email.utils import parsedate_to_datetime

BACKOFF_BASE_MS = 250
BACKOFF_CAP_MS = 60_000


def can_retry(method: str) -> bool:
    return method.upper() == "GET"


def should_retry_response(method: str, status: int, attempt: int, max_retries: int) -> bool:
    if attempt >= max_retries:
        return False
    if status != 429 and not (500 <= status <= 599):
        return False
    return can_retry(method)


def can_retry_error(method: str, attempt: int, max_retries: int) -> bool:
    if attempt >= max_retries:
        return False
    return can_retry(method)


def parse_retry_after(header: str | None, now: float | None = None) -> float | None:
    """Parse a Retry-After header into milliseconds; None when unusable."""
    if not header:
        return None
    try:
        seconds = float(header.strip())
    except ValueError:
        seconds = None
    else:
        if seconds != seconds or seconds in (float("inf"), float("-inf")):
            seconds = None
    if seconds is not None:
        return seconds * 1000
    try:
        moment = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    import time as _time

    current = _time.time() if now is None else now
    return max(0.0, moment.timestamp() * 1000 - current * 1000)


def retry_delay_ms(retry_after_header: str | None, attempt: int) -> float:
    """Delay before the next attempt: Retry-After (clamped) or equal jitter."""
    if retry_after_header:
        parsed = parse_retry_after(retry_after_header)
        if parsed is not None:
            return min(max(parsed, 0.0), float(BACKOFF_CAP_MS))
    capped = min(BACKOFF_CAP_MS, BACKOFF_BASE_MS * (2**attempt))
    return capped / 2 + random.random() * (capped / 2)
