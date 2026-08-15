# Contributing

## Setup

```bash
uv sync --all-extras --group dev
```

## Rules

- `contract/` is the canonical operation boundary. It combines the accepted
  OpenAPI mirror, exact-key overrides, schema patches, expected inventory,
  and pinned source manifest. `src/plaky115/models/generated.py`, raw MCP
  tools, and the bundled docs index are generated surfaces.
- Never hand-edit files with an `AUTO-GENERATED` header. Change
  `contract/operation-overrides.yaml`, `contract/schema-patches.yaml`, or the
  generator in `scripts/`, then run `uv run python scripts/generate.py` and
  review the complete drift.
- Contract changes go through `scripts/contract.py fetch` / `diff` /
  `accept` / `build`; `accept` is always an explicit reviewed step.
- Keep sync and async clients free of event-loop bridging; share only pure
  logic.
- No write retries. No secrets in code, tests, fixtures, or docs.

## Change order

1. Run `uv run python scripts/contract.py fetch` / `diff` for a candidate;
   inspect it, then use the explicitly reviewed `accept` step.
2. Run `uv run python scripts/contract.py build` and
   `uv run python scripts/generate.py`; review the generated diff.
3. Put SDK behavior tests in `tests/sdk`, contract/generator tests in
   `tests/contract`, and MCP protocol, schema, lifecycle, and tool tests in
   `tests/mcp`. Test a behavior, not a coverage bucket.
4. Run the full offline verifier before requesting review.

The source tree is divided into the hand-written SDK (`src/plaky115`) and
MCP boundary (`src/plaky115_mcp`). The base SDK must not import `mcp`.
`docs/port/spec-helpers.md` and `docs/port/spec-transport.md` are the pinned
TypeScript parity baseline; they are not a source of unreviewed behavior.

## MCP evaluations

`evals/mcp-cases.json` is a provider-neutral contract for weak-model tool
selection. Score a JSONL file containing `id`, `tool`, and `arguments` with:

```bash
uv run python scripts/score_mcp_predictions.py --predictions predictions.jsonl
```

For every external model run, record these items outside this repository:

- Provider, model name, and exact model version.
- SHA-256 digests of the system prompt and tool prompt.
- SHA-256 digests of the case set and prediction file.
- UTC date and the full scorer metrics output.

Do not store prompts, predictions, credentials, or workspace content in this
repository. The corpus and scorer are a deterministic safety gate only; they
do not call a model service or set an accuracy threshold. The harness is
provider-neutral and not model proof.

## Release authority

Release, tag, push, publication, deployment, and branch-rule changes require
separate authorization. A release uses the exact pinned source checkout for
provenance, verifies the built artifact, and never triggers the separately
owned cloud deployment.

## Verification

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run python scripts/verify.py --offline
```
