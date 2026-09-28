"""Tool spec validation: names, titles, descriptions, annotations, and scopes."""

from typing import Any

import pytest
from mcp.types import ToolAnnotations

from plaky115_mcp.registry import ToolSpec, validate_spec


def spec(**overrides: Any) -> ToolSpec:
    async def handler() -> None:  # pragma: no cover - never called
        return None

    base: dict[str, Any] = {
        "name": "plaky_x",
        "title": "X",
        "description": "A concrete description.",
        "handler": handler,
        "scopes": frozenset({"read"}),
        "annotations": ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    }
    base.update(overrides)
    return ToolSpec(**base)


def test_validate_spec_rejections() -> None:
    with pytest.raises(ValueError, match="tool name must be"):
        validate_spec(spec(name=""))
    with pytest.raises(ValueError, match="tool title is required"):
        validate_spec(spec(title=""))
    with pytest.raises(ValueError, match="concrete tool description"):
        validate_spec(spec(description="short"))
    with pytest.raises(ValueError, match="annotation read_only_hint must be set"):
        validate_spec(spec(annotations=ToolAnnotations()))
    with pytest.raises(ValueError, match="at least one scope"):
        validate_spec(spec(scopes=frozenset()))
    with pytest.raises(ValueError, match="destructive tools require"):
        validate_spec(
            spec(
                annotations=ToolAnnotations(
                    read_only_hint=False,
                    destructive_hint=True,
                    idempotent_hint=False,
                    open_world_hint=False,
                )
            )
        )
