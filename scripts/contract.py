"""Contract pipeline: fetch, diff, accept, build, and check.

Inputs (hand-maintained):
- contract/upstream.openapi.yaml   accepted upstream mirror
- contract/operation-overrides.yaml exact-key operation metadata
- contract/schema-patches.yaml     minimal JSON Pointer patches
- contract/expected-operations.json pinned operation inventory
- contract/source-manifest.json    provenance record

Outputs (generated, deterministic):
- contract/generated/plaky.openapi.json  patched, canonical spec
- contract/generated/operations.json     operation descriptors
- contract/generated/docs-index.json     documentation index

Usage:
  uv run python scripts/contract.py build
  uv run python scripts/contract.py check
  uv run python scripts/contract.py fetch --url <openapi-url>
  uv run python scripts/contract.py diff
  uv run python scripts/contract.py accept
"""

from __future__ import annotations

# This script manipulates raw parsed JSON/YAML; unknown-type strictness is
# relaxed file-wide. The package sources remain fully strict.
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
import argparse
import copy
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from openapi_spec_validator import validate as validate_openapi

REPO = Path(__file__).resolve().parent.parent
CONTRACT = REPO / "contract"
GENERATED = CONTRACT / "generated"
CANDIDATE = CONTRACT / "candidate"

HTTP_METHODS = ("get", "put", "post", "delete", "patch")

ROOT_TO_SUCCESS_KIND = {
    "page": "paged-object",
    "object": "json-object",
    "array": "json-array",
    "void": "void",
}

OVERRIDES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["version", "operations"],
    "properties": {
        "version": {"const": 1},
        "operations": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": [
                    "operationId",
                    "summary",
                    "sdk",
                    "request",
                    "response",
                    "mcp",
                    "confirmation",
                    "compactKind",
                    "sensitiveOutput",
                ],
                "properties": {
                    "operationId": {"type": "string", "minLength": 1},
                    "summary": {"type": "string", "minLength": 1},
                    "sdk": {
                        "type": "object",
                        "required": ["resource", "method"],
                        "properties": {
                            "resource": {"type": "string", "minLength": 1},
                            "method": {"type": "string", "minLength": 1},
                        },
                    },
                    "request": {
                        "type": "object",
                        "required": ["kind"],
                        "properties": {
                            "kind": {"enum": ["none", "json", "multipart"]},
                            "required": {"type": "boolean"},
                            "model": {"type": "string"},
                        },
                    },
                    "response": {
                        "type": "object",
                        "required": ["root", "status"],
                        "properties": {
                            "root": {"enum": ["page", "object", "array", "void"]},
                            "status": {"type": "integer"},
                            "model": {"type": "string"},
                            "envelope": {"type": "string"},
                        },
                    },
                    "mcp": {
                        "type": "object",
                        "required": ["name", "title", "scopes", "annotations"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "pattern": "^plaky_[a-z0-9_]+$",
                                "maxLength": 64,
                            },
                            "title": {"type": "string", "minLength": 1},
                            "scopes": {
                                "type": "array",
                                "items": {"enum": ["read", "write", "destructive"]},
                                "minItems": 1,
                            },
                            "annotations": {
                                "type": "object",
                                "required": [
                                    "readOnlyHint",
                                    "destructiveHint",
                                    "idempotentHint",
                                    "openWorldHint",
                                ],
                                "additionalProperties": {"type": "boolean"},
                            },
                        },
                    },
                    "confirmation": {"enum": ["none", "destructive"]},
                    "compactKind": {"type": "string", "minLength": 1},
                    "sensitiveOutput": {"type": "boolean"},
                    "pagination": {
                        "type": "object",
                        "required": ["kind", "pageParameter", "sizeParameter"],
                        "properties": {
                            "kind": {"const": "pageNumber"},
                            "pageParameter": {"type": "string"},
                            "sizeParameter": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def resolve_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("#/"):
        raise ValueError(f"unsupported external reference: {pointer}")
    node = document
    for raw in pointer[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            node = node[int(key)]
        elif isinstance(node, dict):
            if key not in node:
                raise ValueError(f"unresolved reference: {pointer}")
            node = node[key]
        else:
            raise ValueError(f"unresolved reference: {pointer}")
    return node


def assert_all_refs_resolve(spec: dict[str, Any]) -> int:
    count = 0

    def walk(node: Any) -> None:
        nonlocal count
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                resolve_pointer(spec, ref)
                count += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(spec)
    return count


def apply_schema_patches(spec: dict[str, Any], patches_path: Path) -> dict[str, Any]:
    """Apply minimal JSON Pointer patches for confirmed upstream defects."""
    patched = copy.deepcopy(spec)
    if not patches_path.is_file():
        return patched
    doc = load_yaml(patches_path) or {}
    patches: list[dict[str, Any]] = doc.get("patches", [])
    for patch in patches:
        pointer: str = patch["pointer"]
        parent_pointer, _, leaf = pointer.rpartition("/")
        parent = resolve_pointer(patched, parent_pointer or "#/")
        op = patch["op"]
        if isinstance(parent, list):
            index = int(leaf)
            if op in ("replace", "add"):
                parent[index] = patch["value"]
            elif op == "remove":
                del parent[index]
            else:
                raise ValueError(f"unsupported patch op: {op}")
        else:
            key = leaf.replace("~1", "/").replace("~0", "~")
            if op in ("replace", "add"):
                parent[key] = patch["value"]
            elif op == "remove":
                del parent[key]
            else:
                raise ValueError(f"unsupported patch op: {op}")
    return patched


def iter_operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    out: list[tuple[str, str, dict[str, Any]]] = []
    for path in sorted(spec["paths"]):
        item = spec["paths"][path]
        for method in HTTP_METHODS:
            if method in item:
                out.append((method.upper(), path, item[method]))
    return out


def request_kind(operation: dict[str, Any]) -> tuple[str, bool, str | None]:
    body = operation.get("requestBody")
    if not body:
        return "none", False, None
    content = body.get("content", {})
    required = bool(body.get("required", False))
    if "application/json" in content:
        ref = content["application/json"].get("schema", {}).get("$ref")
        model = ref.rsplit("/", 1)[-1] if ref else None
        return "json", required, model
    if "multipart/form-data" in content:
        return "multipart", required, None
    raise ValueError(f"unsupported request content: {sorted(content)}")


def normalize_parameter(parameter: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in parameter:
        parameter = resolve_pointer(spec, parameter["$ref"])
    out: dict[str, Any] = {
        "name": parameter["name"],
        "in": parameter["in"],
        "required": bool(parameter.get("required", False)),
    }
    if "description" in parameter:
        out["description"] = parameter["description"]
    if "schema" in parameter:
        out["schema"] = parameter["schema"]
    if parameter["in"] == "query":
        out["style"] = parameter.get("style", "form")
        out["explode"] = bool(parameter.get("explode", out["style"] == "form"))
    return out


def build_descriptor(
    method: str,
    path: str,
    operation: dict[str, Any],
    override: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    mcp = override["mcp"]
    root = override["response"]["root"]
    kind, required, spec_model = request_kind(operation)
    if kind != override["request"]["kind"]:
        raise ValueError(
            f"{override['operationId']}: request kind mismatch "
            f"(spec {kind}, override {override['request']['kind']})"
        )
    status = str(override["response"]["status"])
    if status not in operation.get("responses", {}):
        raise ValueError(f"{override['operationId']}: status {status} not in spec responses")

    raw_parameters: list[dict[str, Any]] = operation.get("parameters") or []
    parameters = [normalize_parameter(p, spec) for p in raw_parameters]
    pagination_names: set[str] = set()
    pagination: dict[str, Any] | None = None
    if "pagination" in override:
        pagination_names = {
            override["pagination"]["pageParameter"],
            override["pagination"]["sizeParameter"],
        }
        inputs = [p for p in parameters if p["name"] in pagination_names]
        if len(inputs) != 2:
            raise ValueError(f"{override['operationId']}: pagination parameters missing in spec")
        pagination = {
            **override["pagination"],
            "resultsPointer": "$.data",
            "hasMorePointer": "$.hasMore",
            "inputs": inputs,
        }
    plain_parameters = [p for p in parameters if p["name"] not in pagination_names]
    query = [
        {
            **{k: v for k, v in p.items() if k != "in"},
            "array": p.get("schema", {}).get("type") == "array",
        }
        for p in plain_parameters
        if p["in"] == "query"
    ]

    scopes = list(mcp["scopes"])
    hints = mcp["annotations"]
    descriptor: dict[str, Any] = {
        "operationId": override["operationId"],
        "method": method,
        "path": path,
        "summary": override["summary"],
        "mcpName": mcp["name"],
        "mcpTitle": mcp["title"],
        "description": operation.get("description", override["summary"]),
        "scopes": scopes,
        "readOnly": hints["readOnlyHint"],
        "destructive": hints["destructiveHint"],
        "idempotent": hints["idempotentHint"],
        "openWorld": hints["openWorldHint"],
        "list": root in ("page", "array"),
        "mutation": "write" in scopes,
        "sdk": dict(override["sdk"]),
        "request": {
            "kind": kind,
            "required": required,
        },
        "success": {
            "status": override["response"]["status"],
            "kind": ROOT_TO_SUCCESS_KIND[root],
            "root": root,
        },
        "confirmation": override["confirmation"],
        "compactKind": override["compactKind"],
        "sensitiveOutput": override["sensitiveOutput"],
        "parameters": plain_parameters,
        "query": query,
    }
    if kind != "none":
        descriptor["request"]["model"] = override["request"]["model"]
        if spec_model and kind == "json" and spec_model != override["request"]["model"]:
            raise ValueError(
                f"{override['operationId']}: request model mismatch "
                f"(spec {spec_model}, override {override['request']['model']})"
            )
    if "model" in override["response"]:
        descriptor["success"]["model"] = override["response"]["model"]
    if "envelope" in override["response"]:
        descriptor["success"]["envelope"] = override["response"]["envelope"]
    if pagination is not None:
        descriptor["pagination"] = pagination
    return descriptor


# Curated workflow inventory used by the docs index and later by the MCP
# registry parity gate. IDs and classes are pinned by the source port.
WORKFLOWS: list[dict[str, str]] = [
    {"id": "workspace.map", "class": "read", "summary": "Bounded compact spaces/boards tree."},
    {
        "id": "items.search",
        "class": "read",
        "summary": "Title and nested scalar field search with exact page/index continuation.",
    },
    {"id": "comments.thread", "class": "read", "summary": "Bounded comment thread."},
    {
        "id": "export.items",
        "class": "read",
        "summary": "One bounded JSONL/CSV chunk with deterministic schema and continuation.",
    },
    {
        "id": "items.create",
        "class": "mutation",
        "summary": "Validated plan; dry-run by default; one write when enabled.",
    },
    {
        "id": "items.updateFields",
        "class": "mutation",
        "summary": "One or many updates with durable per-item receipts.",
    },
    {
        "id": "comments.add",
        "class": "mutation",
        "summary": "Validated comment plan; dry-run by default.",
    },
    {
        "id": "itemGroups.create",
        "class": "mutation",
        "summary": "Title/color validation; dry-run by default.",
    },
    {
        "id": "itemGroups.update",
        "class": "mutation",
        "summary": "Title/ranking/color validation; dry-run by default.",
    },
    {
        "id": "itemFiles.upload",
        "class": "mutation",
        "summary": (
            "Canonical base64 only; metadata validation, SHA-256, bounded bytes; "
            "dry-run by default."
        ),
    },
    {
        "id": "itemFiles.update",
        "class": "mutation",
        "summary": "Validated name/description update; dry-run by default.",
    },
]


def build_docs_index(descriptors: list[dict[str, Any]]) -> dict[str, Any]:
    operations = [
        {
            "kind": "operation",
            "id": d["operationId"],
            "title": d["mcpTitle"],
            "summary": d["summary"],
            "description": d["description"],
            "method": d["method"],
            "path": d["path"],
            "mcpName": d["mcpName"],
            "sdk": f"client.{d['sdk']['resource']}.{d['sdk']['method']}",
            "scopes": d["scopes"],
        }
        for d in descriptors
    ]
    workflows = [
        {
            "kind": "workflow",
            "id": w["id"],
            "title": w["id"],
            "summary": w["summary"],
            "class": w["class"],
        }
        for w in WORKFLOWS
    ]
    guides = [
        {
            "kind": "guide",
            "id": "authentication",
            "title": "Authentication",
            "summary": (
                "API keys are sent only in the X-API-Key header to the configured HTTPS origin."
            ),
        },
        {
            "kind": "guide",
            "id": "pagination",
            "title": "Pagination",
            "summary": (
                "Paged endpoints return {data, hasMore}; page is 1-indexed; "
                "pageSize controls page length."
            ),
        },
        {
            "kind": "guide",
            "id": "rate-limits",
            "title": "Rate limits",
            "summary": (
                "200 requests per user per minute; HTTP 429 with Retry-After when exceeded."
            ),
        },
        {
            "kind": "guide",
            "id": "uploads",
            "title": "File uploads",
            "summary": (
                "Multipart uploads in the SDK; canonical base64 plus metadata over "
                "MCP; 25 MiB ceiling."
            ),
        },
    ]
    return {"version": 1, "entries": operations + workflows + guides}


def build_outputs() -> dict[str, str]:
    """Build all generated contract artifacts; return {relative path: content}."""
    upstream = load_yaml(CONTRACT / "upstream.openapi.yaml")
    overrides_doc = load_yaml(CONTRACT / "operation-overrides.yaml")
    jsonschema.validate(overrides_doc, OVERRIDES_SCHEMA)
    expected = json.loads((CONTRACT / "expected-operations.json").read_text())

    validate_openapi(upstream)
    spec = apply_schema_patches(upstream, CONTRACT / "schema-patches.yaml")
    assert_all_refs_resolve(spec)

    security = spec["components"]["securitySchemes"]
    if list(security) != ["api-key-auth"] or security["api-key-auth"]["name"] != "X-API-Key":
        raise ValueError("security scheme must be X-API-Key api-key-auth")

    overrides: dict[str, dict[str, Any]] = overrides_doc["operations"]
    expected_pairs = {(o["method"], o["path"]): o["operationId"] for o in expected["operations"]}

    spec_ops = iter_operations(spec)
    spec_pairs = {(m, p) for m, p, _ in spec_ops}
    if spec_pairs != set(expected_pairs):
        raise ValueError("spec operations drifted from contract/expected-operations.json")
    if set(overrides) != {f"{m} {p}" for m, p in spec_pairs}:
        raise ValueError("operation overrides drifted from the spec operation set")

    descriptors: list[dict[str, Any]] = []
    for method, path, operation in spec_ops:
        override = overrides[f"{method} {path}"]
        if override["operationId"] != expected_pairs[(method, path)]:
            raise ValueError(f"operationId mismatch for {method} {path}")
        operation["operationId"] = override["operationId"]
        operation["summary"] = override["summary"]
        descriptors.append(build_descriptor(method, path, operation, override, spec))
    descriptors.sort(key=lambda d: d["operationId"])

    ids = [d["operationId"] for d in descriptors]
    names = [d["mcpName"] for d in descriptors]
    if len(descriptors) != 32 or len(set(ids)) != 32 or len(set(names)) != 32:
        raise ValueError("descriptor inventory must contain exactly 32 unique operations")

    operations_doc = {
        "descriptorVersion": 2,
        "source": {
            "upstream": "contract/upstream.openapi.yaml",
            "overrides": "contract/operation-overrides.yaml",
        },
        "operations": descriptors,
        "workflows": WORKFLOWS,
    }
    return {
        "plaky.openapi.json": canonical_json(spec),
        "operations.json": canonical_json(operations_doc),
        "docs-index.json": canonical_json(build_docs_index(descriptors)),
    }


def cmd_build() -> int:
    outputs = build_outputs()
    GENERATED.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (GENERATED / name).write_text(content)
        print(f"wrote contract/generated/{name} ({len(content)} bytes)")
    return 0


def cmd_check() -> int:
    outputs = build_outputs()
    failures: list[str] = []
    for name, content in outputs.items():
        existing = GENERATED / name
        if not existing.is_file():
            failures.append(f"missing contract/generated/{name}")
        elif existing.read_text() != content:
            failures.append(f"drift in contract/generated/{name}")
    if failures:
        print("CONTRACT CHECK FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("CONTRACT CHECK OK: generated artifacts match a fresh deterministic build")
    return 0


def cmd_fetch(url: str) -> int:
    import urllib.request

    CANDIDATE.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        raw = response.read()
    target = CANDIDATE / "upstream.openapi.yaml"
    target.write_bytes(raw)
    manifest = {
        "sourceUrl": url,
        "fetchedAt": datetime.now(UTC).isoformat(),
        "rawSha256": hashlib.sha256(raw).hexdigest(),
    }
    (CANDIDATE / "manifest.json").write_text(canonical_json(manifest))
    print(f"fetched {len(raw)} bytes into contract/candidate/upstream.openapi.yaml")
    return 0


def operation_fingerprint(spec: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for method, path, operation in iter_operations(spec):
        resolved = json.loads(canonical_json(operation))
        out[f"{method} {path}"] = hashlib.sha256(canonical_json(resolved).encode()).hexdigest()
    return out


def cmd_diff() -> int:
    candidate_path = CANDIDATE / "upstream.openapi.yaml"
    if not candidate_path.is_file():
        print("no candidate: run scripts/contract.py fetch first")
        return 1
    accepted = load_yaml(CONTRACT / "upstream.openapi.yaml")
    candidate = load_yaml(candidate_path)
    validate_openapi(candidate)

    old_ops = operation_fingerprint(accepted)
    new_ops = operation_fingerprint(candidate)
    added = sorted(set(new_ops) - set(old_ops))
    removed = sorted(set(old_ops) - set(new_ops))
    changed = sorted(k for k in set(old_ops) & set(new_ops) if old_ops[k] != new_ops[k])

    old_schemas = accepted.get("components", {}).get("schemas", {})
    new_schemas = candidate.get("components", {}).get("schemas", {})
    schema_added = sorted(set(new_schemas) - set(old_schemas))
    schema_removed = sorted(set(old_schemas) - set(new_schemas))
    schema_changed = sorted(
        k
        for k in set(old_schemas) & set(new_schemas)
        if canonical_json(old_schemas[k]) != canonical_json(new_schemas[k])
    )
    old_security = accepted.get("components", {}).get("securitySchemes")
    new_security = candidate.get("components", {}).get("securitySchemes")

    report = {
        "operationsAdded": added,
        "operationsRemoved": removed,
        "operationsChanged": changed,
        "schemasAdded": schema_added,
        "schemasRemoved": schema_removed,
        "schemasChanged": schema_changed,
        "securityChanged": canonical_json(old_security) != canonical_json(new_security),
    }
    print(canonical_json(report), end="")
    identical = not any(v for v in report.values())
    print("IDENTICAL" if identical else "DIFFERENT")
    return 0


def cmd_accept() -> int:
    candidate_path = CANDIDATE / "upstream.openapi.yaml"
    manifest_path = CANDIDATE / "manifest.json"
    if not candidate_path.is_file() or not manifest_path.is_file():
        print("no candidate to accept: run scripts/contract.py fetch first")
        return 1
    candidate = load_yaml(candidate_path)
    validate_openapi(candidate)
    (CONTRACT / "upstream.openapi.yaml").write_bytes(candidate_path.read_bytes())

    fetch_manifest = json.loads(manifest_path.read_text())
    manifest = json.loads((CONTRACT / "source-manifest.json").read_text())
    manifest["upstreamProvenance"] = {
        "sourceUrl": fetch_manifest["sourceUrl"],
        "fetchedAt": fetch_manifest["fetchedAt"],
        "rawSha256": fetch_manifest["rawSha256"],
        "acceptedAt": datetime.now(UTC).isoformat(),
    }
    (CONTRACT / "source-manifest.json").write_text(canonical_json(manifest))
    print("accepted candidate into contract/upstream.openapi.yaml; rebuild and review drift")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("check")
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--url", required=True)
    sub.add_parser("diff")
    sub.add_parser("accept")
    args = parser.parse_args()
    if args.command == "build":
        return cmd_build()
    if args.command == "check":
        return cmd_check()
    if args.command == "fetch":
        return cmd_fetch(args.url)
    if args.command == "diff":
        return cmd_diff()
    return cmd_accept()


if __name__ == "__main__":
    sys.exit(main())
