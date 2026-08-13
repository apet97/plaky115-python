"""Upload validation, decoding, and hashing.

Ported from sdk/src/runtime/upload.ts at the pinned source
(docs/port/spec-helpers.md). Decode happens once; SHA-256 is computed once;
content, keys, and digests are never logged.
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass

from plaky115.errors import UploadValidationError

MEBIBYTE = 1024 * 1024
MAX_UPLOAD_BYTES_HARD_CEILING = 25 * MEBIBYTE  # 26_214_400
MAX_UPLOAD_FILENAME_BYTES = 255
DEFAULT_CONTENT_TYPE = "application/octet-stream"

_CANONICAL_BASE64 = re.compile(r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$")
_TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


@dataclass(frozen=True)
class UploadMetadata:
    file_name: str
    media_type: str
    decoded_bytes: int


@dataclass(frozen=True)
class NormalizedUpload:
    file_name: str
    media_type: str
    decoded_bytes: int
    data: bytes
    sha256: str


def _has_control_character(value: str) -> bool:
    return any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in value)


def validate_upload_limit(max_bytes: int) -> int:
    if (
        isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or max_bytes <= 0
        or max_bytes > MAX_UPLOAD_BYTES_HARD_CEILING
    ):
        raise UploadValidationError(
            f"maxBytes must be between 1 and {MAX_UPLOAD_BYTES_HARD_CEILING}.",
            code="invalid-limit",
            path="maxBytes",
        )
    return max_bytes


def validate_upload_file_name(file_name: str) -> str:
    if not isinstance(file_name, str) or len(file_name) == 0:  # pyright: ignore[reportUnnecessaryIsInstance]
        raise UploadValidationError(
            "fileName must be non-empty.", code="invalid-filename", path="fileName"
        )
    if "/" in file_name or "\\" in file_name or _has_control_character(file_name):
        raise UploadValidationError(
            "fileName must not contain slash or control characters.",
            code="invalid-filename",
            path="fileName",
        )
    if len(file_name.encode("utf-8")) > MAX_UPLOAD_FILENAME_BYTES:
        raise UploadValidationError(
            f"fileName must not exceed {MAX_UPLOAD_FILENAME_BYTES} UTF-8 bytes.",
            code="invalid-filename",
            path="fileName",
        )
    return file_name


def _invalid_media_type() -> UploadValidationError:
    return UploadValidationError(
        "contentType must be a valid media type.",
        code="invalid-media-type",
        path="contentType",
    )


def _split_media_type(value: str) -> list[str]:
    """Split on ';' outside double quotes, honoring backslash escapes."""
    segments: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if quoted and char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            current.append(char)
            continue
        if char == ";" and not quoted:
            segments.append("".join(current))
            current = []
            continue
        current.append(char)
    if quoted or escaped:
        raise _invalid_media_type()
    segments.append("".join(current))
    return segments


def _valid_parameter_value(value: str) -> bool:
    if _TOKEN.fullmatch(value):
        return True
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        interior = value[1:-1]
        index = 0
        while index < len(interior):
            char = interior[index]
            if char == "\\":
                index += 2
                continue
            if char == '"':
                return False
            if (ord(char) < 0x20 and char != "\t") or ord(char) == 0x7F:
                return False
            index += 1
        return index <= len(interior)
    return False


def normalize_upload_media_type(content_type: str | None) -> str:
    if content_type is None:
        return DEFAULT_CONTENT_TYPE
    if (
        not isinstance(content_type, str)
        or not content_type
        or _has_control_character(content_type)
    ):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise _invalid_media_type()
    segments = _split_media_type(content_type.strip())
    head = segments[0]
    slash = head.find("/")
    if slash <= 0 or slash != head.rfind("/"):
        raise _invalid_media_type()
    main_type, subtype = head[:slash], head[slash + 1 :]
    if not _TOKEN.fullmatch(main_type) or not _TOKEN.fullmatch(subtype):
        raise _invalid_media_type()
    parameters: list[str] = []
    for segment in segments[1:]:
        equals = segment.find("=")
        if equals <= 0 or equals != segment.rfind("="):
            raise _invalid_media_type()
        name = segment[:equals].strip()
        value = segment[equals + 1 :].strip()
        if not _TOKEN.fullmatch(name) or not _valid_parameter_value(value):
            raise _invalid_media_type()
        parameters.append(f"{name.lower()}={value}")
    normalized = f"{main_type.lower()}/{subtype.lower()}"
    if parameters:
        normalized += ";" + ";".join(parameters)
    return normalized


def _invalid_base64() -> UploadValidationError:
    return UploadValidationError(
        "fileBase64 must be canonical base64.", code="invalid-base64", path="fileBase64"
    )


def estimate_base64_decoded_bytes(file_base64: str) -> int:
    if not isinstance(file_base64, str) or not _CANONICAL_BASE64.fullmatch(file_base64):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise _invalid_base64()
    if not file_base64:
        return 0
    padding = 2 if file_base64.endswith("==") else 1 if file_base64.endswith("=") else 0
    return (len(file_base64) // 4) * 3 - padding


def decode_base64_upload(
    file_base64: str, max_bytes: int = MAX_UPLOAD_BYTES_HARD_CEILING
) -> bytes:
    limit = validate_upload_limit(max_bytes)
    decoded_bytes = estimate_base64_decoded_bytes(file_base64)
    if decoded_bytes > limit:
        raise UploadValidationError(
            f"Decoded upload exceeds the configured limit of {limit} bytes.",
            code="upload-too-large",
            path="fileBase64",
        )
    try:
        raw = base64.b64decode(file_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise _invalid_base64() from exc
    # Canonicality is proved by exact re-encode comparison.
    if base64.b64encode(raw).decode("ascii") != file_base64:
        raise _invalid_base64()
    return raw


@dataclass(frozen=True)
class Base64UploadInput:
    file_base64: str
    file_name: str
    content_type: str | None = None


def normalize_upload_metadata(
    upload: Base64UploadInput, max_bytes: int = MAX_UPLOAD_BYTES_HARD_CEILING
) -> UploadMetadata:
    limit = validate_upload_limit(max_bytes)
    file_name = validate_upload_file_name(upload.file_name)
    media_type = normalize_upload_media_type(upload.content_type)
    decoded_bytes = estimate_base64_decoded_bytes(upload.file_base64)
    if decoded_bytes > limit:
        raise UploadValidationError(
            f"Decoded upload exceeds the configured limit of {limit} bytes.",
            code="upload-too-large",
            path="fileBase64",
        )
    return UploadMetadata(file_name=file_name, media_type=media_type, decoded_bytes=decoded_bytes)


def normalize_upload(
    upload: Base64UploadInput, max_bytes: int = MAX_UPLOAD_BYTES_HARD_CEILING
) -> NormalizedUpload:
    metadata = normalize_upload_metadata(upload, max_bytes)
    data = decode_base64_upload(upload.file_base64, max_bytes)
    digest = hashlib.sha256(data).hexdigest()
    return NormalizedUpload(
        file_name=metadata.file_name,
        media_type=metadata.media_type,
        decoded_bytes=metadata.decoded_bytes,
        data=data,
        sha256=digest,
    )


def validate_binary_upload(
    file: bytes | bytearray | memoryview,
    file_name: str | None = None,
    content_type: str | None = None,
) -> UploadMetadata:
    """Validate a binary (bytes) upload for the SDK multipart path."""
    if not isinstance(file, bytes | bytearray | memoryview):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise UploadValidationError(
            "file must be bytes or a bytes-like object.",
            code="invalid-filename",
            path="file",
        )
    resolved_name = "blob" if file_name is None else validate_upload_file_name(file_name)
    media_type = normalize_upload_media_type(content_type)
    size = len(file)
    if size > MAX_UPLOAD_BYTES_HARD_CEILING:
        raise UploadValidationError(
            f"Decoded upload exceeds the configured limit of "
            f"{MAX_UPLOAD_BYTES_HARD_CEILING} bytes.",
            code="upload-too-large",
            path="file",
        )
    return UploadMetadata(file_name=resolved_name, media_type=media_type, decoded_bytes=size)
