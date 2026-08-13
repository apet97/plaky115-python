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

from mcp.server import MCPServer
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


def _make_strict(server: MCPServer, name: str) -> None:
    """Rebuild the tool's argument model with extra='forbid'.

    The official SDK derives a permissive argument model from the handler
    signature; the pinned contract requires unknown arguments to fail
    validation, so the model is subclassed with a strict config and the
    published input schema gains additionalProperties: false.
    """
    tool = server._tool_manager.get_tool(name)  # pyright: ignore[reportPrivateUsage]
    if tool is None:  # pragma: no cover - registration just added it
        raise RuntimeError(f"tool {name} was not registered")
    arg_model = tool.fn_metadata.arg_model
    strict_model = type(
        f"{arg_model.__name__}Strict",
        (arg_model,),
        {"model_config": {**arg_model.model_config, "extra": "forbid"}},
    )
    tool.fn_metadata.arg_model = strict_model  # pyright: ignore[reportAttributeAccessIssue]
    tool.parameters["additionalProperties"] = False


def register_tools(
    server: MCPServer,
    specs: list[ToolSpec],
    *,
    mode: str,
    scopes: frozenset[str],
    compat: bool = False,
) -> list[str]:
    """Validate every spec, mount the eligible ones, return mounted names."""
    names = [spec.name for spec in specs]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise ValueError(f"duplicate tool names: {sorted(duplicates)}")
    mounted: list[str] = []
    for spec in specs:
        validate_spec(spec)
        if not mounts(spec, mode, scopes, compat):
            continue
        server.add_tool(
            spec.handler,
            name=spec.name,
            title=spec.title,
            description=spec.description,
            annotations=spec.annotations,
        )
        _make_strict(server, spec.name)
        mounted.append(spec.name)
    return mounted
