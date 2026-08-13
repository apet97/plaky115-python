# Changelog

## Unreleased

Fixes from the adversarial review of PR #2:

- The package imports without the build-generated `plaky115._version`
  module; `__version__` falls back to `0.0.0.dev0`.
- Item group create and update plans accept a missing `color`; a present
  `color` must still match `#RRGGBB`.
- Generated models type int64 fields as `int | str`, so unsafe int64 IDs
  preserved as decimal strings stay strings through validation and
  re-serialization.
- `normalize_server_url` accepts bracketed IPv6 loopback URLs such as
  `http://[::1]/` and still rejects non-loopback IPv6 HTTP hosts.
- `RateLimitSnapshot.reset_at` stores the `X-RateLimit-Reset` header value
  exactly as sent; the dead unit-normalization branch is removed.
- CSV export iteration builds one schema before the first chunk and uses
  it for every chunk, so all rows align with the single header and the
  board definition is fetched once per iteration.
- Export serialization uses `model_dump(mode="json")`; datetimes render
  as ISO-8601 strings (with the `T` separator).

- Initial Python port of the plaky115 SDK and MCP server from pinned source
  `33ae2926aa696f36d9663d44f914d42d9aadc53f` (v1.0.11).
