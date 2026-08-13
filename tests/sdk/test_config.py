"""Client configuration validation gates (spec-transport §server_url)."""

import pytest

from plaky115.config import (
    DEFAULT_SERVER_URL,
    normalize_server_url,
    validate_max_retries,
    validate_response_limit,
    validate_timeout,
)


def test_default_server_url() -> None:
    assert DEFAULT_SERVER_URL == "https://api.plaky.com"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://api.plaky.com", "https://api.plaky.com"),
        ("https://api.plaky.com/", "https://api.plaky.com"),
        ("https://api.plaky.com//", "https://api.plaky.com"),
        ("https://tenant.plaky.com/base/", "https://tenant.plaky.com/base"),
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://127.0.0.1:9999/x", "http://127.0.0.1:9999/x"),
        ("http://[::1]:3000", "http://[::1]:3000"),
        ("http://[::1]", "http://[::1]"),
        ("http://[::1]/", "http://[::1]"),
    ],
)
def test_accepts_and_normalizes(value: str, expected: str) -> None:
    assert normalize_server_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",  # non-loopback HTTP
        "http://[2001:db8::1]/",  # non-loopback IPv6 HTTP
        "http://[2001:db8::1]:8080",
        "ftp://example.com",
        "https://",
        " https://api.plaky.com",
        "https://api.plaky.com ",
        "https://user:pass@api.plaky.com",
        "https://api.plaky.com?x=1",
        "https://api.plaky.com#frag",
        "api.plaky.com",
    ],
)
def test_rejects_unsafe_urls(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_server_url(value)


def test_timeout_validation() -> None:
    assert validate_timeout(30) == 30.0
    assert validate_timeout(0) == 0.0
    for bad in (-1, float("nan"), float("inf"), 3_000_000_000):
        with pytest.raises(ValueError):
            validate_timeout(bad)


def test_max_retries_validation() -> None:
    assert validate_max_retries(0) == 0
    assert validate_max_retries(5) == 5
    for bad in (-1, True):
        with pytest.raises(ValueError):
            validate_max_retries(bad)  # type: ignore[arg-type]


def test_response_limit_validation() -> None:
    assert validate_response_limit(1) == 1
    assert validate_response_limit(64 * 1024 * 1024) == 64 * 1024 * 1024
    for bad in (0, -5, 64 * 1024 * 1024 + 1):
        with pytest.raises(ValueError, match="between 1 and 67108864"):
            validate_response_limit(bad)
