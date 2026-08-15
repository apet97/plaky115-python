# Transport behavioral spec (pinned source 33ae2926, v1.0.11)

Extracted from `sdk/src/runtime/http.ts`, `errors.ts`, `redact.ts`,
`idempotency.ts`, `user-agent.ts`, `rate-limit.ts`, `retries.ts`,
`interceptors.ts`, `internal/{validation,fetcher,request-builders,responses,retry-policy}.ts`,
and `client/client.ts`. This is the parity contract for the Python port.

## Errors

- Hierarchy: PlakyError → {Connection, Timeout, Abort/Cancelled, Decode →
  ResponseContract, ResponseTooLarge, AmbiguousMatch, PartialMutation,
  UploadValidation, Api → {Auth 401, Permission 403, NotFound 404, Conflict
  409, Validation 400, UnprocessableEntity 422, RateLimit 429, Server 5xx}}.
- 3xx and unmapped statuses → bare PlakyApiError. Message is always the
  normalized problem message (no "HTTP 500:" prefixing).
- PlakyResponseTooLargeError message: `Plaky API response exceeds the
  {limit}-byte buffer limit.`
- PlakyResponseContractError message: `Invalid {operationId} response at
  {pointer}.`
- ApiError fields: status, method, url (FULL url, verbatim, un-redacted —
  no query stripping), headers, body (raw bounded, un-redacted), problem,
  request_id, code, retry_after_ms.
- readErrorCode precedence: body.errorCode → body.error.code → body.code
  (str or number only).

## normalize_problem(body, status)

- String body → {family: unknown, status, message: presentation_text(body)}.
- message fallback: detail → message → error.message (or string error) →
  title → errorLabel → `HTTP {status}`; empty strings skipped.
- family: rfc7807 if any of detail/title/type/instance present; validation
  if errorCode/errorLabel/violations; legacy if message/error; else unknown.
  Presence, not truthiness.
- violations: capped at first 100, deep-redacted.
- presentation_text: redact + cap 1024 chars (1023 + "…").

## Retry policy

- Only GET retries. Idempotency-Key never enables write retries.
- Retryable statuses: 429 and 500–599 only.
- Thrown errors: Abort → never retried; Timeout → retried (GET);
  other → coerced to PlakyConnectionError then retried (GET).
- Anything after a received response (decode, hooks, too-large) → never
  retried.
- Backoff: capped = min(60_000, 250 * 2**attempt) ms; equal jitter
  [capped/2, capped). attempt is 0-based.
- Retry-After: seconds (float; JS Number semantics) or HTTP-date; used for
  the sleep clamped to [0, 60000] ms, bypassing jitter. Raw parsed ms stored
  on PlakyRateLimitError.retry_after_ms unclamped.
- max_retries = retries after the first attempt (2 → 3 total). Client
  default 2; transport-level default 0.
- Backoff sleep is cancellable; cancellation raises abort error immediately.
- Rate-limit sink observes EVERY received response before retry decision.

## Redaction

- Pattern: `plk_[A-Za-z0-9_-]+` → `[REDACTED_PLAKY_API_KEY]`.
  Bare `plk_` not redacted. Conformance corpus:
  test/fixtures/security/plaky-api-key-cases.json in source.
- redact_value: JSON round-trip; scrubs keys and values; non-serializable
  returned unchanged.
- presentation_text (errors): cap 1024, NO control-char stripping.
- bound_text (mutations/uploads): redact + control chars (<0x20, 0x7f) →
  space + cap. Receipt caps: operation 256, targetIds keys/values 128,
  error.name 128, error.message 1024.

## Headers

- Order: Accept: application/json; User-Agent; X-API-Key; then user headers
  merged (may override/delete any); Content-Type: application/json only for
  JSON-encodable bodies without existing Content-Type; Idempotency-Key from
  options only if truthy and not already set by user headers.
- merge_headers_into: case-insensitive; value "" deletes the key; set not
  append; source normalized lowercase-sorted.
- resolve_api_key: provider or literal; non-string/blank →
  `PlakyClient: api key provider returned an invalid value` (never includes
  the value). Resolved fresh once per attempt. Literal blank key at
  construction → `PlakyClient: apiKey is required`.
- user_agent: `plaky115/{version} python/{python_version}` (+ ` {suffix}`
  when truthy). options.user_agent REPLACES the whole header.

## Responses

- Limits: default 16 MiB, option ceiling 64 MiB; error message
  `PlakyClient: maxResponseBytes must be an integer between 1 and 67108864`.
- Enforced streamed: content-length pre-check, then chunk accumulation;
  strictly > limit fails; exactly limit OK. Both success and error bodies.
- responseType: json | text | bytes | stream | void. 204/205 → None.
  Empty body json → None (not an error). stream bypasses the limit.
- Malformed 2xx JSON → PlakyDecodeError("Failed to parse the Plaky API
  response body.") with status/request_id; error bodies degrade to raw text
  (never DecodeError): "Failed to parse the Plaky API error body." only for
  bound/abort failures.
- Unsafe JSON int64 preservation: integer literals with |v| >
  9007199254740991 decode to exact decimal STRINGS; safe integers stay ints;
  floats/exponents stay numbers; strings untouched. Python:
  json.loads(text, parse_int=hook). Generated models type int64 fields as
  `int | str`, so preserved decimal strings validate and re-serialize as
  strings.
- request id: x-request-id → request-id → x-correlation-id.
- Paged root checks in order: plain object "/", data present "/data",
  data array "/data", hasMore present "/hasMore", hasMore bool "/hasMore",
  empty data + hasMore=true "/hasMore".
- Redirects: never followed; a 3xx classifies as PlakyApiError.
- URL building: base + path; query skips None; empty arrays skipped;
  expand comma-joined (explode false); other arrays repeated keys;
  Date → ISO; bool → JS String(bool) i.e. lowercase.

## Idempotency

- Header: `Idempotency-Key`. new_idempotency_key(prefix="idmp") →
  `{prefix}_{uuid4}`. resolve_explicit: param → option → None (no header).
  No validation anywhere; empty string → header omitted.

## Hooks

- request hook per attempt: ctx {url, init, operation_id}; may rewrite
  path/query/headers; origin change →
  `PlakyClient: request interceptor must not change the trusted server
  origin`; invalid URL → `PlakyClient: request interceptor returned an
  invalid URL`. Hook errors not retried.
- response hook: observe-only, invoked on success AND error paths (before
  classify raise), not on retried attempts; errors propagate, never retried.
- operation_id defaults to `{METHOD} {path}`.

## Timeout

- Default 30 s; 0 disables; max 2_147_483.647 s. Async uses a fresh total
  per-attempt budget across providers, hooks, I/O, bounded body reads, parsing,
  and response hooks. Async attempts use one total timeout budget; backoff is outside it.
  Sync uses the HTTP client's native I/O timeout. Sync cannot safely interrupt
  a local provider or hook. A GET timeout or connection failure retries only before
  response headers arrive. After headers, body, decode, and hook failures do
  not retry. External task cancellation remains `asyncio.CancelledError`.
  Native HTTP timeouts map to `PlakyTimeoutError("Request timed out.")`.

## with_retries(fn, kind="read", max_retries=2, base_delay_ms=250)

- kind != "read" → Error "withRetries only supports kind=read" before
  calling fn.
- Validation messages: "maxRetries must be a finite non-negative integer",
  "baseDelayMs must be a finite non-negative number".
- Default retryable: PlakyRateLimitError or PlakyApiError 5xx only (NOT
  timeout/connection).
- Wait: retry_after (clamped ≤60s) if >0 else base * 2**attempt (uncapped);
  plus additive uniform [0,100) ms jitter in both branches.

## RateLimitTracker

- Window 60 s, max 200. Headers: x-ratelimit-limit / -remaining / -reset.
  reset_at stores the header value exactly as sent (header-native units;
  no unit normalization).
- last replaced wholesale per observe; observe also records a timestamp.
- estimated_remaining: server remaining wins unclamped; else
  max(0, max - len(window)). would_throttle: remaining <= 0.
  seconds_until_next_slot: 0 if under max else oldest + window - now.
- prune: drop timestamps <= now - window.

## server_url validation

- Absolute HTTPS (or loopback HTTP: localhost, ::1, 127.x.x.x) with host;
  no surrounding whitespace; no credentials; no query/fragment; trailing
  slashes normalized away.
- Messages: `PlakyClient: serverURL must be an absolute HTTPS URL (or
  loopback HTTP) with a host` / `...must not include credentials` /
  `...must not include a query or fragment`.

## Non-features (do NOT invent)

- No URL query/fragment stripping in errors.
- No user-agent suffix validation.
- No idempotency key validation.
- No control-char sanitizing in HTTP error messages (only mutations/uploads).
- No retry of decode/hook failures; no mutation retries ever.
