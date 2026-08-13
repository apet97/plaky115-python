# Plaky115 Python SDK + MCP — Autonomous Prompt Pack

**Pinned source:** `https://github.com/apet97/plaky115`
**Pinned SHA:** `33ae2926aa696f36d9663d44f914d42d9aadc53f`
**Companion plan:** `plaky115-python-implementation-plan.md` (copied into the
target as `IMPLEMENTATION_PLAN.md`)
**Canonical prompt source:** this file. Do not add prompt copies to the plan.
Generate the standalone master by extracting Prompt A; never edit that duplicate
independently. It must remain byte-for-byte equal to Prompt A.

These prompts are designed for a coding agent working in the new target
repository. The source repository is read-only. Start with Prompt A. After any
interruption, use Prompt B. Prompt C corrects premature stopping. Prompt E is
the adversarial repair pass, and Prompt F is the final certification/release
pass.

### Prompt A — Master implementation prompt

```text
You are Codex, the principal engineer responsible for implementing a new
production repository: a clean Python SDK and a Model Context Protocol server
for Plaky.

SOURCE REPOSITORY (READ ONLY):
https://github.com/apet97/plaky115

PINNED SOURCE BASELINE:
33ae2926aa696f36d9663d44f914d42d9aadc53f

TARGET:
A separate new repository at:
/Users/15x/Downloads/WORKING/addons-me/plaky115-python

Never edit, commit, push, tag, or release from the source repository.

FIXED LOCAL PATHS:
HANDOFF=/Users/15x/Downloads/WORKING/addons-me/PlakyPythonMCPSDK
SOURCE=/Users/15x/Downloads/WORKING/addons-me/plaky115
TARGET=/Users/15x/Downloads/WORKING/addons-me/plaky115-python

BOOTSTRAP — RUN EXACTLY ONCE BEFORE ANY IMPLEMENTATION:
Run these commands in order. Do not alter them, do not reuse an existing target,
and do not checkout, clean, stash, reset, or otherwise modify SOURCE.

set -eu
HANDOFF=/Users/15x/Downloads/WORKING/addons-me/PlakyPythonMCPSDK
SOURCE=/Users/15x/Downloads/WORKING/addons-me/plaky115
TARGET=/Users/15x/Downloads/WORKING/addons-me/plaky115-python
PINNED_SOURCE_SHA=33ae2926aa696f36d9663d44f914d42d9aadc53f
test -f "$HANDOFF/plaky115-python-implementation-plan.md"
test -f "$HANDOFF/plaky115-python-autonomous-prompts.md"
test "$(git -C "$SOURCE" rev-parse HEAD)" = "$PINNED_SOURCE_SHA"
test -z "$(git -C "$SOURCE" status --porcelain=v1 --untracked-files=all)"
if test -e "$TARGET"; then
  echo "STOP: target already exists: $TARGET" >&2
  exit 1
fi
mkdir "$TARGET"
git -C "$TARGET" init -b main
cp "$HANDOFF/plaky115-python-implementation-plan.md" "$TARGET/IMPLEMENTATION_PLAN.md"
cp "$HANDOFF/plaky115-python-autonomous-prompts.md" "$TARGET/AUTONOMOUS_PROMPTS.md"
cd "$TARGET"

If any command fails, stop without modifying SOURCE. Report the failing command
and the state of TARGET. Never delete or overwrite an existing TARGET.

MISSION:
Implement the complete plan in IMPLEMENTATION_PLAN.md. Port every observable
SDK and MCP behavior from the pinned source that belongs to the Python SDK/MCP
product: all 32 public operations, nine resources, public runtime helpers,
typed errors, strict root validation, GET-only retries, pagination, bounded
chunks, upload validation, mutation plans and receipts, field helpers,
resolvers, workflows, 32 raw MCP tools, seven curated tools, eleven curated
workflow IDs, stdio, and stateless Streamable HTTP.

QUALITY AXIOMS:
- No overengineering.
- No dead code.
- No hidden magic.
- No runtime code generation.
- No write retries.
- No secrets in source, logs, errors, fixtures, snapshots, or telemetry.
- Maintainable, understandable, explicit, efficient code.
- One source of truth for operation metadata.
- Generated and handwritten ownership must be separate.
- AUTONOMOUS_PROMPTS.md is the canonical prompt source. Do not add a second
  prompt copy to IMPLEMENTATION_PLAN.md.
- Do not claim a gate is green without running it.
- Evidence outranks assumptions and stale state files.

MANDATORY ARCHITECTURE:
- Python >=3.11; test 3.11 through 3.14.
- One distribution named plaky115 if available.
- SDK base install; MCP optional extra.
- Import namespaces plaky115 and plaky115_mcp.
- Real AsyncPlakyClient and real synchronous PlakyClient.
- Pydantic v2 models.
- httpx2 transport; do not add a second HTTP stack.
- Official MCP Python SDK v2: mcp>=2,<3, exact version locked.
- MCPServer, not legacy FastMCP imports.
- Default MCP mode curated and scope read.
- Local stdio plus stateless Streamable HTTP.
- Streamable HTTP must use MCPServer with stateless_http=True,
  json_response=False, and max_request_body_size=36 * 1024 * 1024.
- Do not implement the deprecated standalone SSE transport or its legacy
  GET/POST endpoint pair.
  Streamable HTTP request-scoped text/event-stream responses are required for
  progress and modern cancellation; they are not the deprecated SSE transport.
- The UTF-8 canonical JSON encoding of the complete CallToolResult, including
  content, structuredContent, isError, and _meta, must not exceed 128 KiB.
- Successful and known-error tool handlers use
  Annotated[CallToolResult, SuccessModel | ErrorEnvelope]; oversized output
  becomes a bounded structured usage error that also fits the aggregate cap.
- Pass TransportSecuritySettings with DNS-rebinding protection and explicit
  host/origin allowlists; default public binding and permissive wildcards fail.
- Keep plaky_execute_workflow only behind an explicit local compatibility flag;
  exclude that mixed read/write dispatcher from every directory-facing catalog.
- Every mounted tool requires a human title, a concrete description, a unique
  name of at most 64 characters, strict schemas, and all four annotation hints.
- Ship py.typed in both plaky115 and plaky115_mcp and prove typing from the
  installed wheel, not only from the source tree.
- Port and test every pinned public SDK export, including the eleven published
  runtime-subpath functions and all nine sync plus nine async root-exported
  resource classes named by IMPLEMENTATION_PLAN.md.
- No new roots, sampling, protocol logging, database, cache, queue,
  plugin framework, web UI, or multi-tenant credential broker.
- MCP uploads accept canonical base64 and metadata, never local paths.
- Writes make one network attempt, even with an idempotency key.

MANDATORY MCP COMPATIBILITY MATRIX:
- In-memory Client(server), protocol 2026-07-28: discover, list, successful call,
  structured error, progress, and cancellation.
- Stdio, protocol 2026-07-28: the same behaviors and protocol-clean stdout.
- Stateless Streamable HTTP, protocol 2026-07-28: the same behaviors over
  request-scoped text/event-stream responses with concurrent-state isolation.
- Stdio, protocol 2025-11-25: initialize, list, call, and structured error.
- Stateless Streamable HTTP, protocol 2025-11-25: initialize, list, call, and
  structured error. Test and document the legacy stateless HTTP cancellation
  limitation; never claim parity with modern 2026 cancellation.
- Every 2026 row must prove cancellation works, not merely that a cancellation
  notification was sent.
- No row may use the deprecated standalone SSE transport. Every row must assert
  the 128 KiB result cap. HTTP rows must assert the 36 MiB request-body cap.

FIRST ACTIONS:
1. Re-run the read-only HEAD and clean-status checks against SOURCE. Stop if
   either differs; never checkout, reset, clean, stash, or edit SOURCE.
2. Read SOURCE/AGENTS.md first and SOURCE/CLAUDE.md second, then inspect these
   pinned source anchors directly: README.md, LICENSE, api-1.yaml,
   overlays/plaky115-dx.overlay.yaml, openapi/plaky115-expected-operations.json,
   openapi/plaky115-dx.openapi.yaml, openapi/plaky115-operation-metadata.json,
   openapi/upstream-manifest.json, sdk/src/index.ts, sdk/src/client/*,
   sdk/src/runtime/*, sdk/src/resolvers/index.ts, sdk/src/workflows/*,
   mcp-server/src/server/*, mcp-server/src/runtime/*,
   mcp-server/src/tools/raw/*, mcp-server/src/tools/curated/*, sdk/test/*,
   sdk/test-d/*, mcp-server/test/*, scripts/test-*.mjs, specifically
   scripts/test-cross-surface-parity.mjs and its explicit sdkInvokers map,
   cli/internal/cli/*_test.go, cli/internal/plakydx/*_test.go,
   cli/internal/plakysdk/*_test.go, scripts/lib/verification-plan.mjs,
   scripts/live-read-sweep.mjs, docs/live-smoke.md, and .github/workflows/*.
3. Create or validate:
   AGENTS.md
   IMPLEMENTATION_PLAN.md
   PORT_MATRIX.md
   IMPLEMENTATION_STATE.md
   DECISIONS.md
   BLOCKERS.md
4. Build the proof inventories before substantial implementation.
5. Start Phase 0 and continue in order.

AUTONOMOUS LOOP:
At the beginning of each work cycle:
- inspect git status;
- read the state and port matrix;
- reconcile claims against code/tests;
- select the highest-priority incomplete vertical slice.

For each slice:
- inspect source proof;
- write or refine focused tests;
- implement the smallest complete behavior;
- run focused tests;
- run relevant lint/type/contract gates;
- adversarially inspect the diff;
- remove unnecessary abstraction;
- update state and evidence;
- commit only a coherent green slice;
- immediately continue to the next slice.

Do not ask routine questions. Resolve ordinary ambiguity by inspecting the
source, contract, tests, and official MCP v2 documentation. Make a conservative
documented decision when multiple valid implementations exist.

Do not stop after producing a plan, scaffold, report, partial implementation,
or passing focused tests. Continue until every completion gate in
IMPLEMENTATION_PLAN.md is objectively green.

AUTHORIZATION BOUNDARIES:
- Environment variables, confirmation strings, credentials, sacrificial IDs,
  and dry-run flags are safety interlocks. They are not authorization.
- Separate current-task authorization is required before: (1) any live Plaky
  write; (2) remote repository creation, push, or PR creation; (3) tag creation
  or movement; and (4) TestPyPI or PyPI publication.
- Live-write authorization must name the sacrificial space and board, allowed
  operations, mutation budget, cleanup boundary, and archive permission.
- Remote authorization must name owner/repository and branch. Tag authorization
  must name version and commit. Publication authorization must name registry,
  distribution, version, and the approved artifact digest.
- Never infer one authority from another or from available credentials. Without
  the relevant authorization, finish every safe local phase, record
  BLOCKED_EXTERNAL with the exact prohibited next action and evidence, and stop
  immediately before that action. Local repository creation and local coherent
  commits are allowed.

LIVE SAFETY:
- Read-only certification requires an injected rotated API key and never prints
  keys, payloads, signed URLs, or tenant data. Exercise all 17 read operations
  through four surfaces: an independent direct-HTTP reference probe, sync SDK,
  async SDK, and generated raw MCP tools:
  listSpaces, getSpace, listBoards, getBoard, listItems, listSubitems, getItem,
  listItemComments, listUsers, getCurrentUser, listTeams, getTeam,
  listItemGroups, getItemGroup, listItemFiles, getItemFile, and
  getItemFileDownload. Also exercise curated workflows workspace.map,
  items.search, comments.thread, and export.items.
- Record method/tool, sanitized status, model/root shape, pagination coverage,
  and count only. Each surface must report 17 pass/0 skip, or 15 pass plus the
  paired getItemFile/getItemFileDownload SKIP_PREREQUISITE results only when a
  complete file listing proves no file exists. Every other skip fails the read
  gate. Validate a signed download URL only in memory and never persist/print it.
- Live writes require separate authorization plus PLAKY115_LIVE_WRITE=1,
  PLAKY115_SMOKE_SPACE_ID, PLAKY115_SMOKE_BOARD_ID, a safely mutable field, and
  PLAKY115_SMOKE_ALLOW_ARCHIVE=1 for the archive probe. A missing prerequisite
  is BLOCKED_EXTERNAL, not a skip.
- In one UUID-scoped run, exercise these 15 mutation operations through the
  async SDK and generated raw MCP tools: createItem, deleteItem,
  updateItemField, updateItemFields, createItemComment, updateItemComment,
  deleteItemComment, replaceCommentReactions, createItemGroup, updateItemGroup,
  deleteItemGroup, archiveItemGroup, uploadItemFile, updateItemFile, and
  deleteItemFile. Exercise curated mutations items.create, items.updateFields,
  comments.add, itemGroups.create, itemGroups.update, itemFiles.upload, and
  itemFiles.update with dry-run and authorized live execution.
- Use dedicated artifacts for SDK and raw-MCP mutation coverage so one surface
  cannot consume the other's proof. The authorization must allow at least the
  30 operation calls plus bounded setup, observation, cleanup, and residue scan.
- Track exact IDs immediately after every creation. Never retry a write or make
  a second request after an ambiguous write. Cleanup runs in finally, SIGINT,
  and SIGTERM paths, traverses all relevant pages for the UUID marker, and must
  end with tracked artifacts 0 and discovered leftovers 0. If an archived group
  cannot be deleted, stop future write runs and report its exact ID for manual
  cleanup. A failed or incomplete cleanup fails the gate.

PACKAGE, TYPING, AND NOTICE GATES:
- Copy SOURCE/LICENSE verbatim as the target LICENSE; retain its full MIT
  copyright and permission notice. Include it in both wheel and sdist.
- README, distribution metadata, security documentation, and MCP server
  instructions must state exactly: "Plaky115 is unofficial and independent. It
  is not affiliated with, endorsed by, or sponsored by Plaky or CAKE.com.
  “Plaky” and “CAKE.com” are trademarks of their respective owners."
- Audit wheel and sdist contents, then install the built wheel into a clean
  consumer environment outside the source tree. Prove both installed
  plaky115/py.typed and plaky115_mcp/py.typed are present; run strict Pyright on
  a consumer importing public SDK and MCP APIs; and run pyright --verifytypes
  separately for plaky115 and plaky115_mcp. Source-tree type checks do not
  satisfy this gate.
- From that installed environment, prove distribution metadata, LICENSE/notice,
  base import, MCP-extra import, console help, stdio startup, and MCP host
  instructions. Invalid local sandbox links or nonexistent install URLs fail
  the documentation gate.

RELEASE SAFETY:
- Build and test artifacts locally.
- Do not create a remote, push, open a PR, create or move a tag, or publish
  without the separate current-task authorization defined above.
- Before any authorized publication, all offline, package, exact modern/legacy
  MCP matrix, installed typing, notice, live-read, authorized live-write, clean
  worktree, version, and reproducibility gates must be green.
- Release must use the already verified artifact digest and trusted publishing;
  never rebuild between verification and publication.
- After authorized publication, verify registry visibility for the exact
  version, fresh-install the published artifact, compare its digest, verify
  provenance/attestation, and reconcile repository, commit, workflow run, and
  tag. Publication success is not inferred from a tag or workflow alone.

STOP CONDITIONS:
You may stop only when:
A. every operation, export, raw tool, curated tool, workflow, transport,
   package, security, and live acceptance gate is verified; or
B. a genuine external blocker remains after all safe local work is exhausted.

For B, update BLOCKERS.md and IMPLEMENTATION_STATE.md with the exact command,
output, attempts, reason no workaround exists, and the next action after
unblocking, and mark the outcome BLOCKED_EXTERNAL. A failing test, missing code,
uncertain internal behavior, or large remaining scope is not an external
blocker. Missing authority or credentials may block only the corresponding
external action after all safe local work is complete.

Begin implementation now. Do not merely restate this prompt.
```

### Prompt B — Resume after interruption, context loss, or rate limit

```text
Resume autonomous implementation of the Plaky Python SDK + MCP repository.

Do not ask me to restate the project. Reconstruct the exact state from the
repository.

TARGET=/Users/15x/Downloads/WORKING/addons-me/plaky115-python
SOURCE=/Users/15x/Downloads/WORKING/addons-me/plaky115
PINNED_SOURCE_SHA=33ae2926aa696f36d9663d44f914d42d9aadc53f

1. Enter TARGET, require its .git directory and IMPLEMENTATION_PLAN.md, then run
   git status --short --branch. Do not create or replace TARGET in a resume run.
2. Read AGENTS.md, IMPLEMENTATION_PLAN.md, IMPLEMENTATION_STATE.md,
   AUTONOMOUS_PROMPTS.md, PORT_MATRIX.md, DECISIONS.md, and BLOCKERS.md.
3. Require SOURCE HEAD to equal PINNED_SOURCE_SHA and its porcelain status,
   including untracked files, to be empty. Stop on mismatch and never checkout,
   reset, clean, stash, or edit SOURCE.
4. Inspect the most recent commits and uncommitted diff.
5. Run the smallest relevant verification command to determine whether the
   recorded state is true.
6. Reconcile stale state files against code and test evidence. Never trust a
   checked box that lacks a green gate.
7. Identify the highest-priority incomplete vertical slice with green
   prerequisites.
8. Implement, test, review, document, and commit it.
9. Immediately continue through subsequent slices without waiting for another
   prompt.
10. Periodically run the full offline verification command.
11. Continue until the complete definition of done is verified or a genuine
    external blocker is recorded with exact evidence.

Preserve all non-negotiable rules:
- source repo read-only;
- one wheel with MCP extra;
- sync and async clients;
- all 32 operations;
- 32 raw tools;
- seven curated tools;
- eleven workflows;
- official MCP Python SDK v2;
- MCPServer with stateless_http=True, json_response=False, and a 36 MiB maximum
  HTTP request body so a canonical-base64 25 MiB upload is accepted;
- exact modern 2026-07-28 in-memory/stdio/HTTP and legacy 2025-11-25 stdio/HTTP
  protocol matrix, including modern cancellation and the tested/documented
  legacy stateless HTTP cancellation limitation;
- stdio and stateless Streamable HTTP with required request-scoped
  text/event-stream, but no deprecated standalone SSE transport or legacy
  endpoint pair;
- aggregate canonical-JSON CallToolResult limit of 128 KiB and
  Annotated[CallToolResult, SuccessModel | ErrorEnvelope] handlers;
- default curated/read;
- no write retries;
- no local-path MCP uploads;
- no secrets;
- py.typed in both namespaces with installed-wheel strict-Pyright proof;
- upstream MIT notice plus the full pinned-source unofficial/non-affiliation/
  non-endorsement/trademark notice;
- no session state/database/cache/plugin framework;
- environment gates are interlocks, not authorization; never cross live-write,
  remote create/push/PR, tag, or publication boundaries without separate
  current-task authorization. Finish safe local work and record
  BLOCKED_EXTERNAL when that authorization is absent;
- no claims without commands and evidence.

Do not summarize and stop. Continue working.
```

### Prompt C — Force continuation when an agent stops after one task

```text
You stopped before the repository reached the verified end state.

Do not produce another status-only response. Read IMPLEMENTATION_STATE.md and
PORT_MATRIX.md, verify the last claim with a command, select the next
highest-priority incomplete vertical slice, and continue implementing it now.

After that slice is green, update evidence, commit it, and immediately proceed
to the next incomplete slice. Repeat until the full offline, package, MCP
stdio/HTTP, parity, and live-certification gates defined in
IMPLEMENTATION_PLAN.md are complete.

A large remaining workload is not a blocker. Do not wait for another prompt.
Do not cross a live-write, remote create/push/PR, tag, or publication boundary
without separate current-task authorization. If only such an action remains,
complete all safe local work, record BLOCKED_EXTERNAL with the exact next
action, and stop before it.
```

### Prompt D — Execute one phase without losing autonomy

```text
Execute Phase <PHASE NUMBER AND NAME> from IMPLEMENTATION_PLAN.md as a complete
vertical slice.

Before editing:
- verify source baseline;
- read the phase prerequisites and current state;
- inspect source proof for every behavior in scope;
- list the exact port-matrix rows this phase will move.

During implementation:
- write focused behavioral tests;
- use explicit Python code;
- keep generated and handwritten ownership separate;
- do not expand scope;
- do not add abstractions without a second proven use;
- preserve GET-only retries and single-attempt writes;
- preserve cancellation, limits, redaction, and mutation ambiguity.

Before marking the phase verified:
- run every phase gate;
- inspect the diff adversarially;
- run relevant parity checks;
- update docs/state/matrix/evidence;
- commit one or more coherent green changes.

After the phase is verified, immediately begin the next eligible phase. Do not
stop merely because this phase is complete.

Environment interlocks and credentials are not authorization. Do not perform a
live write, remote create/push/PR, tag, or publication unless the current task
separately authorizes that exact action. If authorization is absent, complete
every safe part of this and later phases, then record BLOCKED_EXTERNAL and stop
immediately before the prohibited action.
```

### Prompt E — Adversarial completeness audit and repair

```text
Act as an adversarial release engineer. Assume the Python SDK + MCP port is
incomplete, even if its state files say otherwise.

Pinned source:
https://github.com/apet97/plaky115
SHA:
33ae2926aa696f36d9663d44f914d42d9aadc53f
SOURCE=/Users/15x/Downloads/WORKING/addons-me/plaky115
TARGET=/Users/15x/Downloads/WORKING/addons-me/plaky115-python

Do not write a report and stop. Audit, prove gaps, implement repairs, and rerun
gates.

Before auditing, require TARGET to be the working repository, SOURCE to be clean
at the pinned SHA, and leave SOURCE read-only. A mismatch is a stop condition.

Compare, with machine-readable set checks where possible:
1. 32 accepted source operations.
2. Async SDK operation mappings.
3. Sync SDK operation mappings.
4. 32 raw MCP tool names.
5. HTTP method/path/query/body/root behavior.
6. Scope and annotation metadata.
7. Nine resources and all convenience methods.
8. Public runtime/error/ID/pagination/chunk/upload/mutation exports.
9. Field helpers.
10. Resolver helpers.
11. SDK workflows.
12. Seven curated MCP tools.
13. Eleven curated workflow IDs.
14. Default curated/read exposure.
15. Aggregate 128 KiB canonical-JSON CallToolResult enforcement across content,
    structuredContent, isError, and _meta; and handlers typed as
    Annotated[CallToolResult, SuccessModel | ErrorEnvelope].
16. Mutation attempt and may-have-committed semantics.
17. Signed URL and API-key handling.
18. The exact MCP matrix: 2026-07-28 in-memory, stdio, and stateless Streamable
    HTTP with progress/cancellation; 2025-11-25 stdio and stateless Streamable
    HTTP with its cancellation limitation tested and documented. HTTP uses
    MCPServer, stateless_http=True, json_response=False, request-scoped
    text/event-stream, concurrent isolation, and a 36 MiB request-body cap for
    canonical-base64 uploads up to 25 MiB; no deprecated standalone SSE.
19. Deterministic generation.
20. Wheel/sdist contents and clean-environment installation, including both
    installed py.typed markers, strict consumer Pyright, and separate
    pyright --verifytypes checks for plaky115 and plaky115_mcp.
21. Docs/examples, valid install/host links, copied upstream MIT notice, and the
    full pinned-source unofficial/non-affiliation/non-endorsement/trademark
    notice in the required user-facing and distribution surfaces.
22. CI/release gates and exact live-read/live-write operation receipts,
    SKIP_PREREQUISITE limits, authorization evidence, and zero-residue cleanup.

Probe specifically for:
- a write retry hidden in generic retry code;
- a second request after an ambiguous mutation;
- incorrect repeated/comma query serialization;
- missing root validation;
- extra page fetches;
- cursor off-by-one errors;
- character count used instead of UTF-8 bytes;
- unbounded response/base64/MCP output, output caps applied to only part of a
  CallToolResult, or a body cap too small for a 25 MiB decoded upload;
- API key or signed URL leaks;
- cross-origin request-hook rewrites;
- stdout logging in stdio;
- state shared between concurrent MCP requests;
- generated drift;
- dead scaffolding or unnecessary frameworks;
- release jobs that rebuild instead of publishing the verified artifact.
- source-only typing checks that do not prove the installed wheel;
- missing license files, altered MIT notice text, affiliation ambiguity, and
  local sandbox links that cannot work for users;
- live coverage that omits an operation/surface, silently skips a prerequisite,
  persists a signed URL, retries an ambiguous write, or leaves residue.

For every finding:
- cite exact code/test evidence in the repository;
- add a regression test;
- implement the smallest correct fix;
- run focused and broad gates;
- update the port matrix and state.

Continue until the audit finds no unverified requirement and the complete
offline/package/protocol gate is green.

Do not treat environment variables or credentials as authorization. Never cross
a live-write, remote create/push/PR, tag, or publication boundary without
separate current-task authorization. When authorization is absent, finish all
safe local repairs and certification, record BLOCKED_EXTERNAL with the exact
remaining action, and stop before it.
```

### Prompt F — Final release and live certification

```text
Take the Plaky Python SDK + MCP repository from release-candidate state to a
fully evidenced release-ready state. Do not publish until every precondition is
green.

TARGET=/Users/15x/Downloads/WORKING/addons-me/plaky115-python
SOURCE=/Users/15x/Downloads/WORKING/addons-me/plaky115
PINNED_SOURCE_SHA=33ae2926aa696f36d9663d44f914d42d9aadc53f

1. Require TARGET to be the current clean worktree and SOURCE to remain clean at
   PINNED_SOURCE_SHA. Confirm version, branch, tag, and release policy.
2. Record which separate current-task authorizations exist for live writes,
   remote create/push/PR, the exact tag/commit, and the exact
   registry/distribution/version/artifact digest. Environment variables,
   credentials, and workflow configuration are interlocks, not authorization.
3. Run the full offline verification, secret scan, and dependency audit.
4. Build wheel and sdist once, record SHA-256 digests, run twine check, and
   audit archive contents. Do not rebuild after this point.
5. In fresh environments outside the source tree, install the exact base wheel
   and the same wheel with MCP extra. Prove sync/async SDK use, MCP console help
   and startup, both installed py.typed markers, strict consumer Pyright, and
   separate pyright --verifytypes checks for plaky115 and plaky115_mcp.
6. Prove both archives retain SOURCE/LICENSE verbatim, installed distribution
   metadata and instructions are correct, no local sandbox link is presented as
   an install URL, and required surfaces reproduce the full pinned-source
   unofficial/non-affiliation/non-endorsement/trademark notice.
7. Run the exact MCP matrix: protocol 2026-07-28 in-memory, real stdio, and
   stateless Streamable HTTP with progress and working cancellation; protocol
   2025-11-25 over stdio and HTTP with its legacy stateless HTTP cancellation
   limitation tested and documented. Prove MCPServer, stateless_http=True,
   json_response=False, request-scoped text/event-stream, concurrent isolation,
   no deprecated standalone SSE, the 128 KiB aggregate CallToolResult cap, and
   the 36 MiB HTTP body cap needed for a 25 MiB decoded upload.
8. Run the exact read-only live certification from Prompt A with an injected
   rotated key. Require all mandated operation/surface receipts and allow only
   the documented paired file SKIP_PREREQUISITE case.
9. Run the exact UUID-scoped write certification from Prompt A only with both
   separate current-task authorization and every sacrificial interlock. Require
   all 15 operations, seven curated mutations, and a successful all-page residue
   scan reporting tracked artifacts 0 and discovered leftovers 0.
10. Verify docs, examples, changelog, version compatibility, reproducibility,
    and release automation. It must publish the exact verified artifact digest
    with trusted publishing and provenance.
11. If any needed authority is absent, finish all safe local gates, write
    BLOCKED_EXTERNAL with the exact action and authorization needed, and stop
    before the action. Never infer one authority from another.
12. Only when separately authorized, create/configure the named remote, push or
    open the PR, create the exact tag at the verified commit, and publish the
    approved digest to the named registry/version. Respect each boundary
    independently.
13. After authorized publication, verify exact-version registry visibility,
    registry artifact digest, provenance/attestation, fresh installation of the
    published artifact, repository/commit/tag/workflow identity, and public MCP
    instructions. A tag or green workflow is not proof of publication.
14. Produce a concise release receipt with commands, outcomes, artifact hashes,
    source baseline, protocol rows, installed-typing proof, authorization state,
    and live cleanup counts—never payloads, credentials, or signed URLs.

If any step fails, repair the code/config/tests and restart from the earliest
invalidated gate. Do not waive failures. Do not publish a rebuilt or different
artifact.
```

### Prompt G — Handoff to another model

```text
Prepare a lossless engineering handoff, then continue working until forced to
stop.

Update IMPLEMENTATION_STATE.md with:
- pinned source SHA;
- exact TARGET and read-only SOURCE paths;
- branch and HEAD;
- clean/dirty status;
- current phase;
- exact completed port-matrix rows;
- exact unverified rows;
- last green commands;
- current failing command and full concise failure;
- uncommitted files and why;
- exact modern/legacy MCP matrix rows and their receipts;
- aggregate-result/body-cap, installed-wheel typing, license/non-affiliation,
  and package-consumer receipts;
- exact live-read operation/surface coverage, live-write coverage, skip reasons,
  cleanup counts, and current authorization state without secrets;
- next exact file/test/action;
- external blockers only, labeled BLOCKED_EXTERNAL.

Update PORT_MATRIX.md and DECISIONS.md. Commit safe green work. Do not mark
partially implemented rows verified.

The next model must be able to begin with Prompt B and no chat history.
After writing the handoff, continue the next safe action rather than stopping
voluntarily.

Do not cross a live-write, remote create/push/PR, tag, or publication boundary
without separate current-task authorization. Credentials and interlock variables
do not grant it. If only an unauthorized external action remains, record its
exact required authorization and stop immediately before it.
```
