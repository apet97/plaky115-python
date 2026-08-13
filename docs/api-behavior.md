# API behavior notes

- Paged roots are strictly `{"data": [...], "hasMore": bool}`; an empty
  page claiming `hasMore: true` is a contract error.
- `listItemComments` and `listItemFiles` return bare arrays; the SDK wraps
  comments in a Page and the MCP boundary presents both as a documented
  `{"data": [...]}` envelope.
- Unsafe JSON integers (beyond ±9007199254740991) decode to exact decimal
  strings; safe integers stay ints.
- `expand` is comma-joined (explode=false); `emails` repeats the key;
  booleans serialize lowercase; page numbers are 1-based.
- Reaction values are Unicode codepoint hex (e.g. `1f44d`); an empty array
  clears the caller's reactions.
- Archive item group is destructive: the public API has no unarchive.
- Rate limit: 200 requests/user/minute; 429 carries Retry-After.
