"""MCP server settings.

Defaults: curated mode, read scope, stdio transport, loopback binding.
Configuration precedence: --server-url > PLAKY115_BASE_URL > SDK default;
PLAKY115_API_KEY > PLAKY115_API_KEY_AUTH. Secrets never appear in process
arguments; blank keys fail before server start.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from plaky115.config import DEFAULT_SERVER_URL

Mode = Literal["curated", "generated", "all"]
Scope = Literal["read", "write", "destructive"]

VALID_MODES: tuple[Mode, ...] = ("curated", "generated", "all")
VALID_SCOPES: tuple[Scope, ...] = ("read", "write", "destructive")

MAX_REQUEST_BODY_BYTES = 36 * 1024 * 1024  # 37_748_736

SERVER_INSTRUCTIONS = (
    "Unofficial toolkit for the Plaky public API. "
    "Plaky115 is unofficial and independent. It is not affiliated with, "
    "endorsed by, or sponsored by Plaky or CAKE.com. "
    "“Plaky” and “CAKE.com” are trademarks of their respective owners. "
    "Default mode is curated with read scope; write and destructive tools "
    "mount only when explicitly enabled. Mutation workflows default to "
    "dry-run. See SECURITY.md for the API-key handling and "
    "destructive-operation model."
)


@dataclass(frozen=True)
class ServerSettings:
    api_key: str
    server_url: str = DEFAULT_SERVER_URL
    mode: Mode = "curated"
    scopes: frozenset[str] = field(default_factory=lambda: frozenset({"read"}))
    enable_compat_workflow: bool = False

    def __post_init__(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise ValueError("plaky115-mcp: API key must be non-blank")
        if self.mode not in VALID_MODES:
            raise ValueError(f"plaky115-mcp: invalid mode {self.mode!r}")
        invalid = self.scopes - set(VALID_SCOPES)
        if invalid:
            raise ValueError(f"plaky115-mcp: invalid scopes {sorted(invalid)!r}")
        if "read" not in self.scopes:
            raise ValueError("plaky115-mcp: the read scope is always required")


def resolve_api_key(env: dict[str, str] | None = None) -> str:
    variables = env if env is not None else dict(os.environ)
    key = variables.get("PLAKY115_API_KEY") or variables.get("PLAKY115_API_KEY_AUTH") or ""
    if not key.strip():
        raise ValueError(
            "plaky115-mcp: set PLAKY115_API_KEY (or PLAKY115_API_KEY_AUTH) "
            "to a non-blank Plaky API key"
        )
    return key


def resolve_server_url(cli_value: str | None, env: dict[str, str] | None = None) -> str:
    variables = env if env is not None else dict(os.environ)
    return cli_value or variables.get("PLAKY115_BASE_URL") or DEFAULT_SERVER_URL
