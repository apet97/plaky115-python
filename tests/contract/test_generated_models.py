"""Generated Pydantic model behavior gates."""

import re
from pathlib import Path

import pydantic
import pytest

import plaky115.models.generated as generated

REPO = Path(__file__).resolve().parent.parent.parent


def test_response_models_allow_additive_fields() -> None:
    space = generated.SpaceResponse.model_validate({"id": 5, "title": "S", "futureField": True})
    assert space.model_extra == {"futureField": True}
    dumped = space.model_dump(by_alias=True, exclude_none=True)
    assert dumped["futureField"] is True


def test_request_models_forbid_unknown_fields() -> None:
    with pytest.raises(pydantic.ValidationError):
        generated.CommentRequest.model_validate({"text": "hello", "bogus": 1})


def test_aliases_round_trip() -> None:
    item = generated.ItemCreateRequest.model_validate({"title": "T", "groupId": 7, "parentId": 9})
    assert item.group_id == 7
    dumped = item.model_dump(by_alias=True, exclude_none=True)
    assert dumped == {"title": "T", "groupId": 7, "parentId": 9}
    # populate_by_name also accepts snake_case input.
    again = generated.ItemCreateRequest(title="T", group_id=7)
    assert again.model_dump(by_alias=True, exclude_none=True) == {"title": "T", "groupId": 7}


def test_all_request_models_are_strict() -> None:
    text = (REPO / "src/plaky115/models/generated.py").read_text(encoding="utf-8")
    request_classes = re.findall(r"class (\w+Request)\(BaseModel\):", text)
    assert len(request_classes) == 7
    assert text.count('extra="forbid"') == len(request_classes)


def test_json_schema_generation() -> None:
    for model in (generated.ItemResponse, generated.SpaceResponse, generated.CommentRequest):
        schema = model.model_json_schema()
        assert schema


def test_generated_header_present() -> None:
    text = (REPO / "src/plaky115/models/generated.py").read_text(encoding="utf-8")
    assert text.startswith("# AUTO-GENERATED. DO NOT EDIT.")
