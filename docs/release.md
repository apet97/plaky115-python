# Release checklist

1. Clean worktree; version and changelog agree.
2. `uv run python scripts/verify.py --offline` green.
3. `uv build`; `uv run twine check dist/*`;
   `uv run python scripts/package_smoke.py dist/*.whl`.
4. Live read certification green (docs/live-certification.md).
5. Separately authorized: remote push, tag (exact version + commit), and
   trusted publishing from CI consuming the exact verified artifact.
   Never rebuild between verification and publication. The release
   workflow enforces this: the tag must match `v[0-9]*` and point at a
   commit on `main`, the built version must equal the tag, the full gate
   suite runs with the online dependency audit
   (`scripts/verify.py --release-online`), and the publish job consumes
   the artifacts that the verify job built. The `pypi` environment only
   deploys from `v[0-9]*` tags.
6. After publication: verify registry version visibility, fresh-install
   the published artifact, compare digests, verify provenance, and
   reconcile repository/commit/workflow/tag.

Environment variables and credentials are interlocks, not authorization.

## Publication receipts

- v1.2.1 (2026-08-14): registry=pypi.org, project=plaky115,
  version=1.2.1, tag=v1.2.1 on commit 49c1113, workflow run 31764762761,
  wheel sha256
  `fb8e96eb67c4d30745205a879606df7eed6eed79e2c6f582bfb1b747664c8397`,
  trusted publishing (OIDC) with attestations. Host-compat fix: tool
  results mirror structured payloads into the text block for text-only
  hosts (claude.ai custom connectors). Deployed to plaky115-mcp-cloud
  staging and live-verified on claude.ai the same day.
- v1.2.0 (2026-08-14): registry=pypi.org, project=plaky115,
  version=1.2.0, tag=v1.2.0 on commit 2c116f2, workflow run 31759925289,
  wheel sha256
  `6b9e2aa06239aa96c2eb7e30b23bc773e3dbbc0a57603da002129769aa5f4d1d`,
  sdist sha256
  `32a00fa668465e3be70bd3d3cb846f823aba26132c7be1d1d592835ba4f17d76`,
  trusted publishing (OIDC) with attestations. Verified installable in a
  scratch venv: `pip install "plaky115[mcp]==1.2.0"`; an in-memory MCP
  client lists `plaky_board_view` with `_meta.ui.resourceUri`, reads
  `ui://plaky115/board-view.html` as `text/html;profile=mcp-app`, and
  lists 49 resources including `plaky115://skills/board-workflow`.
- v1.1.0 (2026-08-14): registry=pypi.org, project=plaky115,
  version=1.1.0, tag=v1.1.0 on commit 683d7e2, workflow run 31757232499,
  wheel sha256
  `11b7b63ada2794fa502e15d27daa3da207538c794a347d428644db7caefdb158`
  (identical for the verify-job digest and the PyPI download), trusted
  publishing (OIDC) with attestations. Verified installable:
  `pip install "plaky115[mcp]==1.1.0"` imports the SDK and the MCP
  package, and the `plaky115-mcp` CLI runs. The first two attempts on
  this tag failed closed before publication: attempt 1 was rejected by
  PyPI (dirty local version), attempt 2 by the artifact-version gate;
  the root cause (uv rewriting the old-format `uv.lock`) is fixed in
  683d7e2.
- v1.0.0 (2026-08-13): version=1.0.0, tag=v1.0.0 on commit c03f0d3,
  workflow run 31736901309, dist sha256
  `7dacb780ecc9ad9f41138421cd3ed8f8e23cd0178e464a03c7b1ea7f5ae07f61`,
  trusted publishing (OIDC) with attestations; install smoke passed.
