# Agent Guide

plaky115-python is an unofficial Python SDK and MCP server for the Plaky
public API, ported from the pinned TypeScript source
`https://github.com/apet97/plaky115` at
`33ae2926aa696f36d9663d44f914d42d9aadc53f` (v1.0.11).

Plaky115 is unofficial and independent. It is not affiliated with, endorsed
by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
of their respective owners.

## Authority and safety

- The source checkout at `/Users/15x/Downloads/WORKING/addons-me/plaky115`
  is read-only. Never edit, commit, tag, push, or clean it.
- Local commits here are allowed. Remote creation/push/PR, tag creation,
  TestPyPI/PyPI publication, and live Plaky writes each require separate
  current-task authorization (IMPLEMENTATION_PLAN.md section 3.8).
  Environment variables and credentials are interlocks, not authorization.
- Never commit or print API keys, signed download URLs, or workspace
  payloads. Redaction is centralized in `plaky115.runtime.redaction`.
- Writes make exactly one network attempt; only GET requests retry.

## Source ownership

- Files with an `AUTO-GENERATED` header are owned by `scripts/generate.py`
  and `scripts/contract.py`. Never hand-edit them; change
  `contract/operation-overrides.yaml`, `contract/schema-patches.yaml`, or the
  generator, then regenerate and review the full drift.
- `contract/upstream.openapi.yaml` mirrors the accepted upstream spec.
  `scripts/contract.py fetch` writes candidates only to `contract/candidate/`;
  `accept` is always an explicit human-reviewed action.
- Handwritten SDK code lives in `src/plaky115/`; handwritten MCP code in
  `src/plaky115_mcp/`; generated raw tools in
  `src/plaky115_mcp/tools/raw/`.

## Verification

Focused work: `uv run pytest tests/<area> -x`, `uv run ruff check .`,
`uv run pyright`.

Release-grade local gate: `uv run python scripts/verify.py --offline`.

Live certification (`scripts/live_read.py`, `scripts/live_write.py`) needs
injected credentials and, for writes, separate authorization plus the
`PLAKY115_LIVE_WRITE=1`, `PLAKY115_SMOKE_SPACE_ID`, `PLAKY115_SMOKE_BOARD_ID`,
and `PLAKY115_SMOKE_ALLOW_ARCHIVE=1` interlocks. Never print environment
values; report secrets only as set/unset.

## State files

- `IMPLEMENTATION_PLAN.md` — authoritative plan; changes need a DECISIONS entry.
- `PORT_MATRIX.md` — one row per required surface; only green gates set `verified`.
- `IMPLEMENTATION_STATE.md` — current phase, last green command, next action.
- `DECISIONS.md` — append-only ADRs.
- `BLOCKERS.md` — external blockers only.

Evidence outranks stale state prose. Reconcile before working.
