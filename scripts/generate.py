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
import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

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
CANONICAL_DECIMAL_ID_PATTERN = r"^(0|[1-9][0-9]*)$"
INT64_MAX = 9_223_372_036_854_775_807


def _widen_int64(node: Any, *, constrained_strings: bool = False) -> None:
    """Give every int64 integer schema a decimal-string alternative, in place.

    The transport decodes JSON integers beyond ±(2**53-1) as exact decimal
    strings (runtime/responses.py). Generated models must accept those
    strings and keep them as strings, so re-serialization never emits a
    number that loses digits in JavaScript consumers.
    """
    if isinstance(node, dict):
        mapping = cast("dict[str, Any]", node)
        if mapping.get("type") == "integer" and mapping.get("format") == "int64":
            del mapping["type"]
            del mapping["format"]
            string_branch: dict[str, Any] = {"type": "string"}
            if constrained_strings:
                string_branch.update({"pattern": CANONICAL_DECIMAL_ID_PATTERN, "maxLength": 19})
            integer_branch: dict[str, Any] = {"type": "integer", "format": "int64"}
            if constrained_strings:
                integer_branch.update({"minimum": 0, "maximum": INT64_MAX})
            mapping["anyOf"] = [integer_branch, string_branch]
            return
        for value in mapping.values():
            _widen_int64(value, constrained_strings=constrained_strings)
    elif isinstance(node, list):
        for value in cast("list[Any]", node):
            _widen_int64(value, constrained_strings=constrained_strings)


def generate_models() -> str:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    _widen_int64(spec)
    with tempfile.TemporaryDirectory() as tmp:
        widened_spec = Path(tmp) / "plaky.openapi.json"
        widened_spec.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        output = Path(tmp) / "generated.py"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(widened_spec),
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
        return block.replace('extra="allow"', 'extra="forbid", strict=True')

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
_OUTPUT_BY_ROOT = {
    "page": "PagedOutput",
    "array": "ListOutput",
    "object": "EntityOutput",
    "void": "OkOutput",
}
_HIGH_VALUE_OUTPUTS = {
    "getItemFileDownload": "DownloadLinkOutput",
}

# Positional-first SDK methods (single ID argument).
_POSITIONAL_SINGLE_ID = {"getSpace": "spaceId", "getTeam": "teamId"}
_LOCAL_REQUEST_ANNOTATIONS = {
    # The contract defines item field keys dynamically, so there is no named
    # component schema to import. The generated local type still makes the
    # outer request object and its keys explicit at the MCP boundary.
    "ItemFieldsUpdateRequest": "dict[StrictStr, Any]",
}


def snake_case(value: str) -> str:
    return _SNAKE.sub("_", value).lower()


def _output_model(descriptor: dict[str, Any]) -> str:
    return _HIGH_VALUE_OUTPUTS.get(
        descriptor["operationId"], _OUTPUT_BY_ROOT[descriptor["success"]["root"]]
    )


def _description_name(name: str) -> str:
    words = _SNAKE.sub(" ", name).lower()
    return words[:-3] + " ID" if words.endswith(" id") else words


def _raw_description(descriptor: dict[str, Any]) -> str:
    """Build a compact, deterministic description from canonical metadata."""
    root = descriptor["success"]["root"]
    if descriptor["mutation"]:
        result_sentence = f"{descriptor['summary']}; it performs the requested change."
    elif root == "page":
        result_sentence = f"{descriptor['summary']}; it returns a paginated result."
    elif root == "array":
        result_sentence = f"{descriptor['summary']}; it returns a list result."
    elif root == "void":
        result_sentence = f"{descriptor['summary']}; it returns a completion result."
    else:
        result_sentence = f"{descriptor['summary']}; it returns the requested result."

    identifiers = [
        _description_name(parameter["name"])
        for parameter in descriptor["parameters"]
        if parameter["in"] == "path"
    ]
    filters = [
        _description_name(parameter["name"])
        for parameter in descriptor["parameters"]
        if parameter["in"] == "query"
    ]
    required = ", ".join(identifiers) if identifiers else "no identifiers"
    scopes = " and ".join(descriptor["scopes"])
    filter_note = f" Optional filters: {', '.join(filters)}." if filters else ""
    requirement_sentence = f"Requires {required} and {scopes} scope.{filter_note}"

    if descriptor["mutation"]:
        safety_sentence = (
            "This performs a live write with no dry-run; if a failure is ambiguous, "
            "inspect the receipt and do not repeat blindly."
        )
    elif "pagination" in descriptor:
        safety_sentence = "Use page and pageSize to continue the result set."
    else:
        safety_sentence = "This operation is read-only."
    return " ".join((result_sentence, requirement_sentence, safety_sentence))


def _annotation_for_schema(schema: dict[str, Any], *, path: bool = False) -> str:
    """Return a strict handler annotation from the canonical JSON schema."""
    if path and schema.get("format") == "int64":
        return "CanonicalId"
    if schema.get("format") == "int64":
        return "CanonicalId"
    if schema.get("type") == "integer":
        return "StrictInt"
    if schema.get("type") == "array":
        item = cast("dict[str, Any]", schema.get("items", {}))
        return f"list[{_annotation_for_schema(item)}]"
    values = schema.get("enum")
    if isinstance(values, list) and values:
        return "Literal[" + ", ".join(repr(value) for value in cast("list[str]", values)) + "]"
    return "StrictStr"


def _field_annotation(parameter: dict[str, Any], *, optional: bool = False) -> str:
    schema = cast("dict[str, Any]", parameter["schema"])
    annotation = _annotation_for_schema(schema, path=parameter.get("in") == "path")
    description = str(parameter.get("description", ""))
    field = f"Field(description={description!r})" if description else "Field()"
    if optional:
        return f"Annotated[{annotation} | None, {field}] = None"
    return f"Annotated[{annotation}, {field}]"


def _handler_params(descriptor: dict[str, Any]) -> list[str]:
    params: list[str] = []
    for parameter in descriptor["parameters"]:
        if parameter["in"] == "path":
            params.append(f"{parameter['name']}: {_field_annotation(parameter)}")
    if descriptor["operationId"] == "uploadItemFile":
        params.extend(
            [
                "fileBase64: Annotated[StrictStr, "
                'Field(description="Canonical base64 file data.")]',
                "fileName: Annotated[StrictStr, Field("
                'description="Upload filename (1-255 UTF-8 bytes; no path separators).")]',
                "contentType: Annotated[StrictStr | None, "
                'Field(description="Optional RFC media type.")] = None',
            ]
        )
    elif descriptor["request"]["kind"] == "json":
        model = str(descriptor["request"]["model"])
        params.append(f"body: {_LOCAL_REQUEST_ANNOTATIONS.get(model, model)}")
    optional: list[str] = []
    for parameter in descriptor["parameters"]:
        if parameter["in"] == "query":
            optional.append(f"{parameter['name']}: {_field_annotation(parameter, optional=True)}")
    if "pagination" in descriptor:
        optional.extend(
            [
                "page: Annotated[StrictInt | None, "
                'Field(description="One-based page number.", ge=1)] = None',
                "pageSize: Annotated[StrictInt | None, "
                'Field(description="Positive page size.", ge=1)] = None',
            ]
        )
    return params + optional


def _schema_from_descriptor_parameter(parameter: dict[str, Any]) -> dict[str, Any]:
    schema = copy.deepcopy(cast("dict[str, Any]", parameter["schema"]))
    if schema.get("format") == "int64":
        schema = {
            "oneOf": [
                {"type": "integer", "format": "int64", "minimum": 0, "maximum": INT64_MAX},
                {
                    "type": "string",
                    "pattern": CANONICAL_DECIMAL_ID_PATTERN,
                    "maxLength": 19,
                },
            ]
        }
    if parameter.get("description"):
        schema["description"] = parameter["description"]
    return schema


def _body_schema(model_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Copy the contract body schema and only the component refs it needs."""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    _widen_int64(spec, constrained_strings=True)
    components = cast("dict[str, Any]", spec["components"]["schemas"])
    if model_name in _LOCAL_REQUEST_ANNOTATIONS:
        return (
            {
                "type": "object",
                "additionalProperties": True,
                "description": "Item field values keyed by canonical field key or field title.",
            },
            {},
        )
    definitions: dict[str, Any] = {}

    def rewrite(node: Any) -> Any:
        if isinstance(node, dict):
            value = cast("dict[str, Any]", node)
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref.rsplit("/", 1)[-1]
                if name not in definitions:
                    definitions[name] = {}
                    definitions[name] = rewrite(copy.deepcopy(components[name]))
                return {"$ref": f"#/$defs/{name}"}
            return {key: rewrite(item) for key, item in value.items()}
        if isinstance(node, list):
            return [rewrite(item) for item in cast("list[Any]", node)]
        return node

    body = cast("dict[str, Any]", rewrite(copy.deepcopy(components[model_name])))
    _allow_null_for_optional_properties(body)
    for definition in definitions.values():
        _allow_null_for_optional_properties(definition)
    if body.get("type") == "object":
        # The generated request model rejects unknown top-level properties.
        # Nested maps retain their contract-defined additional-property rules.
        body["additionalProperties"] = False
    return body, definitions


def _allows_null(schema: dict[str, Any]) -> bool:
    if schema.get("type") == "null":
        return True
    if isinstance(schema.get("type"), list) and "null" in schema["type"]:
        return True
    for key in ("anyOf", "oneOf"):
        variants = schema.get(key)
        if isinstance(variants, list) and any(
            isinstance(branch, dict) and _allows_null(cast("dict[str, Any]", branch))
            for branch in cast("list[Any]", variants)
        ):
            return True
    return False


def _allow_null_for_optional_properties(node: Any) -> None:
    if isinstance(node, list):
        for value in cast("list[Any]", node):
            _allow_null_for_optional_properties(value)
        return
    if not isinstance(node, dict):
        return
    mapping = cast("dict[str, Any]", node)
    properties_value = mapping.get("properties")
    if isinstance(properties_value, dict):
        properties = cast("dict[str, Any]", properties_value)
        required = set(cast("list[str]", mapping.get("required", [])))
        for name, value in properties.items():
            if not isinstance(value, dict):
                continue
            value_schema = cast("dict[str, Any]", value)
            if name not in required and value_schema and not _allows_null(value_schema):
                properties[name] = {"anyOf": [value, {"type": "null"}]}
        for value in properties.values():
            _allow_null_for_optional_properties(value)
    for key, value in mapping.items():
        if key != "properties":
            _allow_null_for_optional_properties(value)


def _parameters_schema(descriptor: dict[str, Any]) -> dict[str, Any]:
    """Publish the canonical, strict raw-tool input schema."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in descriptor["parameters"]:
        properties[parameter["name"]] = _schema_from_descriptor_parameter(parameter)
        if parameter["required"]:
            required.append(parameter["name"])
    if descriptor["request"]["kind"] == "json":
        body, definitions = _body_schema(str(descriptor["request"]["model"]))
        properties["body"] = body
        required.append("body")
    else:
        definitions = {}
    if descriptor["operationId"] == "uploadItemFile":
        properties.update(
            {
                "fileBase64": {
                    "type": "string",
                    "description": (
                        "Canonical base64 file data; decoded bytes are limited by "
                        "the SDK hard ceiling."
                    ),
                },
                "fileName": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255,
                    "description": (
                        "Upload filename without path separators or control characters."
                    ),
                },
                "contentType": {"type": "string", "description": "Optional RFC media type."},
            }
        )
        required.extend(["fileBase64", "fileName"])
    if "pagination" in descriptor:
        properties["page"] = {
            "type": "integer",
            "minimum": 1,
            "description": "One-based page number.",
        }
        properties["pageSize"] = {
            "type": "integer",
            "minimum": 1,
            "description": "Positive page size.",
        }
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }
    if definitions:
        schema["$defs"] = definitions
    return schema


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
    if descriptor["mutation"]:
        args.append("options=RequestOverrides(on_dispatch=tracker.request_started)")
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
            "        entries = [entry.model_dump(mode='json', by_alias=True, exclude_none=True) "
            "for entry in result.data]",
            f'        wire = compact_page(entries, result.has_more, "{kind}")',
            f'        text = f"{op_id}: {{len(entries)}} result(s); hasMore={{result.has_more}}"',
        ]
    if root == "array":
        # comments.list normalizes the bare array into a Page for the SDK;
        # files.list stays a plain list.
        source = "result.data" if descriptor["sdk"]["resource"] == "comments" else "result"
        return [
            "        entries = [entry.model_dump(mode='json', by_alias=True, exclude_none=True) "
            f"for entry in {source}]",
            f'        wire = compact_list(entries, "{kind}")',
            f'        text = f"{op_id}: {{len(entries)}} result(s)"',
        ]
    if root == "void":
        return [
            '        wire = {"ok": True}',
            f'        text = "{op_id}: ok"',
        ]
    dump_call = "result.model_dump(mode='json', by_alias=True, exclude_none=True)"
    if descriptor["sensitiveOutput"]:
        return [
            f'        wire = compact_entity({dump_call}, "{kind}")',
            f'        text = "{op_id}: signed URL returned (sensitive; not repeated in text)"',
        ]
    return [
        f'        wire = compact_entity({dump_call}, "{kind}")',
        f"        text = f\"{op_id}: id={{wire.get('id')}}\"",
    ]


RAW_HEADER = HEADER + (
    "# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false\n"
    "# pyright: reportUnknownArgumentType=false\n"
)


def _generate_raw_tool(descriptor: dict[str, Any]) -> str:
    op_id = descriptor["operationId"]
    module_doc = descriptor["summary"]
    output = _output_model(descriptor)
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
    needs_any = descriptor["request"].get("model") in _LOCAL_REQUEST_ANNOTATIONS or needs_cast
    needs_literal = any(
        parameter["schema"].get("enum")
        or cast("dict[str, Any]", parameter["schema"].get("items", {})).get("enum")
        for parameter in descriptor["parameters"]
    )
    typing_names = ["Annotated"]
    if needs_any:
        typing_names.append("Any")
    if needs_literal:
        typing_names.append("Literal")
    if needs_cast:
        typing_names.append("cast")
    lines.append(f"from typing import {', '.join(typing_names)}")
    lines.append("")
    lines.append("from mcp.types import CallToolResult, ToolAnnotations")
    lines.append("from pydantic import Field, StrictInt, StrictStr")
    lines.append("")
    lines.append("from plaky115.async_client import AsyncPlakyClient")
    lines.append("from plaky115.errors import PlakyError")
    model = descriptor["request"].get("model")
    if (
        descriptor["request"]["kind"] == "json"
        and isinstance(model, str)
        and model not in _LOCAL_REQUEST_ANNOTATIONS
    ):
        lines.append(f"from plaky115.models.generated import {model}")
    if upload:
        lines.append("from plaky115.runtime.upload import Base64UploadInput, normalize_upload")
    if is_mutation:
        lines.append("from plaky115.runtime.mutations import AttemptTracker")
        lines.append("from plaky115.resources._common import RequestOverrides")
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
    lines.append("from plaky115_mcp.workflow_models import CanonicalId")
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
    lines.append(f"                envelope_wire(internal_error(exc, {tracker_ref})),")
    lines.append('                "Internal server error.",')
    lines.append("            )")
    lines.append("")
    lines.append("    return ToolSpec(")
    lines.append(f'        name="{descriptor["mcpName"]}",')
    lines.append(f'        title="{descriptor["mcpTitle"]}",')
    description = _raw_description(descriptor).replace("\\", "\\\\").replace('"', '\\"')
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
    lines.append(f"        parameters={_parameters_schema(descriptor)!r},")
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
        # Orphan generated modules would ship in the wheel unnoticed.
        expected = {t for t in outputs if t.parent == RAW_TOOLS_DIR}
        for orphan in sorted(set(RAW_TOOLS_DIR.glob("generated_*.py")) - expected):
            failures.append(f"orphan generated module {orphan.relative_to(REPO)}")
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
