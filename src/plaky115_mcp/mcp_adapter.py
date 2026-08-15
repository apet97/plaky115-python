"""Compatibility seam for constructing MCP v2 tools without server internals."""

from __future__ import annotations

from mcp.server.mcpserver.tools import Tool

from plaky115_mcp.registry import ToolSpec, mounts, validate_spec


def build_tools(
    specs: list[ToolSpec],
    *,
    mode: str,
    scopes: frozenset[str],
    compat: bool = False,
) -> list[Tool]:
    """Build the v2 Tool objects before MCPServer construction.

    MCP's public ``Tool.from_function`` factory is the only SDK-specific
    behavior in this module. The package owns these objects until it passes
    them to ``MCPServer(tools=...)``.
    """
    names = [spec.name for spec in specs]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate tool names: {duplicates}")

    tools: list[Tool] = []
    for spec in specs:
        validate_spec(spec)
        if not mounts(spec, mode, scopes, compat):
            continue
        tool = Tool.from_function(
            spec.handler,
            name=spec.name,
            title=spec.title,
            description=spec.description,
            annotations=spec.annotations,
            meta=spec.meta,
        )
        _strict_runtime_arguments(tool)
        if spec.parameters is not None:
            tool.parameters = spec.parameters
        tools.append(tool)
    return tools


def _strict_runtime_arguments(tool: Tool) -> None:
    """Make the package-owned argument model reject unknown fields."""
    arg_model = tool.fn_metadata.arg_model
    strict_model = type(
        f"{arg_model.__name__}Strict",
        (arg_model,),
        {"model_config": {**arg_model.model_config, "extra": "forbid"}},
    )
    tool.fn_metadata.arg_model = strict_model
    tool.parameters = strict_model.model_json_schema(by_alias=True)


def assert_mcp_v2_compatibility() -> None:
    """Fail early when the tested public Tool factory changes."""
    required = ("parameters", "fn_metadata")
    missing = [name for name in required if name not in Tool.model_fields]
    if not hasattr(Tool, "from_function"):
        missing.append("from_function")
    if missing:
        raise RuntimeError(
            "Unsupported MCP v2 Tool API; missing public Tool attributes: " + ", ".join(missing)
        )
