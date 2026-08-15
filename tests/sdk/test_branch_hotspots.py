"""Final branch-coverage hotspots: sync transport, exports, uploads, http."""

from typing import Any

import httpx2
import pytest

from plaky115 import (
    Base64UploadInput,
    PlakyClient,
    PlakyDecodeError,
    PlakyResponseTooLargeError,
    export_items,
    normalize_base64_upload_plan,
    normalize_binary_upload_plan,
    normalize_comment_plan,
    normalize_item_file_update_plan,
    normalize_item_group_update_plan,
    read_item_export_chunk,
)
from plaky115.http import RequestOptions, RequestSpec, request, request_with_response
from plaky115.runtime.chunks import PageCursor, sync_read_paged_chunk
from plaky115.runtime.upload import normalize_upload_media_type

pytestmark = pytest.mark.anyio

SERVER = "https://api.example.test"


def options(**overrides: Any) -> RequestOptions:
    defaults: dict[str, Any] = {"api_key": "plk_x", "server_url": SERVER, "max_retries": 0}
    defaults.update(overrides)
    return RequestOptions(**defaults)


def test_sync_public_request_seam() -> None:
    def handler(req: httpx2.Request) -> httpx2.Response:
        if req.url.path == "/big":
            return httpx2.Response(200, content=b"x" * 4096)
        if req.url.path == "/broken":
            return httpx2.Response(200, content=b"{nope", headers={"x-request-id": "r"})
        if req.url.path == "/bytes":
            return httpx2.Response(200, content=b"\x00\x01")
        if req.url.path == "/text":
            return httpx2.Response(200, content=b"plain text")
        return httpx2.Response(200, json={"ok": True})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        envelope = request_with_response(http, RequestSpec(method="GET", path="/x"), options())
        assert envelope.data == {"ok": True} and envelope.status == 200
        assert request(http, RequestSpec(method="GET", path="/x"), options()) == {"ok": True}
        assert (
            request(
                http, RequestSpec(method="GET", path="/bytes", response_type="bytes"), options()
            )
            == b"\x00\x01"
        )
        assert (
            request(http, RequestSpec(method="GET", path="/text", response_type="text"), options())
            == "plain text"
        )
        with pytest.raises(PlakyResponseTooLargeError):
            request(http, RequestSpec(method="GET", path="/big"), options(max_response_bytes=1024))
        with pytest.raises(PlakyDecodeError) as decode_info:
            request(http, RequestSpec(method="GET", path="/broken"), options())
        assert decode_info.value.request_id == "r"


def test_sync_request_hook_paths() -> None:
    seen: dict[str, str] = {}

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen["url"] = str(req.url)
        return httpx2.Response(200, json={})

    def rewrite(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "url": ctx["url"] + "?injected=1"}

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        request(http, RequestSpec(method="GET", path="/x"), options(request_hook=rewrite))
        assert seen["url"].endswith("?injected=1")

        def cross(ctx: dict[str, Any]) -> dict[str, Any]:
            return {**ctx, "url": "https://evil.example/x"}

        with pytest.raises(ValueError, match="trusted server origin"):
            request(http, RequestSpec(method="GET", path="/x"), options(request_hook=cross))

        def broken(ctx: dict[str, Any]) -> str:
            return "nope"

        with pytest.raises(ValueError, match="invalid URL"):
            request(
                http,
                RequestSpec(method="GET", path="/x"),
                options(request_hook=broken),  # type: ignore[arg-type]
            )


def test_sync_response_hook_error_path() -> None:
    observed: list[int] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, json={"message": "gone"})

    def hook(ctx: dict[str, Any]) -> None:
        observed.append(ctx["status"])

    from plaky115 import PlakyNotFoundError

    with (
        httpx2.Client(transport=httpx2.MockTransport(handler)) as http,
        pytest.raises(PlakyNotFoundError),
    ):
        request(http, RequestSpec(method="GET", path="/x"), options(response_hook=hook))
    assert observed == [404]


def test_sync_chunk_reader_edges() -> None:
    pages = [
        {"data": [1, 2], "hasMore": True},
        {"data": [3], "hasMore": False},
    ]
    calls: list[int] = []

    def fetch(page: int, size: int) -> dict[str, Any]:
        calls.append(page)
        return pages[page - 1]

    first = sync_read_paged_chunk(fetch, max_items=1)
    assert first.next_cursor == PageCursor(page=1, index=1)
    rest = sync_read_paged_chunk(fetch, cursor=first.next_cursor)
    assert rest.complete and rest.data == (2, 3)

    from plaky115 import PlakyOutputLimitError

    with pytest.raises(PlakyOutputLimitError):
        sync_read_paged_chunk(fetch, max_items=0)
    with pytest.raises(PlakyOutputLimitError):
        sync_read_paged_chunk(
            lambda p, s: {"data": [{"big": "x" * 99}], "hasMore": False}, max_bytes=5
        )


EXPORT_PAGES: dict[int, dict[str, Any]] = {
    1: {"data": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}], "hasMore": True},
    2: {"data": [{"id": 3, "title": "C"}], "hasMore": False},
}


def export_handler(request_: httpx2.Request) -> httpx2.Response:
    path = request_.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7, "fields": [{"key": "s", "name": "S"}]})
    if path == "/v1/public/spaces/1/boards/7/items":
        page = int(dict(request_.url.params).get("page", "1"))
        return httpx2.Response(200, json=EXPORT_PAGES[page])
    return httpx2.Response(404, json={"message": "nope"})


def export_client() -> PlakyClient:
    return PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(export_handler)
    )


def test_sync_export_chunk_continuation_and_headers() -> None:
    with export_client() as client:
        first = read_item_export_chunk(client, space=1, board=7, format="csv", max_items=2)
        assert first.truncated and first.next_cursor is not None
        assert first.body.splitlines()[0] == "id,title,S"
        second = read_item_export_chunk(
            client,
            space=1,
            board=7,
            format="csv",
            max_items=2,
            cursor=first.next_cursor,
            include_header=False,
        )
        assert second.complete
        assert not second.body.startswith("id,title")

        jsonl_first = read_item_export_chunk(client, space=1, board=7, format="jsonl", max_items=2)
        assert jsonl_first.truncated and jsonl_first.body.count("\n") == 2

        with pytest.raises(Exception, match=r"maxItems must be a non-negative safe integer\."):
            export_items(client, space=1, board=7, max_items=-1)


def test_media_type_quoted_parameter_edges() -> None:
    assert normalize_upload_media_type('a/b; k="v w"; Z=t') == 'a/b;k="v w";z=t'
    from plaky115 import UploadValidationError

    for bad in ('a/b; k="unterminated', "a/b; k=v=w", "a/b; =v"):
        with pytest.raises(UploadValidationError):
            normalize_upload_media_type(bad)


async def test_upload_and_plan_normalizer_edges() -> None:
    plan = await_none = normalize_base64_upload_plan(
        space_id=1,
        board_id=7,
        item_id=3,
        upload=Base64UploadInput(file_base64="aGVsbG8=", file_name="a.txt"),
    )
    del await_none
    assert plan.plan.upload is not None and plan.plan.upload.sha256
    assert "fileBase64" not in dict(plan.plan.body)

    binary_plan, metadata = normalize_binary_upload_plan(
        space_id=1, board_id=7, item_id=3, file=b"xyz", file_name="b.bin"
    )
    assert binary_plan.upload is not None and metadata.decoded_bytes == 3

    with pytest.raises(TypeError, match=r"body\.text must be a non-empty string"):
        normalize_comment_plan(space_id=1, board_id=7, item_id=3, body={"text": "  "})
    with pytest.raises(TypeError, match=r"body\.color must be a six-digit"):
        normalize_item_group_update_plan(
            space_id=1,
            board_id=7,
            item_group_id=5,
            body={"title": "t", "ranking": "r", "color": "red"},
        )
    from plaky115 import UploadValidationError

    with pytest.raises(UploadValidationError):
        normalize_item_file_update_plan(
            space_id=1, board_id=7, item_id=3, item_file_id=9, body={"name": "bad/name"}
        )
    with pytest.raises(TypeError, match="body must be a plain object"):
        normalize_comment_plan(space_id=1, board_id=7, item_id=3, body="x")
    body = {"text": "Reply", "repliesToId": 7}
    plan = normalize_comment_plan(space_id=1, board_id=2, item_id=3, body=body)
    assert body == {"text": "Reply", "repliesToId": 7}
    assert dict(plan.body) == {"text": "Reply", "repliesToId": "7"}


def test_client_validation_errors() -> None:
    from plaky115 import AsyncPlakyClient

    with pytest.raises(ValueError, match="apiKey is required"):
        PlakyClient(api_key="  ")
    with pytest.raises(ValueError, match="apiKey is required"):
        AsyncPlakyClient(api_key="")
    with pytest.raises(ValueError, match="must not include credentials"):
        PlakyClient(api_key="plk_x", server_url="https://user:pw@x.example")
