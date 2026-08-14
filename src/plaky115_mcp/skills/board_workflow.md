# How to work a Plaky board

This guide shows the curated tool flow for the plaky115 MCP server.
Follow the steps in order. Use IDs from earlier results in later calls.

## 1. Discover the workspace

Call `plaky_workspace_context` first. It returns a compact tree of spaces
and boards with their IDs. Do not guess IDs.

## 2. Resolve one entity

Call `plaky_find` when you have a name or an ID and need the entity.
Board, item, and item-group lookups require `spaceId` (and `boardId` for
items and groups). An ambiguous name returns a structured error with the
candidate count; refine the query and call again.

## 3. Read data

Call `plaky_execute_read_workflow` for bounded reads:

- `workspace.map` — the spaces/boards tree.
- `items.search` — search item titles and scalar fields, with exact
  page/index continuation.
- `comments.thread` — one item's comment thread.
- `export.items` — chunked item export (JSONL or CSV).

Call `plaky_board_view` for one board's full table: columns, groups,
label colors, and up to 500 shaped items. Hosts with MCP Apps support
render an interactive table from this result.

## 4. Plan a mutation

Call `plaky_plan_mutation` to build a validated mutation plan. The plan
shows the exact request the server would send. This call makes no
network request.

## 5. Execute with dry-run first

Call `plaky_execute_mutation_workflow`. The `dryRun` argument defaults
to `true`: the server validates and echoes the plan but does not write.
Set `dryRun: false` only after you confirm the dry-run output. Write and
destructive tools mount only when the operator enables those scopes.

## Rate-limit etiquette

The Plaky API allows 200 requests per minute per user. Prefer one
workflow call over many raw calls. Use continuation arguments instead of
re-reading full pages. On a 429 response the server retries with backoff;
do not add your own retry loop.

## ID conventions

- IDs are opaque; pass them back exactly as received (string or number).
- All item and group calls are scoped: `spaceId` → `boardId` → `itemId`.
- Reuse IDs from structured results; do not re-resolve names you already
  resolved.
