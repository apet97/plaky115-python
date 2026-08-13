"""Upload validation gates (spec-helpers §4)."""

import base64

import pytest

from plaky115.errors import UploadValidationError
from plaky115.runtime.upload import (
    MAX_UPLOAD_BYTES_HARD_CEILING,
    Base64UploadInput,
    decode_base64_upload,
    estimate_base64_decoded_bytes,
    normalize_upload,
    normalize_upload_media_type,
    normalize_upload_metadata,
    validate_binary_upload,
    validate_upload_file_name,
    validate_upload_limit,
)


def test_hard_ceiling_constant() -> None:
    assert MAX_UPLOAD_BYTES_HARD_CEILING == 26_214_400


def test_limit_validation() -> None:
    assert validate_upload_limit(1) == 1
    assert validate_upload_limit(26_214_400) == 26_214_400
    for bad in (0, -1, 26_214_401):
        with pytest.raises(
            UploadValidationError, match=r"maxBytes must be between 1 and 26214400\."
        ):
            validate_upload_limit(bad)


def test_filename_rules() -> None:
    assert validate_upload_file_name("report.pdf") == "report.pdf"
    assert validate_upload_file_name("..") == ".."  # plain dots are allowed
    assert validate_upload_file_name(" spaced .txt") == " spaced .txt"
    for bad, message in [
        ("", "fileName must be non-empty."),
        ("a/b.txt", "fileName must not contain slash or control characters."),
        ("a\\b.txt", "fileName must not contain slash or control characters."),
        ("tab\there", "fileName must not contain slash or control characters."),
        ("nl\nhere", "fileName must not contain slash or control characters."),
        ("č" * 200, "fileName must not exceed 255 UTF-8 bytes."),
    ]:
        with pytest.raises(UploadValidationError) as info:
            validate_upload_file_name(bad)
        assert str(info.value) == message


def test_media_type_normalization() -> None:
    assert normalize_upload_media_type(None) == "application/octet-stream"
    assert normalize_upload_media_type("Text/Plain") == "text/plain"
    assert normalize_upload_media_type("Text/Plain; Charset=UTF-8") == "text/plain;charset=UTF-8"
    assert normalize_upload_media_type('text/plain; boundary="a;b"') == 'text/plain;boundary="a;b"'
    for bad in (
        "",
        "noslash",
        "/x",
        "x/",
        "a/b/c",
        "text/plain ; charset=utf-8",
        "a/b; k",
        'a/b; k="',
    ):
        with pytest.raises(
            UploadValidationError, match=r"contentType must be a valid media type\."
        ):
            normalize_upload_media_type(bad)


def test_base64_estimation_and_canonicality() -> None:
    assert estimate_base64_decoded_bytes("") == 0
    assert estimate_base64_decoded_bytes("aGVsbG8=") == 5
    assert estimate_base64_decoded_bytes("aGVsbG9v") == 6
    for bad in ("aGVsbG8", "aGVs bG8=", "aGVsbG8=\n", "aGVsbG8-", "====", "aGVsbG9=="):
        with pytest.raises(UploadValidationError, match=r"fileBase64 must be canonical base64\."):
            estimate_base64_decoded_bytes(bad)


def test_non_canonical_padding_bits_rejected() -> None:
    # "aGVsbG9=" passes the regex shape but the trailing bits are non-zero,
    # so the round-trip re-encode differs.
    with pytest.raises(UploadValidationError, match="canonical base64"):
        decode_base64_upload("aGVsbG9=")


def test_decode_size_guard() -> None:
    data = base64.b64encode(b"x" * 100).decode()
    with pytest.raises(UploadValidationError) as info:
        decode_base64_upload(data, max_bytes=10)
    assert str(info.value) == "Decoded upload exceeds the configured limit of 10 bytes."
    assert decode_base64_upload(data, max_bytes=100) == b"x" * 100


def test_normalize_upload_sha256_vector() -> None:
    upload = normalize_upload(Base64UploadInput(file_base64="aGVsbG8=", file_name="hello.txt"))
    assert upload.decoded_bytes == 5
    assert upload.data == b"hello"
    assert upload.sha256 == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert upload.media_type == "application/octet-stream"


def test_metadata_validates_without_decoding() -> None:
    metadata = normalize_upload_metadata(
        Base64UploadInput(file_base64="aGVsbG8=", file_name="a.txt", content_type="Text/Plain")
    )
    assert metadata.decoded_bytes == 5
    assert metadata.media_type == "text/plain"


def test_binary_upload_validation() -> None:
    metadata = validate_binary_upload(b"hello", "a.bin", "application/pdf")
    assert metadata.decoded_bytes == 5
    assert metadata.media_type == "application/pdf"
    assert validate_binary_upload(b"x").file_name == "blob"
    with pytest.raises(UploadValidationError, match="Decoded upload exceeds"):
        validate_binary_upload(b"x" * (MAX_UPLOAD_BYTES_HARD_CEILING + 1))
