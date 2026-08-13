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

## RESOLVED — tags and publication (was BLOCKED_EXTERNAL)
Date: 2026-08-13 (updated same day)
Remote: RESOLVED — pushed to https://github.com/apet97/plaky115-python (main).
Remaining: tag creation and PyPI publication still require separate
authorization naming registry/version/digest. Release automation is in
place (.github/workflows/release.yml: tag-triggered uv build + twine
check + PyPI trusted publishing under the `pypi` environment). The
operator is not logged into pypi.org in the managed browser, so the
pending-trusted-publisher registration (project plaky115, owner apet97,
repo plaky115-python, workflow release.yml, environment pypi) and the
version tag push are user actions.

Publication receipt (2026-08-13): registry=pypi.org, project=plaky115,
version=1.0.0, tag=v1.0.0 on commit c03f0d3, workflow run 31736901309,
dist artifact sha256:7dacb780ecc9ad9f41138421cd3ed8f8e23cd0178e464a03c7b1ea7f5ae07f61,
trusted publishing (OIDC) with attestations. Verified installable:
`pip install "plaky115[mcp]==1.0.0"` imports SDK + MCP and the
plaky115-mcp CLI runs. User authorized in-session ("do ur thing" after
the v1.0.0 proposal).
