"""Client escape hatches, with_options, and header handling (sync and async)."""

from typing import Any

import httpx2
import pytest

from fakes import echo_handler, paged_workspace_client
from plaky115 import AsyncPlakyClient, PlakyClient
from plaky115.http import async_resolve_headers, resolve_headers
from plaky115.resources._common import RequestOverrides, body_as_dict

pytestmark = pytest.mark.anyio


async def test_async_request_escape_hatch_and_with_options() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(echo_handler)
    ) as client:
        assert await client.request("GET", "/x") == {"echo": ""}
        envelope = await client.request_with_response("GET", "/x")
        assert envelope.status == 200
        clone = client.with_options(timeout=5, max_retries=1, headers={"x-extra": "v"})
        assert await clone.request("GET", "/x") == {"echo": "v"}
        # Clone shares the pool; closing it must not close the parent's client.
        await clone.aclose()
        assert await client.request("GET", "/x") == {"echo": ""}


async def test_async_options_header_merging() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        headers={"x-extra": "base"},
        transport=httpx2.MockTransport(echo_handler),
    ) as client:
        merged = await client.request(
            "GET", "/x", options=RequestOverrides(headers={"x-extra": "override"})
        )
        assert merged == {"echo": "override"}

    async def header_factory() -> dict[str, str]:
        return {"x-extra": "fromfn"}

    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        headers=header_factory,
        transport=httpx2.MockTransport(echo_handler),
    ) as client:
        assert await client.request("GET", "/x") == {"echo": "fromfn"}
        merged = await client.request(
            "GET", "/x", options=RequestOverrides(headers={"x-extra": "override"})
        )
        assert merged == {"echo": "override"}


def test_sync_request_escape_hatch_and_with_options() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(echo_handler)
    ) as client:
        assert client.request("GET", "/x") == {"echo": ""}
        assert client.request_with_response("GET", "/x").status == 200
        clone = client.with_options(max_response_bytes=1024, user_agent="ua/1")
        assert clone.request("GET", "/x") == {"echo": ""}
        merged = client.request("GET", "/x", options=RequestOverrides(headers={"x-extra": "o"}))
        assert merged == {"echo": "o"}

    with PlakyClient(
        api_key="plk_x",
        max_retries=0,
        headers={"x-extra": "base"},
        transport=httpx2.MockTransport(echo_handler),
    ) as client:
        merged = client.request("GET", "/x", options=RequestOverrides(headers={"x-extra": "o"}))
        assert merged == {"echo": "o"}


def test_sync_with_options_shares_pool() -> None:
    with paged_workspace_client() as client:
        clone = client.with_options(timeout=5)
        assert clone.server_url == client.server_url
        assert clone.spaces.get("1").id == 1


def test_header_provider_resolution() -> None:
    assert resolve_headers(None) is None
    assert resolve_headers({"A": "1"}) == {"A": "1"}
    assert resolve_headers(lambda: {"B": "2"}) == {"B": "2"}
    with pytest.raises(TypeError, match="headers provider returned an invalid value"):
        resolve_headers(lambda: "nope")  # type: ignore[arg-type,return-value]


async def test_async_header_provider_resolution() -> None:
    async def provider() -> dict[str, str]:
        return {"C": "3"}

    assert await async_resolve_headers(provider) == {"C": "3"}
    assert await async_resolve_headers({"D": "4"}) == {"D": "4"}
    with pytest.raises(TypeError):
        await async_resolve_headers(lambda: 42)  # type: ignore[arg-type,return-value]


async def test_client_hooks_and_headers_merge() -> None:
    seen: dict[str, Any] = {}

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        return httpx2.Response(200, json={"id": 1})

    client = AsyncPlakyClient(
        api_key="plk_x",
        headers={"X-Base": "b"},
        transport=httpx2.MockTransport(capture),
    )
    from plaky115.resources._common import RequestOverrides

    async with client:
        await client.spaces.get("1", options=RequestOverrides(headers={"X-Extra": "e"}))
    assert seen["headers"]["x-base"] == "b"
    assert seen["headers"]["x-extra"] == "e"

    # Callable base headers merged with per-call overrides.
    client2 = AsyncPlakyClient(
        api_key="plk_x",
        headers=lambda: {"X-Base": "callable"},
        transport=httpx2.MockTransport(capture),
    )
    async with client2:
        await client2.spaces.get("1", options=RequestOverrides(headers={"X-Extra": "e2"}))
    assert seen["headers"]["x-base"] == "callable"
    assert seen["headers"]["x-extra"] == "e2"


def test_sync_client_headers_merge() -> None:
    seen: dict[str, Any] = {}

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        return httpx2.Response(200, json={"id": 1})

    from plaky115.resources._common import RequestOverrides

    with PlakyClient(
        api_key="plk_x",
        headers=lambda: {"X-Base": "s"},
        transport=httpx2.MockTransport(capture),
    ) as client:
        client.spaces.get("1", options=RequestOverrides(headers={"X-Extra": "e"}))
    assert seen["headers"]["x-base"] == "s"

    with PlakyClient(
        api_key="plk_x",
        user_agent_suffix="tester/1.0",
        transport=httpx2.MockTransport(capture),
    ) as client:
        client.spaces.get("1")
    assert seen["headers"]["user-agent"].endswith("tester/1.0")


def test_body_as_dict() -> None:
    from pydantic import BaseModel

    class Body(BaseModel):
        title: str

    assert body_as_dict(Body(title="t")) == {"title": "t"}
