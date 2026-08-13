# Release checklist

1. Clean worktree; version and changelog agree.
2. `uv run python scripts/verify.py --offline` green.
3. `uv build`; `uv run twine check dist/*`;
   `uv run python scripts/package_smoke.py dist/*.whl`.
4. Live read certification green (docs/live-certification.md).
5. Separately authorized: remote push, tag (exact version + commit), and
   trusted publishing from CI consuming the exact verified artifact.
   Never rebuild between verification and publication.
6. After publication: verify registry version visibility, fresh-install
   the published artifact, compare digests, verify provenance, and
   reconcile repository/commit/workflow/tag.

Environment variables and credentials are interlocks, not authorization.
