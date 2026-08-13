# Contributing

## Setup

```bash
uv sync --all-extras --group dev
```

## Rules

- Never hand-edit files with an `AUTO-GENERATED` header. Change
  `contract/operation-overrides.yaml`, `contract/schema-patches.yaml`, or the
  generator in `scripts/`, then run `uv run python scripts/generate.py` and
  review the complete drift.
- Contract changes go through `scripts/contract.py fetch` / `diff` /
  `accept` / `build`; `accept` is always an explicit reviewed step.
- Keep sync and async clients free of event-loop bridging; share only pure
  logic.
- No write retries. No secrets in code, tests, fixtures, or docs.

## Verification

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv run python scripts/verify.py --offline
```
