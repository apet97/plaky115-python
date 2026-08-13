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

## Legacy hosts

Legacy (2025-11-25) stdio and stateless HTTP support initialize/list/call
with structured errors. Legacy stateless HTTP cancellation cannot reach an
in-flight handler (the cancel POST arrives on a fresh transport); do not
expect modern 2026 cancellation semantics there.
