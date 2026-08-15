# Release checklist

1. Confirm a clean worktree, agreed version, and changelog entry.
2. Run `uv run python scripts/verify.py --offline`.
3. Run bounded live-read certification from `docs/live-certification.md`.
4. Obtain separate authority for push, exact-version tag, and trusted
   publication. Never rebuild between verification and publication.
5. The release workflow accepts only `v[0-9]*` tags on `main`, checks the
   built version against the tag, and publishes the exact artifacts from its
   verify job.
6. Release verification clones `apet97/plaky115` at
   `33ae2926aa696f36d9663d44f914d42d9aadc53f`; parity fails if that checkout
   is absent, dirty, or at another commit. The package worktree must also
   stay clean, apart from ignored build artifacts.
7. After publication, verify registry visibility, fresh installation, artifact
   digest, and tag/commit/workflow provenance.

Environment variables and credentials are interlocks, not authorization.

Package verification, Cloud staging, production deployment, Marketplace
listing, and published release proof are separate evidence boundaries. Local
gates prove only the package candidate. Keep past release receipts in history
or an evidence archive, not in this current-release checklist.

Cloud compatibility is a separate handoff after publication. It needs an
exact package version and digest, an independent staging deployment, and a
bounded live compatibility receipt. A package release does not trigger cloud
deployment or prove production readiness.
