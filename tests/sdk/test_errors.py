"""Error classification and problem normalization gates (spec-transport §1)."""

from typing import Any

import pytest

import plaky115.errors as errors
from plaky115.errors import classify, normalize_problem

STATUS_TABLE = [
    (400, errors.PlakyValidationError),
    (401, errors.PlakyAuthError),
    (403, errors.PlakyPermissionError),
    (404, errors.PlakyNotFoundError),
    (409, errors.PlakyConflictError),
    (422, errors.PlakyUnprocessableEntityError),
    (429, errors.PlakyRateLimitError),
    (500, errors.PlakyServerError),
    (599, errors.PlakyServerError),
    (302, errors.PlakyApiError),
    (418, errors.PlakyApiError),
]


@pytest.mark.parametrize(("status", "expected"), STATUS_TABLE)
def test_status_classification(status: int, expected: type[Exception]) -> None:
    error = classify(status=status, method="GET", url="https://x/y", headers={})
    assert type(error) is expected
    assert error.status == status


def test_message_is_normalized_problem_message() -> None:
    error = classify(
        status=404,
        method="GET",
        url="https://x/y?q=1",
        headers={"x-request-id": "rid"},
        body={"message": "Not found."},
        request_id="rid",
    )
    assert str(error) == "Not found."
    assert error.url == "https://x/y?q=1"  # full URL, verbatim
    assert error.request_id == "rid"


def test_error_code_precedence() -> None:
    assert (
        classify(
            status=400, method="GET", url="u", headers={}, body={"errorCode": "A", "code": "C"}
        ).code
        == "A"
    )
    assert (
        classify(
            status=400, method="GET", url="u", headers={}, body={"error": {"code": 7}, "code": "C"}
        ).code
        == 7
    )
    assert classify(status=400, method="GET", url="u", headers={}, body={"code": "C"}).code == "C"
    assert classify(status=400, method="GET", url="u", headers={}, body=[1]).code is None


def test_normalize_problem_string_body() -> None:
    problem = normalize_problem("boom plk_secret", 500)
    assert problem == {
        "family": "unknown",
        "status": 500,
        "message": "boom [REDACTED_PLAKY_API_KEY]",
    }


def test_normalize_problem_families() -> None:
    assert normalize_problem({"detail": "d"}, 400)["family"] == "rfc7807"
    assert normalize_problem({"errorCode": "E"}, 400)["family"] == "validation"
    assert normalize_problem({"message": "m"}, 400)["family"] == "legacy"
    assert normalize_problem({"error": "oops"}, 400)["family"] == "legacy"
    assert normalize_problem({}, 400)["family"] == "unknown"
    assert normalize_problem(None, 400)["family"] == "unknown"
    # Presence, not truthiness: an empty title still marks rfc7807.
    assert normalize_problem({"title": ""}, 400)["family"] == "rfc7807"


def test_message_fallback_chain() -> None:
    body: dict[str, Any] = {
        "detail": "D",
        "message": "M",
        "error": {"message": "N"},
        "title": "T",
        "errorLabel": "L",
    }
    assert normalize_problem(body, 400)["message"] == "D"
    del body["detail"]
    assert normalize_problem(body, 400)["message"] == "M"
    del body["message"]
    assert normalize_problem(body, 400)["message"] == "N"
    body["error"] = {}
    assert normalize_problem(body, 400)["message"] == "T"
    del body["title"]
    assert normalize_problem(body, 400)["message"] == "L"
    del body["errorLabel"]
    assert normalize_problem(body, 400)["message"] == "HTTP 400"


def test_violations_capped_and_redacted() -> None:
    body = {"violations": [{"k": f"v{i} plk_x"} for i in range(150)]}
    problem = normalize_problem(body, 400)
    assert len(problem["violations"]) == 100
    assert "plk_x" not in str(problem["violations"])


def test_empty_strings_skipped_in_fallback() -> None:
    assert normalize_problem({"detail": "", "message": "M"}, 400)["message"] == "M"


def test_abort_alias() -> None:
    assert errors.PlakyAbortError is errors.PlakyCancelledError


def test_response_contract_error_message() -> None:
    error = errors.PlakyResponseContractError("listSpaces", "/data")
    assert str(error) == "Invalid listSpaces response at /data."


def test_response_too_large_message() -> None:
    assert (
        str(errors.PlakyResponseTooLargeError(16777216))
        == "Plaky API response exceeds the 16777216-byte buffer limit."
    )
