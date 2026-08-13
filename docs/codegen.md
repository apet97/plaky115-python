# Code generation

`uv run python scripts/generate.py` renders, deterministically:

- `src/plaky115/models/generated.py` — Pydantic v2 schema models
  (aliases + snake_case, extra=allow responses, extra=forbid requests)
  via pinned datamodel-code-generator.
- `src/plaky115_mcp/tools/raw/generated_*.py` — one raw MCP tool per
  operation and the registry `__init__.py`.
- `src/plaky115_mcp/_docs_index.py` — bundled docs index.

`--check` renders to a temporary directory and byte-compares every file;
CI fails on drift. Output is formatted with the repository ruff config.
