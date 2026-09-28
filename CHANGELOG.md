# Changelog

## v1.3.0

Findings from a live monday.com → Plaky migration (measured 2026-09-21/23):

- New `subscriptions` resource (sync and async): `get` and `replace`, from
  the `getSubscriptions` / `overrideSubscriptions` operations Plaky has
  published since the pinned contract, with raw MCP tools
  `plaky_get_item_subscriptions` and `plaky_replace_item_subscriptions`.
  `ItemCreateRequest` gains `subscribedUserIds` / `subscribedTeamIds`.
  `scripts/contract.py fetch` now reads the spec embedded in the
  docs.plaky.com page.
- A 429 is replayed for every method, not only GET: Plaky never commits a
  request it refuses with 429. A write that meets a 5xx, timeout, or
  connection failure still makes exactly one attempt.
- Mutation receipts gain the `rejected` status: a write refused with 429
  was attempted and definitely not committed, so MCP errors report
  `mayHaveCommitted: false` and `retryable: true` for it. MCP write tools
  return a 429 at once instead of waiting out `Retry-After`.
- New opt-in `RequestPacer` keeps a client under Plaky's 200-per-minute
  limit (190 per 60 s sliding window by default); every attempt claims a
  slot, and `with_options` shares it.
- Fixed `link_field`: it emitted `text`, which the API refuses; it now
  emits `displayText`, defaulting to the URL.
- New `rich_text_field` writes plain text as escaped HTML paragraphs.
- Item group create and update require `color` again (in the SDK, the
  generated models, and the MCP schemas): the server answers 500 without it.
- Tests are organized by behavior instead of coverage bucket, the flaky
  body-phase timeout tests have wide margins, and the eval scorer tests run
  in-process (7.4 s to 2.7 s for that file). Live read certification covers 18
  operations, including `getSubscriptions`.
- Requires `httpx2>=2.12`; the lock moves to 2.13.1, clearing
  PYSEC-2026-3846, -3848, and -3849 in 2.10.0.
- `docs/sdk.md` records the server behaviour behind these changes: list
  defaults, clearing rules per field type, the Person write shape, date
  offsets, ambiguous labels, and rewritten file names.

## v1.2.2

- Fixed mutation attempt tracking, item pagination filters, transport timeout
  phases, stream ownership, trusted-origin normalization, bounded resolvers,
  and export validation.
- Added strict curated and generated MCP input schemas, safe diagnostics,
  modern catalog cache hints, Board View lifecycle cleanup, and a local
  provider-neutral evaluation corpus.
- Hardened release provenance and the stable CI aggregate check.

## v1.2.1

Host-compat fix for text-only MCP hosts:

- Tool results now mirror the structured payload into the text block as
  compact JSON (after the one-line summary). Some hosts — claude.ai
  custom connectors today — show the model only the text block and hide
  `structuredContent`, which made data tools read as bare counts there.
- The mirror is bounded: it is skipped when the payload exceeds 32,000
  characters or when mirroring would push the serialized result over the
  131,072-byte cap; the summary-only text block is kept in those cases.
  Redaction applies to the mirror exactly as to structured output.

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
  support receive the complete structured JSON. The app is read-only.
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
