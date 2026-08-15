"""Typed errors, classification, and problem normalization.

Ported from sdk/src/runtime/errors.ts at the pinned source. Error messages
are always redacted, bounded presentation text; raw bounded bodies remain
available on PlakyApiError for SDK callers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from plaky115.runtime.redaction import presentation_text, redact_value

__all__ = [
    "NormalizedProblem",
    "PlakyAbortError",
    "PlakyAmbiguousMatchError",
    "PlakyApiError",
    "PlakyAuthError",
    "PlakyBoundedResultError",
    "PlakyCancelledError",
    "PlakyConflictError",
    "PlakyConnectionError",
    "PlakyDecodeError",
    "PlakyError",
    "PlakyMaterializationLimitError",
    "PlakyNotFoundError",
    "PlakyOutputLimitError",
    "PlakyPartialMutationError",
    "PlakyPermissionError",
    "PlakyRateLimitError",
    "PlakyResponseContractError",
    "PlakyResponseTooLargeError",
    "PlakyServerError",
    "PlakyTimeoutError",
    "PlakyUnprocessableEntityError",
    "PlakyValidationError",
    "UploadValidationError",
    "classify",
    "normalize_problem",
]


class PlakyError(Exception):
    """Base class for every SDK error."""


class PlakyConnectionError(PlakyError):
    def __init__(
        self, message: str = "Connection error while communicating with the Plaky API."
    ) -> None:
        super().__init__(message)


class PlakyTimeoutError(PlakyError):
    def __init__(self, message: str = "Request timed out.") -> None:
        super().__init__(message)


class PlakyCancelledError(PlakyError):
    def __init__(self, message: str = "Request was aborted.") -> None:
        super().__init__(message)


# Compatibility alias for the source's PlakyAbortError name.
PlakyAbortError = PlakyCancelledError


class PlakyDecodeError(PlakyError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id


class PlakyResponseContractError(PlakyDecodeError):
    def __init__(self, operation_id: str, pointer: str) -> None:
        super().__init__(f"Invalid {operation_id} response at {pointer}.")
        self.operation_id = operation_id
        self.pointer = pointer


class PlakyResponseTooLargeError(PlakyError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Plaky API response exceeds the {limit}-byte buffer limit.")
        self.limit = limit


class PlakyAmbiguousMatchError(PlakyError):
    def __init__(self, message: str, candidates: list[Any], candidate_count: int) -> None:
        super().__init__(message)
        self.candidates = tuple(candidates)
        self.candidate_count = candidate_count


class PlakyBoundedResultError(PlakyError):
    """A one-page reference lookup cannot make a conclusive decision."""


class PlakyOutputLimitError(PlakyError):
    """A configured byte or item bound was reached before the next item."""

    def __init__(self, limit: str, maximum: int) -> None:
        super().__init__(
            f"Output {limit} limit of {maximum} was reached "
            "before the next item could be returned."
        )
        self.limit = limit
        self.maximum = maximum


class PlakyMaterializationLimitError(PlakyOutputLimitError):
    """A materialized collection exceeds the safety bound."""


class UploadValidationError(PlakyError):
    def __init__(self, message: str, *, code: str, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


class PlakyPartialMutationError(PlakyError):
    def __init__(
        self,
        message: str,
        *,
        receipts: tuple[Any, ...],
        failed_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.receipts = receipts
        self.failed_index = failed_index


NormalizedProblem = dict[str, Any]


class PlakyApiError(PlakyError):
    def __init__(
        self,
        message: str,
        *,
        status: int,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Any = None,
        problem: NormalizedProblem | None = None,
        request_id: str | None = None,
        code: str | int | None = None,
        retry_after_ms: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.method = method
        self.url = url
        self.headers = dict(headers)
        self.body = body
        self.problem = problem
        self.request_id = request_id
        self.code = code
        self.retry_after_ms = retry_after_ms


class PlakyAuthError(PlakyApiError):
    pass


class PlakyPermissionError(PlakyApiError):
    pass


class PlakyNotFoundError(PlakyApiError):
    pass


class PlakyConflictError(PlakyApiError):
    pass


class PlakyValidationError(PlakyApiError):
    pass


class PlakyUnprocessableEntityError(PlakyApiError):
    pass


class PlakyRateLimitError(PlakyApiError):
    pass


class PlakyServerError(PlakyApiError):
    pass


def _as_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _read_error_code(body: Any) -> str | int | None:
    record = _as_record(body)
    if record is None:
        return None
    error_code = record.get("errorCode")
    if isinstance(error_code, str | int) and not isinstance(error_code, bool):
        return error_code
    nested = _as_record(record.get("error"))
    if nested is not None:
        nested_code = nested.get("code")
        if isinstance(nested_code, str | int) and not isinstance(nested_code, bool):
            return nested_code
    code = record.get("code")
    if isinstance(code, str | int) and not isinstance(code, bool):
        return code
    return None


def _problem_family(value: dict[str, Any] | None) -> str:
    if value is None:
        return "unknown"
    if any(key in value for key in ("detail", "title", "type", "instance")):
        return "rfc7807"
    if any(key in value for key in ("errorCode", "errorLabel", "violations")):
        return "validation"
    if any(key in value for key in ("message", "error")):
        return "legacy"
    return "unknown"


def normalize_problem(body: Any, status: int) -> NormalizedProblem:
    """Normalize Plaky, legacy, and RFC 7807-like error bodies."""
    if isinstance(body, str):
        return {"family": "unknown", "status": status, "message": presentation_text(body)}

    value = _as_record(body)
    nested = _as_record(value.get("error")) if value is not None else None
    detail = _string_value(value.get("detail")) if value is not None else None
    top_message = _string_value(value.get("message")) if value is not None else None
    nested_message = _string_value(nested.get("message")) if nested is not None else None
    if nested_message is None and value is not None:
        nested_message = _string_value(value.get("error"))
    title = _string_value(value.get("title")) if value is not None else None
    label = _string_value(value.get("errorLabel")) if value is not None else None
    code = _read_error_code(body)
    instance = _string_value(value.get("instance")) if value is not None else None
    type_ = _string_value(value.get("type")) if value is not None else None
    violations: list[Any] | None = None
    if value is not None and isinstance(value.get("violations"), list):
        violations = value["violations"][:100]

    message = detail or top_message or nested_message or title or label or f"HTTP {status}"

    problem: NormalizedProblem = {
        "family": _problem_family(value),
        "status": status,
        "message": presentation_text(message),
    }
    if code is not None:
        problem["code"] = code
    if label is not None:
        problem["label"] = presentation_text(label)
    if title is not None:
        problem["title"] = presentation_text(title)
    if detail is not None:
        problem["detail"] = presentation_text(detail)
    if instance is not None:
        problem["instance"] = presentation_text(instance)
    if type_ is not None:
        problem["type"] = presentation_text(type_)
    if violations is not None:
        problem["violations"] = redact_value(violations)
    return problem


_STATUS_CLASSES: dict[int, type[PlakyApiError]] = {
    401: PlakyAuthError,
    403: PlakyPermissionError,
    404: PlakyNotFoundError,
    409: PlakyConflictError,
    400: PlakyValidationError,
    422: PlakyUnprocessableEntityError,
    429: PlakyRateLimitError,
}


def classify(
    *,
    status: int,
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: Any = None,
    problem: NormalizedProblem | None = None,
    request_id: str | None = None,
    retry_after_ms: float | None = None,
) -> PlakyApiError:
    """Build the typed API error for a non-success response."""
    resolved_problem = problem if problem is not None else normalize_problem(body, status)
    error_class = _STATUS_CLASSES.get(status)
    if error_class is None and 500 <= status <= 599:
        error_class = PlakyServerError
    if error_class is None:
        error_class = PlakyApiError
    return error_class(
        resolved_problem["message"],
        status=status,
        method=method,
        url=url,
        headers=headers,
        body=body,
        problem=resolved_problem,
        request_id=request_id,
        code=_read_error_code(body),
        retry_after_ms=retry_after_ms,
    )
