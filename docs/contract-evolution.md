# Contract evolution

1. `uv run python scripts/contract.py fetch --url <openapi-url>` writes the
   candidate into `contract/candidate/` only.
2. `uv run python scripts/contract.py diff` prints a semantic report:
   operations, schemas, and security changes.
3. Review the diff. Update `contract/expected-operations.json` and
   `contract/operation-overrides.yaml` deliberately (SDK mapping, MCP
   metadata, safety classification) for any new or changed operation.
4. `uv run python scripts/contract.py accept` promotes the candidate and
   records provenance in `contract/source-manifest.json`.
5. `uv run python scripts/contract.py build && uv run python
   scripts/generate.py` regenerates all derived artifacts; review the full
   drift; run `uv run python scripts/verify.py --offline`.

`accept` never runs implicitly. Generated files are never edited by hand.
