
# Plaky115 Python SDK + MCP 2026 — Implementation Plan

**Document date:** 2026-08-13  
**Source repository:** `https://github.com/apet97/plaky115`  
**Pinned source baseline:** `33ae2926aa696f36d9663d44f914d42d9aadc53f`  
**Source release state:** annotated tag and published GitHub/npm release `v1.0.11` at the pinned SHA (published 2026-08-11)  
**Protocol target:** Model Context Protocol specification `2026-07-28`  
**MCP implementation target:** official Python MCP SDK `mcp` v2, pinned as `mcp>=2,<3` and locked exactly in `uv.lock`  
**Target repository name:** `plaky115-python`  
**Handoff directory:** `/Users/15x/Downloads/WORKING/addons-me/PlakyPythonMCPSDK`  
**Read-only source checkout:** `/Users/15x/Downloads/WORKING/addons-me/plaky115`  
**Exact target path:** `/Users/15x/Downloads/WORKING/addons-me/plaky115-python`  
**Implementation executor:** Codex, using the canonical Prompt A/standalone master kickoff  
**Preferred Python distribution name:** `plaky115` (PyPI JSON returned 404 on 2026-08-13; recheck immediately before an authorized first publication because 404 does not reserve the name)  

---

## 1. Mission

Create a new, clean Python repository that provides:

1. A production-quality Plaky Python SDK.
2. A production-quality Plaky MCP server built on the official 2026 MCP Python stack.
3. Exact raw coverage for every currently documented Plaky public operation.
4. Behavioral parity with the useful public SDK, workflow, safety, error, pagination, upload, and MCP behavior in the pinned Plaky115 source.
5. A smaller and more understandable implementation than a line-for-line translation.
6. Deterministic contract generation, objective parity checks, package smoke tests, and live certification.

“Port everything and every function” means **port every observable public behavior that belongs to the SDK or MCP product**, not every private TypeScript function or every Node/Go build detail. The Go CLI itself is not part of this repository. Any CLI-only behavior that defines SDK/MCP correctness—query serialization, dry-run shape, CSV safety, cleanup discipline, mutation receipts, or contract metadata—must still be carried over.

The source snapshot attached to the planning session described an earlier 20-operation state. The implementation must use the pinned current source commit above, which exposes 32 operations, nine SDK resources, seven curated MCP tools, and eleven curated workflows. The source README and changelog contain older historical version strings, so release identity comes from the pinned commit, annotated tag, package manifests, registries, and contract inventories—not those stale examples.

### 1.1 Literal bootstrap boundary

The autonomous executor must start from the handoff directory above. Before creating anything, it must verify that the source checkout is clean and that `HEAD` equals the pinned SHA. It must not fetch, switch, reset, clean, or edit the source checkout. It must stop if the exact target path already exists; it must never merge this plan into an unknown or pre-existing directory.

If those checks pass, the executor may initialize the exact target as a local `main` repository and copy:

- `plaky115-python-implementation-plan.md` to `IMPLEMENTATION_PLAN.md`;
- `plaky115-python-autonomous-prompts.md` to `AUTONOMOUS_PROMPTS.md`.

Run this literal bootstrap once; any failed assertion is a stop condition:

```bash
set -euo pipefail
HANDOFF=/Users/15x/Downloads/WORKING/addons-me/PlakyPythonMCPSDK
SOURCE=/Users/15x/Downloads/WORKING/addons-me/plaky115
TARGET=/Users/15x/Downloads/WORKING/addons-me/plaky115-python
PINNED_SHA=33ae2926aa696f36d9663d44f914d42d9aadc53f

test -d "$HANDOFF"
test -d "$SOURCE/.git"
test "$(git -C "$SOURCE" rev-parse HEAD)" = "$PINNED_SHA"
test -z "$(git -C "$SOURCE" status --porcelain=v1 --untracked-files=all)"
test ! -e "$TARGET"
mkdir "$TARGET"
git -C "$TARGET" init -b main
cp "$HANDOFF/plaky115-python-implementation-plan.md" "$TARGET/IMPLEMENTATION_PLAN.md"
cp "$HANDOFF/plaky115-python-autonomous-prompts.md" "$TARGET/AUTONOMOUS_PROMPTS.md"
```

Repository creation and local coherent commits are within the implementation workflow. Live Plaky mutations, remote repository creation, push/PR actions, tag creation, and PyPI publication are separate authority boundaries defined in section 3.8.

---

## 2. Perfect end state

The project is complete only when all of the following are proven:

- The contract inventory contains exactly the 32 pinned operations, with no missing, duplicate, stale, or extra operation.
- Both `AsyncPlakyClient` and `PlakyClient` expose every required resource method.
- The SDK preserves the current wire behavior: authentication, query encoding, request bodies, response roots, response models, error classification, GET-only retries, timeouts, cancellation, response limits, and explicit idempotency headers.
- Every list endpoint has the correct page or bare-array normalization behavior.
- All current field helpers, resolver helpers, bounded chunk helpers, mutation-plan helpers, and higher-level workflows have Python counterparts.
- The MCP server exposes exactly 32 raw tools in generated mode.
- The MCP server exposes the seven curated tools and eleven workflow IDs listed in this document.
- Tool names, workflow IDs, MCP argument names, scope requirements, annotations, error-envelope field names, and structured result shapes remain wire-compatible with the current Plaky115 MCP surface.
- The default MCP startup policy is `curated` mode plus `read` scope.
- Stdio works for local hosts.
- Stateless Streamable HTTP works for deployment.
- No server implements the deprecated standalone `sse`/HTTP+SSE transport or its legacy endpoint pair. Streamable HTTP uses request-scoped `text/event-stream` responses when progress or cancellation is active.
- Every tool result has validated structured content; known failures return a structured tool error rather than crashing the protocol connection.
- Write operations are never automatically retried, even when an idempotency key is present.
- Mutation failures preserve whether a request was attempted and whether it may have committed.
- MCP file uploads accept canonical base64 plus metadata and never accept arbitrary local filesystem paths.
- Signed download URLs are treated as sensitive output and are never logged.
- All generated files are deterministic and drift-checked.
- The wheel and source distribution install in clean environments; SDK-only installation does not require MCP dependencies.
- Both installed namespaces ship `py.typed`, and an external strict-Pyright consumer proves the installed wheel rather than the source tree.
- The MCP extra installs and starts successfully from the built wheel.
- Offline verification is green on supported Python versions.
- A read-only live sweep is green.
- An explicitly enabled sacrificial write sweep creates, observes, and removes every test artifact, and proves zero residue.
- Documentation is runnable and matches the shipped API.
- The upstream MIT copyright/permission notice is retained, and the README, distribution metadata, security documentation, and MCP server instructions reproduce the pinned source's full unofficial/non-affiliation/non-endorsement/trademark notice.
- The worktree is clean and the release artifact is reproducible from the tag.

No TODO count, model confidence statement, or “tests passed on my machine” claim substitutes for these gates.

---

## 3. Architectural decisions

### 3.1 One repository, one release train, one wheel

Use one repository and one Python distribution:

```text
pip install plaky115          # SDK only
pip install "plaky115[mcp]"   # SDK + MCP server
```

The wheel contains two import namespaces:

```python
import plaky115
import plaky115_mcp
```

The base package must not import `mcp`. The MCP namespace requires the optional extra and raises a clear installation error naming `pip install "plaky115[mcp]"` when imported without it.

Expose one console script:

```text
plaky115-mcp = plaky115_mcp.cli:main
```

Do not create two independently versioned Python packages unless real users later require independent release cadence. Two release trains now would add synchronization, packaging, provenance, and dependency complexity without product value.

### 3.2 Python support

- Minimum: Python 3.11.
- CI: Python 3.11, 3.12, 3.13, and 3.14.
- Use modern standard-library typing and `tomllib`.
- Do not maintain Python 3.10 compatibility merely because the MCP SDK supports it; this is a new 2026 project and 3.11 materially simplifies typing and runtime support.

### 3.3 Async-first, with a real sync client

The canonical implementation is `AsyncPlakyClient`, because MCP handlers are asynchronous.

Also ship `PlakyClient` for ordinary scripts and applications. The sync client must use a real synchronous HTTP client. It must **not** call `asyncio.run`, start a private event loop, or bridge into the async client.

Share only pure logic:

- option validation;
- ID and path normalization;
- query serialization;
- request-body construction;
- response parsing;
- error classification;
- retry policy;
- model validation;
- mutation-plan normalization.

Keep sync and async network executors small and explicit. Avoid a clever generic abstraction that returns “value or awaitable.”

### 3.4 Hand-written public SDK; generated contract surfaces only

Generate:

- Pydantic schema models;
- operation descriptors;
- raw MCP input/output models;
- one raw MCP tool module per operation;
- raw tool registry;
- documentation index;
- parity inventory.

Hand-write:

- clients;
- resources;
- transport;
- pagination and chunks;
- field helpers;
- resolvers;
- workflows;
- curated MCP tools;
- mutation state;
- compaction and error presentation.

Do not expose a generated path-oriented API as the primary SDK. The stable user surface remains resource-oriented and readable.

### 3.5 No runtime code generation

All generation happens in development and CI. Generated Python is committed. Package import must not parse OpenAPI, build models dynamically, access GitHub, or write files.

### 3.6 Boring dependency policy

Base runtime dependencies:

```toml
dependencies = [
  "httpx2>=2.5,<3",
  "pydantic>=2.12,<3",
  "typing-extensions>=4.13",
]
```

MCP extra:

```toml
mcp = [
  "mcp>=2,<3",
]
```

Development dependencies are:

- `pytest`
- `anyio` (its built-in pytest plugin supplies async test support; do not add the `pytest-anyio` placeholder package)
- `coverage`
- `ruff`
- `pyright`
- `build`
- `twine`
- `pip-audit`
- `PyYAML`
- `jsonschema`
- `openapi-spec-validator>=0.9,<1`
- `datamodel-code-generator`, pinned exactly

`scripts/contract.py` validates OpenAPI 3.1 with `openapi-spec-validator`, validates project metadata with `jsonschema`, then resolves every reference; do not add a second overlapping OpenAPI validator.

Do not add Tenacity, a dependency-injection framework, a task runner, Rich, a cache, a database, a plugin framework, or an alternate JSON library without a demonstrated requirement.

### 3.7 MCP 2026 policy

Use `from mcp.server import MCPServer`.

- Local default: stdio.
- Deployed transport: stateless Streamable HTTP.
- Build no deprecated standalone `sse`/HTTP+SSE transport or endpoint pair. Request-scoped `text/event-stream` is part of Streamable HTTP and is required when progress or cancellation is used.
- Use `streamable_http_app(stateless_http=True, json_response=False, ...)`; JSON-only responses are incompatible with the required progress behavior.
- Do not add session state.
- Do not add resources or prompts merely to exercise MCP features.
- Do not use deprecated roots, sampling, or protocol logging.
- Use standard Python logging to stderr.
- Use the SDK’s structured output validation and in-memory `Client(server)` testing.
- Do not claim tasks support until the official SDK exposes a stable tasks extension.
- Multi-round-trip resolution is not required for parity. Do not add interactive confirmations to raw tools in the first release; preserve scope gating and destructive annotations. Revisit only as a separately designed feature.

### 3.8 Execution authority and stop rules

Environment variables, confirmation strings, sacrificial IDs, and dry-run flags are safety interlocks; they are not authorization. The executor must have separate, current-task authorization before each of these classes of action:

1. Live Plaky writes: authorization must name the sacrificial space/board, allowed operation set, mutation budget, cleanup boundary, and archive permission.
2. Remote repository creation, pushing, or opening a PR: authorization must name the remote owner/repository and allowed branch.
3. Creating or moving a Git tag: authorization must name the exact version and commit.
4. TestPyPI or PyPI publication: authorization must name the registry, distribution, exact version, and approved artifact digest.

Without the relevant authorization, complete every safe local phase, record `BLOCKED_EXTERNAL` with the exact remaining action and evidence, and stop before that action. Never infer one authority from another, and never infer authority from credentials merely being present.

---

## 4. Scope boundaries

### In scope

- Every SDK and MCP behavior in the pinned current Plaky115 source.
- All 32 operations.
- Nine resource groups.
- Sync and async clients.
- Typed Pydantic request/response models.
- Low-level request escape hatch.
- Typed errors and normalized problem details.
- Pagination and bare-array normalization.
- Bounded chunks and exact continuation cursors.
- Explicit idempotency headers.
- GET-only retry policy.
- Rate-limit observation and estimation.
- Upload validation and hashing.
- Dry-run mutation plans.
- Durable mutation receipts and ambiguous-outcome handling.
- Field builders.
- Entity resolvers.
- Workspace, search, bulk-update, export, and chunk workflows.
- Seven curated MCP tools.
- Eleven curated MCP workflow IDs.
- Generated raw MCP tools.
- Stdio and stateless Streamable HTTP.
- Contract evolution workflow.
- Offline, package, protocol, and live gates.
- Documentation and examples.
- PyPI-ready release automation.

### Out of scope

- Porting the Go CLI as a Python CLI.
- A database, queue, scheduler, webhook service, cache, or background worker.
- A hosted multi-tenant credential broker.
- Accepting Plaky API keys as tool arguments.
- Persisting API keys, signed URLs, or workspace payloads.
- Local-path file access through MCP.
- A general OpenAPI generator framework.
- A general MCP plugin system.
- A web UI.
- MCP Apps.
- New Plaky operations not present in the accepted contract.
- Automatic write retries.
- Automatic package publication before every release gate is green.
- Compatibility shims for undocumented private TypeScript imports.

---

## 5. Repository layout

```text
plaky115-python/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── live-read.yml
│   │   ├── live-write.yml
│   │   └── release.yml
│   └── dependabot.yml
├── contract/
│   ├── upstream.openapi.yaml
│   ├── operation-overrides.yaml
│   ├── schema-patches.yaml
│   ├── expected-operations.json
│   ├── source-manifest.json
│   ├── candidate/
│   │   └── .gitkeep
│   └── generated/
│       ├── plaky.openapi.json
│       ├── operations.json
│       └── docs-index.json
├── docs/
│   ├── api-behavior.md
│   ├── architecture.md
│   ├── codegen.md
│   ├── compatibility-inventory.md
│   ├── contract-evolution.md
│   ├── live-certification.md
│   ├── mcp.md
│   ├── release.md
│   ├── security.md
│   └── sdk.md
├── examples/
│   ├── async_sdk.py
│   ├── sync_sdk.py
│   ├── fields_and_create.py
│   ├── pagination.py
│   ├── error_handling.py
│   ├── mcp_stdio.json
│   └── mcp_http.md
├── scripts/
│   ├── contract.py
│   ├── generate.py
│   ├── parity.py
│   ├── package_smoke.py
│   ├── secret_scan.py
│   ├── live_read.py
│   ├── live_write.py
│   └── verify.py
├── src/
│   ├── plaky115/
│   │   ├── __init__.py
│   │   ├── _version.py
│   │   ├── py.typed
│   │   ├── client.py
│   │   ├── async_client.py
│   │   ├── config.py
│   │   ├── ids.py
│   │   ├── errors.py
│   │   ├── http.py
│   │   ├── idempotency.py
│   │   ├── pagination.py
│   │   ├── user_agent.py
│   │   ├── fields.py
│   │   ├── resolvers.py
│   │   ├── resources/
│   │   │   ├── _common.py
│   │   │   ├── spaces.py
│   │   │   ├── boards.py
│   │   │   ├── items.py
│   │   │   ├── comments.py
│   │   │   ├── reactions.py
│   │   │   ├── users.py
│   │   │   ├── teams.py
│   │   │   ├── item_groups.py
│   │   │   └── item_files.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── compatibility.py
│   │   │   └── generated.py
│   │   ├── runtime/
│   │   │   ├── transport.py
│   │   │   ├── async_transport.py
│   │   │   ├── request_builders.py
│   │   │   ├── responses.py
│   │   │   ├── retry_policy.py
│   │   │   ├── chunks.py
│   │   │   ├── rate_limit.py
│   │   │   ├── redaction.py
│   │   │   ├── upload.py
│   │   │   └── mutations.py
│   │   └── workflows/
│   │       ├── __init__.py
│   │       ├── workspace.py
│   │       ├── search.py
│   │       ├── bulk.py
│   │       ├── export.py
│   │       ├── csv.py
│   │       └── mutation_plans.py
│   └── plaky115_mcp/
│       ├── __init__.py
│       ├── py.typed
│       ├── cli.py
│       ├── config.py
│       ├── server.py
│       ├── registry.py
│       ├── scopes.py
│       ├── errors.py
│       ├── compaction.py
│       ├── attempts.py
│       ├── docs_index.py
│       ├── tools/
│       │   ├── raw/
│       │   │   ├── __init__.py
│       │   │   └── generated_*.py
│       │   └── curated/
│       │       ├── search_docs.py
│       │       ├── workspace_context.py
│       │       ├── find.py
│       │       ├── plan_mutation.py
│       │       ├── execute_workflow.py
│       │       ├── execute_read_workflow.py
│       │       ├── execute_mutation_workflow.py
│       │       ├── workflow_models.py
│       │       └── workflow_registry.py
│       └── transport/
│           ├── stdio.py
│           └── http.py
├── tests/
│   ├── contract/
│   ├── sdk/
│   ├── mcp/
│   ├── parity/
│   ├── package/
│   └── fixtures/
├── AGENTS.md
├── AUTONOMOUS_PROMPTS.md
├── BLOCKERS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── DECISIONS.md
├── IMPLEMENTATION_PLAN.md
├── IMPLEMENTATION_STATE.md
├── LICENSE
├── PORT_MATRIX.md
├── README.md
├── SECURITY.md
├── pyproject.toml
└── uv.lock
```

This is a target map, not permission to create empty architecture. Add a module only when its first real responsibility is implemented. Merge tiny modules when separation does not improve ownership or testing.

---

## 6. Public SDK design

### 6.1 Basic usage

Async:

```python
from plaky115 import AsyncPlakyClient

async with AsyncPlakyClient(api_key="...") as plaky:
    page = await plaky.spaces.list(page_size=50)
    for space in page.data:
        print(space.id, space.title)
```

Sync:

```python
from plaky115 import PlakyClient

with PlakyClient(api_key="...") as plaky:
    for space in plaky.spaces.iterate(page_size=100):
        print(space.id, space.title)
```

### 6.2 Client options

Both clients support:

- `api_key`: literal string or same-mode provider.
- `server_url`: default `https://api.plaky.com`.
- `timeout`: default 30 seconds.
- `max_retries`: default 2, applied only to GET attempts.
- `max_response_bytes`: default 16 MiB; hard maximum 64 MiB.
- default headers or a same-mode header provider.
- same-mode request and response hooks.
- custom user-agent suffix.
- injected `httpx2.Client`, `httpx2.AsyncClient`, or transport for tests/proxies.
- `with_options(...)`, returning a new client.
- explicit `close()`/`aclose()` plus context-manager support.
- low-level `request(...)` and `request_with_response(...)`.

Rules:

- `PlakyClient` accepts only synchronous providers/hooks: `Callable[[], str]`, `Callable[[], Mapping[str, str]]`, and synchronous request/response callables.
- `AsyncPlakyClient` accepts only asynchronous providers/hooks: `Callable[[], Awaitable[str]]`, `Callable[[], Awaitable[Mapping[str, str]]]`, and asynchronous request/response callables. It may also accept literal strings/mappings; it never silently awaits a sync callback.
- A provider/hook passed to the wrong client fails at configuration or first invocation with a precise type/usage error; no event-loop bridge is allowed.
- A literal API key must be nonblank.
- API keys are sent only in `X-API-Key`.
- User-provided headers may not silently remove or replace authentication unless the API explicitly supports it.
- The base URL must be absolute HTTPS, except loopback HTTP for local tests.
- Reject credentials, query, and fragment in `server_url`.
- Normalize trailing slashes.
- A request hook may rewrite path/query/headers but must not change the trusted origin.
- Redirects are not followed automatically.
- Stdio output must never contain logs.

### 6.3 Python naming versus wire naming

Python SDK attributes and keyword arguments use `snake_case`:

```python
await client.items.get(
    space_id=123,
    board_id=456,
    item_id=789,
    expand=["fields"],
)
```

HTTP and MCP wire names remain Plaky-compatible camelCase:

```json
{
  "spaceId": "123",
  "boardId": "456",
  "itemId": "789",
  "pageSize": 50
}
```

Pydantic models use aliases. Model dumps sent over HTTP or MCP must use `by_alias=True`.

### 6.4 IDs

Expose:

- `SpaceId`
- `BoardId`
- `ItemId`
- `CommentId`
- `FieldKey`
- `UserId`
- `TeamId`
- `ItemGroupId`
- `ItemFileId`
- `FolderId`
- `as_space_id`, `as_board_id`, and corresponding helpers

At public boundaries accept `int | str | branded NewType`.

Canonicalization rules:

- Reject `bool`.
- Integer must be nonnegative.
- String must be canonical decimal: `0` or a nonzero digit followed by digits.
- Reject signs, whitespace, exponent notation, leading zeroes other than `0`, decimal points, and empty strings.
- Reject values above signed int64 maximum `9223372036854775807`.
- Normalize internal IDs to strings.
- Percent-encode every path segment.
- Field keys use ordinary string path encoding, not int64 validation.

### 6.5 Models

Use Pydantic v2.

Generated API models:

- preserve OpenAPI field aliases;
- expose Pythonic snake-case attributes;
- use `extra="allow"` on response models so additive server fields do not break clients;
- use `extra="forbid"` on stable request models;
- use explicit open maps only where Plaky field values are intentionally dynamic;
- avoid recursive eager validation that makes large item trees unusable;
- retain raw unknown fields through model extras;
- serialize deterministically with aliases and omitted `None` where appropriate.

Hand-written models:

- `Page[T]`
- `ApiResponse[T]`
- `RequestOptions`
- `DryRunPlan`
- `PageCursor`
- `BoundedChunk[T]`
- `MutationReceipt`
- `NormalizedProblem`
- `NormalizedMutationPlan`
- `NormalizedUpload`
- MCP error and compact result models

Compatibility behavior:

- `Comment.content` is the API response field.
- A deprecated `Comment.text` read-only compatibility property returns `content` exactly and has no setter.
- Relationship fields remain unions of IDs and expanded models.
- Deprecated TypeScript-only alias fields should be mapped only when they have observable user value; do not reproduce dead type artifacts as mutable duplicate storage.
- `field_label()` prefers `name`, then `title`.

### 6.6 Query serialization

Implement from operation metadata, not ad hoc endpoint code.

- `expand` arrays: comma-joined because the contract declares `explode: false`.
- `emails`: repeated query keys.
- Scalar values: one value.
- Dates: ISO 8601.
- `None`: omitted.
- Empty arrays: omitted.
- Booleans: lowercase `true`/`false`.
- Page numbers are 1-based.
- `page_size` must be positive.
- Do not invent `limit` or `offset` HTTP parameters. SDK iterator `limit` is client-side only.

---

## 7. Required resource surface


| Resource | Required public methods | Behavior that must not be lost |
| --- | --- | --- |
| `spaces` | `list`, `get`, `iterate`, `list_all` | Page validation; `expand=['board']`. |
| `boards` | `list`, `get`, `iterate`, `list_all` | Always scoped by `space_id`. |
| `items` | `list`, `get`, `list_subitems`, `create`, `update_field`, `update_fields`, `delete`, `iterate`, `list_all` | Seven exact expand values; dry-run for create/update-fields; writes single-attempt. |
| `comments` | `list`, `create`, `update`, `delete`, `iterate`, `list_all` | API list root is a bare array; normalize to `Page` with `has_more=False`. |
| `reactions` | `replace` | Reaction value is Unicode codepoint hex such as `1f44d`. |
| `users` | `list`, `me`, `iterate`, `list_all` | Email array uses repeated query keys; status/type enums. |
| `teams` | `list`, `get`, `iterate`, `list_all` | Direct GET for exact IDs. |
| `item_groups` | `list`, `get`, `create`, `update`, `delete`, `archive`, `iterate`, `list_all` | Archive is destructive because the public API has no unarchive operation. |
| `item_files` | `list`, `upload`, `get`, `get_download`, `update`, `delete` | Multipart upload in SDK; signed download URL is sensitive; list root is a bare array. |


### 7.1 Operation parity matrix


| # | Operation | HTTP path | Python SDK | Raw MCP tool | Return | Scope | Safety |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `listSpaces` | `GET /v1/public/spaces` | `client.spaces.list(...)` | `plaky_list_spaces` | `Page[Space]` | read | read-only; idempotent |
| 2 | `getSpace` | `GET /v1/public/spaces/{spaceId}` | `client.spaces.get(...)` | `plaky_get_space` | `Space` | read | read-only; idempotent |
| 3 | `listBoards` | `GET /v1/public/spaces/{spaceId}/boards` | `client.boards.list(...)` | `plaky_list_boards` | `Page[Board]` | read | read-only; idempotent |
| 4 | `getBoard` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}` | `client.boards.get(...)` | `plaky_get_board` | `Board` | read | read-only; idempotent |
| 5 | `listItems` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items` | `client.items.list(...)` | `plaky_list_items` | `Page[Item]` | read | read-only; idempotent |
| 6 | `createItem` | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/items` | `client.items.create(...)` | `plaky_create_item` | `Item / DryRunPlan` | write | mutation; non-idempotent |
| 7 | `listSubitems` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/sub-items` | `client.items.list_subitems(...)` | `plaky_list_subitems` | `Page[Item]` | read | read-only; idempotent |
| 8 | `getItem` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}` | `client.items.get(...)` | `plaky_get_item` | `Item` | read | read-only; idempotent |
| 9 | `deleteItem` | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}` | `client.items.delete(...)` | `plaky_delete_item` | `None / {ok:true}` | write + destructive | destructive; idempotent semantic |
| 10 | `updateItemField` | `PATCH /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/fields/{itemFieldKey}` | `client.items.update_field(...)` | `plaky_update_item_field` | `Item` | write | mutation; idempotent semantic |
| 11 | `updateItemFields` | `PATCH /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/fields` | `client.items.update_fields(...)` | `plaky_update_item_fields` | `Item / DryRunPlan` | write | mutation; idempotent semantic |
| 12 | `listItemComments` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments` | `client.comments.list(...)` | `plaky_list_item_comments` | `Page[Comment] (normalized)` | read | read-only; idempotent |
| 13 | `createItemComment` | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments` | `client.comments.create(...)` | `plaky_create_item_comment` | `Comment` | write | mutation; non-idempotent |
| 14 | `updateItemComment` | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}` | `client.comments.update(...)` | `plaky_update_item_comment` | `Comment` | write | mutation; idempotent semantic |
| 15 | `deleteItemComment` | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}` | `client.comments.delete(...)` | `plaky_delete_item_comment` | `None / {ok:true}` | write + destructive | destructive; idempotent semantic |
| 16 | `replaceCommentReactions` | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}/reactions` | `client.reactions.replace(...)` | `plaky_replace_comment_reactions` | `ReactionReplaceResult` | write | mutation; idempotent semantic |
| 17 | `listUsers` | `GET /v1/public/users` | `client.users.list(...)` | `plaky_list_users` | `Page[User]` | read | read-only; idempotent |
| 18 | `getCurrentUser` | `GET /v1/public/users/me` | `client.users.me(...)` | `plaky_get_current_user` | `User` | read | read-only; idempotent |
| 19 | `listTeams` | `GET /v1/public/teams` | `client.teams.list(...)` | `plaky_list_teams` | `Page[Team]` | read | read-only; idempotent |
| 20 | `getTeam` | `GET /v1/public/teams/{teamId}` | `client.teams.get(...)` | `plaky_get_team` | `Team` | read | read-only; idempotent |
| 21 | `listItemGroups` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups` | `client.item_groups.list(...)` | `plaky_list_item_groups` | `Page[ItemGroup]` | read | read-only; idempotent |
| 22 | `getItemGroup` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}` | `client.item_groups.get(...)` | `plaky_get_item_group` | `ItemGroup` | read | read-only; idempotent |
| 23 | `createItemGroup` | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups` | `client.item_groups.create(...)` | `plaky_create_item_group` | `ItemGroup` | write | mutation; non-idempotent |
| 24 | `updateItemGroup` | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}` | `client.item_groups.update(...)` | `plaky_update_item_group` | `ItemGroup` | write | mutation; idempotent semantic |
| 25 | `deleteItemGroup` | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}` | `client.item_groups.delete(...)` | `plaky_delete_item_group` | `None / {ok:true}` | write + destructive | destructive; idempotent semantic |
| 26 | `archiveItemGroup` | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}/archive` | `client.item_groups.archive(...)` | `plaky_archive_item_group` | `None / {ok:true}` | write + destructive | irreversible via public API; destructive |
| 27 | `uploadItemFile` | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files` | `client.item_files.upload(...)` | `plaky_upload_item_file` | `ItemFile` | write | mutation; non-idempotent; bounded upload |
| 28 | `listItemFiles` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files` | `client.item_files.list(...)` | `plaky_list_item_files` | `list[ItemFile]` | read | read-only; idempotent |
| 29 | `getItemFile` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}` | `client.item_files.get(...)` | `plaky_get_item_file` | `ItemFile` | read | read-only; idempotent |
| 30 | `getItemFileDownload` | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}/download` | `client.item_files.get_download(...)` | `plaky_get_item_file_download` | `ItemFileDownload` | read | read-only; sensitive output |
| 31 | `updateItemFile` | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}` | `client.item_files.update(...)` | `plaky_update_item_file` | `ItemFile` | write | mutation; idempotent semantic |
| 32 | `deleteItemFile` | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}` | `client.item_files.delete(...)` | `plaky_delete_item_file` | `None / {ok:true}` | write + destructive | destructive; idempotent semantic |


### 7.2 Request-body map

| Operation | Python request type | Non-negotiable detail |
| --- | --- | --- |
| `createItem` | `ItemCreateRequest` | title required; optional group/parent/fields/subscriptions as defined by accepted OpenAPI. |
| `updateItemField` | `FieldValueChangeRequest` | strict `{value: ...}` envelope; value remains field-type-specific. |
| `updateItemFields` | `ItemFieldsUpdateRequest`, a Pydantic `RootModel[dict[str, Any]]` | map keyed by field key or title; do not wrap in an extra `fields` object. |
| `createItemComment` | `CommentRequest` | `text` required; optional `repliesToId`. |
| `updateItemComment` | `CommentRequest` | `text` request field; response uses `content`. |
| `replaceCommentReactions` | `ReactionPutRequest` | `reactions: [{value: codepoint_hex}]`; empty array clears caller reactions. |
| `createItemGroup` | `ItemGroupCreateRequest` | schema-derived strict request. |
| `updateItemGroup` | `ItemGroupUpdateRequest` | schema-derived strict request. |
| `uploadItemFile` | SDK binary input / MCP `Base64UploadInput` | multipart field name `file`; bounded validation before allocation. |
| `updateItemFile` | `ItemFileUpdateRequest` | schema-derived metadata update. |

### 7.3 Exact public enums

| Enum | Exact accepted values |
| --- | --- |
| `SpaceExpand` | `board` |
| `ItemExpand` | `space`, `board`, `group`, `createdBy`, `parent`, `subscriptions`, `fields` |
| `SubitemsBehaviour` | `INCLUDE`, `EXCLUDE`, `EMBED` |
| `UserStatus` | `ACTIVE`, `PENDING`, `INACTIVE` |
| `UserType` | `OWNER`, `ADMIN`, `MEMBER`, `VIEWER` |

### 7.4 Operation implementation rule

For every operation, the implementation must have:

1. One accepted contract descriptor.
2. One generated raw MCP tool.
3. One SDK resource method where the operation belongs to the public SDK.
4. A unit test asserting HTTP method, escaped path, query encoding, body encoding, response root, output model, and operation ID.
5. A parity test asserting the descriptor, SDK mapping, raw tool name, scopes, and annotations agree.
6. A mock-transport error test.
7. A live-read or opt-in live-write classification.
8. Documentation generated or linked from the operation index.

No operation may be “covered” through only the low-level request escape hatch.

---

## 8. Runtime and helper parity


| Area | Required Python surface |
| --- | --- |
| Clients | `PlakyClient`, `AsyncPlakyClient`, `DEFAULT_SERVER_URL`, immutable client/request option models, `with_options`, raw request and response-envelope methods. |
| Errors | `PlakyError`, connection, timeout, cancellation/abort, decode, response-contract, response-too-large, API status subclasses, ambiguous-match, output/materialization-limit, upload-validation, partial-mutation. |
| IDs | `SpaceId`, `BoardId`, `ItemId`, `CommentId`, `FieldKey`, `UserId`, `TeamId`, `ItemGroupId`, `ItemFileId`, `FolderId`, plus `as_*` canonicalizers. |
| Pagination | `Page`, sync/async iterators, `first_page`, `pages`, `to_list`, max-page guard, strict root validation. |
| Chunks | `PageCursor`, `BoundedChunk`, `read_paged_chunk`, `iterate_paged_chunks`, UTF-8 byte measurement, output/materialization limits. |
| Retries | `new_idempotency_key`, `with_retries`, `RetryPolicy`; transport retries remain GET-only. |
| Rate limits | `RateLimitTracker` with observed headers and local rolling-window estimate. |
| Hooks | Sync/async request and response hooks; hook URL changes restricted to the configured origin. |
| Redaction | `redact`, `redact_value`, safe URL presentation, bounded messages, no API keys or signed URLs in logs. |
| Uploads | Filename/media-type/base64 validation, decoded-size estimate, decode, SHA-256 normalization, 25 MiB hard ceiling. |
| Fields | `field_values`, `omit_none`, `string_field`, `status_field`, `tag_field`, `person_field`, `timeline_field`, `link_field`, `number_field`, `field_label`. |
| Resolvers | `resolve_space`, `resolve_board`, `resolve_space_and_board`, `resolve_user`, `resolve_team`, `resolve_item`, `resolve_items_in_board`, `resolve_item_group_in_board`, `resolve_item_file_on_item`. |
| Workflows | `workspace_map`, `search_items`, `search_items_detailed`, `bulk_update_items`, `export_items`, item chunk/export chunk readers and iterators, mutation-plan normalizers. |


### 8.1 Explicit public function/class map

| Current source export | Python target | Port requirement |
| --- | --- | --- |
| `PlakyClient` | `PlakyClient` plus `AsyncPlakyClient` | Split sync/async without event-loop bridging. |
| `DEFAULT_SERVER_URL` | `DEFAULT_SERVER_URL` | Same default: `https://api.plaky.com`. |
| `classify` | `classify` in `plaky115.errors` | Public error classification function; preserve status/category mapping. |
| `normalizeProblem` | `normalize_problem` in `plaky115.errors` | Public normalization of Plaky, legacy, and problem-detail bodies. |
| `mergeHeadersInto` | `merge_headers_into` in `plaky115.http` | Case-insensitive deterministic header merge. |
| `resolveHeaders` | `resolve_headers` / `async_resolve_headers` in `plaky115.http` | Same-mode provider resolution; no event-loop bridging. |
| module `request` | `request` / `async_request` in `plaky115.http` | Public low-level request function over an injected same-mode client/transport. |
| module `requestWithResponse` | `request_with_response` / `async_request_with_response` in `plaky115.http` | Public response-envelope function with the same validation and redaction rules. |
| `newIdempotencyKey` | `new_idempotency_key` | Header helper only; does not enable write retries. |
| `resolveIdempotencyKey` | `resolve_idempotency_key` in `plaky115.idempotency` | Resolve explicit/provider key for permitted mutation request construction. |
| `resolveExplicitIdempotencyKey` | `resolve_explicit_idempotency_key` in `plaky115.idempotency` | Reject blank/invalid explicit keys; never enables retry. |
| `assertPagedResult` | `assert_paged_result` in `plaky115.pagination` | Strict `data` plus `hasMore` root validation. |
| `assertArrayResult` | `assert_array_result` in `plaky115.pagination` | Strict bare-array root validation. |
| `buildUserAgent` | `build_user_agent` in `plaky115.user_agent` | Stable package/version/platform value plus validated suffix. |
| `redact` | `redact` | Mask `plk_` values in strings. |
| `redactRecord` | `redact_value` | Recursive JSON-safe redaction. |
| `withRetries` | `with_retries` / `async_with_retries` | Document for explicitly retry-safe operations. |
| `RateLimitSink` | `RateLimitTracker` | Headers plus rolling-window estimate. |
| `paginate` | `paginate` / `async_paginate` | Strict page root and 10,000-page guard. |
| `iteratePagedChunks` | `iterate_paged_chunks` / `async_iterate_paged_chunks` | Exact cursor continuation. |
| `readPagedChunk` | `read_paged_chunk` / `async_read_paged_chunk` | Bounded item/byte result. |
| `utf8ByteLength` | `utf8_byte_length` | Use encoded byte count. |
| `validateUploadLimit` | `validate_upload_limit` | 1 byte through 25 MiB hard ceiling. |
| `validateUploadFileName` | `validate_upload_file_name` | UTF-8 and path/control checks. |
| `normalizeUploadMediaType` | `normalize_upload_media_type` | RFC-style media type normalization. |
| `normalizeUploadMetadata` | `normalize_upload_metadata` | Validate without decoding. |
| `decodeBase64Upload` | `decode_base64_upload` | Canonical base64 and size guard. |
| `normalizeUpload` | `normalize_upload` | Decode once and hash once. |
| `estimateBase64DecodedBytes` | `estimate_base64_decoded_bytes` | Preallocation size check. |
| `validateBlobUpload` | `validate_binary_upload` | Python bytes/file-like equivalent. |
| `fieldValues` | `field_values` | Open field-value map. |
| `omitUndefined` | `omit_none` | Remove absent optional values. |
| `stringField` | `string_field` | Identity with typing. |
| `statusField` | `status_field` | Label or ID. |
| `tagField` | `tag_field` | List of labels/IDs. |
| `personField` | `person_field` | Normalize user/team refs. |
| `timelineField` | `timeline_field` | Require start/end. |
| `linkField` | `link_field` | Require URL; preserve optional display text. |
| `numberField` | `number_field` | Finite numbers only. |
| `fieldLabel` | `field_label` | Prefer name, then title. |
| `resolveSpace` | `resolve_space` / `async_resolve_space` | Exact ID direct GET; text list lookup. |
| `resolveBoard` | `resolve_board` / `async_resolve_board` | Scoped lookup. |
| `resolveSpaceAndBoard` | `resolve_space_and_board` / async counterpart | Resolve space once. |
| `resolveUser` | `resolve_user` / async counterpart | ID/name/email semantics. |
| `resolveTeam` | `resolve_team` / async counterpart | Direct GET for ID. |
| `resolveItem` | `resolve_item` / async counterpart | Board-scoped. |
| `resolveItemsInBoard` | `resolve_items_in_board` / async counterpart | One list for mixed/text refs. |
| `resolveItemGroupInBoard` | `resolve_item_group_in_board` / async counterpart | Board-scoped. |
| `resolveItemFileOnItem` | `resolve_item_file_on_item` / async counterpart | Item-scoped. |
| `workspaceMap` | `workspace_map` / `async_workspace_map` | Bounded map. |
| `searchItems` | `search_items` / async counterpart | Compatibility materialized search. |
| `searchItemsDetailed` | `search_items_detailed` / async counterpart | Continuation-aware bounded search. |
| `bulkUpdateItems` | `bulk_update_items` / async counterpart | Receipts and ambiguous outcomes. |
| `exportItems` | `export_items` / async counterpart | JSONL/CSV. |
| `readItemChunk` | `read_item_chunk` / async counterpart | Bounded item chunk. |
| `iterateItemChunks` | `iterate_item_chunks` / async counterpart | Lazy chunks. |
| `readItemExportChunk` | `read_item_export_chunk` / async counterpart | Bounded export chunk. |
| `iterateItemExportChunks` | `iterate_item_export_chunks` / async counterpart | Lazy export chunks. |
| `normalizeBase64UploadPlan` | `normalize_base64_upload_plan` | MCP upload plan. |
| `normalizeBlobUploadPlan` | `normalize_binary_upload_plan` | SDK upload plan. |
| `normalizeCommentPlan` | `normalize_comment_plan` | Create/update comment body. |
| `normalizeItemCreatePlan` | `normalize_item_create_plan` | Create item plan. |
| `normalizeItemFileUpdatePlan` | `normalize_item_file_update_plan` | File metadata update. |
| `normalizeItemGroupCreatePlan` | `normalize_item_group_create_plan` | Group create. |
| `normalizeItemGroupUpdatePlan` | `normalize_item_group_update_plan` | Group update. |
| `normalizeItemUpdateFieldsPlan` | `normalize_item_update_fields_plan` | Multi-field update. |
| `SpaceId`, `BoardId`, `ItemId`, `CommentId`, `FieldKey`, `UserId`, `TeamId`, `ItemGroupId`, `ItemFileId`, `FolderId` | Same ten Python `NewType` callables | Preserve distinct public types/constructors; canonical signed-int64 decimal strings except `FieldKey`, which is an ordinary validated string. |
| `asSpaceId`, `asBoardId`, `asItemId`, `asCommentId`, `asFieldKey`, `asUserId`, `asTeamId`, `asItemGroupId`, `asItemFileId`, `asFolderId` | `as_space_id`, `as_board_id`, `as_item_id`, `as_comment_id`, `as_field_key`, `as_user_id`, `as_team_id`, `as_item_group_id`, `as_item_file_id`, `as_folder_id` | Export and test every literal helper name; do not satisfy this row with a wildcard claim. |
| `SpacesResource`, `BoardsResource`, `ItemsResource`, `ItemCommentsResource`, `ReactionsResource`, `UsersResource`, `TeamsResource`, `ItemGroupsResource`, `ItemFilesResource` | Same nine sync class names plus `AsyncSpacesResource`, `AsyncBoardsResource`, `AsyncItemsResource`, `AsyncItemCommentsResource`, `AsyncReactionsResource`, `AsyncUsersResource`, `AsyncTeamsResource`, `AsyncItemGroupsResource`, `AsyncItemFilesResource` | All 18 are root exports and are also reachable from their client attributes; this is required public compatibility, not optional. |
| Generated OpenAPI schema types | Generated Pydantic v2 models | Runtime validation plus alias-preserving serialization. |

### 8.2 Public response-model map

| Current source type | Python model | Required behavior |
| --- | --- | --- |
| `PagedResult<T>` / `StrictPagedResult<T>` | `Page[T]` | Root validation requires `data` and `hasMore`. |
| `FieldShape` | `Field` | Name/title compatibility; unknown config preserved. |
| `ItemFieldShape` | `ItemField` | Key/title/type/value. |
| `ItemGroupShape` | `ItemGroup` | ID/title/color/ranking plus additive extras. |
| `FolderShape` | `Folder` | Generated/additive response model. |
| `TeamShortShape` | `TeamShort` | Compact team relationship. |
| `ItemFileShape` | `ItemFile` | Metadata response. |
| `ItemFileDownloadShape` | `ItemFileDownload` | HTTPS URL and optional expiry. |
| `BoardShape` | `Board` | Fields/groups/defaults/space relationship. |
| `SpaceShape` | `Space` | Optional expanded boards. |
| `ShortUserShape` | `ShortUser` | ID/name/email/type. |
| `UserShape` | `User` | Photo/status/details plus additive extras. |
| `TeamShape` | `Team` | Members are IDs or compact users as observed. |
| `ReactionDetailShape` | `ReactionDetail` | User and timestamp. |
| `ReactionShape` | `Reaction` | Code and reacted users. |
| `CommentShape` | `Comment` | Response `content`; deprecated `text` compatibility property. |
| `ItemShape` | `Item` | ID/title/fields/relationships/subscriptions/subitems. |

### 8.3 Error hierarchy

Required Python classes:

```text
PlakyError
├── PlakyConnectionError
├── PlakyTimeoutError
├── PlakyCancelledError
│   └── compatibility alias: PlakyAbortError
├── PlakyDecodeError
│   └── PlakyResponseContractError
├── PlakyResponseTooLargeError
├── PlakyApiError
│   ├── PlakyAuthError                 # 401
│   ├── PlakyPermissionError           # 403
│   ├── PlakyNotFoundError             # 404
│   ├── PlakyConflictError             # 409
│   ├── PlakyValidationError           # 400
│   ├── PlakyUnprocessableEntityError  # 422
│   ├── PlakyRateLimitError            # 429
│   └── PlakyServerError               # 5xx
├── PlakyAmbiguousMatchError
├── PlakyOutputLimitError
│   └── PlakyMaterializationLimitError
├── UploadValidationError
└── PlakyPartialMutationError
```

`PlakyApiError` carries:

- `status`
- `method`
- redacted/safe URL
- bounded response headers
- bounded raw body
- normalized problem
- `request_id`
- `code`
- `retry_after_ms`

Normalize observed error families:

- Plaky validation envelope;
- legacy message/error envelope;
- RFC 7807-like envelope;
- unknown string/object.

Presentation messages are redacted, control-character-safe, and capped. Raw bounded bodies remain available to SDK callers but must not be included automatically in MCP text or logs.

### 8.4 Transport and retry policy

Use a small custom retry loop.

| Request/outcome | Retry? |
| --- | --- |
| GET connection failure | Yes, up to `max_retries` |
| GET timeout | Yes |
| GET 429 | Yes; honor bounded `Retry-After` |
| GET 5xx | Yes |
| GET decode failure after a response | No |
| GET response-hook failure | No |
| Any POST/PUT/PATCH/DELETE | No |
| Caller supplies idempotency key on a write | Still no automatic retry |

Backoff:

- exponential base 250 ms;
- equal jitter, not zero-to-cap full jitter;
- maximum 60 seconds;
- `Retry-After` seconds or HTTP date;
- cancellation during delay stops immediately.

An idempotency key is an explicitly attached header, not evidence that the public Plaky API guarantees deduplication.

### 8.5 Timeout and cancellation

Async:

- cancellation of the calling task must propagate;
- do not catch and wrap cancellation as a connection error;
- a timeout covers API key/header providers, request hooks, network I/O, response reading, decoding, and response hooks for that attempt;
- convert timeout to `PlakyTimeoutError`.

Sync:

- use HTTP timeout support and the same elapsed-attempt policy as closely as the client library permits;
- no fake cancellation API.

### 8.6 Response limits

- Default non-streaming success/error body limit: 16 MiB.
- Configurable range: 1 byte through 64 MiB.
- Read streaming chunks and stop before exceeding the bound.
- Raise `PlakyResponseTooLargeError` without materializing the rest.
- A malformed 2xx body raises `PlakyDecodeError`.
- A valid JSON root with the wrong contract raises `PlakyResponseContractError`.
- Decode and contract errors are deterministic and never retried.

### 8.7 Root contracts

Paged endpoints require a plain object with:

```json
{
  "data": [],
  "hasMore": false
}
```

Both fields are mandatory. `data` must be an array; `hasMore` must be boolean. An empty `data` array with `hasMore: true` is invalid because it would permit an infinite loop.

Bare-array endpoints:

- `listItemComments`
- `listItemFiles`

Validate the array root. The comments resource wraps it in `Page(data=..., has_more=False)` for SDK iterator consistency. File listing remains an ordinary list to preserve the source API.

### 8.8 Pagination

Provide sync and async iterator objects with:

- ordinary iteration;
- `first_page()`;
- `pages()`;
- `to_list(limit=None)`.

Defaults:

- page size 100;
- client-side limit optional;
- 10,000-page hard safety valve.

Do not fetch another page after the iterator is stopped. Do not treat an empty page with `has_more=True` as normal.

### 8.9 Bounded chunks

Required constants:

```text
DEFAULT_CHUNK_MAX_ITEMS = 100
DEFAULT_CHUNK_MAX_BYTES = 1_048_576
MAX_MATERIALIZED_ITEMS = 10_000
MAX_MATERIALIZED_BYTES = 16_777_216
```

A cursor contains exact `{page, index}` state and resumes at the first omitted item. Byte accounting uses UTF-8 encoded bytes, not Python character count.

A single item larger than the byte limit raises `PlakyOutputLimitError`. A collection that exceeds the materialization bound raises `PlakyMaterializationLimitError`.

### 8.10 Uploads

SDK upload input:

- bytes or an opened binary file-like object;
- explicit filename;
- optional media type;
- no implicit arbitrary path reads in the core method.

MCP upload input:

```json
{
  "fileBase64": "...",
  "fileName": "report.pdf",
  "contentType": "application/pdf"
}
```

Validation:

- hard decoded-size ceiling: 25 MiB;
- filename nonempty;
- no slash, backslash, or control character;
- maximum filename length: 255 UTF-8 bytes;
- canonical RFC 4648 base64 only;
- estimate decoded length before allocation;
- decode once;
- verify canonical re-encoding;
- normalize media type and legal parameters;
- compute SHA-256 once;
- never log content, API key, digest-to-content mapping, or signed download URL.

### 8.11 Rate-limit tracker

Preserve both views:

1. Server headers when available.
2. A local rolling 60-second window with a default 200-request maximum.

Expose:

- `last`
- `estimated_remaining()`
- `would_throttle()`
- `seconds_until_next_slot()`
- `reset()`

This is an estimate and must not silently sleep or throttle requests unless the caller explicitly opts into such behavior.

### 8.12 Mutation plans and receipts

Dry-run plan:

```json
{
  "dryRun": true,
  "operation": "createItem",
  "payload": {},
  "targetIds": {},
  "writeCount": 1,
  "requiresLiveResolution": false
}
```

Receipt statuses:

- `planned`
- `request-started`
- `completed`
- `failed`
- `ambiguous`

Phases:

- `preflight`
- `request`
- `response`
- `completed`

Every receipt records:

- operation;
- batch index;
- status;
- `attempted`;
- `mayHaveCommitted`;
- phase;
- canonical target IDs;
- bounded redacted error summary.

If a timeout, disconnect, cancellation, decode error, or response-hook failure happens after request dispatch, the outcome is conservatively `ambiguous` and `mayHaveCommitted=true`.

Batch workflows never repeat a completed item. `PlakyPartialMutationError` carries immutable ordered receipts and the failed index.

### 8.13 CSV export

Preserve:

- JSONL and CSV;
- deterministic top-level key order;
- deterministic field-column order;
- field labels with collision disambiguation;
- canonical nested JSON with sorted object keys;
- exact UTF-8 accounting;
- frozen schema for chunked CSV;
- spreadsheet-formula protection for strings beginning, after leading spaces, with `=`, `+`, `-`, or `@`;
- raw mode only when the caller explicitly requests it;
- newline-terminated CSV.

---

## 9. Resolver behavior

Resolvers accept:

- exact integer/string ID;
- plain text search;
- `{id: ...}`;
- `{title: ...}`;
- `{name: ...}`;
- `{email: ...}`;
- a response-like object carrying an ID.

Rules:

- ID is authoritative when a compatibility object also has labels.
- Multiple selector fields in one object are an error.
- Exact IDs use direct GET when an endpoint exists.
- Text matching is case-insensitive substring matching.
- Zero matches raise local `PlakyNotFoundError`.
- Multiple matches raise `PlakyAmbiguousMatchError` with bounded candidates.
- `resolve_space_and_board` resolves the space once.
- `resolve_items_in_board` performs direct GETs when all refs are IDs; otherwise it lists once and resolves all refs from that result.
- All resolver reads accept ordinary per-request options/cancellation.
- Resolver error URLs use a local pseudo-origin and never pretend to be remote API responses.

---

## 10. MCP server

### 10.1 Tool inventory

The server has two surfaces:

- generated raw tools: one tool per accepted Plaky operation;
- curated tools: assistant-friendly discovery, planning, and workflows.

Modes:

- `curated`
- `generated`
- `all`

Scopes:

- `read`
- `write`
- `destructive`

Defaults:

```text
mode = curated
scopes = [read]
```

A tool is mounted only when every scope it requires is enabled.

### 10.2 Curated tools


| Tool | Purpose | Required scope |
| --- | --- | --- |
| `plaky_search_docs` | Search bundled operation/workflow/guide index. | read |
| `plaky_workspace_context` | Return bounded compact workspace context. | read |
| `plaky_find` | Find spaces, boards, items, users, teams, groups, or files by exact ID/text as supported. | read |
| `plaky_plan_mutation` | Validate and normalize one mutation without executing it. | read |
| `plaky_execute_workflow` | Deprecated mixed read/write compatibility dispatcher; mutation workflows default to dry-run. It is available only behind an explicit local compatibility flag and is never included in a Claude directory-facing catalog. | read + write |
| `plaky_execute_read_workflow` | Discriminated read-only workflow dispatcher. | read |
| `plaky_execute_mutation_workflow` | Discriminated mutation dispatcher with dry-run, progress, and attempt receipts. | read + write |


### 10.3 Curated workflows


| Workflow ID | Class | Required result |
| --- | --- | --- |
| `workspace.map` | read | Bounded compact spaces/boards tree. |
| `items.search` | read | Title and nested scalar field search with exact page/index continuation. |
| `comments.thread` | read | Bounded comment thread. |
| `export.items` | read | One bounded JSONL/CSV chunk with deterministic schema and continuation. |
| `items.create` | mutation | Validated plan; dry-run by default; one write when enabled. |
| `items.updateFields` | mutation | One or many updates with durable per-item receipts. |
| `comments.add` | mutation | Validated comment plan; dry-run by default. |
| `itemGroups.create` | mutation | Title/color validation; dry-run by default. |
| `itemGroups.update` | mutation | Title/ranking/color validation; dry-run by default. |
| `itemFiles.upload` | mutation | Canonical base64 only; metadata validation, SHA-256, bounded bytes; dry-run by default. |
| `itemFiles.update` | mutation | Validated name/description update; dry-run by default. |


### 10.4 Tool input and output rules

- Raw MCP argument names remain camelCase for compatibility.
- Input schemas are strict. Unknown arguments fail validation.
- Raw outputs validate the API root and expected model before presentation.
- Delete/archive tools return `{ "ok": true }`.
- Every successful tool returns structured content.
- Text content is a concise redacted summary or compact JSON.
- A tool with an output schema must not return unvalidated structured content.
- Raw API payloads are never included by default.
- Curated tools may expose `includeRaw` only where the source surface does; any nested raw value is at most 64 KiB so it cannot consume the whole result budget.
- Maximum aggregate serialized `CallToolResult`: 128 KiB (131,072 UTF-8 bytes), including text `content`, `structuredContent`, duplicated/compatibility presentation, and envelope overhead. This is one combined budget, not one budget per channel.
- Larger output returns a structured usage error, not a truncated invalid schema.
- Logical collections larger than the cap must paginate with an exact continuation; test ASCII and multibyte boundaries at 131,072 and 131,073 bytes.
- File download links are HTTPS-only and marked sensitive.
- Sensitive values are not copied into logs or generic summaries.

### 10.5 MCP annotations

Populate all four standard tool hints:

- `readOnlyHint`
- `destructiveHint`
- `idempotentHint`
- `openWorldHint`

These describe operation semantics. `idempotentHint=true` does **not** enable SDK write retries.

Every exposed tool also has a human-readable `title`, a unique name of at most 64 characters, a concrete description, and input/output schemas that agree with the handler. The registry gate validates all of these fields.

Archive item group requires `write` and `destructive` because there is no public unarchive operation.

### 10.6 Error envelope

Known failures return `isError=true` with this wire shape:

```json
{
  "error": {
    "category": "api",
    "name": "PlakyNotFoundError",
    "message": "Not found.",
    "retryable": false,
    "status": 404,
    "code": "NOT_FOUND",
    "requestId": "request-id",
    "retryAfterMs": 1000,
    "attempted": false,
    "mayHaveCommitted": false,
    "phase": "preflight",
    "receipts": []
  }
}
```

Use camelCase aliases on the wire.

Do not implement this by raising an ordinary tool exception: MCP SDK v2 converts such exceptions to error text with `structured_content=None`. Every generated and curated tool must advertise both success and error shapes and return the direct-result form:

```python
ToolOutput = SuccessModel | ErrorEnvelope

async def tool(...) -> Annotated[CallToolResult, ToolOutput]:
    return CallToolResult(
        content=[TextContent(type="text", text=redacted_summary)],
        structured_content=wire_value,
        is_error=is_error,
    )
```

The generator emits the concrete `SuccessModel | ErrorEnvelope` annotation for each raw tool. A shared adapter maps known domain failures to `ErrorEnvelope`; it must re-raise cancellation. The output schema and the 128 KiB aggregate budget validate both the success and error path.

Categories:

- `api`
- `timeout`
- `connection`
- `decode`
- `abort`
- `validation`
- `usage`
- `plaky`

Unknown programmer errors must be redacted, logged to stderr with a correlation ID, and converted through one controlled `CallToolResult` internal-error path. They must not leak stack traces, API keys, request bodies, or signed URLs to the client.

### 10.7 Invocation-local mutation state

Each tool call gets a fresh attempt tracker. It is never global, shared, cached, or serialized directly.

The tracker marks:

- before request;
- request started;
- response received;
- completed;
- ambiguous outcome.

Generated mutation tools and curated mutation workflows use the same helper. Do not preserve the current TypeScript exception where generated tools infer attempt state after the fact; the Python port can make every mutation wrapper explicit from the first implementation.

### 10.8 Progress and cancellation

- Call `await ctx.report_progress(...)` unconditionally at bounded, monotonically increasing checkpoints; MCP SDK v2 no-ops when the caller supplied no progress callback/token.
- Search, export, upload normalization, and multi-item updates report bounded progress.
- Cancellation stops future reads or writes.
- If cancellation occurs after downstream write dispatch, record the outcome as internally ambiguous and stop future work. Re-raise cancellation: a cancelled modern MCP request is not answered and must not return an ambiguous receipt.
- Modern `2026-07-28` in-memory, stdio, and Streamable HTTP cancellation must interrupt the handler. Legacy stateless HTTP cancellation cannot reliably reach an in-flight handler because the cancel POST receives a fresh transport; prove and document that limitation with a read-only blocking fixture.
- Do not emit protocol logging notifications; use ordinary logging.

### 10.9 Stdio transport

CLI:

```text
plaky115-mcp   --transport stdio   --mode curated   --scope read
```

Configuration precedence:

```text
--server-url > PLAKY115_BASE_URL > SDK default
PLAKY115_API_KEY > PLAKY115_API_KEY_AUTH
```

Requirements:

- stdout is reserved for MCP frames;
- `--help` prints help and exits before serving;
- all logs go to stderr;
- unknown flags fail;
- blank keys fail before server start;
- no `.env` auto-loading in production code;
- no secrets in process arguments.

### 10.10 Stateless Streamable HTTP

CLI:

```text
plaky115-mcp   --transport streamable-http   --host 127.0.0.1   --port 8000   --mode curated   --scope read
```

Requirements:

- official MCP SDK v2 Streamable HTTP;
- `server.streamable_http_app(stateless_http=True, json_response=False, ...)`;
- modern `2026-07-28` request handling is sessionless; `stateless_http=True` also keeps the legacy compatibility leg stateless;
- request-scoped `text/event-stream` responses remain enabled for progress and modern cancellation;
- default bind is loopback;
- `0.0.0.0` requires explicit operator choice;
- no deprecated standalone SSE endpoint pair;
- no session database;
- `GET /healthz` returns only `{ "status": "ok", "version": "..." }`, never credentials or workspace details;
- set `max_request_body_size=36 * 1024 * 1024` (37,748,736 bytes). MCP SDK v2 defaults to 4 MiB, but a valid 25 MiB upload expands to 34,952,536 base64 bytes before JSON overhead. Reject the raw HTTP body above 36 MiB and the decoded file above 25 MiB; test the exact decoded maximum, one decoded byte over, the exact HTTP maximum, and one HTTP byte over;
- pass `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=..., allowed_origins=...)`; loopback defaults include only `127.0.0.1:*`, `localhost:*`, and `[::1]:*`, while non-loopback hosts/origins must be explicit;
- CORS disabled by default;
- allowed origins explicit when browser access is enabled;
- single-tenant deployment in v1.

Remote security model:

- Plaky API key remains a process secret.
- The initial v1 deployment is private-network or authenticated-reverse-proxy only; do not add a speculative auth provider interface.
- Never reuse the Plaky key as MCP bearer authentication.
- Never accept the Plaky key in tool input.
- Multi-tenant per-user credential brokerage is a separate product and is not part of this implementation.
- Do not claim Claude-hosted custom-connector or directory readiness from a loopback/private deployment. Such a claim requires a public HTTPS endpoint, separately implemented MCP-layer authentication, a real production Claude connector test, and any upstream/domain authorization required by the directory. `plaky_execute_workflow` is excluded from every directory-facing catalog because it mixes read and write behavior.

---

## 11. Contract and generation pipeline

### 11.1 Sources

Store:

- `contract/upstream.openapi.yaml`: accepted upstream mirror.
- `contract/source-manifest.json`: source URL, source commit/version, SHA-256, acceptance date.
- `contract/operation-overrides.yaml`: names, MCP metadata, SDK mapping, pagination/root behavior, sensitivity.
- `contract/schema-patches.yaml`: minimal exact JSON Pointer patches for confirmed upstream defects.
- `contract/expected-operations.json`: pinned method/path/operation inventory.

Do not edit `contract/generated/*` manually.

### 11.2 Operation override shape

Example:

```yaml
operations:
  "GET /v1/public/spaces":
    operationId: listSpaces
    sdk:
      resource: spaces
      method: list
    response:
      root: page
      model: SpaceResponse
    query:
      expand:
        style: form
        explode: false
    mcp:
      name: plaky_list_spaces
      title: List spaces
      scopes: [read]
      annotations:
        readOnlyHint: true
        destructiveHint: false
        idempotentHint: true
        openWorldHint: true
```

All metadata for an operation lives in this exact-key entry. Do not spread operation truth across handwritten registries.

### 11.3 Commands

```bash
uv run python scripts/contract.py fetch
uv run python scripts/contract.py diff
uv run python scripts/contract.py accept
uv run python scripts/contract.py build
uv run python scripts/contract.py check

uv run python scripts/generate.py
uv run python scripts/generate.py --check
uv run python scripts/parity.py
```

Behavior:

- `fetch` writes only to `contract/candidate/`.
- `diff` produces a semantic report: added/removed/changed operations, parameters, bodies, responses, schemas, enums, and security.
- `accept` never runs implicitly. It updates the accepted source and manifest only after explicit invocation.
- `build` applies minimal patches and operation metadata, resolves/validates refs, and emits deterministic JSON.
- `check` fails on unresolved refs, duplicate operation IDs, missing metadata, operation drift, unsupported schema constructs, or a changed generated digest.
- `generate --check` renders into a temporary directory and byte-compares every generated file.
- `parity.py` compares contract, SDK map, raw tools, curated workflow registry, docs index, and live classification.

### 11.4 Generated-file policy

Every generated file begins with:

```python
# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
```

Generated files are formatted deterministically. Handwritten changes go into the generator, contract metadata, or adjacent handwritten layer.

### 11.5 Contract acceptance gate

A contract change is accepted only when:

- semantic diff is reviewed;
- expected operation inventory is deliberately updated;
- all new operations have SDK and MCP mappings;
- safety classification is explicit;
- request and response models generate;
- focused tests exist;
- docs index updates;
- offline verification passes;
- live classification is updated.

---

## 12. Implementation phases

Each phase is a vertical slice. Do not begin a later phase while the current phase gate is red, except to fix a prerequisite discovered by evidence.

### Phase 0 — Freeze source and create proof inventories

**Tasks**

1. Execute the literal bootstrap boundary in section 1.1; stop if the target exists or the source is dirty/not at the pinned SHA.
2. Treat the source repository as read-only and read its root `AGENTS.md` first, then `CLAUDE.md`, before any source inspection.
3. Record baseline SHA `33ae2926aa696f36d9663d44f914d42d9aadc53f` and release `v1.0.11` in `contract/source-manifest.json`.
4. Map source to target exactly:
   - `api-1.yaml` -> `contract/upstream.openapi.yaml`;
   - `overlays/plaky115-dx.overlay.yaml` -> exact reviewed JSON Pointer patches/operation overrides, with a canonical generated result compared against `openapi/plaky115-dx.openapi.yaml`;
   - `openapi/plaky115-expected-operations.json` -> `contract/expected-operations.json`;
   - `openapi/plaky115-operation-metadata.json` -> the MCP/safety/request/success portions of `contract/operation-overrides.yaml`, preserving every operation ID, method/path, raw tool name/title, scope, annotation, request kind, success/root kind, compaction kind, and sensitivity flag;
   - `scripts/test-cross-surface-parity.mjs` `sdkInvokers` -> the SDK resource/method portion of `contract/operation-overrides.yaml`; this is the pinned source's explicit 32-operation SDK map and must be compared to section 7.1 rather than inferred mechanically from operation IDs;
   - root `LICENSE` -> target `LICENSE`, retaining the upstream MIT copyright and permission notice;
   - selected source behavioral fixtures -> named target fixtures with source path and hash.
5. Use `contract/source-manifest.json` as the sole baseline record. It contains source paths, SHA-256 hashes, copy/translation targets, tag/SHA, and acceptance date; do not create a duplicate `SOURCE_BASELINE.md`.
6. Create `PORT_MATRIX.md` containing:
   - 32 operations;
   - nine resources;
   - current public SDK exports;
   - seven curated tools;
   - eleven workflows;
   - runtime behaviors;
   - docs/release gates.
7. Mark every row `not-started`; no optimistic completion.
8. Create `IMPLEMENTATION_STATE.md`, `DECISIONS.md`, and `BLOCKERS.md`; copy the canonical prompt pack as `AUTONOMOUS_PROMPTS.md`.

**Tests/gate**

- A script reads `expected-operations.json` and asserts exactly 32 unique method/path pairs.
- Every operation has an SDK resource/method and raw MCP tool name.
- Every current curated tool and workflow ID is present.
- Source SHA and copied source hashes are recorded.
- No implementation has silently started outside the matrix.

### Phase 1 — Minimal Python project scaffold

**Tasks**

1. Add `pyproject.toml`, `uv.lock`, `src` layout, `src/plaky115/py.typed`, `src/plaky115_mcp/py.typed`, the retained MIT license, README skeleton, security notice, changelog, and contribution guide.
2. Configure Hatchling and tag-derived versions.
3. Add dependency groups.
4. Add Ruff and strict Pyright configuration.
5. Add pytest and coverage configuration.
6. Add `AGENTS.md` with generated-file, secret, live-test, and autonomy rules.
7. Add a minimal CI workflow with pinned action SHAs.
8. Expose package version and empty client imports.
9. Put this exact pinned-source notice in README/PyPI long description, `SECURITY.md`, and MCP server instructions; test those installed/distributed surfaces: `Plaky115 is unofficial and independent. It is not affiliated with, endorsed by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” are trademarks of their respective owners.`

**Tests/gate**

```bash
uv sync --frozen --all-extras --group dev
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
uv build
uv run twine check dist/*
```

A fresh virtual environment installs the wheel and imports `plaky115`. Base installation does not import or require `mcp`.

### Phase 2 — Contract builder and deterministic model generation

**Tasks**

1. Implement `scripts/contract.py`.
2. Validate OpenAPI 3.1 and all refs.
3. Implement exact-key operation overrides and minimal JSON Pointer schema patches.
4. Emit deterministic canonical JSON and operation descriptors.
5. Implement expected-operation drift checks.
6. Configure deterministic Pydantic v2 model generation.
7. Add generated-model public re-exports.
8. Add operation and schema snapshots.

**Tests/gate**

- Build twice: byte-identical output.
- 32 operations exactly.
- Every operation has unique operation ID and MCP name.
- Security scheme is `X-API-Key`.
- No generated runtime client is public.
- Model import and JSON-schema generation succeed.
- `git diff --exit-code` after generation.

### Phase 3 — IDs, configuration, models, and redaction

**Tasks**

1. Implement canonical int64 IDs and path encoding.
2. Implement immutable client and request option models.
3. Implement base URL validation, including loopback HTTP exception.
4. Implement redaction and bounded presentation.
5. Implement common `Page`, `ApiResponse`, and raw request models.
6. Implement response compatibility properties.
7. Implement user-agent construction.

**Tests/gate**

- Table-driven ID edge cases.
- Unicode path segments for field keys.
- Unsafe URLs rejected.
- Cross-origin hook target rejected.
- API keys redacted from nested objects and exception presentation.
- Signed URLs absent from logs.
- Pydantic aliases round-trip.

### Phase 4 — Async transport core

**Tasks**

1. Implement `AsyncTransport` with injected `httpx2.AsyncClient`/transport.
2. Build URL and headers.
3. Encode JSON and multipart bodies.
4. Implement bounded streamed response reads.
5. Implement response type handling: JSON, text, bytes, stream, none.
6. Implement GET-only retries and bounded backoff.
7. Implement timeout across providers/hooks/I/O/parse/hooks.
8. Preserve cancellation.
9. Implement typed error classification and request IDs.
10. Observe rate-limit headers.
11. Disable redirect following.

**Tests/gate**

- One table covers success, 204/205, malformed JSON, oversized body, timeout, cancellation, connection failure, 3xx, every mapped status, Retry-After seconds/date, hook failure, and origin rewrite.
- Tests assert writes make exactly one attempt.
- Tests assert decode/hook failures are not retried.
- No secret appears in exceptions or captured logs.

### Phase 5 — Pagination, chunks, rate tracking, uploads, mutations

**Tasks**

1. Implement strict page and array-root validators.
2. Implement async pagination iterator.
3. Implement bounded chunk readers and cursors.
4. Implement rate-limit tracker.
5. Implement idempotency helper and generic `with_retries`.
6. Implement upload metadata/base64/media-type validation and SHA-256.
7. Implement mutation plans, receipts, and partial-mutation error.

**Tests/gate**

- Empty page with `has_more=True` fails.
- Iterator stops without an extra page.
- Exact continuation resumes at first omitted item.
- UTF-8 byte limits use encoded bytes.
- Oversized first item fails.
- Canonical base64/property edge cases covered.
- Mutation receipts are immutable and redacted.

### Phase 6 — Async read resources

**Tasks**

Implement and test:

- spaces list/get/iterate/list_all;
- boards list/get/iterate/list_all;
- users list/me/iterate/list_all;
- teams list/get/iterate/list_all;
- items list/get/list_subitems/iterate/list_all;
- comments list normalization/iterate/list_all;
- item groups list/get/iterate/list_all;
- item files list/get/get_download.

**Tests/gate**

For every read operation:

- method;
- exact escaped path;
- exact query serialization;
- operation ID;
- response root;
- response model;
- request options;
- 404/error behavior.

Cross-surface read parity reports no missing operation.

### Phase 7 — Async mutation resources

**Tasks**

Implement and test:

- item create/update-field/update-fields/delete;
- comment create/update/delete;
- reaction replace;
- item-group create/update/delete/archive;
- item-file upload/update/delete;
- dry-run plans where applicable;
- explicit idempotency-key header;
- no implicit idempotency key;
- no automatic write retry.

**Tests/gate**

- Every mutation performs zero network calls on dry-run.
- Every live mutation performs at most one HTTP attempt.
- All local validation completes before dispatch.
- Request-started failures are represented conservatively.
- Multipart upload has exact filename/media type/bytes.
- Delete/archive returns `None`.
- Raw delete receipts become `{ok:true}` at MCP layer only.

### Phase 8 — Field helpers, resolvers, and async workflows

**Tasks**

1. Port all field helpers.
2. Port all resolvers with exact ID/direct-GET behavior.
3. Implement workspace map with bounds.
4. Implement detailed item search with nested scalar traversal and continuation.
5. Keep deprecated `search_items` convenience wrapper.
6. Implement bulk item updates with immutable receipts.
7. Implement deterministic JSONL/CSV export.
8. Implement item and export chunk readers/iterators.
9. Implement every mutation-plan normalizer.

**Tests/gate**

- Golden fixtures from pinned source behavior.
- Nested object/array search.
- Ambiguous resolver behavior.
- One-list resolution optimization.
- Deterministic CSV and spreadsheet safety.
- Bulk update abort/progress/failure receipts.
- Materialization and continuation bounds.

### Phase 9 — Real synchronous client parity

**Tasks**

1. Implement sync transport using `httpx2.Client`.
2. Implement all nine sync resources.
3. Implement sync pagination/chunks.
4. Provide sync resolver and workflow variants where ordinary network I/O is required.
5. Reuse pure normalization/model logic.
6. Keep public names predictable; document async equivalents.

**Tests/gate**

- Introspection parity: every async resource operation has a sync counterpart.
- Shared request fixture produces byte-identical method/path/query/body.
- Sync and async error classes and response models match.
- No event-loop bridge exists.
- Package examples run.

### Phase 10 — Generated raw MCP tools

**Tasks**

1. Implement MCP tool metadata model.
2. Generate one typed module per operation.
3. Generate exact raw registry.
4. Register strict Pydantic inputs and outputs.
5. Use camelCase aliases.
6. Apply scopes, annotations, compaction kind, and sensitive-output flags.
7. Route mutations through invocation-local attempt tracking.
8. Return `{ok:true}` for void operations.
9. Generate a concrete `Annotated[CallToolResult, SuccessModel | ErrorEnvelope]` return type and direct success/error result adapter per operation.
10. Validate tool title, description, name length, and all four annotations.

**Tests/gate**

- Tool registry contains exactly 32 unique names.
- Each name matches operation metadata.
- Every tool can be invoked in memory against mock transport.
- Unknown arguments fail.
- All outputs validate.
- Every mutation tool records attempt state.
- Mode/scope filtering is exact.

### Phase 11 — Curated MCP tools and workflows

**Tasks**

1. Port docs index/search.
2. Port workspace context.
3. Port find.
4. Port mutation planning.
5. Implement typed read and mutation workflow dispatchers.
6. Keep the mixed compatibility dispatcher only behind an explicit local compatibility flag; exclude it from directory-facing catalogs.
7. Port all eleven workflow IDs.
8. Default mutation workflows to dry-run.
9. Add progress and cancellation.
10. Implement compact direct `CallToolResult` success/errors and the aggregate 128 KiB serialized-result cap.

**Tests/gate**

- Registry and discriminated workflow models agree.
- Read dispatcher cannot invoke mutations.
- Mutation dispatcher cannot accept unknown workflow IDs.
- Dry-run makes no write.
- Progress uses request context only.
- Structured errors include conservative attempt details.
- Result and raw limits enforced.
- Signed URL tool is sensitive.

### Phase 12 — MCP stdio and stateless HTTP

**Tasks**

1. Implement a single `build_server(settings, client_factory)` used by all transports.
2. Implement strict argparse CLI.
3. Implement stdio startup.
4. Implement Streamable HTTP with `stateless_http=True`, `json_response=False`, a 36 MiB raw-request cap, and explicit `TransportSecuritySettings` host/origin allowlists.
5. Add loopback-default binding.
6. Add health/readiness endpoint without secrets.
7. Document the v1 private-network/authenticated-reverse-proxy, single-tenant deployment; do not add a speculative auth hook.
8. Explicitly omit the deprecated standalone SSE endpoint pair and all server-side session storage while retaining request-scoped Streamable HTTP SSE responses.
9. Document the legacy-stateless HTTP cancellation limitation and do not claim Claude-hosted/directory readiness without the separate requirements in section 10.10.

**Tests/gate**

- In-memory modern `Client(server)` discovery/call with success/error schemas, progress, and cancellation.
- Modern stdio subprocess in `mode="2026-07-28"`: `server/discover`, list/call, progress, cancellation, and protocol-clean stdout.
- Legacy stdio in `mode="legacy"`: `initialize`, list/call, progress, and cancellation.
- Modern HTTP with `json_response=False`: no session ID, progress arrives, abandoning the response interrupts the handler, and no cancellation result is emitted.
- Legacy stateless HTTP with `stateless_http=True`, `json_response=False`: initialize/call/progress pass; a read-only blocking fixture proves a separate cancel POST does not interrupt the original handler.
- Negative configuration test proves `json_response=True` drops progress and is rejected when this server's progress/cancellation guarantees are enabled.
- Request-size gates cover the 25 MiB decoded upload and 36 MiB HTTP-body boundaries.
- Serialized result gates cover 131,072/131,073 bytes with ASCII and multibyte values.
- Concurrent stateless HTTP requests do not share mutation state.
- Default mounted tools are curated read-only.
- Broader scopes require explicit flags.
- stdout remains protocol-clean.

### Phase 13 — Documentation and examples

**Tasks**

Write and test:

- root quick start;
- sync SDK guide;
- async SDK guide;
- model/alias guide;
- error and retry guide;
- pagination/chunk guide;
- file upload guide;
- MCP host configs;
- stateless HTTP deployment;
- API behavior;
- security;
- contract evolution;
- release checklist;
- live certification;
- compatibility inventory;
- runnable examples.

**Tests/gate**

- Every code example is syntax-checked.
- Selected examples execute against mock transport.
- Host config uses environment secrets.
- Docs never contain literal `plk_` keys or signed URLs.
- Version/support claims match `pyproject.toml`.

### Phase 14 — Packaging, CI, and release engineering

**Tasks**

1. Complete `scripts/verify.py`.
2. Add wheel/sdist content audit.
3. Add separate clean-environment base-wheel and MCP-extra consumer smoke tests.
4. Add installed-wheel typing proof: assert both `py.typed` files are in the wheel, then run a checked-in external strict-Pyright consumer against both installed namespaces with the source tree unavailable.
5. Audit the clean base-wheel dependency set and clean MCP-extra dependency set separately. Online current advisory data is mandatory in CI/release; the offline verifier must report `NOT_RUN_OFFLINE`, never pass, when that data is unavailable.
6. Add four explicit secret-scan scopes: tracked current source, reachable Git history, built artifacts, and local-only evidence. Report file/category/count without printing matched secret values.
7. Add cross-platform CI.
8. Add trusted PyPI publishing with provenance.
9. Add release version/changelog gates.
10. Pin GitHub actions by commit SHA.
11. Make the release job consume the exact previously built artifact.
12. After separately authorized publication, verify exact registry version visibility, install that version in a fresh environment, and prove registry artifact digest, attestation/provenance, tag, repository, workflow, and commit agreement.

**Tests/gate**

```bash
uv run python scripts/verify.py --offline
uv build
uv run twine check dist/*
uv run python scripts/package_smoke.py dist/*
uv run python scripts/verify.py --release-online  # CI/release only; current advisory data required
```

Fresh environments prove:

- SDK base install;
- sync and async import;
- MCP extra install;
- `plaky115-mcp --help`;
- stdio start;
- no tests/source/private scripts accidentally shipped;
- upstream MIT notice and both `py.typed` markers shipped;
- installed external-consumer typing for `plaky115` and `plaky115_mcp`;
- unofficial/non-affiliation language present in distribution metadata and MCP server instructions.

### Phase 15 — Live certification

**Read-only gate**

- Requires injected rotated key.
- Runs exactly these 17 operation IDs through each of four surfaces: independent direct HTTP reference probe, `AsyncPlakyClient`, `PlakyClient`, and generated raw MCP: `listSpaces`, `getSpace`, `listBoards`, `getBoard`, `listItems`, `listSubitems`, `getItem`, `listItemComments`, `listUsers`, `getCurrentUser`, `listTeams`, `getTeam`, `listItemGroups`, `getItemGroup`, `listItemFiles`, `getItemFile`, `getItemFileDownload`.
- Expected receipt per surface is 17 passed and 0 skipped, or 15 passed plus exactly the paired `getItemFile`/`getItemFileDownload` prerequisite skips when no file exists. No other skip is allowed.
- Records counts and shapes, never real payloads.
- Verifies tenant-specific base URL support.
- Prints secrets only as `set`/`unset`.
- Missing credentials, unreachable provider state, or missing prerequisites outside the single paired skip are `BLOCKED_EXTERNAL`, never pass or silent skip.

**Write gate**

Requires all:

```text
PLAKY115_LIVE_WRITE=1
PLAKY115_SMOKE_SPACE_ID
PLAKY115_SMOKE_BOARD_ID
PLAKY115_SMOKE_ALLOW_ARCHIVE=1   # only for archive probe
```

These variables are interlocks only. The current task must also carry the live-write authorization described in section 3.8, including the exact 30-call minimum budget for proving 15 mutation operation IDs through both the async SDK and generated raw MCP surfaces (plus bounded setup/observation/cleanup calls).

Behavior:

- one UUID marker for the run;
- prove exactly these 15 mutation operation IDs through `AsyncPlakyClient` and generated raw MCP, with no arbitrary skip: `createItem`, `deleteItem`, `updateItemField`, `updateItemFields`, `createItemComment`, `updateItemComment`, `deleteItemComment`, `replaceCommentReactions`, `createItemGroup`, `updateItemGroup`, `deleteItemGroup`, `archiveItemGroup`, `uploadItemFile`, `updateItemFile`, `deleteItemFile`;
- use dedicated artifacts per surface so one surface cannot consume the other's proof;
- observe file get/download metadata after upload, but count those as read prerequisites rather than mutation coverage;
- track every artifact immediately after creation;
- cleanup in `finally`, SIGINT, and SIGTERM paths;
- scan all relevant pages for marker residue;
- fail if cleanup scan itself fails;
- require tracked artifacts `0` and discovered leftovers `0`.
- If an archived test group cannot be deleted, fail certification, record its exact ID in `BLOCKERS.md` without payload data, mark future live-write runs quarantined, and stop every later live-write run until that residue is explicitly recovered. Never work around it with a new marker.

Never run live writes against a non-sacrificial workspace.

### Phase 16 — Adversarial final audit

An independent pass must assume the project is incomplete.

Audit:

- contract versus 32 SDK methods;
- contract versus 32 raw tools;
- public exports versus port matrix;
- seven curated tools;
- eleven workflows;
- sync/async parity;
- safety annotations;
- GET-only retry;
- ambiguous mutations;
- output limits;
- sensitive data;
- package contents;
- docs;
- CI/release;
- live evidence.

Fix every proved gap, rerun all gates, and update evidence. Do not waive a failure because it appears peripheral.

---

## 13. Test architecture

### 13.1 Unit tests

Use `httpx2.MockTransport` or an equivalent injected transport. Do not bind network ports for SDK unit tests.

Test categories:

- configuration and URL validation;
- IDs/path encoding;
- query serialization;
- headers/auth/user-agent;
- JSON/multipart body construction;
- response parsing;
- all error statuses;
- retries/backoff;
- timeout/cancellation;
- hooks;
- response limits;
- pagination;
- chunks;
- rate limits;
- redaction;
- uploads;
- mutation receipts;
- each resource operation;
- each helper/resolver/workflow;
- CSV.

### 13.2 Contract tests

- OpenAPI validation.
- Ref resolution.
- operation ID uniqueness.
- 32-operation expected inventory.
- operation metadata completeness.
- query serialization metadata.
- request/response model existence.
- safety classification.
- generated drift.
- source manifest integrity.

### 13.3 Parity tests

Maintain machine-readable inventories:

```text
contract operations
SDK async operations
SDK sync operations
raw MCP tools
curated tools
workflow IDs
docs entries
live classifications
```

The parity script fails on any set difference or metadata mismatch.

### 13.4 MCP tests

Use the official v2 `Client(server)` in memory for most tests.

Also test:

- every modern/legacy leg and negative configuration listed in Phase 12, including modern `server/discover`, legacy `initialize`, HTTP progress, modern cancellation, and the proved legacy-stateless cancellation limitation;
- tool list by mode/scope;
- strict input errors;
- structured output;
- tool error envelopes;
- progress;
- cancellation;
- concurrent mutation-state isolation;
- response size limits;
- aggregate serialized result boundaries at 131,072/131,073 bytes for ASCII and multibyte data;
- decoded upload and raw HTTP body boundaries at 25 MiB/36 MiB;
- signed URL handling;
- unknown tool;
- unsupported task invocation behavior delegated to the official SDK.

### 13.5 Differential fixtures

Create source-anchored golden fixtures for pure behavior:

- query strings;
- canonical IDs;
- normalized problems;
- mutation plans;
- upload metadata;
- compact MCP results;
- error envelopes;
- CSV;
- search continuation;
- mutation receipts.

Each fixture records the source baseline SHA. Do not require Node in normal Python CI; regenerate fixtures only through an explicit maintainer task.

### 13.6 Coverage

Generated models and generated raw wrappers may be excluded from percentage calculations only when their behavior is covered through registry/operation tests.

Target:

- at least 95% branch coverage for handwritten runtime code;
- explicit branch tests for transport, retry, pagination, uploads, mutation attempts, and MCP error mapping;
- no coverage-only tests that assert nothing meaningful.

Coverage is a guard, not the definition of correctness.

### 13.7 Platform matrix

- Ubuntu: Python 3.11–3.14.
- Windows: one current Python version for package, sync client, stdio, and path handling.
- macOS: one current Python version for package and stdio smoke.
- Live tests: manual workflow only.

---

## 14. Verification command

`uv run python scripts/verify.py --offline` is the one release-grade local command.

It runs, in order:

1. source/contract manifest check;
2. OpenAPI validation;
3. operation inventory;
4. deterministic contract build;
5. deterministic code generation;
6. parity inventory;
7. Ruff format check;
8. Ruff lint;
9. strict Pyright;
10. unit/integration tests with branch coverage;
11. example checks;
12. docs checks;
13. wheel/sdist build;
14. package content audit;
15. fresh-environment base install;
16. fresh-environment MCP-extra install;
17. installed-wheel external typing proof for both namespaces;
18. in-memory modern MCP smoke;
19. modern and legacy stdio MCP smoke;
20. modern and legacy Streamable HTTP smoke with `json_response=False`;
21. result/upload/request boundary tests;
22. secret scan over tracked source, reachable history, built artifacts, and local-only evidence as separate receipts;
23. dependency-lock integrity; current online advisory status is explicitly `NOT_RUN_OFFLINE`.

The script emits a final JSON receipt with each gate, command, exit code, and artifact digest. It must not hide failed output.

CI and release additionally run `scripts/verify.py --release-online`, which repeats the offline gates and audits clean base-wheel and MCP-extra environments separately against current advisory data. `NOT_RUN_OFFLINE` is not acceptable for a release. Publication/post-publication checks remain conditional on the separate authority in section 3.8.

Focused developer commands remain available, but CI and release use the same orchestrator.

---

## 15. Security rules

- API keys only from constructor/provider or environment.
- Never put API keys in tool schemas, command arguments, docs, fixtures, logs, exception messages, snapshots, or telemetry.
- Redact `plk_`-style values recursively.
- Strip query/fragment when presenting URLs in errors.
- Signed download URLs are secret-equivalent until expiry.
- Do not follow redirects automatically.
- Request hooks cannot change origin.
- Reject non-HTTPS base URLs except loopback HTTP.
- Bound all nonstreaming bodies.
- Bound MCP input and output.
- Bound upload decoding before allocation.
- No local file paths in MCP.
- No write retries.
- Default MCP access is read-only curated.
- Destructive tools require explicit destructive scope and annotation.
- Archive requires destructive classification.
- HTTP mode is single-tenant unless a separate reviewed credential architecture is implemented.
- CORS and public binding are opt-in.
- Live writes require both explicit environment interlocks/sacrificial IDs and separate current-task authorization with scope and budget.
- Remote create/push/PR, tag creation, and PyPI publication each require their own current-task authorization; available credentials are not authorization.
- Release uses trusted publishing; no long-lived PyPI token in repository secrets.
- Dependency updates occur in dedicated commits with full verification.
- Security fixes may change internals immediately but public behavior changes require a documented compatibility decision.

---

## 16. Rules against overengineering

1. Prefer one explicit function over a registry plus three abstractions when only one caller exists.
2. Do not create interfaces before a second implementation exists.
3. Do not create a base resource class that hides method/path/body behavior.
4. Do not make public methods dynamic.
5. Do not build a generic OpenAPI framework; build the exact Plaky pipeline.
6. Do not generate public SDK resource methods.
7. Do not use runtime reflection to register tools when deterministic generated modules are clearer.
8. Do not add a database, cache, queue, or worker.
9. Do not add a user-facing Python CLI beyond the MCP server entry point.
10. Do not add retries to writes.
11. Do not expose arbitrary raw HTTP as an MCP tool.
12. Do not add MCP prompts/resources/apps without a concrete user requirement.
13. Do not add the deprecated standalone SSE/HTTP+SSE transport or endpoint pair; request-scoped Streamable HTTP SSE responses remain enabled.
14. Do not support two package release trains.
15. Do not duplicate contract metadata.
16. Do not copy deprecated private implementation details from TypeScript.
17. Do not preserve bugs for superficial parity; document and test any intentional correction.
18. Delete dead scaffolding immediately.
19. Keep generated and handwritten ownership visibly separate.
20. Optimize for a maintainer reading the code six months later.

---

## 17. Autonomous execution control

### 17.1 Required state files

#### `IMPLEMENTATION_PLAN.md`

Copy this implementation plan into the target repository and keep it authoritative. Changes require a dated decision entry.

#### `PORT_MATRIX.md`

One row per required item:

```markdown
| ID | Surface | Source proof | Python target | Tests | Status | Evidence |
```

Allowed status:

- `not-started`
- `in-progress`
- `blocked`
- `implemented`
- `verified`

Only a green objective gate permits `verified`.

#### `IMPLEMENTATION_STATE.md`

Keep concise and current:

```markdown
# Implementation State

- Baseline SHA:
- Current phase:
- Current branch:
- Last completed slice:
- Last green focused command:
- Last green offline verification:
- Current failures:
- Next exact action:
- Uncommitted files:
- External blockers:
```

#### `DECISIONS.md`

Append-only short decisions:

```markdown
## ADR-0001 — One wheel with MCP extra
Date:
Status:
Context:
Decision:
Consequences:
Evidence:
```

#### `BLOCKERS.md`

Only external blockers belong here. A failing test, missing function, unclear internal code, or ordinary bug is work, not a blocker.

### 17.2 Autonomous work loop

The implementing agent repeats:

1. Read `AGENTS.md`, `IMPLEMENTATION_STATE.md`, `PORT_MATRIX.md`, and current `git status`.
2. Reconcile state files against code and tests; code/evidence wins over stale prose.
3. Select the highest-priority incomplete vertical slice whose prerequisites are green.
4. Inspect the pinned source paths for that slice.
5. Write or update focused tests first when behavior is not already pinned.
6. Implement the smallest complete behavior.
7. Run focused tests.
8. Run relevant type/lint/contract checks.
9. Review the diff adversarially:
   - hidden retry?
   - leaked secret?
   - wrong root shape?
   - missing cancellation?
   - extra abstraction?
   - duplicated metadata?
10. Fix all findings.
11. Update matrix, state, and decisions.
12. Commit one coherent green slice.
13. Immediately select the next slice.
14. Periodically run full offline verification.
15. Continue until every acceptance gate is green.

The agent does not stop after planning, scaffolding, a single phase, or a summary. It stops only when:

- the complete end state is verified; or
- a genuinely external blocker prevents progress.

Before stopping for a blocker, it must record:

- exact blocker;
- command and output;
- what was tried;
- why no safe local workaround exists;
- clean handoff state;
- next command after unblocking.

### 17.3 Commit policy

- Small, coherent, reviewable commits.
- Never commit red tests.
- Never combine dependency upgrades with feature work.
- Never rewrite generated output manually.
- Never push secrets or live evidence containing payloads.
- Local commits are permitted.
- Push only when separately authorized for the exact configured target repository/branch; otherwise keep local commits and record the external gate.
- Never modify or push the source repository.
- Remote creation/PR, tag creation, package publication, and live writes remain separately authorized and gated; environment variables never grant that authority.

---

## 18. Canonical autonomous prompt pack

The canonical executable prompts are maintained in `plaky115-python-autonomous-prompts.md` in the handoff directory and copied to target `AUTONOMOUS_PROMPTS.md` during bootstrap. The standalone `plaky115-python-master-kickoff-prompt.txt` must be byte-identical to Prompt A extracted from that pack. Do not embed additional prompt copies in this plan.

Before handoff, run this drift check from the handoff directory. It extracts Prompt A, compares it byte-for-byte with the standalone master, verifies both exact source/target paths and the pinned SHA are present, and fails on any legacy notebook-sandbox artifact link:

```bash
cmp <(awk 'BEGIN{in_a=0} /^### Prompt A /{seen=1; next} seen && /^```text$/{in_a=1; next} in_a && /^```$/{exit} in_a{print}' \
  plaky115-python-autonomous-prompts.md) plaky115-python-master-kickoff-prompt.txt
rg -F '/Users/15x/Downloads/WORKING/addons-me/plaky115-python' \
  plaky115-python-implementation-plan.md plaky115-python-autonomous-prompts.md plaky115-python-master-kickoff-prompt.txt
rg -F '33ae2926aa696f36d9663d44f914d42d9aadc53f' \
  plaky115-python-implementation-plan.md plaky115-python-autonomous-prompts.md plaky115-python-master-kickoff-prompt.txt
! rg -n 'sandbox:'"/mnt/data" .
```

## 19. Completion checklist

### Contract

- [ ] Source baseline SHA recorded.
- [ ] Accepted OpenAPI and manifest pinned.
- [ ] 32 unique operations.
- [ ] All refs resolve.
- [ ] Every operation has complete metadata.
- [ ] Generation deterministic.
- [ ] Candidate fetch/diff/accept flow tested.

### SDK core

- [ ] Async client.
- [ ] Sync client.
- [ ] Context management and closing.
- [ ] Low-level request and response envelope.
- [ ] URL trust boundary.
- [ ] Query serialization.
- [ ] Bounded bodies.
- [ ] Typed errors.
- [ ] GET-only retries.
- [ ] Cancellation.
- [ ] Hooks.
- [ ] Rate-limit tracker.
- [ ] Redaction.
- [ ] All eleven published runtime-subpath functions mapped and tested.

### Resources

- [ ] Spaces.
- [ ] Boards.
- [ ] Items.
- [ ] Comments.
- [ ] Reactions.
- [ ] Users.
- [ ] Teams.
- [ ] Item groups.
- [ ] Item files.
- [ ] All 32 operation rows verified.
- [ ] Sync/async parity verified.
- [ ] All nine sync and nine async resource classes are root exports.

### Helpers/workflows

- [ ] IDs.
- [ ] Pydantic models and aliases.
- [ ] Pagination.
- [ ] Bounded chunks.
- [ ] Upload validation.
- [ ] Mutation plans.
- [ ] Mutation receipts.
- [ ] Field helpers.
- [ ] Resolvers.
- [ ] Workspace map.
- [ ] Detailed search.
- [ ] Bulk update.
- [ ] JSONL/CSV export.
- [ ] Chunked export.

### MCP

- [ ] Official `mcp` v2.
- [ ] `MCPServer`.
- [ ] 32 raw tools.
- [ ] Seven curated tools.
- [ ] Eleven workflow IDs.
- [ ] Exact mode/scope behavior.
- [ ] Default curated/read.
- [ ] Structured outputs.
- [ ] Direct `Annotated[CallToolResult, SuccessModel | ErrorEnvelope]` success/error paths.
- [ ] Progress/cancellation.
- [ ] Invocation-local mutation attempts.
- [ ] 128 KiB aggregate serialized-result limit.
- [ ] Sensitive signed URLs.
- [ ] Base64-only MCP uploads.
- [ ] Stdio.
- [ ] Stateless Streamable HTTP.
- [ ] 36 MiB request cap plus 25 MiB decoded upload cap.
- [ ] Modern/legacy transport matrix and documented legacy-stateless cancellation limit.
- [ ] No deprecated standalone SSE endpoint pair or session storage.

### Quality/release

- [ ] Ruff.
- [ ] Strict Pyright.
- [ ] Branch coverage gate.
- [ ] Contract tests.
- [ ] Parity tests.
- [ ] MCP in-memory tests.
- [ ] MCP stdio tests.
- [ ] MCP HTTP tests.
- [ ] Docs/examples.
- [ ] Wheel/sdist audit.
- [ ] Base consumer smoke.
- [ ] MCP-extra consumer smoke.
- [ ] Both `py.typed` markers and installed external typing proof.
- [ ] Four-scope secret scan.
- [ ] Separate base/MCP-extra online dependency audits.
- [ ] MIT attribution and unofficial/non-affiliation distribution gates.
- [ ] CI matrix.
- [ ] Trusted publishing.
- [ ] Artifact provenance.
- [ ] Exact 17-operation read gate per required surface, with only the paired file skip allowed.
- [ ] Exact 15-operation write gate on SDK and raw MCP, under separate current-task authorization.
- [ ] Zero-residue proof.
- [ ] Adversarial final audit.
- [ ] Clean worktree.

---

## 20. Source anchors

The implementation should inspect these paths at the pinned source SHA rather
than relying on this plan alone:

- `README.md`
- `AGENTS.md` (read first)
- `CLAUDE.md` (read second)
- `LICENSE`
- `api-1.yaml`
- `overlays/plaky115-dx.overlay.yaml`
- `openapi/plaky115-expected-operations.json`
- `openapi/plaky115-dx.openapi.yaml`
- `openapi/plaky115-operation-metadata.json`
- `openapi/upstream-manifest.json`
- `sdk/src/index.ts`
- `sdk/src/client/*`
- `sdk/src/runtime/*`
- `sdk/src/resolvers/index.ts`
- `sdk/src/workflows/*`
- `mcp-server/src/server/*`
- `mcp-server/src/runtime/*`
- `mcp-server/src/tools/raw/*`
- `mcp-server/src/tools/curated/*`
- `sdk/test/*`
- `sdk/test-d/*`
- `mcp-server/test/*`
- `scripts/test-*.mjs`
- `scripts/test-cross-surface-parity.mjs` (`sdkInvokers` is the explicit SDK map)
- `cli/internal/cli/*_test.go`
- `cli/internal/plakydx/*_test.go`
- `cli/internal/plakysdk/*_test.go`
- `scripts/lib/verification-plan.mjs`
- `scripts/live-read-sweep.mjs`
- `docs/live-smoke.md`
- `.github/workflows/*`
- `docs/*`

For MCP implementation details, use the final `2026-07-28` specification and
the official Python SDK source/docs corresponding to the locked release
`v2.0.0` (`https://github.com/modelcontextprotocol/python-sdk/tree/v2.0.0`).
Do not copy examples from the legacy v1 API or rely on mutable `main` when an
immutable tag exists.

---

## 21. Final principle

The target is not “a Python translation that compiles.” The target is a small,
explicit, source-backed Python product whose SDK and MCP surfaces are complete,
safe under failure, deterministic to maintain, easy to read, and objectively
verified end to end.
