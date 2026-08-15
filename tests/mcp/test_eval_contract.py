"""Provider-neutral MCP evaluation corpus and scorer tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]


def _case(identifier: str, **overrides: object) -> dict[str, object]:
    case: dict[str, object] = {
        "id": identifier,
        "prompt": "List the available workspace context.",
        "mode": "curated",
        "scopes": ["read"],
        "expectedTool": "plaky_workspace_context",
        "expectedArguments": {},
        "forbiddenTools": [],
        "safetyAssertions": [],
    }
    case.update(overrides)
    return case


def _run_scorer(
    tmp_path: Path,
    cases: list[dict[str, object]],
    predictions: list[dict[str, object]],
) -> subprocess.CompletedProcess[str]:
    cases_path = tmp_path / "cases.json"
    predictions_path = tmp_path / "predictions.jsonl"
    cases_path.write_text(json.dumps(cases), encoding="utf-8")
    predictions_path.write_text(
        "\n".join(json.dumps(prediction) for prediction in predictions), encoding="utf-8"
    )
    return subprocess.run(
        [
            sys.executable,
            "scripts/score_mcp_predictions.py",
            "--cases",
            str(cases_path),
            "--predictions",
            str(predictions_path),
        ],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_eval_corpus_is_valid_and_fixed_predictions_score_perfectly(tmp_path: Path) -> None:
    cases = json.loads((REPO / "evals/mcp-cases.json").read_text(encoding="utf-8"))
    predictions: list[dict[str, object]] = [
        {
            "id": case["id"],
            "tool": case["expectedTool"],
            "arguments": case["expectedArguments"],
        }
        for case in cases
    ]
    path = tmp_path / "predictions.jsonl"
    path.write_text(
        "\n".join(json.dumps(prediction) for prediction in predictions), encoding="utf-8"
    )
    completed = subprocess.run(
        [sys.executable, "scripts/score_mcp_predictions.py", "--predictions", str(path)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result["caseCount"] >= 10
    assert result["toolSelectionAccuracy"] == 1.0
    assert result["schemaValidRate"] == 1.0
    assert result["forbiddenToolRate"] == 0.0
    assert result["dryRunSafetyRate"] == 1.0
    assert json.dumps(result["details"])


def test_eval_safety_rate_counts_only_safety_cases(tmp_path: Path) -> None:
    cases = [
        _case("has-safety", safetyAssertions=["forbiddenToolAbsent"]),
        _case("no-safety"),
    ]
    predictions: list[dict[str, object]] = [
        {"id": case["id"], "tool": case["expectedTool"], "arguments": case["expectedArguments"]}
        for case in cases
    ]
    completed = _run_scorer(tmp_path, cases, predictions)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["safetyCaseCount"] == 1
    assert result["dryRunSafetyRate"] == 1.0

    completed = _run_scorer(
        tmp_path,
        [_case("no-safety")],
        [_case("no-safety") | {"tool": "plaky_workspace_context", "arguments": {}}],
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["safetyCaseCount"] == 0
    assert result["dryRunSafetyRate"] == 0.0


def test_eval_safety_detects_invented_ids_after_absent_or_nested_ids(tmp_path: Path) -> None:
    cases = [
        _case("absent-id", safetyAssertions=["noInventedIds"]),
        _case("nested-absent-id", safetyAssertions=["noInventedIds"]),
    ]
    predictions: list[dict[str, object]] = [
        {
            "id": "absent-id",
            "tool": "plaky_workspace_context",
            "arguments": {"itemId": None, "boardId": 999},
        },
        {
            "id": "nested-absent-id",
            "tool": "plaky_workspace_context",
            "arguments": {"nested": {"itemId": None, "boardId": 999}},
        },
    ]
    completed = _run_scorer(tmp_path, cases, predictions)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert [detail["safetyPassed"] for detail in result["details"]] == [False, False]


@pytest.mark.parametrize(
    "overrides",
    [
        {"mode": "unsupported"},
        {"scopes": "read"},
        {"forbiddenTools": "plaky_delete_item"},
        {"safetyAssertions": "noInventedIds"},
        {"safetyAssertions": ["unknownAssertion"]},
    ],
)
def test_eval_corpus_rejects_invalid_contract_fields(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    case = _case("invalid", **overrides)
    completed = _run_scorer(
        tmp_path,
        [case],
        [{"id": "invalid", "tool": "plaky_workspace_context", "arguments": {}}],
    )
    assert completed.returncode == 2
    assert "MCP EVAL FAIL:" in completed.stderr


def test_eval_reports_missing_and_extra_prediction_ids(tmp_path: Path) -> None:
    cases = [_case("expected"), _case("missing")]
    completed = _run_scorer(
        tmp_path,
        cases,
        [
            {"id": "expected", "tool": "plaky_workspace_context", "arguments": {}},
            {"id": "extra", "tool": "plaky_workspace_context", "arguments": {}},
        ],
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["missingPredictionIds"] == ["missing"]
    assert result["extraPredictionIds"] == ["extra"]


def test_eval_rejects_malformed_tool_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_mcp_predictions", REPO / "scripts/score_mcp_predictions.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def malformed_schemas(_case: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {"plaky_workspace_context": {"type": "not-a-json-schema-type"}}

    monkeypatch.setattr(module, "_schemas_for_case", malformed_schemas)
    with pytest.raises(ValueError, match="invalid JSON Schema"):
        module.score(
            [_case("malformed")],
            {"malformed": {"id": "malformed", "tool": "plaky_workspace_context", "arguments": {}}},
        )
