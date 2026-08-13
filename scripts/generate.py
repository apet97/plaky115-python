"""Deterministic code generation from the accepted contract.

Currently generates:
- src/plaky115/models/generated.py  (Pydantic v2 schema models)

Usage:
  uv run python scripts/generate.py          # write generated files
  uv run python scripts/generate.py --check  # verify committed output matches
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "contract/generated/plaky.openapi.json"

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
                "--formatters",
                "ruff-format",
            ],
            check=True,
            cwd=REPO,
        )
        text = output.read_text()

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
    return HEADER + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    outputs = {MODEL_TARGET: generate_models()}

    if args.check:
        failures: list[str] = []
        for target, content in outputs.items():
            rel = target.relative_to(REPO)
            if not target.is_file():
                failures.append(f"missing {rel}")
            elif target.read_text() != content:
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
        target.write_text(content)
        print(f"wrote {target.relative_to(REPO)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
