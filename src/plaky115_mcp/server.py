"""Server assembly: one build_server used by every transport."""

from __future__ import annotations

from mcp.server import MCPServer
from mcp.server.apps import Apps

from plaky115._version import __version__
from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.apps import BOARD_VIEW_URI, board_view_html
from plaky115_mcp.config import SERVER_INSTRUCTIONS, ServerSettings
from plaky115_mcp.registry import mounts, register_tools
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
    specs = build_raw_tools(plaky) + build_curated_tools(plaky)
    extensions: list[Apps] = []
    board_view = next(spec for spec in specs if spec.name == "plaky_board_view")
    if mounts(board_view, settings.mode, settings.scopes, settings.enable_compat_workflow):
        apps = Apps()
        apps.add_html_resource(
            BOARD_VIEW_URI,
            board_view_html(),
            name="plaky115-board-view",
            title="Plaky board view",
            description="Interactive read-only board table rendered by MCP Apps hosts.",
        )
        extensions.append(apps)
    server = MCPServer(
        name="plaky115",
        title="Plaky115 (unofficial)",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
        extensions=extensions,
    )
    register_tools(
        server,
        specs,
        mode=settings.mode,
        scopes=settings.scopes,
        compat=settings.enable_compat_workflow,
    )
    return server
