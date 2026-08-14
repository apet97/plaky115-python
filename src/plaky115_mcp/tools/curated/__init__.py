"""Curated MCP tools: discovery, planning, and workflow dispatchers."""

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.tools.curated.board_view import build_board_view
from plaky115_mcp.tools.curated.execute_mutation_workflow import (
    build_execute_mutation_workflow,
)
from plaky115_mcp.tools.curated.execute_read_workflow import build_execute_read_workflow
from plaky115_mcp.tools.curated.execute_workflow import build_execute_workflow
from plaky115_mcp.tools.curated.find import build_find
from plaky115_mcp.tools.curated.plan_mutation import build_plan_mutation
from plaky115_mcp.tools.curated.search_docs import build_search_docs
from plaky115_mcp.tools.curated.workspace_context import build_workspace_context

__all__ = ["build_curated_tools"]


def build_curated_tools(client: AsyncPlakyClient) -> list[ToolSpec]:
    return [
        build_search_docs(),
        build_workspace_context(client),
        build_find(client),
        build_board_view(client),
        build_plan_mutation(),
        build_execute_read_workflow(client),
        build_execute_mutation_workflow(client),
        build_execute_workflow(client),
    ]
