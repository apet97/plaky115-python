"""Tool registry: metadata-validated registration with mode/scope gating.

Every mounted tool must carry a human title, a concrete description, a
unique name of at most 64 characters, strict input schemas, and all four
annotation hints. A tool mounts only when every scope it requires is
enabled.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from mcp.types import ToolAnnotations

MAX_TOOL_NAME_LENGTH = 64


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    handler: Callable[..., Any]
    scopes: frozenset[str]
    annotations: ToolAnnotations
    kind: str = "raw"  # "raw" | "curated"
    compat_only: bool = field(default=False)
    meta: dict[str, Any] | None = None  # extra _meta published on tools/list (e.g. MCP Apps "ui")
    parameters: dict[str, Any] | None = None  # package-owned published input schema


def validate_spec(spec: ToolSpec) -> None:
    if not spec.name or len(spec.name) > MAX_TOOL_NAME_LENGTH:
        raise ValueError(f"tool name must be 1-{MAX_TOOL_NAME_LENGTH} characters: {spec.name!r}")
    if not spec.title:
        raise ValueError(f"{spec.name}: tool title is required")
    if not spec.description or len(spec.description) < 10:
        raise ValueError(f"{spec.name}: a concrete tool description is required")
    for hint in ("read_only_hint", "destructive_hint", "idempotent_hint", "open_world_hint"):
        if not isinstance(getattr(spec.annotations, hint), bool):
            raise ValueError(f"{spec.name}: annotation {hint} must be set explicitly")
    if not spec.scopes:
        raise ValueError(f"{spec.name}: at least one scope is required")
    if spec.annotations.destructive_hint and "destructive" not in spec.scopes:
        raise ValueError(f"{spec.name}: destructive tools require the destructive scope")


def mounts(spec: ToolSpec, mode: str, scopes: frozenset[str], compat: bool) -> bool:
    """Whether a tool mounts under the given mode/scope configuration."""
    if spec.compat_only and not compat:
        return False
    if spec.kind == "raw" and mode not in ("generated", "all"):
        return False
    if spec.kind == "curated" and mode not in ("curated", "all"):
        return False
    return spec.scopes <= scopes
