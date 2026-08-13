# Cloudflare deployment

## Why not a Cloudflare Worker

This server cannot run on Cloudflare Workers. Workers' Python support runs
on Pyodide with a restricted package set; the mandated stack — the official
`mcp` v2 server (Starlette/uvicorn ASGI, `sse-starlette`), `httpx2` socket
transport, and stateless Streamable HTTP with request-scoped SSE — is not
available or runnable there, and the implementation plan forbids a second
HTTP stack or a TypeScript rewrite. A "Worker deployment" of this codebase
would require a from-scratch TypeScript reimplementation, which is a
separate product.

## Supported Cloudflare routes

Both routes put Cloudflare in front of the real server unchanged.

### 1. Cloudflare Tunnel (works today)

Run the server bound to loopback and publish it through `cloudflared`:

```bash
export PLAKY115_API_KEY=...          # injected secret
plaky115-mcp --transport streamable-http --host 127.0.0.1 --port 8000 &

# Named tunnel on your own domain (requires cloudflared login):
cloudflared tunnel create plaky115-mcp
cloudflared tunnel route dns plaky115-mcp mcp.example.com
cloudflared tunnel run --url http://127.0.0.1:8000 plaky115-mcp
```

The MCP endpoint is `https://mcp.example.com/mcp`; `/healthz` stays
secret-free. **Add authentication in front** (Cloudflare Access is the
natural choice): the v1 server is single-tenant and holds one Plaky API
key as a process secret, so an unauthenticated public URL would hand your
workspace to anyone. Never use the quick `trycloudflare.com` tunnels for
anything but a short-lived demo, and even then only with a disposable key.

### 2. Cloudflare Containers

Package the server as a container and run it on Cloudflare's container
platform behind a Worker route:

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir "plaky115[mcp]"
EXPOSE 8000
# The key arrives via the platform's secret store, never baked in.
CMD ["plaky115-mcp", "--transport", "streamable-http", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--allowed-origin", "https://your-mcp-host.example"]
```

Bind the container to a Worker route, terminate TLS at Cloudflare, and put
Cloudflare Access (or another auth layer) in front of `/mcp`.

## Boundaries

Actual deployment to a Cloudflare account (tunnel creation on a real
domain, container publication) is an external action: it needs your
Cloudflare credentials plus a rotated Plaky API key, and per the release
policy it stays private-network or authenticated-proxy only. Nothing in
this repository claims Claude-hosted connector or directory readiness;
that requires a public HTTPS endpoint with separate MCP-layer
authentication and a production connector test.
