# Architecture

- `contract/` owns operation truth: accepted upstream OpenAPI + exact-key
  overrides -> deterministic generated descriptors.
- `scripts/contract.py` and `scripts/generate.py` are the only writers of
  generated artifacts (`AUTO-GENERATED` headers).
- `src/plaky115/` is the hand-written SDK: transports (sync + async, no
  event-loop bridging), nine resources, runtime helpers, resolvers,
  workflows.
- `src/plaky115_mcp/` is the MCP layer: generated raw tools, curated
  tools/workflows, error envelope, result compaction, registry gating,
  and transports. The base package never imports `mcp`.
- See docs/port/spec-transport.md and docs/port/spec-helpers.md for the
  behavioral parity contracts extracted from the pinned TypeScript source.
