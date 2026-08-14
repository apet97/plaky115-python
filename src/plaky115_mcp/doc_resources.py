"""Read-only MCP resources: the docs index and the board workflow guide.

Hosts can load the server's know-how without tool calls. Each docs-index
entry becomes one markdown resource under `plaky115://docs/{id}`; the
curated "how to work a Plaky board" guide is `plaky115://skills/board-workflow`.
The Skills-over-MCP extension (SEP-2640) is still in review, so plain
resources with stable URIs are the v1 shape.
"""

from __future__ import annotations

from importlib import resources as importlib_resources
from typing import Any, cast

from mcp.server.mcpserver.resources import TextResource

from plaky115_mcp._docs_index import DOCS_INDEX

DOCS_URI_PREFIX = "plaky115://docs/"
SKILL_URI = "plaky115://skills/board-workflow"
_MARKDOWN = "text/markdown"


def _entry_markdown(entry: dict[str, Any]) -> str:
    lines = [f"# {entry['title']}", "", entry.get("summary") or entry.get("description") or ""]
    detail_keys = ("kind", "mcpName", "method", "path", "scopes", "sdk", "class")
    details = [(key, entry[key]) for key in detail_keys if entry.get(key) is not None]
    if details:
        lines += ["", *(f"- **{key}**: `{value}`" for key, value in details)]
    return "\n".join(lines) + "\n"


def _skill_markdown() -> str:
    path = importlib_resources.files("plaky115_mcp.skills") / "board_workflow.md"
    return path.read_text(encoding="utf-8")


def build_doc_resources() -> list[TextResource]:
    """One resource per docs-index entry, plus the board workflow guide."""
    docs: list[TextResource] = [
        TextResource(
            uri=f"{DOCS_URI_PREFIX}{entry['id']}",
            name=f"plaky115-docs-{entry['id']}",
            title=entry["title"],
            description=entry.get("summary") or entry.get("description"),
            mime_type=_MARKDOWN,
            text=_entry_markdown(entry),
        )
        for entry in cast("list[dict[str, Any]]", DOCS_INDEX["entries"])
    ]
    docs.append(
        TextResource(
            uri=SKILL_URI,
            name="plaky115-skill-board-workflow",
            title="How to work a Plaky board",
            description=(
                "Curated workflow guide: discovery, reads, dry-run mutation "
                "planning, rate-limit etiquette, and ID conventions."
            ),
            mime_type=_MARKDOWN,
            text=_skill_markdown(),
        )
    )
    return docs
