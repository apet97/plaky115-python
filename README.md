# plaky115 · Python SDK + MCP server for Plaky

[![CI](https://github.com/apet97/plaky115-python/actions/workflows/ci.yml/badge.svg)](https://github.com/apet97/plaky115-python/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-strict%20pyright-informational)](pyproject.toml)

A clean, typed Python SDK and a Model Context Protocol server for the
[Plaky](https://plaky.com) public API — every documented operation, one
wheel, no surprises. Ported from the pinned TypeScript source
[apet97/plaky115](https://github.com/apet97/plaky115) (`33ae2926`, v1.0.11)
with behavior-level parity tests.

> Plaky115 is unofficial and independent. It is not affiliated with, endorsed
> by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
> of their respective owners.

## Install

```bash
pip install plaky115          # SDK only
pip install "plaky115[mcp]"   # SDK + MCP server
```

Python 3.11+. One dependency stack: `httpx2` + `pydantic` v2 (+ the
official `mcp` v2 SDK behind the extra).

## Highlights

- **All 32 public operations** across nine resources — spaces, boards,
  items, comments, reactions, users, teams, item groups, item files —
  each pinned by contract descriptors and cross-surface parity tests.
- **Async-first with a real sync client.** `AsyncPlakyClient` and
  `PlakyClient` share pure logic only; the sync client never touches an
  event loop.
- **Safe under failure.** Only GET requests retry (equal-jitter backoff,
  bounded `Retry-After`); writes make exactly one network attempt — even
  with an idempotency key. Mutation receipts record `attempted` /
  `mayHaveCommitted` conservatively.
- **Strict wire contracts.** Paged roots must be `{"data": [...],
  "hasMore": bool}`; unsafe int64 JSON integers survive as exact decimal
  strings; bodies are bounded (16 MiB default / 64 MiB max); redirects are
  never followed; `plk_` keys are redacted everywhere.
- **Batteries for real workflows.** Resolvers (exact-ID fast path, one
  bounded list for text refs), field builders, bounded chunk readers with
  exact `{page, index}` continuation, deterministic spreadsheet-safe
  CSV/JSONL export, bulk updates with durable receipts.
- **Deterministic generation.** OpenAPI contract → models and raw MCP
  tools are committed, drift-checked artifacts; `scripts/generate.py
  --check` fails CI on a single changed byte.

## SDK quick start

```python
from plaky115 import AsyncPlakyClient

async with AsyncPlakyClient(api_key="...") as plaky:
    page = await plaky.spaces.list(page_size=50)
    for space in page.data:
        print(space.id, space.title)
```

```python
from plaky115 import PlakyClient

with PlakyClient(api_key="...") as plaky:
    for space in plaky.spaces.iterate(page_size=100):
        print(space.id, space.title)
```

The API key is sent only in the `X-API-Key` header, only to the configured
HTTPS origin. Python surfaces are snake_case; wire names stay Plaky
camelCase via model aliases.

## MCP server

```bash
export PLAKY115_API_KEY=...   # environment only; never an argument
plaky115-mcp --transport stdio                       # local hosts
plaky115-mcp --transport streamable-http --port 8000 # deployment
```

- **Safe by default:** `curated` mode + `read` scope. Write and
  destructive tools mount only with explicit flags; mutation workflows
  default to **dry-run**.
- **Two tool surfaces:** 32 generated raw tools (one per operation) and 8
  curated tools with 11 workflow IDs (`workspace.map`, `items.search`,
  `comments.thread`, `export.items`, `items.create`, `items.updateFields`,
  `comments.add`, `itemGroups.create`, `itemGroups.update`,
  `itemFiles.upload`, `itemFiles.update`).
- **Structured everything:** every tool publishes success *and* error
  output schemas; known failures return a typed envelope with attempt
  state; results are capped at 128 KiB with exact continuations.
- **Hardened HTTP:** stateless Streamable HTTP with request-scoped SSE,
  36 MiB body cap, DNS-rebinding protection, loopback-default binding,
  secret-free `/healthz`. Uploads accept canonical base64 + metadata —
  never local paths.

Host config example: [`examples/mcp_stdio.json`](examples/mcp_stdio.json).
Deployment notes: [`docs/mcp.md`](docs/mcp.md) and
[`docs/deploy-cloudflare.md`](docs/deploy-cloudflare.md).

## Documentation

| Guide | Contents |
| --- | --- |
| [docs/sdk.md](docs/sdk.md) | Clients, options, resources, errors, pagination |
| [docs/mcp.md](docs/mcp.md) | Modes, scopes, result contracts, deployment |
| [docs/compatibility-inventory.md](docs/compatibility-inventory.md) | All 32 operations mapped to SDK + MCP names |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Architecture, generated boundaries, contract and evaluation workflow |
| [SECURITY.md](SECURITY.md) | Credential and transport policy |
| [docs/live-certification.md](docs/live-certification.md) | Read/write live gates |

## Development

```bash
uv sync --all-extras --group dev
uv run pytest
uv run python scripts/verify.py --offline  # full release-grade gate
```

The offline verifier checks: parity inventories, contract + generation
determinism, format/lint, strict pyright, tests with branch coverage,
example syntax, docs gates, wheel/sdist build, twine, fresh-environment
package smoke (base install without `mcp`, installed-wheel typing proof),
four-scope secret scan, and lock integrity. The read-only live
certification exercises all 17 read operations across four independent
surfaces.

## License

MIT — see [LICENSE](LICENSE). Retains the upstream copyright notice from
the pinned source.
