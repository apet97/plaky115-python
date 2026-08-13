"""Phase 12 transport gates: stdio subprocess, stateless Streamable HTTP, CLI."""

import json
import socket
import subprocess
import sys
import threading
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx2
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.anyio


class _FakePlakyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/v1/public/spaces":
            body = json.dumps({"data": [{"id": 1, "title": "Alpha"}], "hasMore": False})
            payload = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format: str, *args: Any) -> None:
        return


@pytest.fixture
def fake_plaky_api() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakePlakyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _stdio_params(base_url: str, *extra: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "plaky115_mcp.cli", "--transport", "stdio", *extra],
        env={
            "PLAKY115_API_KEY": "plk_test_key",
            "PLAKY115_BASE_URL": base_url,
            "PATH": "/usr/bin:/bin",
        },
        cwd=str(REPO),
    )


@pytest.mark.parametrize("mode", ["2026-07-28", "legacy"])
async def test_stdio_list_and_call(fake_plaky_api: str, mode: str) -> None:
    params = _stdio_params(fake_plaky_api, "--mode", "generated")
    async with Client(stdio_client(params), mode=mode) as client:  # type: ignore[arg-type]
        tools = (await client.list_tools()).tools
        assert len(tools) == 17  # read scope default over generated mode
        result = await client.call_tool("plaky_list_spaces", {"pageSize": 5})
        assert result.is_error is False
        assert result.structured_content == {
            "data": [{"id": 1, "title": "Alpha"}],
            "hasMore": False,
        }
        # Structured error over the same transport.
        missing = await client.call_tool("plaky_get_space", {"spaceId": "9"})
        assert missing.is_error is True
        assert missing.structured_content["error"]["status"] == 404


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@asynccontextmanager
async def _http_server(base_url: str) -> AsyncGenerator[str]:
    import anyio
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    from plaky115.async_client import AsyncPlakyClient
    from plaky115_mcp.cli import build_http_app
    from plaky115_mcp.config import ServerSettings
    from plaky115_mcp.server import build_server

    settings = ServerSettings(api_key="plk_test_key", server_url=base_url, mode="generated")
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
    port = _free_port()
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


@pytest.mark.parametrize("mode", ["2026-07-28", "legacy"])
async def test_streamable_http_list_and_call(fake_plaky_api: str, mode: str) -> None:
    async with _http_server(fake_plaky_api) as base, Client(f"{base}/mcp", mode=mode) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 17
        result = await client.call_tool("plaky_list_spaces", {})
        assert result.is_error is False
        missing = await client.call_tool("plaky_get_space", {"spaceId": "9"})
        assert missing.is_error is True
        assert missing.structured_content["error"]["name"] == "PlakyNotFoundError"


async def test_http_request_body_cap_and_health(fake_plaky_api: str) -> None:
    async with _http_server(fake_plaky_api) as base, httpx2.AsyncClient() as http:
        health = await http.get(f"{base}/healthz")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ok",
            "version": health.json()["version"],
        }
        assert "key" not in health.text.lower()

        oversized = b"x" * (36 * 1024 * 1024 + 1)
        response = await http.post(
            f"{base}/mcp",
            content=oversized,
            headers={
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
            },
        )
        assert response.status_code == 413


def _run_cli(*argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "plaky115_mcp.cli", *argv],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO,
        env={"PATH": "/usr/bin:/bin", **(env or {})},
        check=False,
    )


def test_cli_help_exits_before_serving() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "plaky115-mcp" in result.stdout
    assert "unofficial and independent" in result.stdout


def test_cli_unknown_flag_fails() -> None:
    result = _run_cli("--bogus")
    assert result.returncode == 2


def test_cli_blank_key_fails_before_start() -> None:
    result = _run_cli(env={"PLAKY115_API_KEY": "   "})
    assert result.returncode == 2
    assert "PLAKY115_API_KEY" in result.stderr


def test_cli_destructive_requires_write() -> None:
    result = _run_cli("--scope", "destructive", env={"PLAKY115_API_KEY": "plk_x"})
    assert result.returncode == 2
    assert "destructive scope requires the write scope" in result.stderr
