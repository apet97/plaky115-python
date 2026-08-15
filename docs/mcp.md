# MCP server guide

Plaky115 is unofficial and independent. It is not affiliated with, endorsed
by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
of their respective owners.

## Startup

```bash
export PLAKY115_API_KEY=...   # never pass secrets as arguments
plaky115-mcp --transport stdio --mode curated --scope read
```

Defaults: `curated` mode, `read` scope. Modes: `curated`, `generated`
(32 raw tools), `all`. Scopes: `read`, `write`, `destructive`
(destructive requires write). The deprecated mixed dispatcher
`plaky_execute_workflow` mounts only with `--enable-compat-workflow` and
is excluded from any directory-facing catalog.

The default six curated read tools are `plaky_search_docs`,
`plaky_workspace_context`, `plaky_find`, `plaky_board_view`,
`plaky_plan_mutation`, and `plaky_execute_read_workflow`. Adding `write`
mounts `plaky_execute_mutation_workflow`; the eighth dispatcher is
compatibility-only. All eleven workflow IDs use a discriminated `workflow`
schema with strict argument objects. Unknown fields, boolean IDs, and string
booleans are rejected before a resolver, progress callback, or network call.
Fixed mutation bodies use the generated Plaky request models and reject
unknown keys. Item-field maps remain dynamic because Plaky defines their keys,
but each value must match `FieldValueChangeRequest`.
Bulk field updates allow at most 50 entries and 64 KiB of UTF-8 JSON.

Configuration precedence: `--server-url` > `PLAKY115_BASE_URL` > SDK
default. Key: `PLAKY115_API_KEY` > `PLAKY115_API_KEY_AUTH`.

## Host configuration (stdio)

See `examples/mcp_stdio.json`. The API key comes from the host's
environment injection, never from the config file text.

## Streamable HTTP deployment

```bash
plaky115-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

- Stateless (`stateless_http=True`, `json_response=False`); request-scoped
  SSE responses carry progress and modern cancellation.
- 36 MiB raw request cap (a valid 25 MiB upload is ~34.9 MiB of base64).
- DNS-rebinding protection on; loopback hosts allowed by default.
  Non-loopback binding requires explicit `--allowed-host` (the public
  `host[:port]` clients send in the Host header) and `--allowed-origin`
  values; the bind address is never used as the Host allowlist. On a
  loopback bind, extra `--allowed-host` values are additive (for tunnels
  that forward the public Host header).
- `GET /healthz` returns only `{"status": "ok", "version": ...}`.
- v1 is single-tenant: deploy private-network or behind an authenticated
  reverse proxy. Never reuse the Plaky key as MCP authentication; the key
  is never accepted as tool input.

## Result contracts

- Every tool advertises success and error output schemas; known failures
  return `isError=true` with the structured envelope
  (`category`, `name`, `message`, `retryable`, `status`, `code`, `path`,
  `limit`, `maximum`, `candidateCount`, `failedIndex`, `operationId`,
  `pointer`, `requestId`, `retryAfterMs`, `attempted`, `mayHaveCommitted`,
  `phase`, `receipts`). Optional diagnostics are safe, stable values only;
  no body, header, candidate content, upload data, or signed URL is exposed.
- The complete serialized result is capped at 131,072 bytes; larger output
  degrades to a structured usage error. Collections paginate with exact
  continuations.
- The text block carries a one-line summary followed by a compact JSON
  mirror of the structured payload, so hosts that show the model only the
  text block (claude.ai custom connectors today) still see the data. The
  mirror is skipped above 32,000 characters or when it would exceed the
  result cap.
- Uploads accept `fileBase64` + `fileName` (+ `contentType`); local paths
  are never accepted; base64 is never echoed back.
- Mutation workflows default to dry-run; live execution returns durable
  attempt receipts.

## Board View app (MCP Apps)

The curated read tool `plaky_board_view` returns one board's snapshot:
columns from the board's field definitions, groups, status/tag label
colors, and up to 500 shaped items. On hosts that negotiated the MCP Apps
extension (claude.ai, Claude Desktop, and others), the tool renders an
interactive table: grouped rows, colored status and tag pills, client-side
sort and text filter, and a refresh action that calls the tool again
through the host bridge.

- The UI template is one self-contained HTML resource at
  `ui://plaky115/board-view.html` (MIME `text/html;profile=mcp-app`).
  It loads no external assets and makes no network requests.
- The tool mounts in `curated` and `all` modes with the `read` scope, the
  same gating as every curated tool.
- Hosts without Apps support ignore the template and receive the complete
  structured JSON result; the tool is useful on its own.
- Item output is bounded twice: at 500 items and at a byte budget below
  the 131,072-byte result cap. The result reports `itemCount`, `hasMore`,
  and `truncated`, so the widget shows "showing N of more".
- The Plaky API reports no total item count; `hasMore` is the honest
  indicator that the board holds more items than the snapshot.

The app stays read-only. It accepts messages only from its parent, uses a
strict color allowlist, places unknown or ungrouped items in an explicit
group, and handles teardown by removing listeners, rejecting pending bridge
calls, and disabling controls. It does not use widget-initiated writes.

## Doc resources (skills over MCP)

The server serves its know-how as read-only MCP resources, so hosts can
load documentation without tool calls:

- `plaky115://docs/{id}` — one markdown resource per docs-index entry
  (operations, workflows, guides). The same content backs
  `plaky_search_docs`.
- `plaky115://skills/board-workflow` — the curated "How to work a Plaky
  board" guide: discovery, reads, dry-run mutation planning, rate-limit
  etiquette, and ID conventions.

Hosts discover both through the standard `resources/list` and
`resources/read` requests. The Skills-over-MCP extension (SEP-2640) is
not final; when it stabilizes, these resources can adopt its metadata
without changing URIs.

The server adds private five-minute cache hints to `server/discover`,
`tools/list`, `prompts/list`, `resources/list`, `resources/templates/list`,
and `resources/read`. Dynamic tool calls receive no extra cache behavior.
The server supports modern and legacy protocol clients; tasks, sampling, and
server-initiated elicitation are intentionally absent until a product
requirement and host matrix justify them.

## Legacy hosts

Legacy (2025-11-25) stdio and stateless HTTP support initialize/list/call
with structured errors. Legacy stateless HTTP cancellation cannot reach an
in-flight handler (the cancel POST arrives on a fresh transport); do not
expect modern 2026 cancellation semantics there.
