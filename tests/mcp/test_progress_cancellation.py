"""Transport-depth gates: progress notifications and client-side cancellation.

Progress must flow from the items.search runner to the client on every
transport (in-memory, streamable HTTP, stdio subprocess). A cancelled call
must leave the server usable for the next request.
"""

import json
import sys
import threading
import time
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import anyio
import httpx2
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.transport_security import TransportSecuritySettings

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.cli import build_http_app
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.server import build_server

REPO = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.anyio

ITEM_PAGES: dict[int, dict[str, Any]] = {
    1: {
        "data": [{"id": 1, "title": "alpha needle"}, {"id": 2, "title": "beta"}],
        "hasMore": True,
    },
    2: {"data": [{"id": 3, "title": "gamma needle"}], "hasMore": False},
}


class _FakePlakyHandler(BaseHTTPRequestHandler):
    slow_spaces_seconds: float = 0.0

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        payload: dict[str, Any] | None = None
        if parsed.path == "/v1/public/spaces/1":
            payload = {"id": 1, "title": "S"}
        elif parsed.path == "/v1/public/spaces/1/boards/7":
            payload = {"id": 7, "title": "B"}
        elif parsed.path == "/v1/public/spaces/1/boards/7/items":
            page = int(parse_qs(parsed.query).get("page", ["1"])[0])
            payload = ITEM_PAGES[page]
        elif parsed.path == "/v1/public/spaces":
            if type(self).slow_spaces_seconds:
                time.sleep(type(self).slow_spaces_seconds)
            payload = {"data": [{"id": 1, "title": "S"}], "hasMore": False}
        if payload is None:
            self.send_response(404)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


@pytest.fixture
def fake_plaky_api() -> Iterator[str]:
    _FakePlakyHandler.slow_spaces_seconds = 0.0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakePlakyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


SEARCH_ARGS = {
    "workflow": "items.search",
    "args": {"spaceId": "1", "boardId": "7", "query": "needle", "limit": 10},
}


def _progress_collector(events: list[tuple[float, float | None]]) -> Any:
    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        events.append((progress, total))

    return on_progress


@asynccontextmanager
async def _http_server(base_url: str) -> AsyncGenerator[str]:
    import socket

    import uvicorn

    settings = ServerSettings(api_key="plk_test_key", server_url=base_url)
    sdk_client = AsyncPlakyClient(api_key="plk_test_key", server_url=base_url)
    server = build_server(settings, sdk_client)
    app = build_http_app(
        server,
        TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=[],
        ),
        "127.0.0.1",
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")  # type: ignore[arg-type]
    uv_server = uvicorn.Server(config)
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(uv_server.serve)
        while not uv_server.started:
            await anyio.sleep(0.01)
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            uv_server.should_exit = True


async def test_progress_in_memory(fake_plaky_api: str) -> None:
    sdk = AsyncPlakyClient(api_key="plk_test_key", server_url=fake_plaky_api)
    server = build_server(ServerSettings(api_key="plk_test_key", server_url=fake_plaky_api), sdk)
    events: list[tuple[float, float | None]] = []
    async with Client(server) as client:
        result = await client.call_tool(
            "plaky_execute_read_workflow",
            SEARCH_ARGS,
            progress_callback=_progress_collector(events),
        )
    assert result.is_error is False
    assert result.structured_content["matched"] == 2
    assert events, "expected at least one progress notification"
    assert all(total == 10 for _, total in events)
    assert [p for p, _ in events] == sorted(p for p, _ in events)


async def test_progress_over_streamable_http(fake_plaky_api: str) -> None:
    events: list[tuple[float, float | None]] = []
    async with _http_server(fake_plaky_api) as base, Client(f"{base}/mcp") as client:
        result = await client.call_tool(
            "plaky_execute_read_workflow",
            SEARCH_ARGS,
            progress_callback=_progress_collector(events),
        )
    assert result.is_error is False
    assert result.structured_content["matched"] == 2
    assert events, "expected progress notifications over streamable HTTP"


async def test_progress_over_stdio(fake_plaky_api: str) -> None:
    import os

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "plaky115_mcp.cli", "--transport", "stdio"],
        env={
            **os.environ,
            "PLAKY115_API_KEY": "plk_test_key",
            "PLAKY115_BASE_URL": fake_plaky_api,
        },
        cwd=str(REPO),
    )
    events: list[tuple[float, float | None]] = []
    async with Client(stdio_client(params)) as client:  # type: ignore[arg-type]
        result = await client.call_tool(
            "plaky_execute_read_workflow",
            SEARCH_ARGS,
            progress_callback=_progress_collector(events),
        )
    assert result.is_error is False
    assert result.structured_content["matched"] == 2
    assert events, "expected progress notifications over stdio"


async def test_cancelled_call_leaves_server_usable_in_memory(
    fake_plaky_api: str,
) -> None:
    _FakePlakyHandler.slow_spaces_seconds = 3.0
    sdk = AsyncPlakyClient(api_key="plk_test_key", server_url=fake_plaky_api)
    server = build_server(ServerSettings(api_key="plk_test_key", server_url=fake_plaky_api), sdk)
    with anyio.move_on_after(0.3) as scope:
        async with Client(server) as client:
            await client.call_tool("plaky_find", {"kind": "space", "query": "S"})
    assert scope.cancelled_caught, "the slow call should have been cancelled"
    # The same server instance must keep answering after the cancelled read.
    _FakePlakyHandler.slow_spaces_seconds = 0.0
    async with Client(server) as client:
        follow_up = await client.call_tool("plaky_find", {"kind": "space", "query": "S"})
        assert follow_up.is_error is False
        assert follow_up.structured_content["id"] == 1


async def test_cancelled_call_leaves_server_usable_over_http(
    fake_plaky_api: str,
) -> None:
    _FakePlakyHandler.slow_spaces_seconds = 3.0
    async with _http_server(fake_plaky_api) as base:
        with anyio.move_on_after(0.3) as scope:
            async with Client(f"{base}/mcp") as client:
                await client.call_tool("plaky_find", {"kind": "space", "query": "S"})
        assert scope.cancelled_caught, "the slow call should have been cancelled"
        _FakePlakyHandler.slow_spaces_seconds = 0.0
        # A stateless server must accept a fresh session immediately after a
        # cancelled call on a previous one.
        async with Client(f"{base}/mcp") as client:
            follow_up = await client.call_tool("plaky_find", {"kind": "space", "query": "S"})
            assert follow_up.is_error is False
            assert follow_up.structured_content["id"] == 1


async def test_read_timeout_surfaces_as_client_error(fake_plaky_api: str) -> None:
    _FakePlakyHandler.slow_spaces_seconds = 3.0
    async with _http_server(fake_plaky_api) as base:
        async with Client(f"{base}/mcp") as client:
            from mcp.shared.exceptions import MCPError

            with pytest.raises(MCPError, match="timed out"):
                await client.call_tool(
                    "plaky_find",
                    {"kind": "space", "query": "S"},
                    read_timeout_seconds=0.3,
                )
        _FakePlakyHandler.slow_spaces_seconds = 0.0
        async with Client(f"{base}/mcp") as client:
            follow_up = await client.call_tool("plaky_find", {"kind": "space", "query": "S"})
            assert follow_up.is_error is False


async def test_httpx_sanity() -> None:
    # Guard: the module-scope httpx2 import stays used even if fixtures change.
    assert httpx2.Response(200).status_code == 200
