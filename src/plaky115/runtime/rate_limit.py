"""Rate-limit observation and local estimation.

Preserves both views from the pinned source's RateLimitSink: server headers
when available, and a local rolling 60-second window with a 200-request
default maximum. Estimates only; never sleeps or throttles implicitly.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RateLimitSnapshot:
    """Last-seen server rate-limit headers.

    ``reset_at`` is the ``X-RateLimit-Reset`` value exactly as the server
    sent it; no unit normalization is applied.
    """

    limit: float | None = None
    remaining: float | None = None
    reset_at: float | None = None


DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60.0
DEFAULT_RATE_LIMIT_MAX = 200


def _parse_num(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


@dataclass
class RateLimitTracker:
    window_seconds: float = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    max_per_window: int = DEFAULT_RATE_LIMIT_MAX
    last: RateLimitSnapshot = field(default_factory=RateLimitSnapshot)
    _timestamps: list[float] = field(default_factory=lambda: [])

    def observe(self, headers: Mapping[str, str], now: float | None = None) -> None:
        """Record one response's rate-limit headers and count the request."""
        lookup = {k.lower(): v for k, v in headers.items()}
        self.last = RateLimitSnapshot(
            limit=_parse_num(lookup.get("x-ratelimit-limit")),
            remaining=_parse_num(lookup.get("x-ratelimit-remaining")),
            reset_at=_parse_num(lookup.get("x-ratelimit-reset")),
        )
        self.record(now)

    def record(self, now: float | None = None) -> None:
        moment = time.monotonic() if now is None else now
        self._timestamps.append(moment)
        self._prune(moment)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        index = 0
        while index < len(self._timestamps) and self._timestamps[index] <= cutoff:
            index += 1
        if index:
            del self._timestamps[:index]

    def estimated_remaining(self, now: float | None = None) -> float:
        moment = time.monotonic() if now is None else now
        self._prune(moment)
        if self.last.remaining is not None:
            return self.last.remaining
        return max(0, self.max_per_window - len(self._timestamps))

    def would_throttle(self, now: float | None = None) -> bool:
        return self.estimated_remaining(now) <= 0

    def seconds_until_next_slot(self, now: float | None = None) -> float:
        moment = time.monotonic() if now is None else now
        self._prune(moment)
        if len(self._timestamps) < self.max_per_window:
            return 0.0
        return max(0.0, self._timestamps[0] + self.window_seconds - moment)

    def reset(self) -> None:
        self._timestamps.clear()
        self.last = RateLimitSnapshot()
