"""Contract pipeline gates: inventory, determinism, and descriptor invariants."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent.parent
OPERATIONS = json.loads((REPO / "contract/generated/operations.json").read_text(encoding="utf-8"))
DESCRIPTORS = OPERATIONS["operations"]


def test_exactly_34_unique_operations() -> None:
    assert len(DESCRIPTORS) == 34
    assert len({d["operationId"] for d in DESCRIPTORS}) == 34
    assert len({(d["method"], d["path"]) for d in DESCRIPTORS}) == 34
    assert len({d["mcpName"] for d in DESCRIPTORS}) == 34


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
        "overrideSubscriptions",
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
    spec = json.loads((REPO / "contract/generated/plaky.openapi.json").read_text(encoding="utf-8"))
    schemes = spec["components"]["securitySchemes"]
    assert list(schemes) == ["api-key-auth"]
    assert schemes["api-key-auth"] == {"in": "header", "name": "X-API-Key", "type": "apiKey"}


def test_docs_index_covers_operations_workflows_guides() -> None:
    index = json.loads((REPO / "contract/generated/docs-index.json").read_text(encoding="utf-8"))
    kinds: dict[str, int] = {}
    for entry in index["entries"]:
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    assert kinds["operation"] == 34
    assert kinds["workflow"] == 11
    assert kinds["guide"] >= 3


def _contract_script() -> Any:
    spec = importlib.util.spec_from_file_location("contract_script", REPO / "scripts/contract.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fetch_extracts_the_spec_embedded_in_the_docs_page() -> None:
    contract = _contract_script()
    page = (
        "<!doctype html><script>\n  const openApiSpec = "
        '{"openapi": "3.1.0", "info": {"title": "a } b"}, "paths": {}};\n'
        "  Scalar.createApiReference(openApiSpec);</script>"
    )
    spec = contract.extract_embedded_spec(page)
    assert spec == {"openapi": "3.1.0", "info": {"title": "a } b"}, "paths": {}}

    with pytest.raises(ValueError, match="no embedded OpenAPI"):
        contract.extract_embedded_spec("<!doctype html><p>nothing here</p>")
    with pytest.raises(ValueError, match="not an OpenAPI object"):
        contract.extract_embedded_spec('const openApiSpec = {"swagger": "2.0"};')


def test_upstream_mirror_round_trips_through_the_fetch_dumper() -> None:
    contract = _contract_script()
    spec = contract.load_yaml(REPO / "contract/upstream.openapi.yaml")
    dumped = yaml.dump(
        spec,
        Dumper=contract._UpstreamYamlDumper,
        sort_keys=True,
        explicit_start=True,
        allow_unicode=True,
    )
    assert yaml.safe_load(dumped) == spec
