"""Table-driven ID canonicalization gates (plan 6.4, spec-helpers §1)."""

import pytest

from plaky115.ids import (
    as_board_id,
    as_comment_id,
    as_field_key,
    as_folder_id,
    as_item_file_id,
    as_item_group_id,
    as_item_id,
    as_space_id,
    as_team_id,
    as_user_id,
    encode_path_segment,
    id_path_segment,
)

ACCEPT = [
    (0, "0"),
    (1, "1"),
    (123, "123"),
    (9223372036854775807, "9223372036854775807"),
    ("0", "0"),
    ("1", "1"),
    ("9007199254740992", "9007199254740992"),
    ("9223372036854775807", "9223372036854775807"),
]

REJECT = [
    -1,
    1.5,
    True,
    False,
    "01",
    "007",
    " 1",
    "1 ",
    "1\n",
    "+1",
    "-1",
    "1.0",
    "1e3",
    "",
    "9223372036854775808",
    9223372036854775808,
]


@pytest.mark.parametrize(("value", "expected"), ACCEPT)
def test_accepts_canonical(value: int | str, expected: str) -> None:
    assert id_path_segment(value) == expected


@pytest.mark.parametrize("value", REJECT)
def test_rejects_malformed(value: object) -> None:
    with pytest.raises(ValueError):
        id_path_segment(value)  # type: ignore[arg-type]


def test_all_ten_helpers_exported() -> None:
    helpers = [
        as_space_id,
        as_board_id,
        as_item_id,
        as_comment_id,
        as_user_id,
        as_team_id,
        as_item_group_id,
        as_item_file_id,
        as_folder_id,
    ]
    for helper in helpers:
        assert helper(7) == "7"
        assert helper("42") == "42"
    assert as_field_key("status-1") == "status-1"


def test_field_key_rules() -> None:
    with pytest.raises(ValueError):
        as_field_key("")
    assert as_field_key("čšž-1") == "čšž-1"


def test_unicode_path_segment_encoding() -> None:
    assert encode_path_segment("čšž key/../x") == "%C4%8D%C5%A1%C5%BE%20key%2F..%2Fx"
    # encodeURIComponent-safe punctuation stays literal.
    assert encode_path_segment("a-b_c.d!e~f*g'h(i)j") == "a-b_c.d!e~f*g'h(i)j"
