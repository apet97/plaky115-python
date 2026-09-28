# SDK guide

Plaky115 is unofficial and independent. It is not affiliated with, endorsed
by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks
of their respective owners.

## Clients

- `AsyncPlakyClient` is the canonical client (MCP handlers are async).
- `PlakyClient` is a real synchronous client over `httpx2.Client`; it never
  starts an event loop or bridges into the async client.
- Both accept: `api_key` (literal or same-mode provider), `server_url`,
  `timeout` (30 s default), `max_retries` (2; see "Errors and retries"),
  `max_response_bytes` (16 MiB default, 64 MiB maximum), `headers` (mapping
  or same-mode provider), `user_agent` / `user_agent_suffix`,
  `request_hook` / `response_hook`, injected `http_client` or `transport`,
  an optional `pacer` (see "Rate limit"), and support `with_options`, `close()`/`aclose()`, and context managers.
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

spaces, boards, items, comments, reactions, subscriptions, users, teams,
item_groups, item_files — see `docs/compatibility-inventory.md` for all 34
operations.
List endpoints offer `list`, `iterate` (lazy), and `list_all` (bounded by
`limit`). `comments.list` normalizes the API's bare array into
`Page(has_more=False)`. `item_files.list` stays a plain list.

`items.iterate` and `items.list_all` preserve `board_view_id`, `parent_id`,
and `subitems_behaviour` on every page. Text resolvers make one bounded page
decision: an incomplete page is inconclusive rather than a false match.

Server behaviour worth knowing (measured live 2026-09-21/23):

- `listItems` defaults to `subitemsBehaviour=INCLUDE`, so native subitems
  appear in the top-level list. Pass `subitems_behaviour="EXCLUDE"` when
  indexing a board's items. An item or group archived in the UI disappears
  from every list call, and no API call lists or restores it.
- `listItems` accepts `page_size` up to 1000 (2000 is refused); the SDK
  default is 100. A full board read is far cheaper at 1000.
- `item_groups.create` and `item_groups.update` require `color`: the server
  answers 500 without it, although the spec marks it optional. `update`
  keeps a new `ranking` only when title, ranking, and color are all sent.
  Groups and items created through the API land on top of the board.
- `subscriptions.replace` sets the complete list of an item's subscribers.
  To choose them at creation, send `subscribedUserIds` /
  `subscribedTeamIds` on `items.create`; they replace the default
  subscriber (the creator) in the same request.
- Uploaded file names are rewritten: the extension moves to a separate
  `extension` field, and spaces, dots, `%`, and `&` become `_`
  (`Q3 report.pdf` is stored as `Q3_report` + `pdf`). Match a re-upload on
  the name's letters and digits, not the exact name.

## Field values

Builders in `plaky115.fields` produce write values; the server owns type
semantics. Rules the server enforces (measured live 2026-09-23):

- `null` is refused for every type, and `items.create` answers 500 to a
  null value, so drop absent values with `omit_none`.
- Clearing differs by type: `""` for text, rich text, number (not on
  create, where `""` for a number answers 500), and link; `""` (the empty
  label's title) for status; `[]` for tag; `{"users": [], "teams": []}` for
  person. Date and timeline values cannot be cleared.
- Person values are written as `{"users": [{"id"}], "teams": [{"id"}]}`
  (`person_field`). The read shape, `{"assignedUsers", "assignedTeams"}`,
  is accepted on write but assigns nobody. Read values hold ids as numbers
  or exact decimal strings, and full objects when expanded, so compare ids
  after normalizing all three forms.
- Links need `displayText`; `link_field` defaults it to the URL.
- Dates need an explicit UTC offset, and Plaky shows the day in the offset
  the value was written with, whatever the viewer's time zone.
- Status and tag values match a label's key or title. A value that matches
  two labels (a label titled `"0"` beside the empty label's key `"0"`) is
  refused; send that label's key instead.
- Rich text and comments are stored verbatim and rendered as HTML, so a bare
  newline collapses into a space. `rich_text_field` writes plain text as one
  escaped paragraph per line.

## Errors and retries

Typed errors under `PlakyError`; API failures map by status
(401/403/404/409/400/422/429/5xx). GET requests retry on 429, 5xx,
timeouts, and connection failures, with equal-jitter backoff and bounded
Retry-After. A write is replayed only after a 429: Plaky never commits a
request it refuses with 429 (of 600 burst creates, exactly the 500 answered
201 existed; measured 2026-09-22), and a replay resends the same body and
`Idempotency-Key`. After a 5xx, timeout, or connection failure a write may
have committed, so it makes exactly one network attempt, even with an
explicit `idempotency_key`.

Mutation receipts follow the same rule. A failure before dispatch is
`failed`; a 429 after dispatch is `rejected` (attempted, not committed);
any other failure after dispatch is `ambiguous` with `may_have_committed`.

## Rate limit

Plaky allows 200 requests per user per minute and answers anything beyond
with 429 and `Retry-After: 60`. `client.rate_limit` only observes. To stay
under the limit, give the client a `RequestPacer`:

```python
from plaky115 import PlakyClient, RequestPacer

pacer = RequestPacer()  # 190 requests per 60 s sliding window
client = PlakyClient(api_key=key, pacer=pacer)
```

Every attempt claims a slot before it is sent, retries and replays
included. The limit is per user, so share one pacer between clients that
use the same key; `with_options` keeps it. The async client waits with
`asyncio.sleep`, outside the attempt's timeout.

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
