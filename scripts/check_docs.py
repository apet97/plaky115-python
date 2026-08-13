"""Documentation gates: no secrets, notice present, versions consistent.

Usage: uv run python scripts/check_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

NOTICE_FRAGMENT = "unofficial and independent"
KEY_PATTERN = re.compile(r"plk_[A-Za-z0-9_-]{12,}")
SIGNED_URL_PATTERN = re.compile(r"X-Amz-Signature=|Signature=[A-Za-z0-9]{16,}")


def main() -> int:
    failures: list[str] = []

    docs = [
        *sorted((REPO / "docs").rglob("*.md")),
        *sorted((REPO / "examples").glob("*")),
        REPO / "README.md",
        REPO / "SECURITY.md",
    ]
    for path in docs:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if KEY_PATTERN.search(text):
            failures.append(f"{path.relative_to(REPO)}: literal plk_ key")
        if SIGNED_URL_PATTERN.search(text):
            failures.append(f"{path.relative_to(REPO)}: signed URL")

    for required in ("README.md", "SECURITY.md", "docs/sdk.md", "docs/mcp.md"):
        if NOTICE_FRAGMENT not in (REPO / required).read_text(encoding="utf-8"):
            failures.append(f"{required}: unofficial notice missing")

    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    if 'requires-python = ">=3.11"' not in pyproject:
        failures.append("pyproject.toml: requires-python drifted from documented support")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    if "Python 3.11" not in readme:
        failures.append("README.md: supported Python version claim missing")

    if failures:
        print("DOCS CHECK FAIL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("DOCS CHECK OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
