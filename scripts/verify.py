"""Release-grade verification orchestrator.

`uv run python scripts/verify.py --offline` runs every offline gate in
order and emits a final JSON receipt (gate, command, exit code). It never
hides failed output. `--release-online` additionally audits dependencies
against current advisory data; offline runs report that gate as
NOT_RUN_OFFLINE, which is never acceptable for a release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def gate(name: str, cmd: list[str]) -> dict[str, object]:
    started = time.monotonic()
    result = subprocess.run(cmd, cwd=REPO, check=False)
    return {
        "gate": name,
        "command": " ".join(cmd),
        "exit_code": result.returncode,
        "seconds": round(time.monotonic() - started, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline", action="store_true")
    group.add_argument("--release-online", action="store_true")
    args = parser.parse_args()

    python = sys.executable
    receipts: list[dict[str, object]] = []

    def run_gate(name: str, cmd: list[str]) -> None:
        receipts.append(gate(name, cmd))

    run_gate("parity-inventory", [python, "scripts/parity.py"])
    run_gate("contract-check", [python, "scripts/contract.py", "check"])
    run_gate("generate-check", [python, "scripts/generate.py", "--check"])
    run_gate("ruff-format", [python, "-m", "ruff", "format", "--check", "."])
    run_gate("ruff-lint", [python, "-m", "ruff", "check", "."])
    run_gate("pyright", [python, "-m", "pyright"])
    run_gate(
        "tests-coverage",
        [python, "-m", "coverage", "run", "-m", "pytest", "-q"],
    )
    run_gate("coverage-report", [python, "-m", "coverage", "report"])
    run_gate(
        "examples-syntax",
        [python, "-m", "py_compile", *sorted(str(p) for p in (REPO / "examples").glob("*.py"))],
    )
    run_gate("docs-secrets", [python, "scripts/check_docs.py"])
    # Stale artifacts from earlier commits must not reach twine-check,
    # package-smoke, or the digest receipt.
    for stale in (REPO / "dist").glob("plaky115-*"):
        stale.unlink()
    run_gate("build", ["uv", "build"])
    run_gate("twine-check", [python, "-m", "twine", "check", "dist/plaky115-*"])

    wheels = sorted((REPO / "dist").glob("plaky115-*.whl"))
    if wheels:
        newest = max(wheels, key=lambda p: p.stat().st_mtime)
        run_gate("package-smoke", [python, "scripts/package_smoke.py", str(newest)])
        digest = hashlib.sha256(newest.read_bytes()).hexdigest()
        receipts.append(
            {
                "gate": "artifact-digest",
                "command": str(newest.name),
                "exit_code": 0,
                "sha256": digest,
            }
        )
    else:
        receipts.append({"gate": "package-smoke", "command": "(no wheel built)", "exit_code": 1})

    run_gate("secret-scan", [python, "scripts/secret_scan.py"])
    run_gate("lock-integrity", ["uv", "lock", "--check"])

    if args.release_online:
        # Audit the exported lockfile: the project itself is not on PyPI
        # yet at release time, so an environment audit cannot be strict.
        requirements = Path(tempfile.gettempdir()) / "plaky115-requirements-audit.txt"
        run_gate(
            "dependency-export",
            [
                "uv",
                "export",
                "--frozen",
                "--all-extras",
                "--no-emit-project",
                "-o",
                str(requirements),
            ],
        )
        run_gate(
            "dependency-audit",
            [
                python,
                "-m",
                "pip_audit",
                "--strict",
                "--disable-pip",
                "--require-hashes",
                "-r",
                str(requirements),
            ],
        )
        requirements.unlink(missing_ok=True)
    else:
        receipts.append(
            {
                "gate": "dependency-audit",
                "command": "pip-audit (requires network)",
                "exit_code": 0,
                "status": "NOT_RUN_OFFLINE",
            }
        )

    failed = [r for r in receipts if r["exit_code"] != 0]
    print(json.dumps({"receipts": receipts, "failed": len(failed)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
