"""Result compaction: bounded entities and text summaries with a JSON mirror."""

from plaky115_mcp.compaction import MAX_TEXT_CHARS, compact_entity, make_result


def test_compaction_edges() -> None:
    unknown = compact_entity({str(i): i for i in range(30)}, "mystery")
    assert len(unknown) == 20  # bounded fallback for unknown kinds
    nested = compact_entity({"id": 1, "group": {"id": 9, "title": "x"}}, "item")
    assert nested["group"] == 9
    long_text = make_result(text="y" * (MAX_TEXT_CHARS + 50), structured={"ok": True})
    text_block = long_text.content[0]
    summary, mirror = getattr(text_block, "text", "").split("\n", 1)
    assert len(summary) == MAX_TEXT_CHARS  # summary truncates independently
    assert mirror == '{"ok":true}'  # structured payload mirrored after it
