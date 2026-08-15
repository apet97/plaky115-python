"""Release provenance command-line boundary tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_require_source_rejects_a_missing_checkout(tmp_path: Path) -> None:
    env = {**os.environ, "PLAKY115_SOURCE_CHECKOUT": str(tmp_path / "missing-source")}
    result = subprocess.run(
        [sys.executable, "scripts/parity.py", "--require-source"],
        cwd=REPO,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "required source checkout is unavailable" in result.stdout
