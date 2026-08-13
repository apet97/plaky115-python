# Streamable HTTP deployment example

```bash
export PLAKY115_API_KEY=...   # injected secret; never in files or args
plaky115-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Probe:

```bash
curl -s http://127.0.0.1:8000/healthz
```

Deploy single-tenant, private-network or behind an authenticated reverse
proxy only. Non-loopback binding requires explicit --allowed-origin values.
