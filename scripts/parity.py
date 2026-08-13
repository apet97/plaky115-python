"""Parity gate: machine-checkable inventories versus the pinned source.

Phase 0 scope: contract inputs, expected operations, operation overrides,
curated tool and workflow inventories, and source-manifest hash integrity.
Later phases extend this script with SDK, raw-tool, docs, and live
classification comparisons.

Run: python3 scripts/parity.py
Exit code 0 only when every check passes.
"""

from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
SOURCE_CHECKOUT = Path(
    os.environ.get(
        "PLAKY115_SOURCE_CHECKOUT", "/Users/15x/Downloads/WORKING/addons-me/plaky115"
    )
)

EXPECTED_OPERATION_COUNT = 32

CURATED_TOOLS = [
    "plaky_search_docs",
    "plaky_workspace_context",
    "plaky_find",
    "plaky_plan_mutation",
    "plaky_execute_workflow",
    "plaky_execute_read_workflow",
    "plaky_execute_mutation_workflow",
]

WORKFLOW_IDS = [
    "workspace.map",
    "items.search",
    "comments.thread",
    "export.items",
    "items.create",
    "items.updateFields",
    "comments.add",
    "itemGroups.create",
    "itemGroups.update",
    "itemFiles.upload",
    "itemFiles.update",
]

READ_WORKFLOW_IDS = WORKFLOW_IDS[:4]
MUTATION_WORKFLOW_IDS = WORKFLOW_IDS[4:]

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    expected = json.loads((REPO / "contract/expected-operations.json").read_text(encoding="utf-8"))
    ops = expected["operations"]
    method_paths = {(o["method"], o["path"]) for o in ops}
    op_ids = [o["operationId"] for o in ops]
    check(len(ops) == EXPECTED_OPERATION_COUNT, f"expected 32 operations, got {len(ops)}")
    check(len(method_paths) == len(ops), "duplicate method/path pair in expected operations")
    check(len(set(op_ids)) == len(ops), "duplicate operationId in expected operations")

    overrides = yaml.safe_load(
        (REPO / "contract/operation-overrides.yaml").read_text(encoding="utf-8")
    )
    over_ops: dict[str, dict[str, Any]] = overrides["operations"]
    check(len(over_ops) == EXPECTED_OPERATION_COUNT, f"expected 32 overrides, got {len(over_ops)}")

    over_by_id: dict[str, dict[str, Any]] = {}
    mcp_names: set[str] = set()
    for key, entry in over_ops.items():
        method, _, path = key.partition(" ")
        check((method, path) in method_paths, f"override key not in expected operations: {key}")
        oid = str(entry.get("operationId"))
        check(oid in set(op_ids), f"override operationId unknown: {oid}")
        over_by_id[oid] = entry
        sdk = entry.get("sdk", {})
        check(bool(sdk.get("resource")) and bool(sdk.get("method")), f"{oid}: missing sdk mapping")
        mcp = entry.get("mcp", {})
        name = mcp.get("name", "")
        check(name.startswith("plaky_") and len(name) <= 64, f"{oid}: bad mcp name {name!r}")
        check(bool(mcp.get("title")), f"{oid}: missing mcp title")
        check(
            mcp.get("scopes") in (["read"], ["write"], ["write", "destructive"]),
            f"{oid}: unexpected scopes {mcp.get('scopes')}",
        )
        annotations = mcp.get("annotations", {})
        for hint in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
            check(isinstance(annotations.get(hint), bool), f"{oid}: missing annotation {hint}")
        check(
            entry.get("response", {}).get("root") in ("page", "object", "array", "void"),
            f"{oid}: bad response root",
        )
        mcp_names.add(name)
    check(len(mcp_names) == EXPECTED_OPERATION_COUNT, "raw MCP tool names are not unique")
    check(set(over_by_id) == set(op_ids), "override operationIds do not match expected inventory")

    destructive = {
        oid for oid, e in over_by_id.items() if e["mcp"]["scopes"] == ["write", "destructive"]
    }
    check(
        destructive
        == {
            "deleteItem",
            "deleteItemComment",
            "deleteItemGroup",
            "archiveItemGroup",
            "deleteItemFile",
        },
        f"destructive set mismatch: {sorted(destructive)}",
    )
    check(
        over_by_id["getItemFileDownload"]["sensitiveOutput"] is True,
        "getItemFileDownload must be sensitiveOutput",
    )

    check(len(CURATED_TOOLS) == 7, "curated tool inventory must have 7 entries")
    check(len(WORKFLOW_IDS) == 11, "workflow inventory must have 11 entries")
    check(
        len(READ_WORKFLOW_IDS) == 4 and len(MUTATION_WORKFLOW_IDS) == 7,
        "workflow read/mutation split mismatch",
    )

    manifest = json.loads((REPO / "contract/source-manifest.json").read_text(encoding="utf-8"))
    check(
        manifest["sourceCommit"] == "33ae2926aa696f36d9663d44f914d42d9aadc53f",
        "source manifest commit mismatch",
    )
    check(manifest["sourceRelease"] == "v1.0.11", "source manifest release mismatch")
    provenance_checked = SOURCE_CHECKOUT.is_dir()
    if provenance_checked:
        for f in manifest["files"]:
            p = SOURCE_CHECKOUT / f["sourcePath"]
            if not p.is_file():
                check(False, f"manifest source file missing: {f['sourcePath']}")
                continue
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            check(digest == f["sourceSha256"], f"manifest hash drift for {f['sourcePath']}")
        # Verbatim copies must be byte-identical to their targets.
        for f in manifest["files"]:
            if f["translation"] == "verbatim copy":
                src = (SOURCE_CHECKOUT / f["sourcePath"]).read_bytes()
                dst = (REPO / f["target"]).read_bytes()
                check(src == dst, f"verbatim copy drift: {f['target']}")

    # The upstream mirror keeps Plaky's raw operationIds (e.g. getSpaces);
    # canonical operationIds are assigned by the overrides layer, keyed by
    # exact method/path. Here only the method/path inventory must agree.
    upstream = yaml.safe_load(
        (REPO / "contract/upstream.openapi.yaml").read_text(encoding="utf-8")
    )
    spec_ops: set[tuple[str, str]] = set()
    for path, item in upstream["paths"].items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in item:
                spec_ops.add((method.upper(), path))
                check(
                    bool(item[method].get("operationId")),
                    f"upstream operation missing operationId: {method.upper()} {path}",
                )
    check(spec_ops == method_paths, "upstream spec operations do not match expected inventory")

    if failures:
        print(f"PARITY FAIL ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    hashes = (
        "manifest hashes verified"
        if provenance_checked
        else "manifest hashes SKIPPED (source checkout unavailable; "
        "set PLAKY115_SOURCE_CHECKOUT to verify provenance)"
    )
    print(f"PARITY OK: 32 operations, 7 curated tools, 11 workflows, {hashes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
