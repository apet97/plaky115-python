"""The read-only with_retries helper: bounded retries and argument checks."""

import pytest

from plaky115 import (
    PlakyError,
    PlakyRateLimitError,
    PlakyServerError,
    async_with_retries,
    with_retries,
)

pytestmark = pytest.mark.anyio


def rate_limited(retry_after_ms: float | None = 1) -> PlakyRateLimitError:
    return PlakyRateLimitError(
        "slow down",
        status=429,
        method="GET",
        url="https://api.example.test/x",
        headers={},
        retry_after_ms=retry_after_ms,
    )


def test_with_retries_sync_paths() -> None:
    calls: list[int] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise rate_limited()
        return "ok"

    assert with_retries(flaky, max_retries=3, base_delay_ms=0) == "ok"
    assert len(calls) == 3

    with pytest.raises(PlakyError, match="kind=read"):
        with_retries(lambda: "x", kind="write")
    with pytest.raises(ValueError, match="maxRetries must be a finite non-negative integer"):
        with_retries(lambda: "x", max_retries=-1)
    with pytest.raises(ValueError, match="baseDelayMs must be a finite non-negative number"):
        with_retries(lambda: "x", base_delay_ms=float("nan"))
    with pytest.raises(KeyError):
        with_retries(lambda: (_ for _ in ()).throw(KeyError("boom")), max_retries=2)


async def test_with_retries_async_paths() -> None:
    calls: list[int] = []

    async def flaky() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise rate_limited()
        return "ok"

    assert await async_with_retries(flaky, max_retries=2, base_delay_ms=0) == "ok"

    async def hopeless() -> str:
        raise rate_limited(retry_after_ms=None)

    with pytest.raises(PlakyRateLimitError):
        await async_with_retries(hopeless, max_retries=1, base_delay_ms=0)


def test_with_retries_sync() -> None:
    calls = 0

    def flaky() -> int:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise PlakyServerError("boom", status=500, method="GET", url="u", headers={})
        return 42

    assert with_retries(flaky, base_delay_ms=0) == 42
    assert calls == 2
    with pytest.raises(Exception, match="withRetries only supports kind=read"):
        with_retries(lambda: 1, kind="write")


async def test_async_with_retries() -> None:
    calls = 0

    async def flaky() -> int:
        nonlocal calls
        calls += 1
        if calls < 2:
            from plaky115 import PlakyServerError

            raise PlakyServerError("boom", status=500, method="GET", url="u", headers={})
        return 7

    assert await async_with_retries(flaky, base_delay_ms=0) == 7
    assert calls == 2
