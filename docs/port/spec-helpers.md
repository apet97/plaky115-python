# Helpers/workflows behavioral spec (pinned source 33ae2926, v1.0.11)

Extracted from `sdk/src/client/path.ts`, `runtime/{pagination,chunks,upload,mutations}.ts`,
`fields/*`, `resolvers/index.ts`, `workflows/*`, `workflows/internal/csv.ts`
and their tests. Parity contract for the Python port.

## IDs (client/path.ts)

- idPathSegment: numbers must be safe non-negative integers →
  `ID numbers must be non-negative safe integers; use a decimal string for
  larger int64 IDs`; strings must match `^(0|[1-9]\d*)$` and be ≤
  9223372036854775807 → `IDs must be canonical non-negative signed int64
  decimal strings`. No trim, no coercion. Booleans rejected.
- pathSegment (percent-encode) used ONLY for the item field-key segment;
  JS encodeURIComponent semantics: safe chars `A-Za-z0-9 - _ . ! ~ * ' ( )`.
- FieldKey has zero validation in the source (brand only).

## Pagination (runtime/pagination.ts)

- DEFAULT_PAGE_SIZE=100 (private), MAX_PAGES=10_000.
- paginate(fetcher, {page_size, limit}): page starts at 1;
  "pageSize must be a positive integer." / "limit must be a non-negative
  integer." / "Pagination exceeded 10000 pages." (guard BEFORE fetch).
- limit=0 legal, yields nothing. Fetcher failure retryable at same page
  (page increments only after success).
- first_page(): always fetches page 1 fresh; does not advance iterator.
- pages(): independent cursor; yields Page objects; ignores limit; stops
  after last page yielded.
- to_list(limit=None): own cursor; min of iterator limit and arg limit.
- Page root checks: see transport spec (6 checks, exact pointers).

## Chunks (runtime/chunks.ts)

- DEFAULT_CHUNK_MAX_ITEMS=100, DEFAULT_CHUNK_MAX_BYTES=1_048_576,
  MAX_MATERIALIZED_ITEMS=10_000, MAX_MATERIALIZED_BYTES=16_777_216.
- PlakyOutputLimitError(limit ∈ {"items","bytes"}, maximum), message:
  `Output {limit} limit of {maximum} was reached before the next item could
  be returned.` MaterializationLimitError subclass, same template.
- utf8_byte_length = len(s.encode("utf-8")).
- Cursor {page≥1, index≥0}: "cursor.page must be a positive safe integer." /
  "cursor.index must be a non-negative safe integer."; generic templates
  `{name} must be a positive safe integer.` / `{name} must be a non-negative
  safe integer.`
- read_paged_chunk: maxItems=0 → immediate items limit error. Per item:
  items cap → truncate at {page, index of first omitted}; byte accounting =
  utf8 bytes of serialize(item) (default JSON, no separators); single item
  over byte budget with empty chunk → raise bytes limit error; else
  truncate. Page exhausted + hasMore + (items or bytes at cap) → cursor
  {page+1, 0}. !hasMore → complete, NO nextCursor key. cursor.index > page
  length → ResponseContractError("boundedChunk","/data"); == allowed.
- Chunk shape: {data, scanned=returned=len(data), bytes, complete,
  truncated, next_cursor?}.
- iterate_paged_chunks: yields final chunk then stops; close() prevents
  further fetches.

## Uploads (runtime/upload.ts)

- Constants: 25 MiB = 26_214_400 hard ceiling; filename ≤ 255 UTF-8 bytes;
  default content type application/octet-stream.
- CANONICAL_BASE64 = ^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$
- TOKEN (tchar) = ^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$
- Control chars: code < 0x20 or 0x7f–0x9f, by code point.
- Error codes: invalid-filename, invalid-media-type, invalid-base64,
  upload-too-large, invalid-limit. Messages exactly:
  "fileName must be non-empty." / "fileName must not contain slash or
  control characters." / "fileName must not exceed 255 UTF-8 bytes." /
  "contentType must be a valid media type." / "fileBase64 must be canonical
  base64." / "Decoded upload exceeds the configured limit of {limit} bytes."
  / "maxBytes must be between 1 and 26214400."
- Filename: no trim; ".." allowed; slash/backslash/control rejected.
- Media type: split on ; outside double quotes with \ escapes; head not
  trimmed ("text/plain ; x" rejected); exactly one /; type/subtype
  lowercased; params name lowercased, value original case incl. quotes;
  output joined with ";" no spaces.
- estimate: (len/4)*3 - padding. decode: estimate → size check → decode →
  round-trip re-encode must equal input. normalize_upload: decode once,
  SHA-256 lowercase hex. Test vector: "aGVsbG8=" → 5 bytes, sha256
  2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824.
- Binary (Blob) uploads: non-bytes → invalid-filename code, path "file",
  "file must be a Blob." (Python: bytes/file-like). fileName default
  literal "blob". Size > ceiling → upload-too-large (always hard ceiling).
- Multipart: single field named "file"; SDK sets no Content-Type header.

## Mutations (runtime/mutations.ts, workflows/mutation-plans.ts)

- NormalizedMutationPlan: {version: 1, operationId, targetIds (str→str),
  body, writeCount: 1, requiresLiveResolution, upload?}. Frozen.
- DryRunPlan: {dryRun: true, operation, payload: {...targetIds, body},
  targetIds, writeCount, requiresLiveResolution}. Only items.create and
  items.updateFields expose dry_run in the SDK.
- Plan validation errors (TypeError): `{path} must be a plain object`,
  `{label}: {idPathSegment message}`, `{label} must be a number or decimal
  string`, `body.{key} must be a non-empty string`, `body.{key} must be a
  non-empty string when provided`, `body.color must be a six-digit RGB
  hexadecimal color` (#RRGGBB), `body.groupId and body.groupTitle cannot
  both be provided`.
- normalizeItemCreatePlan: requiresLiveResolution = groupTitle present.
  groupId/parentId canonicalized in place. Empty body valid.
- normalizeItemGroupCreatePlan: title req, color req, ranking opt.
  UpdatePlan: title req, ranking req, color req.
- normalizeCommentPlan: text req; operationId param default
  createItemComment. normalizeItemFileUpdatePlan: body.name via full
  filename validation.
- Upload plans: body {}; base64 NEVER in body; upload metadata
  {fileName, mediaType, decodedBytes, sha256} on plan.upload.
- Receipts: statuses planned|request-started|completed|failed|ambiguous
  ("failed" declared, never produced); phases preflight|request|response|
  completed. attempted = status != planned; mayHaveCommitted = status in
  (ambiguous, request-started). Any post-dispatch error → ambiguous.
  error {name, message} bounded (128/1024); omitted when absent.
- PlakyPartialMutationError: message bounded 1024; receipts frozen;
  failed_index optional.

## Fields (fields/*)

- field_values, string_field, status_field, tag_field: identity.
- omit_none: drops only undefined (Python: drop None — document the
  deviation OR use sentinel; port decision: drop None, matching "absent
  optional values").
- person_field: numbers → {id: n}; object refs pass through unchanged;
  absent keys omitted; empty arrays preserved.
- timeline_field: falsy start or end → Error("timelineField: both start and
  end are required (ISO date strings)"); no date parsing.
- link_field: falsy url → Error("linkField: url is required"); no URL
  validation. number_field: finite only →
  Error("numberField: value must be a finite number").
- field_label precedence: name → title → key, first non-empty string; ""
  means skip the field (lives in csv module in source).

## Resolvers (resolvers/index.ts)

- asId: number → id; string all-digits → canonical id (so "01" throws);
  other string → needle lowercased (no trim); {id} authoritative (labels
  ignored, no list call); exactly one of {title|name|email} → field selector
  (non-empty string else `{field} selector must be a non-empty string`);
  2+ selectors → `entity reference selectors conflict: {selectors}` (order
  title, name, email); else empty match.
- Resolver canonicalId messages (plain Error): "identifier must be a safe
  non-negative integer; pass larger identifiers as decimal strings" /
  "identifier must be a canonical non-negative decimal string" /
  "identifier exceeds signed int64 range".
- pick: id match by canonical equality; miss → local 404 `{label} not
  found: id={id}`. Needle: case-insensitive substring over
  title/name/email (or only declared field); 0 → `{label} not found:
  {needle}`; >1 → PlakyAmbiguousMatchError(`{label} ambiguous: {needle}`,
  ALL candidates, candidate_count; candidates non-enumerable). Empty ref →
  `{label}: empty ref`.
- Local 404: PlakyNotFoundError(status=404, method="LOCAL",
  url="plaky115://resolver", headers={}).
- getById: direct GET then pick([result]); transport 404 rewrapped as local
  `{label} not found: id={id}`.
- resolveUser: ALWAYS lists (no user GET endpoint). resolveTeam: GET for
  id. resolveSpaceAndBoard: space resolved once. resolveItemsInBoard:
  all-ID → concurrent direct GETs order preserved; else exactly one
  listAll; empty items → list branch → []. Labels: space, board, user,
  team, item, "item group", "item file". Options/signal forwarded to all
  calls.

## Workflows (workflows/index.ts)

- workspace_map: maxItems def 10_000 / maxBytes def 16_777_216, each
  `{name} must be a non-negative safe integer.`; spaces.listAll(expand=
  [board], limit=maxItems+1); materialization checks (items then bytes per
  collection); space.boards array (even []) used as-is else boards.listAll;
  entry exactly {id, title, boards}; running output byte budget separate.
- search_items_detailed: limit def 200, `limit must be a finite positive
  integer` BEFORE any I/O; needle lowercased no trim; cursor `cursor must
  contain a positive page and non-negative index`; pageSize =
  min(100, limit - scanned); `item search cursor index {index} exceeds page
  {page} length`; `item search page {page} was empty while hasMore was
  true`; onProgress(scanned, limit) after each page; truncated result adds
  continuation {page, index} + deprecated nextPage; complete result has NO
  continuation/nextPage keys; complete wins when limit hit at exact end.
- Match: title substring, else field.value scalars: str/num/bool →
  String(value); arrays flat; objects values by sorted keys (keys not
  searched); None skipped.
- search_items: thin deprecated wrapper returning .data.
- bulk_update_items: validate all updates BEFORE resolution/network
  ("updates must be an array", "updates[{i}] must be an object",
  "updates[{i}].itemId must be a number or decimal string",
  "updates[{i}].body must be a plain object"). Receipts operation
  "items.updateFields". Abort before first write → PartialMutationError
  "Bulk item update was aborted before the first write." (failedIndex 0);
  before next write → "...before the next write."; write error → receipt
  ambiguous, mayHaveCommitted true; throwOnError → "Bulk item update has an
  unconfirmed mutation outcome."; progress callback error → "Bulk item
  update progress reporting failed." Completed receipts never repeated.
  dryRun → all receipts stay planned, zero writes.
- export_items: format jsonl|csv; csv_safety def "spreadsheet";
  items.listAll(limit=maxItems+1) + materialization checks. JSONL: lines
  joined "\n" NO trailing newline; byte budget includes separators. CSV:
  whole-output byte check. Empty → "".
- read_item_chunk / iterate_item_chunks: readPagedChunk over items.list.
- read_item_export_chunk: JSONL serialize = JSON + "\n" (every line
  newline-terminated, unlike export_items). CSV: schema frozen from
  boards.get(board.fields) + seed page (cached, not refetched);
  maxBytes def 1_048_576 (chunk default); header bytes reserved
  (header > maxBytes → bytes materialization error); body "" when
  returned==0 and complete and includeHeader. iterate_item_export_chunks:
  header exactly once in chunk 0.

## CSV (workflows/internal/csv.ts)

- Safety modes spreadsheet|raw. Top columns: all item keys except
  "fields", set-deduped, sorted by code point.
- Field identity: "key:{key}" or "missing:{label}:{occurrence}" (per-item
  occurrence counter). First occurrence per identity wins within an item.
  Schema registers board definitions first, then seed items.
- Order: by (label, identity) code-point sort; missingIndex assigned 1..n in
  sorted order to keyless descriptors. Collision (top key or duplicate
  label): base = `{label} [{key}]` or `{label} [#{missingIndex}]`; then
  uniqueColumn appends ` [#1]`, ` [#2]`… against used set (top keys +
  taken).
- Cells: None → ""; str → protected (spreadsheet) or verbatim (raw);
  finite num → JSON; non-finite → "null"; bool → "true"/"false"; other →
  canonical JSON (sorted keys, no spaces, undefined dropped in objects /
  null in arrays).
- Formula protection: "" unchanged; first char \t/\r/\n → "'"+value; else
  strip leading spaces+tabs for the TEST only, if first remaining char in
  =+-@ → "'"+original.
- Quoting: contains " , \r \n OR starts with any Unicode whitespace →
  quote + double inner quotes. (Protected "'  -42" no longer quoted.)
- Rows joined "\n" with trailing "\n". Empty items → "". Chunk render with
  includeHeader and no items → header + "\n".
- Golden fixtures to port verbatim: test/fixtures/export/items.json,
  items.safe.csv, items.raw.csv (also test/fixtures/security/
  plaky-api-key-cases.json for redaction).
