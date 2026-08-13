"""Deterministic code generation from the accepted contract.

Generates:
- src/plaky115/models/generated.py            (Pydantic v2 schema models)
- src/plaky115_mcp/tools/raw/generated_*.py   (one raw MCP tool per operation)
- src/plaky115_mcp/tools/raw/__init__.py      (raw tool registry)
- src/plaky115_mcp/_docs_index.py             (bundled docs index)

Usage:
  uv run python scripts/generate.py          # write generated files
  uv run python scripts/generate.py --check  # verify committed output matches
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "contract/generated/plaky.openapi.json"
OPERATIONS = REPO / "contract/generated/operations.json"
DOCS_INDEX = REPO / "contract/generated/docs-index.json"
RAW_TOOLS_DIR = REPO / "src/plaky115_mcp/tools/raw"

HEADER = """\
# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
"""

MODEL_TARGET = REPO / "src/plaky115/models/generated.py"


def generate_models() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "generated.py"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(SPEC),
                "--input-file-type",
                "openapi",
                "--output",
                str(output),
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.11",
                "--snake-case-field",
                "--use-standard-collections",
                "--use-union-operator",
                "--use-annotated",
                "--use-schema-description",
                "--extra-fields",
                "allow",
                "--allow-population-by-field-name",
                "--disable-timestamp",
                "--use-double-quotes",
                # The live API emits timezone-naive ISO timestamps; plain
                # datetime accepts both naive and aware values (ADR-0006).
                "--output-datetime-class",
                "datetime",
                "--formatters",
                "ruff-format",
            ],
            check=True,
            cwd=REPO,
        )
        text = output.read_text(encoding="utf-8")

    # datamodel-code-generator emits its own comment header; replace it with
    # the repository generated-file header.
    lines = text.splitlines()
    first_code = 0
    for index, line in enumerate(lines):
        if line and not line.startswith("#"):
            first_code = index
            break
    body = "\n".join(lines[first_code:]).lstrip("\n")

    # Stable request models are strict: unknown request fields must fail
    # validation. Response models keep extra="allow" for additive server
    # fields. The generator emits one ConfigDict per class; rewrite only the
    # config immediately inside *Request classes.
    def strict_requests(match: re.Match[str]) -> str:
        block = match.group(0)
        return block.replace('extra="allow"', 'extra="forbid"')

    body = re.sub(
        r"class \w+Request\(BaseModel\):\n(?:    .*\n|\n)*?    model_config = ConfigDict\([^)]*\)",
        strict_requests,
        body,
    )
    if not body.endswith("\n"):
        body += "\n"
    return _repo_format(HEADER + body)


def _repo_format(content: str) -> str:
    """Format generated code with the repository's own ruff configuration."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "generated.py"
        target.write_text(content, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--fix",
                "--select",
                "I001,F401",
                "--config",
                str(REPO / "pyproject.toml"),
                str(target),
            ],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--config",
                str(REPO / "pyproject.toml"),
                str(target),
            ],
            check=True,
            capture_output=True,
        )
        return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Raw MCP tool generation
# ---------------------------------------------------------------------------

_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")

# camelCase wire names -> SDK keyword arguments.
_PATH_KWARGS = {
    "spaceId": "space_id",
    "boardId": "board_id",
    "itemId": "item_id",
    "itemCommentId": "item_comment_id",
    "itemGroupId": "item_group_id",
    "itemFileId": "item_file_id",
    "teamId": "team_id",
    "itemFieldKey": "item_field_key",
}
_QUERY_KWARGS = {
    "page": "page",
    "pageSize": "page_size",
    "expand": "expand",
    "emails": "emails",
    "status": "status",
    "type": "type",
    "boardViewId": "board_view_id",
    "parentId": "parent_id",
    "subitemsBehaviour": "subitems_behaviour",
}
_QUERY_TYPES = {
    "page": "int | None = None",
    "pageSize": "int | None = None",
    "expand": "list[str] | None = None",
    "emails": "list[str] | None = None",
    "status": "str | None = None",
    "type": "str | None = None",
    "boardViewId": "int | str | None = None",
    "parentId": "int | str | None = None",
    "subitemsBehaviour": "str | None = None",
}

_OUTPUT_BY_ROOT = {
    "page": "PagedOutput",
    "array": "ListOutput",
    "object": "EntityOutput",
    "void": "OkOutput",
}

# Positional-first SDK methods (single ID argument).
_POSITIONAL_SINGLE_ID = {"getSpace": "spaceId", "getTeam": "teamId"}


def snake_case(value: str) -> str:
    return _SNAKE.sub("_", value).lower()


def _handler_params(descriptor: dict[str, Any]) -> list[str]:
    params: list[str] = []
    for parameter in descriptor["parameters"]:
        if parameter["in"] == "path":
            kind = "str" if parameter["name"] == "itemFieldKey" else "int | str"
            params.append(f"{parameter['name']}: {kind}")
    if descriptor["operationId"] == "uploadItemFile":
        params.extend(["fileBase64: str", "fileName: str", "contentType: str | None = None"])
    elif descriptor["request"]["kind"] == "json":
        params.append("body: dict[str, Any]")
    optional: list[str] = []
    for parameter in descriptor["parameters"]:
        if parameter["in"] == "query":
            optional.append(f"{parameter['name']}: {_QUERY_TYPES[parameter['name']]}")
    if "pagination" in descriptor:
        optional.append("page: int | None = None")
        optional.append("pageSize: int | None = None")
    return params + optional


def _sdk_call(descriptor: dict[str, Any]) -> str:
    op_id = descriptor["operationId"]
    resource = descriptor["sdk"]["resource"]
    method = descriptor["sdk"]["method"]
    args: list[str] = []
    if op_id in _POSITIONAL_SINGLE_ID:
        args.append(_POSITIONAL_SINGLE_ID[op_id])
    else:
        for parameter in descriptor["parameters"]:
            if parameter["in"] == "path":
                wire = parameter["name"]
                args.append(f"{_PATH_KWARGS[wire]}={wire}")
    for parameter in descriptor["parameters"]:
        if parameter["in"] == "query":
            wire = parameter["name"]
            args.append(f"{_QUERY_KWARGS[wire]}={wire}")
    if "pagination" in descriptor:
        args.append("page=page")
        args.append("page_size=pageSize")
    if op_id == "uploadItemFile":
        args.append("file=upload.data")
        args.append("file_name=upload.file_name")
        args.append("content_type=upload.media_type")
    elif descriptor["request"]["kind"] == "json":
        args.append("body=body")
    call = f"client.{resource}.{method}({', '.join(args)})"
    if op_id in ("createItem", "updateItemFields"):
        # These SDK methods can also return DryRunPlan; the raw tool always
        # performs the live call, so narrow the union for typing.
        call = f'cast("Any", await {call})'
        return call
    return f"await {call}"


def _success_block(descriptor: dict[str, Any]) -> list[str]:
    op_id = descriptor["operationId"]
    kind = descriptor["compactKind"]
    root = descriptor["success"]["root"]
    if root == "page":
        return [
            "        entries = [entry.model_dump(by_alias=True, exclude_none=True) "
            "for entry in result.data]",
            f'        wire = compact_page(entries, result.has_more, "{kind}")',
            f'        text = f"{op_id}: {{len(entries)}} result(s); hasMore={{result.has_more}}"',
        ]
    if root == "array":
        # comments.list normalizes the bare array into a Page for the SDK;
        # files.list stays a plain list.
        source = "result.data" if descriptor["sdk"]["resource"] == "comments" else "result"
        return [
            "        entries = [entry.model_dump(by_alias=True, exclude_none=True) "
            f"for entry in {source}]",
            f'        wire = compact_list(entries, "{kind}")',
            f'        text = f"{op_id}: {{len(entries)}} result(s)"',
        ]
    if root == "void":
        return [
            '        wire = {"ok": True}',
            f'        text = "{op_id}: ok"',
        ]
    if descriptor["sensitiveOutput"]:
        return [
            "        wire = compact_entity("
            'result.model_dump(by_alias=True, exclude_none=True), "' + kind + '")',
            f'        text = "{op_id}: signed URL returned (sensitive; not repeated in text)"',
        ]
    return [
        "        wire = compact_entity("
        'result.model_dump(by_alias=True, exclude_none=True), "' + kind + '")',
        f"        text = f\"{op_id}: id={{wire.get('id')}}\"",
    ]


RAW_HEADER = HEADER + (
    "# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false\n"
    "# pyright: reportUnknownArgumentType=false\n"
)


def _generate_raw_tool(descriptor: dict[str, Any]) -> str:
    op_id = descriptor["operationId"]
    module_doc = descriptor["summary"]
    output = _OUTPUT_BY_ROOT[descriptor["success"]["root"]]
    params = _handler_params(descriptor)
    param_lines = "".join(f"        {p},\n" for p in params)
    is_mutation = descriptor["mutation"]
    upload = op_id == "uploadItemFile"
    scopes = ", ".join(f'"{s}"' for s in descriptor["scopes"])
    annotations = descriptor
    target_ids = [p["name"] for p in descriptor["parameters"] if p["in"] == "path"]
    target_dict = ", ".join(f'"{n}": str({n})' for n in target_ids)

    lines: list[str] = []
    lines.append(RAW_HEADER.rstrip("\n"))
    lines.append(f'"""Raw MCP tool for {op_id}: {module_doc}."""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import asyncio")
    needs_cast = op_id in ("createItem", "updateItemFields")
    needs_any = descriptor["request"]["kind"] == "json"
    typing_names = ["Annotated"]
    if needs_any:
        typing_names.append("Any")
    if needs_cast:
        typing_names.append("cast")
    lines.append(f"from typing import {', '.join(typing_names)}")
    lines.append("")
    lines.append("from mcp.types import CallToolResult, ToolAnnotations")
    lines.append("")
    lines.append("from plaky115.async_client import AsyncPlakyClient")
    lines.append("from plaky115.errors import PlakyError")
    if upload:
        lines.append("from plaky115.runtime.upload import Base64UploadInput, normalize_upload")
    if is_mutation:
        lines.append("from plaky115.runtime.mutations import AttemptTracker")
    lines.append("from plaky115_mcp.compaction import (")
    compaction_imports: list[str] = sorted(
        {
            "make_result",
            "error_result",
            *(
                {"compact_page"}
                if descriptor["success"]["root"] == "page"
                else {"compact_list"}
                if descriptor["success"]["root"] == "array"
                else set()
                if descriptor["success"]["root"] == "void"
                else {"compact_entity"}
            ),
        }
    )
    for name in compaction_imports:
        lines.append(f"    {name},")
    lines.append(")")
    lines.append("from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error")
    lines.append(f"from plaky115_mcp.outputs import {output}")
    lines.append("from plaky115_mcp.registry import ToolSpec")
    lines.append("")
    lines.append("")
    lines.append("def build_tool(client: AsyncPlakyClient) -> ToolSpec:")
    lines.append(f"    async def {snake_case(op_id)}(")
    if param_lines:
        lines.append(param_lines.rstrip("\n"))
    lines.append(f"    ) -> Annotated[CallToolResult, {output}]:")
    if is_mutation:
        tracker_arg = "{" + target_dict + "}" if target_dict else "{}"
        lines.append(f'        tracker = AttemptTracker("{op_id}", {tracker_arg})')
        tracker_ref = "tracker"
    else:
        tracker_ref = "None"
    lines.append("        try:")
    if upload:
        lines.append("            upload = normalize_upload(")
        lines.append(
            "                Base64UploadInput(file_base64=fileBase64, "
            "file_name=fileName, content_type=contentType)"
        )
        lines.append("            )")
    if is_mutation:
        lines.append("            tracker.request_started()")
    lines.append(f"            result = {_sdk_call(descriptor)}")
    if is_mutation:
        lines.append("            tracker.completed()")
    if descriptor["success"]["root"] == "void":
        lines.append("            del result")
    for line in _success_block(descriptor):
        lines.append("    " + line)
    lines.append("            return make_result(text=text, structured=wire)")
    lines.append("        except asyncio.CancelledError:")
    lines.append("            raise")
    lines.append("        except (PlakyError, ValueError, TypeError) as exc:")
    lines.append(
        "            return error_result("
        f"envelope_wire(error_envelope(exc, {tracker_ref})), str(exc))"
    )
    lines.append("        except Exception as exc:  # controlled internal-error path")
    lines.append("            return error_result(")
    lines.append('                envelope_wire(internal_error(exc)), "Internal server error."')
    lines.append("            )")
    lines.append("")
    lines.append("    return ToolSpec(")
    lines.append(f'        name="{descriptor["mcpName"]}",')
    lines.append(f'        title="{descriptor["mcpTitle"]}",')
    description = descriptor["description"].replace("\\", "\\\\").replace('"', '\\"')
    description = " ".join(description.split())
    lines.append(f'        description="{description}",')
    lines.append(f"        handler={snake_case(op_id)},")
    lines.append(f"        scopes=frozenset({{{scopes}}}),")
    lines.append("        annotations=ToolAnnotations(")
    lines.append(f"            read_only_hint={annotations['readOnly']},")
    lines.append(f"            destructive_hint={annotations['destructive']},")
    lines.append(f"            idempotent_hint={annotations['idempotent']},")
    lines.append(f"            open_world_hint={annotations['openWorld']},")
    lines.append("        ),")
    lines.append('        kind="raw",')
    lines.append("    )")
    lines.append("")
    return "\n".join(lines)


def generate_raw_tools() -> dict[Path, str]:
    operations = json.loads(OPERATIONS.read_text(encoding="utf-8"))["operations"]
    outputs: dict[Path, str] = {}
    module_names: list[tuple[str, str]] = []
    for descriptor in operations:
        module = f"generated_{snake_case(descriptor['operationId'])}"
        module_names.append((module, descriptor["operationId"]))
        outputs[RAW_TOOLS_DIR / f"{module}.py"] = _repo_format(_generate_raw_tool(descriptor))

    registry_lines = [HEADER.rstrip("\n")]
    registry_lines.append('"""Raw MCP tool registry: one generated tool per operation."""')
    registry_lines.append("")
    registry_lines.append("from __future__ import annotations")
    registry_lines.append("")
    registry_lines.append("from plaky115.async_client import AsyncPlakyClient")
    registry_lines.append("from plaky115_mcp.registry import ToolSpec")
    for module, _ in module_names:
        registry_lines.append(
            f"from plaky115_mcp.tools.raw.{module} import build_tool as _{module}"
        )
    registry_lines.append("")
    registry_lines.append("")
    registry_lines.append("def build_raw_tools(client: AsyncPlakyClient) -> list[ToolSpec]:")
    registry_lines.append("    return [")
    for module, _ in module_names:
        registry_lines.append(f"        _{module}(client),")
    registry_lines.append("    ]")
    registry_lines.append("")
    outputs[RAW_TOOLS_DIR / "__init__.py"] = _repo_format("\n".join(registry_lines))

    docs = DOCS_INDEX.read_text(encoding="utf-8").strip()
    docs_module = (
        HEADER
        + '"""Bundled documentation index for plaky_search_docs."""\n\n'
        + "DOCS_INDEX = "
        + repr(json.loads(docs))
        + "\n"
    )
    outputs[REPO / "src/plaky115_mcp/_docs_index.py"] = _repo_format(docs_module)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    outputs: dict[Path, str] = {MODEL_TARGET: generate_models()}
    outputs.update(generate_raw_tools())

    if args.check:
        failures: list[str] = []
        for target, content in outputs.items():
            rel = target.relative_to(REPO)
            if not target.is_file():
                failures.append(f"missing {rel}")
            elif target.read_text(encoding="utf-8") != content:
                failures.append(f"drift in {rel}")
        if failures:
            print("GENERATE CHECK FAIL:")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("GENERATE CHECK OK: generated files match a fresh deterministic run")
        return 0

    for target, content in outputs.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"wrote {target.relative_to(REPO)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
