# SDK guide

Plaky115 is unofficial and independent. It is not affiliated with, endorsed
by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
of their respective owners.

## Clients

- `AsyncPlakyClient` is the canonical client (MCP handlers are async).
- `PlakyClient` is a real synchronous client over `httpx2.Client`; it never
  starts an event loop or bridges into the async client.
- Both accept: `api_key` (literal or same-mode provider), `server_url`,
  `timeout` (30 s default), `max_retries` (2, GET-only),
  `max_response_bytes` (16 MiB default, 64 MiB maximum), `headers` (mapping
  or same-mode provider), `user_agent` / `user_agent_suffix`,
  `request_hook` / `response_hook`, injected `http_client` or `transport`,
  and support `with_options`, `close()`/`aclose()`, and context managers.
- Low-level escape hatches: `client.request(...)` and
  `client.request_with_response(...)`.
- Passing both `http_client` and `transport` raises `ValueError`; select one
  injection boundary. An explicit method `idempotency_key` wins over an
  override; an explicit empty string intentionally suppresses the header.
- Each async attempt has one timeout budget for API-key and header providers,
  request and response hooks, HTTP I/O, bounded body reads, and decoding.
  Async attempts use one total timeout budget; backoff is outside it. Only a GET failure before response headers
  can retry; a timeout or connection failure after headers never retries.
  Sync timeout enforcement applies to HTTP I/O, including body and stream
  reads. Sync cannot safely interrupt a local provider or hook.
  Response streams close on exhaustion, error, explicit close, or
  context-manager exit; stream I/O timeouts use `PlakyTimeoutError`.

## Naming

Python attributes and keyword arguments are snake_case; HTTP and MCP wire
names stay camelCase (`spaceId`, `pageSize`). Models use aliases and are
dumped `by_alias=True`.

## Resources

spaces, boards, items, comments, reactions, users, teams, item_groups,
item_files — see `docs/compatibility-inventory.md` for all 32 operations.
List endpoints offer `list`, `iterate` (lazy), and `list_all` (bounded by
`limit`). `comments.list` normalizes the API's bare array into
`Page(has_more=False)`. `item_files.list` stays a plain list.

`items.iterate` and `items.list_all` preserve `board_view_id`, `parent_id`,
and `subitems_behaviour` on every page. Text resolvers make one bounded page
decision: an incomplete page is inconclusive rather than a false match.

## Errors and retries

Typed errors under `PlakyError`; API failures map by status
(401/403/404/409/400/422/429/5xx). Only GET requests retry (429/5xx,
timeouts, connection failures) with equal-jitter backoff and bounded
Retry-After. Writes make exactly one network attempt, even with an
explicit `idempotency_key`.

Export format and CSV-safety values are validated before any reference lookup
or network call. Use only `jsonl` or `csv`, and `spreadsheet` or `raw` CSV
safety. Download-link expiry metadata is exposed as `expiresInSeconds` at the
MCP compaction boundary; signed URLs remain sensitive capabilities.

## Pagination and chunks

`Page[T]` requires the strict `{data, hasMore}` root. Iterators stop at a
10,000-page safety valve. Bounded chunk readers (`read_item_chunk`,
`read_item_export_chunk`) return exact `{page, index}` continuation
cursors; byte accounting is UTF-8.

## Uploads

`item_files.upload` takes bytes plus an explicit filename (25 MiB hard
ceiling; multipart field name `file`). Signed download URLs from
`get_download` are bearer capabilities: never log or persist them.
