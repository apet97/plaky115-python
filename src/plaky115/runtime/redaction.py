"""Secret redaction and bounded presentation text.

Ported from sdk/src/runtime/redact.ts and the presentation helpers in
sdk/src/runtime/errors.ts / mutations.ts at the pinned source.
"""

from __future__ import annotations

import json
import re
from typing import Any

PLAKY_API_KEY_PATTERN = re.compile(r"plk_[A-Za-z0-9_-]+")
PLAKY_API_KEY_REDACTION_MARKER = "[REDACTED_PLAKY_API_KEY]"

MAX_PRESENTATION_MESSAGE_LENGTH = 1024


def redact(value: str) -> str:
    """Mask every plk_ API-key-shaped token in a string."""
    return PLAKY_API_KEY_PATTERN.sub(PLAKY_API_KEY_REDACTION_MARKER, value)


def redact_value(value: Any) -> Any:
    """Deep-redact a JSON-safe value.

    Round-trips through JSON so both keys and values are scrubbed; values that
    cannot be serialized are returned unchanged, matching the source's
    redactRecord behavior for non-JSON inputs.
    """
    try:
        serialized = json.dumps(value)
    except (TypeError, ValueError):
        return value
    return json.loads(redact(serialized))


def presentation_text(value: str) -> str:
    """Redact and cap a message for exception presentation (1024 chars)."""
    safe = redact(value)
    if len(safe) <= MAX_PRESENTATION_MESSAGE_LENGTH:
        return safe
    return safe[: MAX_PRESENTATION_MESSAGE_LENGTH - 1] + "…"


def bound_text(value: str, limit: int = MAX_PRESENTATION_MESSAGE_LENGTH) -> str:
    """Redact, replace control characters with spaces, and cap length.

    Used for mutation receipts and other durable summaries.
    """
    redacted = redact(value)
    safe = "".join(" " if ord(c) < 0x20 or ord(c) == 0x7F else c for c in redacted)
    if len(safe) <= limit:
        return safe
    return safe[: limit - 1] + "…"
