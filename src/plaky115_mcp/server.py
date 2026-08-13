"""Server assembly: one build_server used by every transport."""

from __future__ import annotations

from mcp.server import MCPServer

from plaky115._version import __version__
from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.config import SERVER_INSTRUCTIONS, ServerSettings
from plaky115_mcp.registry import register_tools
from plaky115_mcp.tools.curated import build_curated_tools
from plaky115_mcp.tools.raw import build_raw_tools

__all__ = ["build_server", "make_client"]


def make_client(settings: ServerSettings) -> AsyncPlakyClient:
    return AsyncPlakyClient(api_key=settings.api_key, server_url=settings.server_url)


def build_server(
    settings: ServerSettings,
    client: AsyncPlakyClient | None = None,
) -> MCPServer:
    """Build the MCP server with tools filtered by mode and scopes."""
    plaky = client if client is not None else make_client(settings)
    server = MCPServer(
        name="plaky115",
        title="Plaky115 (unofficial)",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )
    specs = build_raw_tools(plaky) + build_curated_tools(plaky)
    register_tools(
        server,
        specs,
        mode=settings.mode,
        scopes=settings.scopes,
        compat=settings.enable_compat_workflow,
    )
    return server
