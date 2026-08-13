"""Response decoding helpers.

Ported from sdk/src/runtime/internal/responses.ts at the pinned source.
Unsafe JSON integers (beyond ±9007199254740991) decode to exact decimal
strings so no digits are lost; safe integers remain ints.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

MAX_SAFE_INTEGER = 9007199254740991


def _parse_int_preserving(text: str) -> int | str:
    value = int(text)
    if value > MAX_SAFE_INTEGER or value < -MAX_SAFE_INTEGER:
        return text
    return value


def parse_json_preserving_int64(text: str) -> Any:
    """Decode JSON, preserving unsafe integer literals as decimal strings."""
    return json.loads(text, parse_int=_parse_int_preserving)


_REQUEST_ID_HEADERS = ("x-request-id", "request-id", "x-correlation-id")


def get_request_id(headers: Mapping[str, str]) -> str | None:
    lookup = {k.lower(): v for k, v in headers.items()}
    for name in _REQUEST_ID_HEADERS:
        if name in lookup:
            return lookup[name]
    return None
