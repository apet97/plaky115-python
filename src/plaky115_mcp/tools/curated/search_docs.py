"""plaky_search_docs: search the bundled operation/workflow/guide index."""

from __future__ import annotations

from typing import Annotated, Any, cast

from mcp.types import CallToolResult, ToolAnnotations

from plaky115_mcp._docs_index import DOCS_INDEX
from plaky115_mcp.compaction import make_result
from plaky115_mcp.outputs import ListOutput
from plaky115_mcp.registry import ToolSpec


def search_entries(query: str, limit: int) -> list[dict[str, Any]]:
    needle = query.lower().strip()
    entries = cast("list[dict[str, Any]]", DOCS_INDEX["entries"])
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        haystacks = [
            str(entry.get(field, "")).lower()
            for field in ("id", "title", "summary", "description", "mcpName", "sdk", "path")
        ]
        if not needle:
            scored.append((1, entry))
            continue
        score = 0
        for haystack in haystacks:
            if needle == haystack:
                score += 10
            elif needle in haystack:
                score += 3
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("id"))))
    slim = [
        {
            key: value
            for key, value in entry.items()
            if key in ("kind", "id", "title", "summary", "method", "path", "mcpName", "sdk")
        }
        for _, entry in scored[:limit]
    ]
    return slim


def build_search_docs() -> ToolSpec:
    async def plaky_search_docs(
        query: str,
        limit: int = 10,
    ) -> Annotated[CallToolResult, ListOutput]:
        bounded = max(1, min(int(limit), 50))
        results = search_entries(query, bounded)
        return make_result(
            text=f"plaky_search_docs: {len(results)} match(es) for {query!r}",
            structured={"data": results},
        )

    return ToolSpec(
        name="plaky_search_docs",
        title="Search Plaky docs",
        description=(
            "Search the bundled Plaky operation, workflow, and guide index by "
            "keyword. Returns matching entries with their MCP tool and SDK names."
        ),
        handler=plaky_search_docs,
        scopes=frozenset({"read"}),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        kind="curated",
    )
