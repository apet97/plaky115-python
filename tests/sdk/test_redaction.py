"""Redaction gates against the source conformance corpus."""

import json
from pathlib import Path

from plaky115.runtime.redaction import bound_text, presentation_text, redact, redact_value

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_source_corpus() -> None:
    corpus = json.loads(
        (FIXTURES / "security/plaky-api-key-cases.json").read_text(encoding="utf-8")
    )
    assert corpus["marker"] == "[REDACTED_PLAKY_API_KEY]"
    for case in corpus["cases"]:
        source = "".join(case["inputParts"])
        expected = "".join(case["expectedParts"])
        assert redact(source) == expected, case["name"]


def test_redact_value_scrubs_keys_and_values() -> None:
    value = {"plk_secretkey": "plk_another", "nested": [{"k": "x plk_abc y"}]}
    result = redact_value(value)
    text = json.dumps(result)
    assert "plk_secretkey" not in text
    assert "plk_another" not in text
    assert "plk_abc" not in text
    assert text.count("[REDACTED_PLAKY_API_KEY]") == 3


def test_redact_value_returns_unserializable_unchanged() -> None:
    marker = object()
    assert redact_value(marker) is marker


def test_presentation_text_caps_at_1024() -> None:
    long = "x" * 3000
    out = presentation_text(long)
    assert len(out) == 1024
    assert out.endswith("…")
    assert presentation_text("x" * 1024) == "x" * 1024


def test_bound_text_replaces_control_characters() -> None:
    out = bound_text("a\x00b\x1fc\x7fd\ne")
    assert out == "a b c d e"


def test_bound_text_redacts_and_caps() -> None:
    out = bound_text("key plk_abc end", 10)
    assert "plk_abc" not in out
    assert len(out) == 10
    assert out.endswith("…")
