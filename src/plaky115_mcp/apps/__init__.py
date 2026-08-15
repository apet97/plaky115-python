"""MCP Apps assets: the Board View UI template.

The template is one self-contained HTML file served as a `ui://` resource
through the SDK's Apps extension. Hosts that negotiated MCP Apps render it
in a sandboxed iframe; every other host still gets the tool's structured
JSON result.
"""

from __future__ import annotations

from importlib import resources

from plaky115 import __version__

BOARD_VIEW_URI = "ui://plaky115/board-view.html"


def board_view_html() -> str:
    """The Board View template text, loaded from the packaged file."""
    template = (resources.files("plaky115_mcp.apps") / "board_view.html").read_text(
        encoding="utf-8"
    )
    return template.replace("__PLAKY115_VERSION__", __version__)
