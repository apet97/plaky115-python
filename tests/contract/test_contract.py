"""Contract pipeline gates: inventory, determinism, and descriptor invariants."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
OPERATIONS = json.loads((REPO / "contract/generated/operations.json").read_text())
DESCRIPTORS = OPERATIONS["operations"]


def test_exactly_32_unique_operations() -> None:
    assert len(DESCRIPTORS) == 32
    assert len({d["operationId"] for d in DESCRIPTORS}) == 32
    assert len({(d["method"], d["path"]) for d in DESCRIPTORS}) == 32
    assert len({d["mcpName"] for d in DESCRIPTORS}) == 32


def test_descriptors_sorted_and_complete() -> None:
    ids = [d["operationId"] for d in DESCRIPTORS]
    assert ids == sorted(ids)
    for d in DESCRIPTORS:
        assert d["mcpName"].startswith("plaky_") and len(d["mcpName"]) <= 64
        assert d["scopes"] in (["read"], ["write"], ["write", "destructive"])
        assert d["success"]["root"] in ("page", "object", "array", "void")
        assert d["request"]["kind"] in ("none", "json", "multipart")
        assert d["sdk"]["resource"] and d["sdk"]["method"]
        assert isinstance(d["readOnly"], bool)
        assert d["readOnly"] == (d["scopes"] == ["read"])
        assert d["destructive"] == ("destructive" in d["scopes"])
        if d["success"]["root"] == "page":
            assert d["pagination"]["kind"] == "pageNumber"
            assert d["success"]["envelope"].startswith("PublicPagedResponseV1")


def test_bare_array_and_void_inventory() -> None:
    arrays = {d["operationId"] for d in DESCRIPTORS if d["success"]["root"] == "array"}
    assert arrays == {"listItemComments", "listItemFiles"}
    voids = {d["operationId"] for d in DESCRIPTORS if d["success"]["root"] == "void"}
    assert voids == {
        "deleteItem",
        "deleteItemComment",
        "deleteItemGroup",
        "archiveItemGroup",
        "deleteItemFile",
    }


def test_expand_is_comma_joined_not_exploded() -> None:
    by_id = {d["operationId"]: d for d in DESCRIPTORS}
    for op_id in ("listSpaces", "getSpace", "listItems", "getItem", "listSubitems"):
        expand = [q for q in by_id[op_id]["query"] if q["name"] == "expand"]
        assert expand, op_id
        assert expand[0]["explode"] is False
        assert expand[0]["array"] is True


def test_emails_are_exploded_repeated_keys() -> None:
    by_id = {d["operationId"]: d for d in DESCRIPTORS}
    emails = [q for q in by_id["listUsers"]["query"] if q["name"] == "emails"]
    assert emails and emails[0]["explode"] is True and emails[0]["array"] is True


def test_contract_check_is_green() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/contract.py", "check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_security_scheme_is_x_api_key() -> None:
    spec = json.loads((REPO / "contract/generated/plaky.openapi.json").read_text())
    schemes = spec["components"]["securitySchemes"]
    assert list(schemes) == ["api-key-auth"]
    assert schemes["api-key-auth"] == {"in": "header", "name": "X-API-Key", "type": "apiKey"}


def test_docs_index_covers_operations_workflows_guides() -> None:
    index = json.loads((REPO / "contract/generated/docs-index.json").read_text())
    kinds: dict[str, int] = {}
    for entry in index["entries"]:
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    assert kinds["operation"] == 32
    assert kinds["workflow"] == 11
    assert kinds["guide"] >= 3
