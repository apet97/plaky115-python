# Security

Plaky115 is unofficial and independent. It is not affiliated with, endorsed
by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
of their respective owners.

## Reporting

Report suspected vulnerabilities through GitHub security advisories on the
repository, not through public issues.

## Credential handling

- API keys are accepted only from the client constructor, a provider
  callable, or (for the MCP server) the `PLAKY115_API_KEY` /
  `PLAKY115_API_KEY_AUTH` environment variables.
- Keys are sent only in the `X-API-Key` header, only to the configured
  HTTPS origin (loopback HTTP is permitted for local tests).
- `plk_`-style values are redacted recursively from error messages, logs,
  and structured tool output.
- Signed file-download URLs are bearer capabilities: the SDK and MCP server
  never log, persist, or follow them, and never copy them into summaries.

## Transport hardening

- The base URL must be absolute HTTPS without credentials, query, or fragment.
- Redirects are not followed automatically.
- Request hooks cannot change the trusted origin.
- Non-streaming bodies are bounded: 16 MiB default, 64 MiB hard maximum.
- Only GET requests retry. Writes make exactly one network attempt, even
  with an explicit idempotency key.

## MCP server model

- Default startup is curated mode with read scope; write and destructive
  tools require explicit flags.
- Uploads accept canonical base64 plus metadata (25 MiB decoded ceiling);
  local filesystem paths are never accepted.
- Streamable HTTP binds loopback by default, enables DNS-rebinding
  protection with explicit host/origin allowlists, and caps request bodies
  at 36 MiB.
- The v1 HTTP deployment is single-tenant, private-network or
  authenticated-reverse-proxy only. The Plaky API key is a process secret
  and is never accepted as tool input or reused as MCP authentication.
