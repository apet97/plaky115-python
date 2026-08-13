"""Coverage closure batch: escape hatches, retries, registry, tool error paths."""

from typing import Any

import httpx2
import pytest
from mcp.client import Client
from mcp.types import ToolAnnotations

from plaky115 import (
    AsyncPlakyClient,
    PlakyClient,
    PlakyError,
    PlakyRateLimitError,
    UploadValidationError,
    search_items_detailed,
)
from plaky115.resources._common import RequestOverrides, body_as_dict, with_idempotency
from plaky115.runtime.retries import async_with_retries, with_retries
from plaky115.runtime.upload import normalize_upload_media_type
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.registry import ToolSpec, validate_spec
from plaky115_mcp.server import build_server

pytestmark = pytest.mark.anyio


def ok_handler(request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(200, json={"echo": request.headers.get("x-extra", "")})


# --- client escape hatches and with_options ---------------------------------


async def test_async_request_escape_hatch_and_with_options() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(ok_handler)
    ) as client:
        assert await client.request("GET", "/x") == {"echo": ""}
        envelope = await client.request_with_response("GET", "/x")
        assert envelope.status == 200
        clone = client.with_options(timeout=5, max_retries=1, headers={"x-extra": "v"})
        assert await clone.request("GET", "/x") == {"echo": "v"}
        # Clone shares the pool; closing it must not close the parent's client.
        await clone.aclose()
        assert await client.request("GET", "/x") == {"echo": ""}


async def test_async_options_header_merging() -> None:
    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        headers={"x-extra": "base"},
        transport=httpx2.MockTransport(ok_handler),
    ) as client:
        merged = await client.request(
            "GET", "/x", options=RequestOverrides(headers={"x-extra": "override"})
        )
        assert merged == {"echo": "override"}

    async def header_factory() -> dict[str, str]:
        return {"x-extra": "fromfn"}

    async with AsyncPlakyClient(
        api_key="plk_x",
        max_retries=0,
        headers=header_factory,
        transport=httpx2.MockTransport(ok_handler),
    ) as client:
        assert await client.request("GET", "/x") == {"echo": "fromfn"}
        merged = await client.request(
            "GET", "/x", options=RequestOverrides(headers={"x-extra": "override"})
        )
        assert merged == {"echo": "override"}


def test_sync_request_escape_hatch_and_with_options() -> None:
    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(ok_handler)
    ) as client:
        assert client.request("GET", "/x") == {"echo": ""}
        assert client.request_with_response("GET", "/x").status == 200
        clone = client.with_options(max_response_bytes=1024, user_agent="ua/1")
        assert clone.request("GET", "/x") == {"echo": ""}
        merged = client.request("GET", "/x", options=RequestOverrides(headers={"x-extra": "o"}))
        assert merged == {"echo": "o"}

    with PlakyClient(
        api_key="plk_x",
        max_retries=0,
        headers={"x-extra": "base"},
        transport=httpx2.MockTransport(ok_handler),
    ) as client:
        merged = client.request("GET", "/x", options=RequestOverrides(headers={"x-extra": "o"}))
        assert merged == {"echo": "o"}


# --- retries helper ----------------------------------------------------------


def rate_limited(retry_after_ms: float | None = 1) -> PlakyRateLimitError:
    return PlakyRateLimitError(
        "slow down",
        status=429,
        method="GET",
        url="https://api.example.test/x",
        headers={},
        retry_after_ms=retry_after_ms,
    )


def test_with_retries_sync_paths() -> None:
    calls: list[int] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise rate_limited()
        return "ok"

    assert with_retries(flaky, max_retries=3, base_delay_ms=0) == "ok"
    assert len(calls) == 3

    with pytest.raises(PlakyError, match="kind=read"):
        with_retries(lambda: "x", kind="write")
    with pytest.raises(ValueError, match="maxRetries must be a finite non-negative integer"):
        with_retries(lambda: "x", max_retries=-1)
    with pytest.raises(ValueError, match="baseDelayMs must be a finite non-negative number"):
        with_retries(lambda: "x", base_delay_ms=float("nan"))
    with pytest.raises(KeyError):
        with_retries(lambda: (_ for _ in ()).throw(KeyError("boom")), max_retries=2)


async def test_with_retries_async_paths() -> None:
    calls: list[int] = []

    async def flaky() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise rate_limited()
        return "ok"

    assert await async_with_retries(flaky, max_retries=2, base_delay_ms=0) == "ok"

    async def hopeless() -> str:
        raise rate_limited(retry_after_ms=None)

    with pytest.raises(PlakyRateLimitError):
        await async_with_retries(hopeless, max_retries=1, base_delay_ms=0)


# --- registry validation ------------------------------------------------------


def spec(**overrides: Any) -> ToolSpec:
    async def handler() -> None:  # pragma: no cover - never called
        return None

    base: dict[str, Any] = {
        "name": "plaky_x",
        "title": "X",
        "description": "A concrete description.",
        "handler": handler,
        "scopes": frozenset({"read"}),
        "annotations": ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    }
    base.update(overrides)
    return ToolSpec(**base)


def test_validate_spec_rejections() -> None:
    with pytest.raises(ValueError, match="tool name must be"):
        validate_spec(spec(name=""))
    with pytest.raises(ValueError, match="tool title is required"):
        validate_spec(spec(title=""))
    with pytest.raises(ValueError, match="concrete tool description"):
        validate_spec(spec(description="short"))
    with pytest.raises(ValueError, match="annotation read_only_hint must be set"):
        validate_spec(spec(annotations=ToolAnnotations()))
    with pytest.raises(ValueError, match="at least one scope"):
        validate_spec(spec(scopes=frozenset()))
    with pytest.raises(ValueError, match="destructive tools require"):
        validate_spec(
            spec(
                annotations=ToolAnnotations(
                    read_only_hint=False,
                    destructive_hint=True,
                    idempotent_hint=False,
                    open_world_hint=False,
                )
            )
        )


# --- resource helpers ---------------------------------------------------------


def test_body_as_dict_and_idempotency_merge() -> None:
    from pydantic import BaseModel

    class Body(BaseModel):
        title: str

    assert body_as_dict(Body(title="t")) == {"title": "t"}
    assert with_idempotency(None, None) is None
    fresh = with_idempotency(None, "k1")
    assert fresh is not None and fresh.idempotency_key == "k1"
    kept = with_idempotency(RequestOverrides(idempotency_key="orig"), "k2")
    assert kept is not None and kept.idempotency_key == "orig"
    merged = with_idempotency(RequestOverrides(timeout=9), "k3")
    assert merged is not None and merged.idempotency_key == "k3" and merged.timeout == 9


# --- curated tool internal-error paths ---------------------------------------


def crash_handler(request: httpx2.Request) -> httpx2.Response:
    raise RuntimeError("wire exploded")


async def test_curated_tools_internal_error_paths() -> None:
    sdk = AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(crash_handler)
    )
    server = build_server(ServerSettings(api_key="plk_x"), sdk)
    async with Client(server) as client:
        calls: list[tuple[str, dict[str, Any]]] = [
            ("plaky_workspace_context", {}),
            ("plaky_find", {"kind": "space", "query": "x"}),
            (
                "plaky_execute_read_workflow",
                {"workflow": "workspace.map", "args": {}},
            ),
        ]
        for name, args in calls:
            result = await client.call_tool(name, args)
            assert result.is_error, name
            assert result.structured_content["error"]["name"] == "InternalError", name
            assert "correlation" in result.structured_content["error"]["message"]


async def test_execute_read_workflow_unknown_id() -> None:
    sdk = AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(ok_handler)
    )
    server = build_server(ServerSettings(api_key="plk_x"), sdk)
    async with Client(server) as client:
        result = await client.call_tool(
            "plaky_execute_read_workflow", {"workflow": "nope.nothing", "args": {}}
        )
        assert result.is_error
        assert result.structured_content["error"]["category"] == "usage"


# --- search continuation + empty-page guard ----------------------------------


SEARCH_PAGES: dict[int, dict[str, Any]] = {}


def search_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7})
    if path == "/v1/public/spaces/1/boards/7/items":
        page = int(dict(request.url.params).get("page", "1"))
        return httpx2.Response(200, json=SEARCH_PAGES[page])
    return httpx2.Response(404, json={"message": "nope"})


def search_client() -> PlakyClient:
    return PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(search_handler)
    )


def test_sync_search_truncation_and_field_scalars() -> None:
    SEARCH_PAGES.clear()
    SEARCH_PAGES[1] = {
        "data": [
            {"id": 1, "title": "Alpha", "fields": [{"key": "s", "value": {"z": ["NEEDLE", 2]}}]},
            {"id": 2, "title": "beta needle"},
            {"id": 3, "title": "gamma", "fields": [{"key": "s", "value": True}]},
        ],
        "hasMore": True,
    }
    SEARCH_PAGES[2] = {"data": [{"id": 4, "title": "delta needle"}], "hasMore": False}
    with search_client() as client:
        first = search_items_detailed(client, space=1, board=7, query="needle", limit=2)
        assert first.truncated and not first.complete
        assert [i.id for i in first.data] == [1, 2]
        assert first.continuation is not None
        rest = search_items_detailed(
            client, space=1, board=7, query="needle", limit=10, cursor=first.continuation
        )
        assert rest.complete and [i.id for i in rest.data] == [4]


def test_sync_search_empty_page_with_has_more_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The pagination contract normally rejects this shape; the search loop
    # keeps its own guard, exercised here through a stubbed resource.
    from types import SimpleNamespace

    SEARCH_PAGES.clear()
    SEARCH_PAGES[1] = {"data": [{"id": 1, "title": "x"}], "hasMore": True}
    with search_client() as client:
        monkeypatch.setattr(
            client.items,
            "list",
            lambda **_kwargs: SimpleNamespace(data=[], has_more=True),  # pyright: ignore[reportUnknownLambdaType,reportUnknownArgumentType]
        )
        with pytest.raises(ValueError, match="was empty while hasMore was true"):
            search_items_detailed(client, space=1, board=7, query="x", limit=5)


# --- upload media-type internals ---------------------------------------------


def test_media_type_quote_and_escape_internals() -> None:
    # Escaped quote and escaped backslash inside a quoted value survive.
    assert normalize_upload_media_type('a/b; k="v\\"w"') == 'a/b;k="v\\"w"'
    assert normalize_upload_media_type('a/b; k="v\\\\"') == 'a/b;k="v\\\\"'
    # A quoted semicolon must not split parameters.
    assert normalize_upload_media_type('a/b; k="v;w"') == 'a/b;k="v;w"'
    for bad in (
        'a/b; k="v\\',  # trailing escape
        'a/b; k="v\x01"',  # control character in value
        'a/b; k="v"x',  # trailing junk after close quote
        "a/b; k=\x7f",
    ):
        with pytest.raises(UploadValidationError):
            normalize_upload_media_type(bad)


# --- workspace map limits ------------------------------------------------------


def test_workspace_map_bound_validation() -> None:
    from plaky115 import workspace_map

    with PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(ok_handler)
    ) as client:
        with pytest.raises(ValueError, match=r"maxItems must be a non-negative safe integer\."):
            workspace_map(client, max_items=-1)
        with pytest.raises(ValueError, match=r"maxBytes must be a non-negative safe integer\."):
            workspace_map(client, max_bytes=True)  # type: ignore[arg-type]
