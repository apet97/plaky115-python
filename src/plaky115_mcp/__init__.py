"""Unofficial Plaky MCP server namespace.

Plaky115 is unofficial and independent. It is not affiliated with, endorsed
by, or sponsored by Plaky or CAKE.com. "Plaky" and "CAKE.com" are trademarks
of their respective owners.

Importing this package requires the optional MCP extra:

    pip install "plaky115[mcp]"
"""

from importlib.util import find_spec

from plaky115._version import __version__

if find_spec("mcp") is None:  # pragma: no cover - exercised via package smoke
    raise ImportError(
        "plaky115_mcp requires the optional MCP dependency. "
        'Install it with: pip install "plaky115[mcp]"'
    )

__all__ = ["__version__"]
