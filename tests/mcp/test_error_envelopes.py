"""Stable, redacted diagnostics exposed at the MCP error boundary."""

import logging

import pytest

from plaky115.errors import (
    PlakyAmbiguousMatchError,
    PlakyOutputLimitError,
    PlakyPartialMutationError,
    PlakyResponseContractError,
    UploadValidationError,
)
from plaky115.runtime.mutations import new_receipt, transition_receipt
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error


def test_error_envelope_exposes_only_safe_stable_diagnostics() -> None:
    cases = [
        (
            UploadValidationError("bad", code="invalid-filename", path="fileName"),
            {"code": "invalid-filename", "path": "fileName"},
        ),
        (
            PlakyOutputLimitError("items", 10),
            {"limit": "items", "maximum": 10},
        ),
        (
            PlakyAmbiguousMatchError("many", candidates=[{"secret": "no"}], candidate_count=2),
            {"candidateCount": 2},
        ),
        (
            PlakyResponseContractError("getItem", "/data/0"),
            {"operationId": "getItem", "pointer": "/data/0"},
        ),
        (
            PlakyPartialMutationError(
                "one failed",
                receipts=(new_receipt("updateItemFields", 0, {}),),
                failed_index=0,
            ),
            {"failedIndex": 0},
        ),
    ]

    for error, expected in cases:
        detail = envelope_wire(error_envelope(error))["error"]
        assert {key: detail[key] for key in expected} == expected
        assert "secret" not in str(detail)


def test_partial_mutation_envelope_derives_conservative_truth_from_receipts() -> None:
    planned = new_receipt("items.updateFields", 0, {"itemId": "1"})
    completed = transition_receipt(planned, "completed", "completed")
    ambiguous = transition_receipt(
        new_receipt("items.updateFields", 1, {"itemId": "2"}),
        "ambiguous",
        "response",
        RuntimeError("late failure"),
    )

    ambiguous_wire = envelope_wire(
        error_envelope(
            PlakyPartialMutationError("partial", receipts=(completed, ambiguous), failed_index=1)
        )
    )["error"]
    assert ambiguous_wire["attempted"] is True
    assert ambiguous_wire["mayHaveCommitted"] is True
    assert ambiguous_wire["phase"] == "response"
    assert ambiguous_wire["retryable"] is False

    completed_wire = envelope_wire(
        error_envelope(
            PlakyPartialMutationError("progress", receipts=(completed,), failed_index=0)
        )
    )["error"]
    assert completed_wire["attempted"] is True
    assert completed_wire["mayHaveCommitted"] is False
    assert completed_wire["phase"] == "completed"

    preflight_wire = envelope_wire(
        error_envelope(PlakyPartialMutationError("preflight", receipts=(planned,), failed_index=0))
    )["error"]
    assert preflight_wire["attempted"] is False
    assert preflight_wire["mayHaveCommitted"] is False
    assert preflight_wire["phase"] == "preflight"


def test_internal_error_logs_only_class_and_correlation(caplog: pytest.LogCaptureFixture) -> None:
    canary = (
        "comment-canary bearer-canary https://download.example.test/file?sig=signed-canary "
        "YmFzZTY0LWNhbmFyeQ=="
    )
    caplog.set_level(logging.ERROR, logger="plaky115_mcp")
    envelope = internal_error(RuntimeError(canary))
    assert canary not in caplog.text
    assert "RuntimeError" in caplog.text
    assert "Internal server error (correlation " in envelope.error.message
    assert canary not in envelope.error.message
