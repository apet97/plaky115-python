# plaky115 (Python)

Unofficial Python SDK and Model Context Protocol (MCP) server for the
[Plaky](https://plaky.com) public API.

> Plaky115 is unofficial and independent. It is not affiliated with, endorsed
> by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
> of their respective owners.

## Install

```bash
pip install plaky115          # SDK only
pip install "plaky115[mcp]"   # SDK + MCP server
```

Python 3.11 or newer is required.

## SDK quick start

Async:

```python
from plaky115 import AsyncPlakyClient

async with AsyncPlakyClient(api_key="...") as plaky:
    page = await plaky.spaces.list(page_size=50)
    for space in page.data:
        print(space.id, space.title)
```

Sync:

```python
from plaky115 import PlakyClient

with PlakyClient(api_key="...") as plaky:
    for space in plaky.spaces.iterate(page_size=100):
        print(space.id, space.title)
```

The API key is sent only in the `X-API-Key` header. Keys come from the
constructor or a provider callable; never hardcode keys in source.

## MCP server

```bash
plaky115-mcp --transport stdio --mode curated --scope read
```

The default mode is `curated` and the default scope is `read`. Write and
destructive tools mount only with explicit `--scope write` /
`--scope destructive` flags. For deployment, the server also supports
stateless Streamable HTTP:

```bash
plaky115-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

See `docs/mcp.md` for host configuration and the security model.

## Behavior guarantees

- Only GET requests retry; writes make exactly one network attempt, even
  with an explicit idempotency key.
- Response bodies are bounded (16 MiB default, 64 MiB hard maximum).
- Strict paged-root validation: `{"data": [...], "hasMore": bool}`.
- Signed download URLs are treated as sensitive and never logged.
- MCP uploads accept canonical base64 plus metadata, never local paths.

## Development

```bash
uv sync --all-extras --group dev
uv run pytest
uv run python scripts/verify.py --offline
```

Ported from the pinned TypeScript source
[apet97/plaky115](https://github.com/apet97/plaky115) at
`33ae2926aa696f36d9663d44f914d42d9aadc53f` (v1.0.11).

## License

MIT. See [LICENSE](LICENSE).
