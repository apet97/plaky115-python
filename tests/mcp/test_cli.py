"""plaky115-mcp command line: arguments, settings, and transport startup."""

import argparse
from typing import Any

import pytest


def test_cli_units() -> None:
    from plaky115_mcp.cli import build_parser, make_settings

    parser = build_parser()
    args = parser.parse_args(["--mode", "all", "--scope", "write", "--scope", "read"])
    import os

    os.environ["PLAKY115_API_KEY"] = "plk_unit"
    try:
        settings = make_settings(args)
    finally:
        del os.environ["PLAKY115_API_KEY"]
    assert settings.mode == "all"
    assert settings.scopes == frozenset({"read", "write"})

    bad = parser.parse_args(["--scope", "destructive"])
    os.environ["PLAKY115_API_KEY"] = "plk_unit"
    try:
        with pytest.raises(ValueError, match="destructive scope requires"):
            make_settings(bad)
    finally:
        del os.environ["PLAKY115_API_KEY"]


def test_cli_http_guard_requires_allowlists() -> None:
    from plaky115_mcp.cli import _run_http  # pyright: ignore[reportPrivateUsage]

    args = argparse.Namespace(host="0.0.0.0", port=8000, allowed_host=None, allowed_origin=None)
    assert _run_http(object(), args) == 2
    args = argparse.Namespace(
        host="0.0.0.0", port=8000, allowed_host=["mcp.example"], allowed_origin=None
    )
    assert _run_http(object(), args) == 2


def test_settings_validation() -> None:
    from plaky115_mcp.config import ServerSettings, resolve_api_key, resolve_server_url

    with pytest.raises(ValueError, match="API key must be non-blank"):
        ServerSettings(api_key=" ")
    with pytest.raises(ValueError, match="invalid mode"):
        ServerSettings(api_key="plk_x", mode="wild")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="invalid scopes"):
        ServerSettings(api_key="plk_x", scopes=frozenset({"read", "root"}))
    with pytest.raises(ValueError, match="read scope is always required"):
        ServerSettings(api_key="plk_x", scopes=frozenset({"write"}))
    assert resolve_api_key({"PLAKY115_API_KEY_AUTH": "plk_alt"}) == "plk_alt"
    with pytest.raises(ValueError, match="PLAKY115_API_KEY"):
        resolve_api_key({})
    assert resolve_server_url(None, {"PLAKY115_BASE_URL": "https://x.example"}) == (
        "https://x.example"
    )
    assert resolve_server_url("https://cli.example", {}) == "https://cli.example"


def test_cli_main_stdio_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import anyio

    import plaky115_mcp.cli as cli

    ran: list[Any] = []
    monkeypatch.setenv("PLAKY115_API_KEY", "plk_unit")

    def fake_run(fn: Any) -> None:
        ran.append(fn)

    monkeypatch.setattr(anyio, "run", fake_run)
    assert cli.main(["--transport", "stdio"]) == 0
    assert len(ran) == 1


def test_cli_main_http_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn

    import plaky115_mcp.cli as cli

    served: list[Any] = []
    monkeypatch.setenv("PLAKY115_API_KEY", "plk_unit")

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served.append(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_serve)
    assert cli.main(["--transport", "streamable-http", "--port", "8123"]) == 0
    assert served[0]["port"] == 8123
    assert served[0]["host"] == "127.0.0.1"


def test_cli_main_blank_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import plaky115_mcp.cli as cli

    monkeypatch.setenv("PLAKY115_API_KEY", "   ")
    monkeypatch.delenv("PLAKY115_API_KEY_AUTH", raising=False)
    assert cli.main(["--transport", "stdio"]) == 2


def test_cli_non_loopback_with_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn

    import plaky115_mcp.cli as cli

    served: list[Any] = []
    monkeypatch.setenv("PLAKY115_API_KEY", "plk_unit")

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served.append(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_serve)
    assert (
        cli.main(
            [
                "--transport",
                "streamable-http",
                "--host",
                "0.0.0.0",
                "--allowed-host",
                "mcp.example",
                "--allowed-origin",
                "https://mcp.example",
            ]
        )
        == 0
    )
    assert served[0]["host"] == "0.0.0.0"
