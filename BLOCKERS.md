# Blockers

Only genuine external blockers belong here. A failing test, missing function,
unclear internal code, or ordinary bug is work, not a blocker.

## RESOLVED — live read certification run
Date: 2026-08-13
An injected PLAKY115_API_KEY was present in the execution environment.
`uv run python scripts/live_read.py` ACCEPTED all four surfaces
(direct-http, sync-sdk, async-sdk, raw-mcp): 15 pass + exactly the paired
getItemFile/getItemFileDownload SKIP_PREREQUISITE (complete file listing
proved no file exists). The run also surfaced and fixed a real model
defect (ADR-0006: naive datetimes). Counts and shapes only were recorded.

## RESOLVED — live write certification
Date: 2026-08-13
Authorization: granted in-task, naming sacrificial workspace a5115x
(space 41478, board 157742) with unrestricted mutation and archive
permission. Run with all four interlocks set.
Result: WRITE GATE ACCEPT — 15/15 mutation operations through the async
SDK and 15/15 through generated raw MCP tools with dedicated artifacts;
tracked artifacts 0; discovered leftovers 0; no quarantined archived
groups (the archived probe group deleted cleanly). The run surfaced and
fixed a real defect: MCP structured content carried non-JSON-serializable
datetimes (fixed via model_dump(mode="json") across MCP surfaces).

## BLOCKED_EXTERNAL — remote repository, tags, and publication
Date: 2026-08-13
Reason: remote creation/push/PR, tag creation, and TestPyPI/PyPI
publication each require separate current-task authorization naming the
owner/repository/branch, version/commit, or registry/version/digest. None
was granted. Local commits are complete and reproducible.
Next action after unblocking: push to the named remote, tag the named
version, and publish via trusted publishing using the verified artifact
digest recorded in the verify receipt.
