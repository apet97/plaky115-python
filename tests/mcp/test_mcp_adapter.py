"""Public MCP v2 tool-construction compatibility seam."""

from __future__ import annotations

import pytest
from mcp.types import ToolAnnotations

from plaky115_mcp.mcp_adapter import assert_mcp_v2_compatibility, build_tools
from plaky115_mcp.registry import ToolSpec


def _spec(name: str) -> ToolSpec:
    async def handler(value: int = 1) -> dict[str, int]:
        return {"value": value}

    return ToolSpec(
        name=name,
        title="Test tool",
        description="A concrete adapter test tool.",
        handler=handler,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        kind="curated",
    )


def test_adapter_uses_public_factory_and_rejects_duplicate_names() -> None:
    assert_mcp_v2_compatibility()
    tools = build_tools([_spec("plaky_test")], mode="curated", scopes=frozenset({"read"}))
    assert tools[0].parameters["additionalProperties"] is False
    with pytest.raises(ValueError, match="duplicate tool names"):
        build_tools(
            [_spec("plaky_test"), _spec("plaky_test")], mode="curated", scopes=frozenset({"read"})
        )
