"""Cross-surface parity: every contract operation through both clients.

Port of the pinned source's scripts/test-cross-surface-parity.mjs. Each
operation is invoked through AsyncPlakyClient and PlakyClient against a
mock transport that asserts the exact method, escaped path, query string,
and body, and returns a shape matching the declared response root.
"""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx2
import pytest

from plaky115 import AsyncPlakyClient, PlakyClient

pytestmark = pytest.mark.anyio

REPO = Path(__file__).resolve().parent.parent.parent
OPERATIONS = {
    d["operationId"]: d
    for d in json.loads((REPO / "contract/generated/operations.json").read_text(encoding="utf-8"))[
        "operations"
    ]
}

SPACE, BOARD, ITEM, COMMENT = "11", "22", "33", "44"
GROUP, FILE_ID, TEAM = "55", "66", "77"
FIELD_KEY = "status-1"

BODIES: dict[str, Any] = {
    "createItem": {"title": "T", "groupId": "7"},
    "updateItemField": {"value": "To do"},
    "updateItemFields": {"status-1": "1"},
    "createItemComment": {"text": "hello"},
    "updateItemComment": {"text": "edited"},
    "replaceCommentReactions": {"reactions": [{"value": "1f44d"}]},
    "createItemGroup": {"title": "G", "color": "#AABBCC"},
    "updateItemGroup": {"title": "G", "color": "#AABBCC", "ranking": "aaa"},
    "updateItemFile": {"name": "renamed.txt"},
}

# (expected query string, expected body or None, invoker kwargs builder)
AsyncInvoker = Callable[[AsyncPlakyClient], Awaitable[Any]]
SyncInvoker = Callable[[PlakyClient], Any]


def async_invokers() -> dict[str, AsyncInvoker]:
    return {
        "listSpaces": lambda c: c.spaces.list(page=2, page_size=5, expand=["board"]),
        "getSpace": lambda c: c.spaces.get(SPACE, expand=["board"]),
        "listBoards": lambda c: c.boards.list(space_id=SPACE, page=2, page_size=5),
        "getBoard": lambda c: c.boards.get(space_id=SPACE, board_id=BOARD),
        "listItems": lambda c: c.items.list(
            space_id=SPACE,
            board_id=BOARD,
            page=2,
            page_size=5,
            expand=["space", "board"],
            board_view_id=5,
            parent_id="9",
            subitems_behaviour="INCLUDE",
        ),
        "createItem": lambda c: c.items.create(
            space_id=SPACE, board_id=BOARD, body=BODIES["createItem"]
        ),
        "listSubitems": lambda c: c.items.list_subitems(
            space_id=SPACE,
            board_id=BOARD,
            item_id=ITEM,
            page=2,
            page_size=5,
            expand=["space", "board"],
        ),
        "getItem": lambda c: c.items.get(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, expand=["space", "board"]
        ),
        "deleteItem": lambda c: c.items.delete(space_id=SPACE, board_id=BOARD, item_id=ITEM),
        "updateItemField": lambda c: c.items.update_field(
            space_id=SPACE,
            board_id=BOARD,
            item_id=ITEM,
            item_field_key=FIELD_KEY,
            body=BODIES["updateItemField"],
        ),
        "updateItemFields": lambda c: c.items.update_fields(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, body=BODIES["updateItemFields"]
        ),
        "listItemComments": lambda c: c.comments.list(
            space_id=SPACE, board_id=BOARD, item_id=ITEM
        ),
        "createItemComment": lambda c: c.comments.create(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, body=BODIES["createItemComment"]
        ),
        "updateItemComment": lambda c: c.comments.update(
            space_id=SPACE,
            board_id=BOARD,
            item_id=ITEM,
            item_comment_id=COMMENT,
            body=BODIES["updateItemComment"],
        ),
        "deleteItemComment": lambda c: c.comments.delete(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, item_comment_id=COMMENT
        ),
        "replaceCommentReactions": lambda c: c.reactions.replace(
            space_id=SPACE,
            board_id=BOARD,
            item_id=ITEM,
            item_comment_id=COMMENT,
            body=BODIES["replaceCommentReactions"],
        ),
        "listUsers": lambda c: c.users.list(
            page=2, page_size=5, emails=["a@x.com", "b@x.com"], status="ACTIVE", type="MEMBER"
        ),
        "getCurrentUser": lambda c: c.users.me(),
        "listTeams": lambda c: c.teams.list(page=2, page_size=5),
        "getTeam": lambda c: c.teams.get(TEAM),
        "listItemGroups": lambda c: c.item_groups.list(
            space_id=SPACE, board_id=BOARD, page=2, page_size=5
        ),
        "getItemGroup": lambda c: c.item_groups.get(
            space_id=SPACE, board_id=BOARD, item_group_id=GROUP
        ),
        "createItemGroup": lambda c: c.item_groups.create(
            space_id=SPACE, board_id=BOARD, body=BODIES["createItemGroup"]
        ),
        "updateItemGroup": lambda c: c.item_groups.update(
            space_id=SPACE, board_id=BOARD, item_group_id=GROUP, body=BODIES["updateItemGroup"]
        ),
        "deleteItemGroup": lambda c: c.item_groups.delete(
            space_id=SPACE, board_id=BOARD, item_group_id=GROUP
        ),
        "archiveItemGroup": lambda c: c.item_groups.archive(
            space_id=SPACE, board_id=BOARD, item_group_id=GROUP
        ),
        "uploadItemFile": lambda c: c.item_files.upload(
            space_id=SPACE,
            board_id=BOARD,
            item_id=ITEM,
            file=b"parity",
            file_name="parity.txt",
            content_type="text/plain",
        ),
        "listItemFiles": lambda c: c.item_files.list(space_id=SPACE, board_id=BOARD, item_id=ITEM),
        "getItemFile": lambda c: c.item_files.get(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, item_file_id=FILE_ID
        ),
        "getItemFileDownload": lambda c: c.item_files.get_download(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, item_file_id=FILE_ID
        ),
        "updateItemFile": lambda c: c.item_files.update(
            space_id=SPACE,
            board_id=BOARD,
            item_id=ITEM,
            item_file_id=FILE_ID,
            body=BODIES["updateItemFile"],
        ),
        "deleteItemFile": lambda c: c.item_files.delete(
            space_id=SPACE, board_id=BOARD, item_id=ITEM, item_file_id=FILE_ID
        ),
    }


def sync_invokers() -> dict[str, SyncInvoker]:
    # Sync methods have identical names and signatures; reuse the async table
    # since each lambda only calls resource methods present on both clients.
    return dict(async_invokers().items())  # type: ignore[arg-type]


EXPECTED_QUERY: dict[str, str] = {
    "listSpaces": "page=2&pageSize=5&expand=board",
    "getSpace": "expand=board",
    "listBoards": "page=2&pageSize=5",
    "listItems": (
        "page=2&pageSize=5&expand=space%2Cboard&boardViewId=5&parentId=9&subitemsBehaviour=INCLUDE"
    ),
    "listSubitems": "page=2&pageSize=5&expand=space%2Cboard",
    "getItem": "expand=space%2Cboard",
    "listUsers": "page=2&pageSize=5&emails=a%40x.com&emails=b%40x.com&status=ACTIVE&type=MEMBER",
    "listTeams": "page=2&pageSize=5",
    "listItemGroups": "page=2&pageSize=5",
}

SUCCESS_PAYLOADS: dict[str, Any] = {
    "paged-object": {"data": [], "hasMore": False},
    "json-array": [],
    "json-object": {"id": 1},
    "void": None,
}


def make_handler(descriptor: dict[str, Any], calls: list[str]) -> Any:
    op_id = descriptor["operationId"]
    expected_path = descriptor["path"]
    for name, value in (
        ("spaceId", SPACE),
        ("boardId", BOARD),
        ("itemId", ITEM),
        ("itemCommentId", COMMENT),
        ("itemGroupId", GROUP),
        ("itemFileId", FILE_ID),
        ("teamId", TEAM),
        ("itemFieldKey", FIELD_KEY),
    ):
        expected_path = expected_path.replace("{" + name + "}", value)

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(op_id)
        assert request.method == descriptor["method"], op_id
        assert request.url.path == expected_path, (op_id, request.url.path)
        assert request.url.query.decode() == EXPECTED_QUERY.get(op_id, ""), op_id
        if descriptor["request"]["kind"] == "json":
            assert json.loads(request.read()) == BODIES[op_id], op_id
        elif descriptor["request"]["kind"] == "multipart":
            content = request.read()
            assert b'name="file"' in content and b"parity" in content, op_id
        else:
            assert request.read() == b"", op_id
        kind = descriptor["success"]["kind"]
        if kind == "void":
            return httpx2.Response(200)
        return httpx2.Response(descriptor["success"]["status"], json=SUCCESS_PAYLOADS[kind])

    return handler


def test_invoker_tables_cover_all_32_operations() -> None:
    assert set(async_invokers()) == set(OPERATIONS)
    assert len(OPERATIONS) == 32


@pytest.mark.parametrize("op_id", sorted(OPERATIONS))
async def test_async_operation_wire_shape(op_id: str) -> None:
    descriptor = OPERATIONS[op_id]
    calls: list[str] = []
    async with AsyncPlakyClient(
        api_key="plk_test",
        max_retries=0,
        transport=httpx2.MockTransport(make_handler(descriptor, calls)),
    ) as client:
        await async_invokers()[op_id](client)
    assert calls == [op_id]


@pytest.mark.parametrize("op_id", sorted(OPERATIONS))
def test_sync_operation_wire_shape(op_id: str) -> None:
    descriptor = OPERATIONS[op_id]
    calls: list[str] = []
    with PlakyClient(
        api_key="plk_test",
        max_retries=0,
        transport=httpx2.MockTransport(make_handler(descriptor, calls)),
    ) as client:
        sync_invokers()[op_id](client)
    assert calls == [op_id]


def test_sync_async_resource_parity() -> None:
    """Every async resource method has a sync counterpart with the same name."""
    import plaky115.resources as resources

    pairs = [
        ("SpacesResource", "AsyncSpacesResource"),
        ("BoardsResource", "AsyncBoardsResource"),
        ("ItemsResource", "AsyncItemsResource"),
        ("ItemCommentsResource", "AsyncItemCommentsResource"),
        ("ReactionsResource", "AsyncReactionsResource"),
        ("UsersResource", "AsyncUsersResource"),
        ("TeamsResource", "AsyncTeamsResource"),
        ("ItemGroupsResource", "AsyncItemGroupsResource"),
        ("ItemFilesResource", "AsyncItemFilesResource"),
    ]
    for sync_name, async_name in pairs:
        sync_methods = {m for m in dir(getattr(resources, sync_name)) if not m.startswith("_")}
        async_methods = {m for m in dir(getattr(resources, async_name)) if not m.startswith("_")}
        assert sync_methods == async_methods, sync_name


def test_operation_sdk_map_matches_descriptors() -> None:
    """Descriptor sdk.resource/sdk.method map onto real client attributes."""
    client = PlakyClient(api_key="plk_test", transport=httpx2.MockTransport(lambda _: None))  # type: ignore[arg-type,return-value]
    for descriptor in OPERATIONS.values():
        resource = getattr(client, descriptor["sdk"]["resource"])
        assert callable(getattr(resource, descriptor["sdk"]["method"])), descriptor["operationId"]
