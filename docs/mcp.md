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
  (`category`, `name`, `message`, `retryable`, `status`, `code`,
  `requestId`, `retryAfterMs`, `attempted`, `mayHaveCommitted`, `phase`,
  `receipts`).
- The complete serialized result is capped at 131,072 bytes; larger output
  degrades to a structured usage error. Collections paginate with exact
  continuations.
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

Future writes (design note): the app stays read-only in v1. A later
release can add widget-initiated edits by bridging the existing mutation
contract into the UI: the widget calls `plaky_plan_mutation` through the
host bridge to build a validated plan, shows the plan to the user inside
the widget, and only then calls `plaky_execute_mutation_workflow` — first
with the default `dryRun=true` echo, then with `dryRun=false` after an
explicit in-widget confirmation. The server-side scope gates are
unchanged: without the `write` scope those tools do not mount, so a
widget can never widen access.

## Legacy hosts

Legacy (2025-11-25) stdio and stateless HTTP support initialize/list/call
with structured errors. Legacy stateless HTTP cancellation cannot reach an
in-flight handler (the cancel POST arrives on a fresh transport); do not
expect modern 2026 cancellation semantics there.
