"""Synchronous transport: the request seam, hooks, decoding, limits, and failures."""

from typing import Any

import httpx2
import pytest

from fakes import make_options, paged_workspace_client
from plaky115 import (
    PlakyClient,
    PlakyConnectionError,
    PlakyDecodeError,
    PlakyResponseTooLargeError,
    PlakyTimeoutError,
)
from plaky115.http import RequestSpec, request, request_with_response
from plaky115.runtime.request_builders import assert_trusted_request_url


def test_sync_public_request_seam() -> None:
    def handler(req: httpx2.Request) -> httpx2.Response:
        if req.url.path == "/big":
            return httpx2.Response(200, content=b"x" * 4096)
        if req.url.path == "/broken":
            return httpx2.Response(200, content=b"{nope", headers={"x-request-id": "r"})
        if req.url.path == "/bytes":
            return httpx2.Response(200, content=b"\x00\x01")
        if req.url.path == "/text":
            return httpx2.Response(200, content=b"plain text")
        return httpx2.Response(200, json={"ok": True})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        envelope = request_with_response(
            http, RequestSpec(method="GET", path="/x"), make_options()
        )
        assert envelope.data == {"ok": True} and envelope.status == 200
        assert request(http, RequestSpec(method="GET", path="/x"), make_options()) == {"ok": True}
        assert (
            request(
                http,
                RequestSpec(method="GET", path="/bytes", response_type="bytes"),
                make_options(),
            )
            == b"\x00\x01"
        )
        assert (
            request(
                http, RequestSpec(method="GET", path="/text", response_type="text"), make_options()
            )
            == "plain text"
        )
        with pytest.raises(PlakyResponseTooLargeError):
            request(
                http, RequestSpec(method="GET", path="/big"), make_options(max_response_bytes=1024)
            )
        with pytest.raises(PlakyDecodeError) as decode_info:
            request(http, RequestSpec(method="GET", path="/broken"), make_options())
        assert decode_info.value.request_id == "r"


def test_sync_request_hook_paths() -> None:
    seen: dict[str, str] = {}

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen["url"] = str(req.url)
        return httpx2.Response(200, json={})

    def rewrite(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "url": ctx["url"] + "?injected=1"}

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        request(http, RequestSpec(method="GET", path="/x"), make_options(request_hook=rewrite))
        assert seen["url"].endswith("?injected=1")

        def cross(ctx: dict[str, Any]) -> dict[str, Any]:
            return {**ctx, "url": "https://evil.example/x"}

        with pytest.raises(ValueError, match="trusted server origin"):
            request(http, RequestSpec(method="GET", path="/x"), make_options(request_hook=cross))

        def broken(ctx: dict[str, Any]) -> str:
            return "nope"

        with pytest.raises(ValueError, match="invalid URL"):
            request(
                http,
                RequestSpec(method="GET", path="/x"),
                make_options(request_hook=broken),  # type: ignore[arg-type]
            )


def test_trusted_origin_normalizes_default_ports_and_rejects_unsafe_origins() -> None:
    assert_trusted_request_url("https://EXAMPLE.com:443/path", "https://example.com")
    assert_trusted_request_url("http://example.com:80/path", "http://example.com")
    for rewritten in (
        "https://user@example.com/path",
        "https://example.com:444/path",
        "ftp://example.com/path",
    ):
        with pytest.raises(ValueError, match=r"invalid URL|trusted server origin"):
            assert_trusted_request_url(rewritten, "https://example.com")


def test_sync_response_hook_error_path() -> None:
    observed: list[int] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, json={"message": "gone"})

    def hook(ctx: dict[str, Any]) -> None:
        observed.append(ctx["status"])

    from plaky115 import PlakyNotFoundError

    with (
        httpx2.Client(transport=httpx2.MockTransport(handler)) as http,
        pytest.raises(PlakyNotFoundError),
    ):
        request(http, RequestSpec(method="GET", path="/x"), make_options(response_hook=hook))
    assert observed == [404]


def test_sync_transport_error_paths() -> None:
    def failing(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down")

    with (
        PlakyClient(
            api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(failing)
        ) as client,
        pytest.raises(PlakyConnectionError),
    ):
        client.users.me()

    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow")

    with (
        PlakyClient(
            api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(slow)
        ) as client,
        pytest.raises(PlakyTimeoutError),
    ):
        client.users.me()

    calls = 0

    def retryable(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(503, headers={"retry-after": "0"})
        return httpx2.Response(200, json={"id": 1})

    with PlakyClient(
        api_key="plk_x", max_retries=1, transport=httpx2.MockTransport(retryable)
    ) as client:
        assert client.users.me().id == 1
    assert calls == 2

    # Low-level escape hatch.
    with paged_workspace_client() as client:
        envelope = client.request_with_response("GET", "/v1/public/spaces/1")
        assert envelope.status == 200 and envelope.data["id"] == 1
        assert client.request("GET", "/v1/public/spaces/1")["id"] == 1
