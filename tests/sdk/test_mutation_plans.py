"""Mutation plan normalizers: required fields, conflicts, and canonical ids."""

import pytest

from plaky115 import (
    Base64UploadInput,
    normalize_base64_upload_plan,
    normalize_binary_upload_plan,
    normalize_comment_plan,
    normalize_item_file_update_plan,
    normalize_item_group_update_plan,
)
from plaky115.workflows.mutation_plans import (
    normalize_item_create_plan,
    normalize_item_group_create_plan,
)

pytestmark = pytest.mark.anyio


def test_plan_normalizer_conflicts_and_types() -> None:
    with pytest.raises(TypeError, match="cannot both be provided"):
        normalize_item_create_plan(
            space_id=1, board_id=7, body={"title": "t", "groupId": 1, "groupTitle": "g"}
        )
    with pytest.raises(TypeError, match=r"body\.groupTitle must be a non-empty string"):
        normalize_item_create_plan(space_id=1, board_id=7, body={"groupTitle": " "})
    plan = normalize_item_create_plan(
        space_id=1, board_id=7, body={"title": "t", "groupTitle": "Launch"}
    )
    assert plan.requires_live_resolution is True
    with pytest.raises(TypeError, match=r"body\.groupId must be a number or decimal string"):
        normalize_item_create_plan(space_id=1, board_id=7, body={"groupId": 1.5})
    with pytest.raises(TypeError, match="spaceId:"):
        normalize_item_group_create_plan(
            space_id="01", board_id=7, body={"title": "t", "color": "#AABBCC"}
        )
    with pytest.raises(TypeError, match=r"body\.ranking must be a non-empty string when provided"):
        normalize_item_group_create_plan(
            space_id=1, board_id=7, body={"title": "t", "color": "#AABBCC", "ranking": " "}
        )


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
