# Decisions

Append-only. Short entries; evidence over narrative.

## ADR-0001 — One wheel with MCP extra
Date: 2026-08-13
Status: accepted
Context: IMPLEMENTATION_PLAN.md section 3.1 mandates one distribution.
Decision: One `plaky115` distribution; `plaky115_mcp` namespace behind the `mcp` extra.
Consequences: Base import must not require `mcp`; import guard raises with install hint.
Evidence: plan sections 3.1, 12 Phase 1.

## ADR-0002 — operation-overrides.yaml ported by one-time translation
Date: 2026-08-13
Status: accepted
Context: The pinned source's `openapi/plaky115-operation-metadata.json` is the
generated single source of operation semantics, and
`scripts/test-cross-surface-parity.mjs` `sdkInvokers` is the explicit SDK map.
Decision: Translate both once into `contract/operation-overrides.yaml`
(exact-key format from plan section 11.2). The translator lives outside the
repository (session scratchpad) because it is a one-time port tool, not
maintained code. Page-root entries record the item model plus the
`PublicPagedResponseV1*` envelope; bare-array item models
(`CommentResponse`, `ItemFileResponse`) come from the accepted OpenAPI
response schemas.
Consequences: `contract/operation-overrides.yaml` is hand-maintained from now
on; `scripts/contract.py check` guards drift against
`contract/expected-operations.json`.
Evidence: contract/source-manifest.json records source paths and SHA-256.

## ADR-0003 — Cloudflare deployment is a post-build decision
Date: 2026-08-13
Status: accepted
Context: The task requester asked to "put on cloudflare worker". The mandated
stack (Python 3.11+, official `mcp` v2 server, `httpx2`, uvicorn/ASGI) cannot
run on the Cloudflare Workers Pyodide runtime; the `mcp` package is not
available there and the plan forbids a second HTTP stack or a TypeScript
rewrite.
Decision: Build per plan. Deliver Cloudflare deployment as an adjacent
artifact after the server exists, using a container-based or tunnel-based
route (Cloudflare Containers or cloudflared in front of the stateless
Streamable HTTP server), and surface the tradeoff to the requester. Any
remote deployment remains separately authorized per plan section 3.8.
Consequences: No Workers-specific code inside this repository's Python
packages.
Evidence: plan sections 3.6, 3.7, 10.10.
