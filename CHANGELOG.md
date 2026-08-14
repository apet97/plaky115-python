# Changelog

## v1.2.0

The first MCP App and skills-over-MCP resources:

- New curated read-scope tool `plaky_board_view`: one board's snapshot
  with columns from the board's field definitions, groups, status/tag
  label colors, and up to 500 shaped items. Output is bounded twice: at
  500 items and at a byte budget below the 131,072-byte result cap, with
  `itemCount`, `hasMore`, and `truncated` reported.
- The tool links a self-contained HTML template
  (`ui://plaky115/board-view.html`, served through the SDK's MCP Apps
  extension). Hosts with Apps support render an interactive table:
  grouped rows, colored status/tag pills, client-side sort and filter,
  and a refresh action through the host bridge. Hosts without Apps
  support receive the complete structured JSON. The app is read-only;
  see docs/mcp.md for the future-writes design note.
- The server now serves read-only doc resources: one markdown resource
  per docs-index entry under `plaky115://docs/{id}`, plus the curated
  "How to work a Plaky board" guide at `plaky115://skills/board-workflow`.
- `ToolSpec` gains an optional `meta` pass-through published on
  `tools/list`; registry validation, mode/scope gating, and strict input
  schemas are unchanged.

## v1.1.0

Fixes from the adversarial review of the MCP server, scripts, CI, and
test suite:

- A live mutation that fails after network dispatch now returns its
  attempt receipt: `attempted=true`, `mayHaveCommitted=true`, and the
  real phase. Before this fix, the error envelope reported
  `attempted=false` and `phase=preflight` for a write that may have
  committed. Both `plaky_execute_mutation_workflow` and the compat
  dispatcher are fixed.
- `export.items` rejects unknown `csvSafety` values with a validation
  error. Before this fix, a typo such as `"Spreadsheet"` silently
  disabled CSV formula-injection protection.
- Structured tool output is redacted with the same `plk_` rules as text
  output.
- Bulk `items.updateFields` output carries a `dryRun` marker, and a
  dry-run reports "dry-run validated" instead of "0/N completed".
- New repeatable `--allowed-host` flag for Streamable HTTP. Non-loopback
  binding requires explicit `--allowed-host` and `--allowed-origin`
  values; the Host allowlist is no longer derived from the bind address
  (binding `0.0.0.0` used to reject every real Host header).
- `--log-level` validates its value and exits cleanly instead of raising
  a traceback.
- `scripts/parity.py` reports "manifest hashes SKIPPED" when the pinned
  source checkout is unavailable (`PLAKY115_SOURCE_CHECKOUT` overrides
  the path). Before this fix, it printed "verified" without checking.
- `scripts/generate.py --check` fails on orphan `generated_*.py` modules
  that a fresh run would not produce.
- `scripts/package_smoke.py` asserts the stdio server exits with code 0.
- `scripts/verify.py` deletes stale `dist/` artifacts before the build
  gate, and the release-online dependency audit runs `pip-audit` against
  the exported lockfile.
- The release workflow verifies before it publishes: the tag must point
  at a commit on `main`, the built version must equal the tag, the full
  gate suite (with the online dependency audit) must pass, and the
  publish job consumes the exact verified artifacts. All actions are
  pinned to commit SHAs. The tag trigger is narrowed to `v[0-9]*`.
- Regression tests pin the retry backoff to the server `Retry-After`
  value, the exact timeout error type over Streamable HTTP, zero writes
  during mutation planning, and redaction of key-bearing transport
  exception messages.

Fixes from the adversarial review of PR #2 (SDK core):

- The package imports without the build-generated `plaky115._version`
  module; `__version__` falls back to `0.0.0.dev0`.
- Item group create and update plans accept a missing `color`; a present
  `color` must still match `#RRGGBB`.
- Generated models type int64 fields as `int | str`, so unsafe int64 IDs
  preserved as decimal strings stay strings through validation and
  re-serialization.
- `normalize_server_url` accepts bracketed IPv6 loopback URLs such as
  `http://[::1]/` and still rejects non-loopback IPv6 HTTP hosts.
- `RateLimitSnapshot.reset_at` stores the `X-RateLimit-Reset` header value
  exactly as sent; the dead unit-normalization branch is removed.
- CSV export iteration builds one schema before the first chunk and uses
  it for every chunk, so all rows align with the single header and the
  board definition is fetched once per iteration.
- Export serialization uses `model_dump(mode="json")`; datetimes render
  as ISO-8601 strings (with the `T` separator).

- Initial Python port of the plaky115 SDK and MCP server from pinned source
  `33ae2926aa696f36d9663d44f914d42d9aadc53f` (v1.0.11).
