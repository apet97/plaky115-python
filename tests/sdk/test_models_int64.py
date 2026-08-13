"""Response models must keep unsafe int64 IDs as exact decimal strings.

The transport decodes JSON integers beyond +-2**53-1 as decimal strings
(runtime/responses.py). Model validation must not coerce those strings
back to a bare number, or JSON re-serialization loses digits for
JavaScript consumers.
"""

from plaky115.models.generated import ItemGroupResponse, ItemResponse
from plaky115.runtime.responses import parse_json_preserving_int64

UNSAFE_ID = "9223372036854775807"  # max signed int64; beyond 2**53-1


def test_unsafe_int64_id_survives_model_round_trip() -> None:
    payload = parse_json_preserving_int64(f'{{"id": {UNSAFE_ID}, "title": "x"}}')
    assert payload["id"] == UNSAFE_ID  # decoded as a string
    item = ItemResponse.model_validate(payload)
    assert item.id == UNSAFE_ID
    assert item.model_dump(mode="json", by_alias=True)["id"] == UNSAFE_ID


def test_safe_int_id_stays_int() -> None:
    item = ItemResponse.model_validate({"id": 42})
    assert item.id == 42
    assert isinstance(item.id, int)


def test_unsafe_int64_survives_expandable_union() -> None:
    payload = parse_json_preserving_int64(f'{{"id": 1, "group": {UNSAFE_ID}}}')
    item = ItemResponse.model_validate(payload)
    assert item.group == UNSAFE_ID
    expanded = ItemResponse.model_validate({"id": 1, "group": {"id": 3, "title": "g"}})
    assert isinstance(expanded.group, ItemGroupResponse)
