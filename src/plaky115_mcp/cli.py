"""plaky115-mcp console entry point.

Local default is stdio; deployment uses stateless Streamable HTTP. stdout
is reserved for MCP frames; all logs go to stderr; unknown flags fail;
blank keys fail before server start; no secrets in process arguments.
"""

from __future__ import annotations

import argparse
import logging
import sys

from plaky115_mcp.config import (
    MAX_REQUEST_BODY_BYTES,
    VALID_MODES,
    VALID_SCOPES,
    ServerSettings,
    resolve_api_key,
    resolve_server_url,
)

_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plaky115-mcp",
        description=(
            "Unofficial Plaky MCP server. Plaky115 is unofficial and "
            "independent. It is not affiliated with, endorsed by, or "
            "sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are "
            "trademarks of their respective owners. The API key comes from "
            "PLAKY115_API_KEY (or PLAKY115_API_KEY_AUTH); never pass "
            "secrets as arguments."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="stdio for local hosts (default); streamable-http for deployment",
    )
    parser.add_argument("--mode", choices=VALID_MODES, default="curated")
    parser.add_argument(
        "--scope",
        action="append",
        choices=VALID_SCOPES,
        default=None,
        help="repeatable; defaults to read only",
    )
    parser.add_argument("--server-url", default=None, help="Plaky API base URL override")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host (loopback default)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port")
    parser.add_argument(
        "--allowed-origin",
        action="append",
        default=None,
        help="explicit allowed Origin for HTTP (repeatable); CORS stays off by default",
    )
    parser.add_argument(
        "--enable-compat-workflow",
        action="store_true",
        help="mount the deprecated mixed plaky_execute_workflow dispatcher",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser


def make_settings(args: argparse.Namespace) -> ServerSettings:
    scopes = frozenset(args.scope) if args.scope else frozenset({"read"})
    if "destructive" in scopes and "write" not in scopes:
        raise ValueError("plaky115-mcp: the destructive scope requires the write scope")
    scopes = scopes | {"read"}
    return ServerSettings(
        api_key=resolve_api_key(),
        server_url=resolve_server_url(args.server_url),
        mode=args.mode,
        scopes=scopes,
        enable_compat_workflow=bool(args.enable_compat_workflow),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=args.log_level.upper())

    try:
        settings = make_settings(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    from plaky115_mcp.server import build_server

    server = build_server(settings)

    if args.transport == "stdio":
        import anyio

        anyio.run(server.run_stdio_async)
        return 0

    return _run_http(server, args)


def _run_http(server: object, args: argparse.Namespace) -> int:
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from plaky115._version import __version__
    from plaky115_mcp.server import MCPServer

    assert isinstance(server, MCPServer)

    host: str = args.host
    if host in _LOOPBACK_HOSTS:
        allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        allowed_origins = list(args.allowed_origin or [])
    else:
        # Non-loopback binding is an explicit operator choice and requires
        # explicit host/origin allowlists.
        if not args.allowed_origin:
            print(
                "plaky115-mcp: non-loopback binding requires at least one --allowed-origin",
                file=sys.stderr,
            )
            return 2
        allowed_hosts = [f"{host}:*"]
        allowed_origins = list(args.allowed_origin)

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )
    app = server.streamable_http_app(
        stateless_http=True,
        json_response=False,
        max_request_body_size=MAX_REQUEST_BODY_BYTES,
        transport_security=security,
        host=host,
    )

    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    app.add_route("/healthz", healthz, methods=["GET"])

    uvicorn.run(app, host=host, port=args.port, log_config=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
