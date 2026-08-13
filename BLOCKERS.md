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

## BLOCKED_EXTERNAL — live write certification (script and run)
Date: 2026-08-13
Command: (not yet runnable) planned `scripts/live_write.py`
Reason: live writes require separate current-task authorization naming the
sacrificial space/board, allowed operations, mutation budget, cleanup
boundary, and archive permission (plan section 3.8), plus the
PLAKY115_LIVE_WRITE/SMOKE_* interlocks. No such authorization exists in
this task. The write-sweep script itself is deferred with the run; its
behavior contract is documented in docs/live-certification.md and plan
Phase 15.
Next action after unblocking: implement scripts/live_write.py to the
Phase 15 contract (UUID marker, 15 mutations x async SDK + raw MCP with
dedicated artifacts, finally/SIGINT/SIGTERM cleanup, zero-residue proof),
then run under the named authorization.

## BLOCKED_EXTERNAL — remote repository, tags, and publication
Date: 2026-08-13
Reason: remote creation/push/PR, tag creation, and TestPyPI/PyPI
publication each require separate current-task authorization naming the
owner/repository/branch, version/commit, or registry/version/digest. None
was granted. Local commits are complete and reproducible.
Next action after unblocking: push to the named remote, tag the named
version, and publish via trusted publishing using the verified artifact
digest recorded in the verify receipt.
