"""Current documentation claims that must track the MCP and SDK boundaries."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_remediation_docs_keep_current_behavior_and_proof_boundaries() -> None:
    sdk = (REPO / "docs/sdk.md").read_text(encoding="utf-8")
    transport = (REPO / "docs/port/spec-transport.md").read_text(encoding="utf-8")
    mcp = (REPO / "docs/mcp.md").read_text(encoding="utf-8")
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    release = (REPO / "docs/release.md").read_text(encoding="utf-8")

    timeout_contract = "Async attempts use one total timeout budget; backoff is outside it."
    assert timeout_contract in sdk
    assert timeout_contract in transport
    for document in (sdk, transport):
        assert "Sync cannot safely interrupt" in document
        assert "a local provider or hook" in document
    assert (
        "Fixed mutation bodies use the generated Plaky request models and reject unknown keys."
        in " ".join(mcp.split())
    )
    for method in (
        "server/discover",
        "tools/list",
        "prompts/list",
        "resources/list",
        "resources/templates/list",
        "resources/read",
    ):
        assert method in mcp
    assert "provider-neutral" in contributing and "not model proof" in contributing
    assert "Marketplace" in release and "production" in release and "staging" in release
