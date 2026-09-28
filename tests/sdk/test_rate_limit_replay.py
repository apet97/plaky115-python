"""429 replay for every method, GET-only retry for everything else, and pacing."""

from typing import Any

import httpx2
import pytest

import plaky115.errors as errors
import plaky115.runtime.async_transport as async_transport_module
import plaky115.runtime.transport as sync_transport_module
from fakes import make_options, mock_client
from plaky115 import AsyncPlakyClient, PlakyClient, RequestPacer
from plaky115.http import RequestSpec, async_request, request
from plaky115.runtime.retry_policy import should_retry_response

pytestmark = pytest.mark.anyio

WRITES = ["POST", "PUT", "PATCH", "DELETE"]


def _no_delay(retry_after: str | None, attempt: int) -> float:
    return 0.0


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync_transport_module, "retry_delay_ms", _no_delay)
    monkeypatch.setattr(async_transport_module, "retry_delay_ms", _no_delay)


class Recorder:
    """Answer each attempt from a status script and keep what was sent."""

    def __init__(self, *statuses: int) -> None:
        self.statuses = list(statuses)
        self.requests: list[httpx2.Request] = []

    def __call__(self, request_in: httpx2.Request) -> httpx2.Response:
        request_in.read()
        self.requests.append(request_in)
        status = self.statuses[min(len(self.requests), len(self.statuses)) - 1]
        if status == 429:
            return httpx2.Response(429, headers={"retry-after": "60"})
        return httpx2.Response(status, json={"id": 1})


def test_policy_replays_429_for_every_method_and_5xx_for_get_only() -> None:
    for method in ["GET", *WRITES]:
        assert should_retry_response(method, 429, 0, 2)
        assert not should_retry_response(method, 429, 2, 2)  # budget still bounds it
    assert should_retry_response("GET", 503, 0, 2)
    for method in WRITES:
        assert not should_retry_response(method, 500, 0, 2)
        assert not should_retry_response(method, 503, 0, 2)


@pytest.mark.parametrize("method", WRITES)
async def test_async_write_replays_429_with_same_body_and_idempotency_key(method: str) -> None:
    recorder = Recorder(429, 201)
    dispatched: list[int] = []
    async with mock_client(recorder) as client:
        data = await async_request(
            client,
            RequestSpec(method=method, path="/items", body={"title": "T"}),
            make_options(
                max_retries=2, idempotency_key="idmp_1", on_dispatch=lambda: dispatched.append(1)
            ),
        )
    assert data == {"id": 1}
    assert len(recorder.requests) == 2
    assert len(dispatched) == 2
    assert [r.headers["idempotency-key"] for r in recorder.requests] == ["idmp_1", "idmp_1"]
    assert [r.content for r in recorder.requests] == [b'{"title": "T"}'] * 2


@pytest.mark.parametrize("method", WRITES)
def test_sync_write_replays_429(method: str) -> None:
    recorder = Recorder(429, 429, 201)
    with httpx2.Client(transport=httpx2.MockTransport(recorder)) as client:
        data = request(
            client, RequestSpec(method=method, path="/items", body={}), make_options(max_retries=2)
        )
    assert data == {"id": 1}
    assert len(recorder.requests) == 3


async def test_write_429_replay_is_bounded_and_surfaces_rate_limit_error() -> None:
    recorder = Recorder(429)
    async with mock_client(recorder) as client:
        with pytest.raises(errors.PlakyRateLimitError) as info:
            await async_request(
                client,
                RequestSpec(method="POST", path="/items", body={}),
                make_options(max_retries=2),
            )
    assert len(recorder.requests) == 3  # max_retries=2
    assert info.value.retry_after_ms == 60_000


async def test_write_without_retry_budget_makes_one_attempt_on_429() -> None:
    recorder = Recorder(429)
    async with mock_client(recorder) as client:
        with pytest.raises(errors.PlakyRateLimitError):
            await async_request(
                client,
                RequestSpec(method="POST", path="/items", body={}),
                make_options(max_retries=0),
            )
    assert len(recorder.requests) == 1


@pytest.mark.parametrize("method", WRITES)
def test_sync_write_after_5xx_is_never_retried(method: str) -> None:
    # A 5xx may follow a commit, so the outcome is unknown and a replay could duplicate it.
    recorder = Recorder(503, 201)
    with (
        httpx2.Client(transport=httpx2.MockTransport(recorder)) as client,
        pytest.raises(errors.PlakyServerError),
    ):
        request(
            client, RequestSpec(method=method, path="/items", body={}), make_options(max_retries=2)
        )
    assert len(recorder.requests) == 1


def test_sync_write_after_connection_failure_is_never_retried() -> None:
    calls = 0

    def handler(request_in: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise httpx2.ConnectError("reset", request=request_in)

    with (
        httpx2.Client(transport=httpx2.MockTransport(handler)) as client,
        pytest.raises(errors.PlakyConnectionError),
    ):
        request(
            client, RequestSpec(method="POST", path="/items", body={}), make_options(max_retries=2)
        )
    assert calls == 1


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_pacer_claims_slots_over_a_sliding_window() -> None:
    clock = FakeClock()
    pacer = RequestPacer(limit=3, window_seconds=60, clock=clock)
    assert [pacer.reserve() for _ in range(3)] == [0.0, 0.0, 0.0]
    assert pacer.reserve() == 60.0  # the fourth waits for the first to leave
    assert pacer.reserve() == 60.0
    clock.now += 10
    assert pacer.reserve() == 50.0
    clock.now += 50  # the first three have left; the next three are claimed
    assert pacer.reserve() == 60.0


def test_pacer_frees_slots_once_the_window_passes() -> None:
    clock = FakeClock()
    pacer = RequestPacer(limit=2, window_seconds=60, clock=clock)
    pacer.reserve()
    clock.now += 30
    pacer.reserve()
    clock.now += 31
    assert pacer.reserve() == 0.0
    assert pacer.reserve() == 29.0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"limit": 0}, "limit"),
        ({"limit": True}, "limit"),
        ({"window_seconds": 0}, "window_seconds"),
        ({"window_seconds": float("nan")}, "window_seconds"),
        ({"window_seconds": float("inf")}, "window_seconds"),
    ],
)
def test_pacer_rejects_invalid_configuration(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        RequestPacer(**kwargs)


def test_sync_client_paces_every_attempt_including_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    waits: list[float] = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(sync_transport_module.time, "sleep", sleep)
    pacer = RequestPacer(limit=2, window_seconds=60, clock=clock)
    recorder = Recorder(429, 201, 200)
    with PlakyClient(
        api_key="plk_test", transport=httpx2.MockTransport(recorder), pacer=pacer
    ) as client:
        client.request("POST", "/v1/public/x", body={})
        client.request("GET", "/v1/public/x")
    assert len(recorder.requests) == 3
    assert waits == [0.0, 60.0]  # the replay's zero backoff, then the pacer's wait


async def test_async_client_waits_for_a_slot_outside_the_attempt_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(async_transport_module.asyncio, "sleep", sleep)
    pacer = RequestPacer(limit=1, window_seconds=60, clock=clock)
    recorder = Recorder(200)
    async with AsyncPlakyClient(
        api_key="plk_test",
        transport=httpx2.MockTransport(recorder),
        pacer=pacer,
        timeout=1.0,
    ) as client:
        await client.request("GET", "/v1/public/x")
        await client.request("GET", "/v1/public/x")
    assert waits == [60.0]
    assert len(recorder.requests) == 2


def test_with_options_shares_the_pacer() -> None:
    clock = FakeClock()
    pacer = RequestPacer(limit=1, window_seconds=60, clock=clock)
    recorder = Recorder(200)
    with PlakyClient(
        api_key="plk_test", transport=httpx2.MockTransport(recorder), pacer=pacer
    ) as client:
        client.request("GET", "/v1/public/x")
        assert pacer.reserve() == 60.0
        clone = client.with_options(timeout=5)
        assert clone._options(None).pacer is pacer  # pyright: ignore[reportPrivateUsage]
