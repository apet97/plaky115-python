"""User-agent construction."""

from __future__ import annotations

import platform

from plaky115._version import __version__


def build_user_agent(suffix: str | None = None) -> str:
    """Stable package/version/platform value plus an optional suffix."""
    base = f"plaky115/{__version__} python/{platform.python_version()}"
    if suffix:
        return f"{base} {suffix}"
    return base
