"""Distribution notice and metadata gates (plan Phase 1 task 9)."""

from pathlib import Path

import plaky115

REPO = Path(__file__).resolve().parent.parent.parent

NOTICE = (
    "Plaky115 is unofficial and independent. It is not affiliated with, "
    "endorsed by, or sponsored by Plaky or CAKE.com. “Plaky” and “CAKE.com” "
    "are trademarks of their respective owners."
)


def test_version_exposed() -> None:
    assert isinstance(plaky115.__version__, str)
    assert plaky115.__version__


def test_notice_in_readme() -> None:
    readme = (REPO / "README.md").read_text()
    # The README carries the notice as a blockquote; compare without the
    # markdown quote prefixes and line wrapping.
    flattened = " ".join(line.lstrip("> ").strip() for line in readme.splitlines())
    assert NOTICE in flattened


def test_notice_in_security_md() -> None:
    flattened = " ".join((REPO / "SECURITY.md").read_text().split())
    assert NOTICE in flattened


def test_license_is_upstream_mit() -> None:
    text = (REPO / "LICENSE").read_text()
    assert "MIT License" in text
    assert "Copyright (c) 2026 apet97" in text
    assert "Permission is hereby granted, free of charge" in text


def test_base_import_does_not_require_mcp() -> None:
    import subprocess
    import sys

    # A fresh interpreter importing plaky115 must not import mcp.
    code = "import sys, plaky115; sys.exit(1 if 'mcp' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], check=False)
    assert result.returncode == 0
