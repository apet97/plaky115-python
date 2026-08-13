"""Client configuration validation.

Ported from sdk/src/runtime/internal/validation.ts and client option rules
at the pinned source.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

DEFAULT_SERVER_URL = "https://api.plaky.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 2_147_483.647
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_BYTES = 64 * 1024 * 1024

_SERVER_URL_ERROR = (
    "PlakyClient: server_url must be an absolute HTTPS URL (or loopback HTTP) with a host"
)

_LOOPBACK_IPV4 = re.compile(r"^127(?:\.\d{1,3}){3}$")


def _is_loopback_host(host: str) -> bool:
    stripped = host.strip("[]")
    if stripped in ("localhost", "::1"):
        return True
    if _LOOPBACK_IPV4.fullmatch(stripped):
        return all(0 <= int(octet) <= 255 for octet in stripped.split("."))
    return False


def normalize_server_url(server_url: str) -> str:
    """Validate and normalize the trusted base URL.

    HTTPS only, except loopback HTTP for local development. Credentials,
    query, and fragment are rejected; trailing slashes are normalized away.
    """
    if server_url != server_url.strip():
        raise ValueError(_SERVER_URL_ERROR)
    if not re.match(r"^https?://[^/]", server_url, re.IGNORECASE):
        raise ValueError(_SERVER_URL_ERROR)
    parts = urlsplit(server_url)
    if not parts.hostname:
        raise ValueError(_SERVER_URL_ERROR)
    if parts.scheme.lower() == "http" and not _is_loopback_host(
        parts.netloc.split("@")[-1].rsplit(":", 1)[0] if ":" in parts.netloc else parts.netloc
    ):
        raise ValueError(_SERVER_URL_ERROR)
    if parts.username is not None or parts.password is not None:
        raise ValueError("PlakyClient: server_url must not include credentials")
    if parts.query or parts.fragment:
        raise ValueError("PlakyClient: server_url must not include a query or fragment")
    path = parts.path.rstrip("/")
    netloc = parts.netloc
    return f"{parts.scheme.lower()}://{netloc}{path}"


def validate_timeout(value: float, name: str = "timeout") -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"PlakyClient: {name} must be a non-negative number")
    if value != value or value < 0 or value in (float("inf"),):
        raise ValueError(f"PlakyClient: {name} must be a non-negative number")
    if value > MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"PlakyClient: {name} must be a non-negative number no greater than "
            f"{MAX_TIMEOUT_SECONDS} seconds"
        )
    return float(value)


def validate_max_retries(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("PlakyClient: max_retries must be a non-negative integer")
    return value


def validate_response_limit(value: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > MAX_RESPONSE_BYTES
    ):
        raise ValueError(
            "PlakyClient: max_response_bytes must be an integer "
            f"between 1 and {MAX_RESPONSE_BYTES}"
        )
    return value
