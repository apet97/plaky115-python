"""Async transport gates over httpx2.MockTransport (plan Phase 4)."""

import asyncio
import json
from typing import Any

import httpx2
import pytest

import plaky115.errors as errors
import plaky115.runtime.async_transport as transport_module
from plaky115.http import RequestOptions, RequestSpec, async_request, async_request_with_response

pytestmark = pytest.mark.anyio

SERVER = "https://api.example.test"


def make_options(**overrides: Any) -> RequestOptions:
    defaults: dict[str, Any] = {
        "api_key": "plk_test_key",
        "server_url": SERVER,
        "timeout": 5.0,
        "max_retries": 0,
    }
    defaults.update(overrides)
    return RequestOptions(**defaults)


def mock_client(handler: Any) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


@pytest.fixture(autouse=True)
def fast_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transport_module, "retry_delay_ms", lambda *_args: 0.0)  # pyright: ignore[reportUnknownLambdaType,reportUnknownArgumentType]


async def test_success_json_and_headers() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        seen["url"] = str(request.url)
        return httpx2.Response(200, json={"data": [], "hasMore": False})

    async with mock_client(handler) as client:
        envelope = await async_request_with_response(
            client,
            RequestSpec(method="GET", path="/v1/public/spaces", operation_id="listSpaces"),
            make_options(),
        )
    assert envelope.status == 200
    assert envelope.data == {"data": [], "hasMore": False}
    assert seen["headers"]["x-api-key"] == "plk_test_key"
    assert seen["headers"]["accept"] == "application/json"
    assert seen["headers"]["user-agent"].startswith("plaky115/")
    assert "idempotency-key" not in seen["headers"]
    assert seen["url"] == f"{SERVER}/v1/public/spaces"


async def test_query_serialization() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["query"] = str(request.url.query.decode())
        return httpx2.Response(200, json={})

    spec = RequestSpec(
        method="GET",
        path="/v1/public/users",
        query={
            "expand": ["space", "board"],
            "emails": ["a@x.com", "b@x.com"],
            "flag": True,
            "skip": None,
            "empty": [],
            "page": 1,
        },
    )
    async with mock_client(handler) as client:
        await async_request(client, spec, make_options())
    assert (
        seen["query"] == "expand=space%2Cboard&emails=a%40x.com&emails=b%40x.com&flag=true&page=1"
    )


async def test_unsafe_int64_preserved() -> None:
    body = '{"max":9223372036854775807,"safe":9007199254740991,"neg":-9223372036854775808}'

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=body, headers={"content-type": "application/json"})

    async with mock_client(handler) as client:
        data = await async_request(client, RequestSpec(method="GET", path="/x"), make_options())
    assert data == {
        "max": "9223372036854775807",
        "safe": 9007199254740991,
        "neg": "-9223372036854775808",
    }


async def test_204_and_empty_body_return_none() -> None:
    async with mock_client(lambda _request: httpx2.Response(204)) as client:  # pyright: ignore[reportUnknownLambdaType]
        assert (
            await async_request(client, RequestSpec(method="DELETE", path="/x"), make_options())
            is None
        )
    async with mock_client(lambda _request: httpx2.Response(200, content=b"")) as client:  # pyright: ignore[reportUnknownLambdaType]
        assert (
            await async_request(client, RequestSpec(method="GET", path="/x"), make_options())
            is None
        )


async def test_malformed_json_raises_decode_error_not_retried() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, content=b"{nope", headers={"x-request-id": "rid-1"})

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyDecodeError) as info:
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(max_retries=2)
            )
    assert calls == 1
    assert info.value.request_id == "rid-1"
    assert str(info.value) == "Failed to parse the Plaky API response body."


async def test_oversized_body_fails_without_retry() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, content=b"x" * 2048)

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyResponseTooLargeError):
            await async_request(
                client,
                RequestSpec(method="GET", path="/x"),
                make_options(max_response_bytes=1024, max_retries=2),
            )
    assert calls == 1


async def test_oversized_error_body_also_bounded() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, content=b"e" * 2048)

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyResponseTooLargeError):
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(max_response_bytes=1024)
            )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, errors.PlakyValidationError),
        (401, errors.PlakyAuthError),
        (403, errors.PlakyPermissionError),
        (404, errors.PlakyNotFoundError),
        (409, errors.PlakyConflictError),
        (422, errors.PlakyUnprocessableEntityError),
        (302, errors.PlakyApiError),
    ],
)
async def test_status_classification(status: int, expected: type[Exception]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json={"message": "nope"})

    async with mock_client(handler) as client:
        with pytest.raises(expected):
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(max_retries=2)
            )


async def test_redirects_never_followed() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(302, headers={"location": "https://evil.example/steal"})

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyApiError) as info:
            await async_request(client, RequestSpec(method="GET", path="/x"), make_options())
    assert info.value.status == 302


async def test_get_retries_on_429_and_5xx() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(429, headers={"retry-after": "0"})
        if calls == 2:
            return httpx2.Response(503)
        return httpx2.Response(200, json={"ok": True})

    async with mock_client(handler) as client:
        data = await async_request(
            client, RequestSpec(method="GET", path="/x"), make_options(max_retries=2)
        )
    assert data == {"ok": True}
    assert calls == 3


async def test_retry_after_header_reaches_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server's Retry-After value must drive the retry delay (async)."""
    seen: list[tuple[str | None, int]] = []

    def record(retry_after: str | None, attempt: int) -> float:
        seen.append((retry_after, attempt))
        return 0.0

    monkeypatch.setattr(transport_module, "retry_delay_ms", record)

    def handler(request: httpx2.Request) -> httpx2.Response:
        if not seen:
            return httpx2.Response(429, headers={"retry-after": "1"})
        return httpx2.Response(200, json={"ok": True})

    async with mock_client(handler) as client:
        await async_request(
            client, RequestSpec(method="GET", path="/x"), make_options(max_retries=1)
        )
    assert seen == [("1", 0)]


def test_retry_after_header_reaches_backoff_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server's Retry-After value must drive the retry delay (sync)."""
    import plaky115.runtime.transport as sync_transport_module
    from plaky115.http import request

    seen: list[tuple[str | None, int]] = []

    def record(retry_after: str | None, attempt: int) -> float:
        seen.append((retry_after, attempt))
        return 0.0

    monkeypatch.setattr(sync_transport_module, "retry_delay_ms", record)

    def handler(request_in: httpx2.Request) -> httpx2.Response:
        if not seen:
            return httpx2.Response(429, headers={"retry-after": "1"})
        return httpx2.Response(200, json={"ok": True})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        request(client, RequestSpec(method="GET", path="/x"), make_options(max_retries=1))
    assert seen == [("1", 0)]


async def test_retry_budget_exhaustion_raises_last_error() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(429, headers={"retry-after": "1"})

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyRateLimitError) as info:
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(max_retries=2)
            )
    assert calls == 3  # max_retries=2 means 3 total attempts
    assert info.value.retry_after_ms == 1000


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_writes_make_exactly_one_attempt(method: str) -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyServerError):
            await async_request(
                client,
                RequestSpec(method=method, path="/x", body={"a": 1}),
                make_options(max_retries=5, idempotency_key="idmp_x"),
            )
    assert calls == 1


async def test_connection_error_retried_for_get_only() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx2.ConnectError("boom")
        return httpx2.Response(200, json={})

    async with mock_client(handler) as client:
        assert (
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(max_retries=1)
            )
            == {}
        )
    assert calls == 2

    calls = 0

    def always_fail(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise httpx2.ConnectError("boom")

    async with mock_client(always_fail) as client:
        with pytest.raises(errors.PlakyConnectionError):
            await async_request(
                client, RequestSpec(method="POST", path="/x"), make_options(max_retries=5)
            )
    assert calls == 1


async def test_timeout_maps_to_timeout_error() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        await asyncio.sleep(10)
        return httpx2.Response(200)

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyTimeoutError) as info:
            await async_request(
                client, RequestSpec(method="POST", path="/x"), make_options(timeout=0.05)
            )
    assert str(info.value) == "Request timed out."


async def test_cancellation_propagates_uncaught() -> None:
    started = asyncio.Event()

    async def handler(request: httpx2.Request) -> httpx2.Response:
        started.set()
        await asyncio.sleep(10)
        return httpx2.Response(200)

    async with mock_client(handler) as client:
        task = asyncio.create_task(
            async_request(client, RequestSpec(method="GET", path="/x"), make_options())
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_api_key_provider_resolved_fresh_per_attempt() -> None:
    keys: list[str] = []
    provided = 0

    async def provider() -> str:
        nonlocal provided
        provided += 1
        return f"plk_key_{provided}"

    def handler(request: httpx2.Request) -> httpx2.Response:
        keys.append(request.headers["x-api-key"])
        if len(keys) < 2:
            return httpx2.Response(500)
        return httpx2.Response(200, json={})

    async with mock_client(handler) as client:
        await async_request(
            client,
            RequestSpec(method="GET", path="/x"),
            make_options(api_key=provider, max_retries=2),
        )
    assert keys == ["plk_key_1", "plk_key_2"]


async def test_invalid_api_key_fails_before_fetch() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200)

    async with mock_client(handler) as client:
        with pytest.raises(ValueError, match="api key provider returned an invalid value"):
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(api_key="   ")
            )
    assert calls == 0


async def test_user_headers_override_and_delete() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        return httpx2.Response(200, json={})

    options = make_options(headers={"User-Agent": "custom-agent", "Accept": ""})
    async with mock_client(handler) as client:
        await async_request(client, RequestSpec(method="GET", path="/x"), options)
    assert seen["headers"]["user-agent"] == "custom-agent"
    assert "accept" not in seen["headers"]


async def test_idempotency_key_header_set_once() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        return httpx2.Response(200, json={})

    async with mock_client(handler) as client:
        await async_request(
            client,
            RequestSpec(method="POST", path="/x", body={}),
            make_options(idempotency_key="idmp_abc"),
        )
    assert seen["headers"]["idempotency-key"] == "idmp_abc"

    # A user-supplied header wins over the option.
    async with mock_client(handler) as client:
        await async_request(
            client,
            RequestSpec(method="POST", path="/x", body={}),
            make_options(idempotency_key="idmp_abc", headers={"Idempotency-Key": "user_key"}),
        )
    assert seen["headers"]["idempotency-key"] == "user_key"


async def test_request_hook_can_rewrite_path_but_not_origin() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["url"] = str(request.url)
        return httpx2.Response(200, json={})

    def rewrite(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "url": ctx["url"] + "?injected=1"}

    async with mock_client(handler) as client:
        await async_request(
            client, RequestSpec(method="GET", path="/x"), make_options(request_hook=rewrite)
        )
    assert seen["url"].endswith("/x?injected=1")

    def cross_origin(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "url": "https://evil.example/x"}

    async with mock_client(handler) as client:
        with pytest.raises(ValueError, match="must not change the trusted server origin"):
            await async_request(
                client,
                RequestSpec(method="GET", path="/x"),
                make_options(request_hook=cross_origin),
            )


async def test_response_hook_sees_error_body_and_failures_not_retried() -> None:
    observed: list[dict[str, Any]] = []
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(404, json={"message": "nope"})

    async def hook(ctx: dict[str, Any]) -> None:
        observed.append(ctx)

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyNotFoundError):
            await async_request(
                client, RequestSpec(method="GET", path="/x"), make_options(response_hook=hook)
            )
    assert observed[0]["status"] == 404
    assert observed[0]["body"] == {"message": "nope"}

    calls = 0
    boom = RuntimeError("hook exploded")

    def ok_handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json={})

    def bad_hook(ctx: dict[str, Any]) -> None:
        raise boom

    async with mock_client(ok_handler) as client:
        with pytest.raises(RuntimeError) as info:
            await async_request(
                client,
                RequestSpec(method="GET", path="/x"),
                make_options(response_hook=bad_hook, max_retries=3),
            )
    assert info.value is boom
    assert calls == 1


async def test_rate_limit_tracker_observes_every_attempt() -> None:
    from plaky115.runtime.rate_limit import RateLimitTracker

    tracker = RateLimitTracker()
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(429, headers={"x-ratelimit-remaining": "0", "retry-after": "0"})
        return httpx2.Response(200, json={}, headers={"x-ratelimit-remaining": "42"})

    async with mock_client(handler) as client:
        await async_request(
            client,
            RequestSpec(method="GET", path="/x"),
            make_options(max_retries=1, rate_limit_tracker=tracker),
        )
    assert tracker.last.remaining == 42
    assert tracker.estimated_remaining() == 42


async def test_error_body_string_degrades_to_text_problem() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, content=b"{broken json")

    async with mock_client(handler) as client:
        with pytest.raises(errors.PlakyServerError) as info:
            await async_request(client, RequestSpec(method="GET", path="/x"), make_options())
    assert info.value.problem is not None
    assert info.value.problem["message"] == "{broken json"


async def test_multipart_upload_has_file_field_and_no_json_content_type() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["content_type"] = request.headers.get("content-type", "")
        seen["body"] = request.read()
        return httpx2.Response(201, json={"id": 1})

    spec = RequestSpec(
        method="POST",
        path="/upload",
        files={"file": ("report.txt", b"hello", "text/plain")},
    )
    async with mock_client(handler) as client:
        await async_request(client, spec, make_options())
    assert seen["content_type"].startswith("multipart/form-data")
    assert b'name="file"' in seen["body"]
    assert b'filename="report.txt"' in seen["body"]
    assert b"hello" in seen["body"]


async def test_pydantic_body_serialized_by_alias() -> None:
    from plaky115.models.generated import ItemCreateRequest

    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["body"] = json.loads(request.read())
        return httpx2.Response(201, json={"id": 1})

    body = ItemCreateRequest(title="T", group_id=7)
    async with mock_client(handler) as client:
        await async_request(
            client, RequestSpec(method="POST", path="/items", body=body), make_options()
        )
    assert seen["body"] == {"title": "T", "groupId": 7}
