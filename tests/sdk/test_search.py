"""Item search: matching, truncation, continuation cursors, and guards."""

from typing import Any

import httpx2
import pytest

from fakes import paged_workspace_client
from plaky115 import PlakyClient, search_items_detailed

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


def test_sync_search_progress_and_cursor_errors() -> None:
    from plaky115 import search_items, search_items_detailed
    from plaky115.runtime.chunks import PageCursor

    with paged_workspace_client() as client:
        progress: list[tuple[int, int]] = []
        result = search_items_detailed(
            client,
            space=1,
            board=7,
            query="o",
            on_progress=lambda scanned, limit: progress.append((scanned, limit)),
        )
        assert result.matched >= 2 and progress
        assert search_items(client, space=1, board=7, query="three") != []
        with pytest.raises(ValueError, match="cursor must contain a positive page"):
            search_items_detailed(
                client, space=1, board=7, query="x", cursor=PageCursor(page=0, index=0)
            )
        with pytest.raises(ValueError, match="cursor index 9 exceeds page 1 length"):
            search_items_detailed(
                client, space=1, board=7, query="x", cursor=PageCursor(page=1, index=9)
            )
