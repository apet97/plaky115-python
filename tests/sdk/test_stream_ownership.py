"""Response-owned streaming closes exactly once on every exit path."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import httpx2
import pytest

from plaky115.errors import PlakyTimeoutError
from plaky115.http import AsyncByteStream, SyncByteStream


class SyncResponse:
    def __init__(self, values: list[bytes | BaseException]) -> None:
        self.values = values
        self.close_calls = 0

    def iter_bytes(self) -> Iterator[bytes]:
        for value in self.values:
            if isinstance(value, BaseException):
                raise value
            yield value

    def close(self) -> None:
        self.close_calls += 1


class AsyncResponse:
    def __init__(self, values: list[bytes | BaseException]) -> None:
        self.values = values
        self.close_calls = 0

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for value in self.values:
            if isinstance(value, BaseException):
                raise value
            yield value

    async def aclose(self) -> None:
        self.close_calls += 1


def test_sync_stream_closes_on_exhaustion_error_and_context_exit() -> None:
    exhausted = SyncResponse([b"one"])
    stream = SyncByteStream(exhausted)
    assert list(stream) == [b"one"]
    stream.close()
    assert exhausted.close_calls == 1

    failed = SyncResponse([RuntimeError("broken")])
    with pytest.raises(RuntimeError, match="broken"):
        next(SyncByteStream(failed))
    assert failed.close_calls == 1

    contextual = SyncResponse([])
    with SyncByteStream(contextual) as entered:
        assert entered is not None
    assert contextual.close_calls == 1

    timed_out = SyncResponse([httpx2.ReadTimeout("slow")])
    with pytest.raises(PlakyTimeoutError):
        next(SyncByteStream(timed_out))
    assert timed_out.close_calls == 1


@pytest.mark.anyio
async def test_async_stream_closes_on_exhaustion_error_and_context_exit() -> None:
    exhausted = AsyncResponse([b"one"])
    stream = AsyncByteStream(exhausted)
    assert [value async for value in stream] == [b"one"]
    await stream.aclose()
    assert exhausted.close_calls == 1

    failed = AsyncResponse([RuntimeError("broken")])
    with pytest.raises(RuntimeError, match="broken"):
        await anext(AsyncByteStream(failed))
    assert failed.close_calls == 1

    contextual = AsyncResponse([])
    async with AsyncByteStream(contextual) as entered:
        assert entered is not None
    assert contextual.close_calls == 1

    timed_out = AsyncResponse([httpx2.ReadTimeout("slow")])
    with pytest.raises(PlakyTimeoutError):
        await anext(AsyncByteStream(timed_out))
    assert timed_out.close_calls == 1
