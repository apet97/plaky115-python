"""Idempotency-key helpers.

The Idempotency-Key header is an explicitly attached header only; it never
enables write retries and its presence is never inferred. Ported from
sdk/src/runtime/idempotency.ts at the pinned source.
"""

from __future__ import annotations

import uuid

IDEMPOTENCY_HEADER = "Idempotency-Key"


def new_idempotency_key(prefix: str = "idmp") -> str:
    """Generate a fresh explicit idempotency key (prefix + UUIDv4)."""
    return f"{prefix}_{uuid.uuid4()}"


def resolve_explicit_idempotency_key(
    key: str | None,
    option_key: str | None = None,
) -> str | None:
    """Resolve an explicitly supplied key; None when neither is set.

    Never generates a key implicitly and never enables retries.
    """
    if key is not None:
        return key
    return option_key


def resolve_idempotency_key(
    key: str | None,
    option_key: str | None = None,
    prefix: str = "idmp",
) -> str:
    """Deprecated resolution that generates a key when none is supplied."""
    explicit = resolve_explicit_idempotency_key(key, option_key)
    if explicit is not None:
        return explicit
    return new_idempotency_key(prefix)
