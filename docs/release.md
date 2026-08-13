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
