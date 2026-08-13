# Live certification

## Read-only gate

Requires an injected rotated `PLAKY115_API_KEY`. Runs the 17 read
operations through four surfaces (direct HTTP probe, sync SDK, async SDK,
generated raw MCP) plus curated workflows workspace.map, items.search,
comments.thread, export.items. Acceptance per surface: 17 pass / 0 skip,
or 15 pass plus the paired getItemFile/getItemFileDownload
SKIP_PREREQUISITE only when a complete file listing proves no file exists.
Records method/tool, sanitized status, root shape, pagination coverage,
and counts only; signed URLs validate in memory and are never printed.

## Write gate

Interlocks (not authorization): `PLAKY115_LIVE_WRITE=1`,
`PLAKY115_SMOKE_SPACE_ID`, `PLAKY115_SMOKE_BOARD_ID`, and
`PLAKY115_SMOKE_ALLOW_ARCHIVE=1` for the archive probe. Separate
current-task authorization must name the sacrificial space/board, allowed
operations, mutation budget, cleanup boundary, and archive permission.
One UUID-marked run proves the 15 mutation operations through the async
SDK and raw MCP with dedicated artifacts per surface; cleanup runs in
finally/SIGINT/SIGTERM, scans all pages for the marker, and must end with
0 tracked artifacts and 0 leftovers. An undeletable archived group fails
certification and quarantines future write runs until recovered.
