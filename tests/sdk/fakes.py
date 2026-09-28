"""Shared SDK test fakes: request options, mock clients, and canned workspaces."""

from typing import Any

import httpx2

from plaky115 import AsyncPlakyClient, PlakyClient
from plaky115.http import RequestOptions

SERVER = "https://api.example.test"


def make_options(**overrides: Any) -> RequestOptions:
    defaults: dict[str, Any] = {
        "api_key": "plk_test_key",
        "server_url": SERVER,
        "timeout": 5.0,
        "max_retries": 0,
    }
    defaults.update(overrides)
    return RequestOptions(**defaults)


def mock_client(handler: Any) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


def echo_handler(request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(200, json={"echo": request.headers.get("x-extra", "")})


def simple_board_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
    if path == "/v1/public/spaces":
        return httpx2.Response(200, json={"data": [{"id": 1, "title": "Alpha"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(200, json={"id": 7, "title": "B", "fields": []})
    if path == "/v1/public/spaces/1/boards":
        return httpx2.Response(200, json={"data": [{"id": 7, "title": "B"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7/items":
        return httpx2.Response(
            200,
            json={
                "data": [{"id": 3, "title": "One"}, {"id": 4, "title": "Two"}],
                "hasMore": False,
            },
        )
    if path == "/v1/public/spaces/1/boards/7/items/3":
        return httpx2.Response(200, json={"id": 3, "title": "One"})
    return httpx2.Response(404, json={"message": "nope"})


def simple_board_async_client() -> AsyncPlakyClient:
    return AsyncPlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(simple_board_handler)
    )


def simple_board_client() -> PlakyClient:
    return PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(simple_board_handler)
    )


ITEMS_PAGE_1 = {
    "data": [
        {"id": 1, "title": "One", "fields": [{"key": "s", "name": "Status", "value": "To do"}]},
        {"id": 2, "title": "Two"},
    ],
    "hasMore": True,
}


ITEMS_PAGE_2 = {"data": [{"id": 3, "title": "Three"}], "hasMore": False}


def paged_workspace_handler(request: httpx2.Request) -> httpx2.Response:
    path = request.url.path
    method = request.method
    if path == "/v1/public/spaces":
        return httpx2.Response(
            200,
            json={
                "data": [{"id": 1, "title": "Alpha", "boards": [{"id": 7, "title": "B"}]}],
                "hasMore": False,
            },
        )
    if path == "/v1/public/spaces/1":
        return httpx2.Response(200, json={"id": 1, "title": "Alpha"})
    if path == "/v1/public/spaces/1/boards":
        return httpx2.Response(200, json={"data": [{"id": 7, "title": "B"}], "hasMore": False})
    if path == "/v1/public/spaces/1/boards/7":
        return httpx2.Response(
            200, json={"id": 7, "title": "B", "fields": [{"key": "s", "name": "Status"}]}
        )
    if path == "/v1/public/spaces/1/boards/7/items" and method == "GET":
        page = int(dict(request.url.params).get("page", "1"))
        return httpx2.Response(200, json=ITEMS_PAGE_1 if page == 1 else ITEMS_PAGE_2)
    if path == "/v1/public/spaces/1/boards/7/items/1":
        return httpx2.Response(200, json={"id": 1, "title": "One"})
    if path.startswith("/v1/public/spaces/1/boards/7/items/") and method == "PATCH":
        item_id = path.split("/items/")[1].split("/")[0]
        if item_id == "13":
            return httpx2.Response(500, json={"message": "boom"})
        return httpx2.Response(200, json={"id": int(item_id)})
    if path == "/v1/public/teams/9":
        return httpx2.Response(200, json={"id": 9, "title": "Team"})
    if path == "/v1/public/users":
        return httpx2.Response(
            200, json={"data": [{"id": 5, "email": "ada@x.com"}], "hasMore": False}
        )
    if path == "/v1/public/spaces/1/boards/7/item-groups":
        return httpx2.Response(
            200, json={"data": [{"id": 55, "title": "Group"}], "hasMore": False}
        )
    if path == "/v1/public/spaces/1/boards/7/items/1/files":
        return httpx2.Response(200, json=[{"id": 66, "name": "f.txt"}])
    return httpx2.Response(404, json={"message": "nope"})


def paged_workspace_client() -> PlakyClient:
    return PlakyClient(
        api_key="plk_x", max_retries=0, transport=httpx2.MockTransport(paged_workspace_handler)
    )
