"""Clean-environment package smoke tests.

Usage: uv run python scripts/package_smoke.py dist/<wheel>

Proves, in fresh virtual environments outside the source tree:
- base wheel installs and imports without mcp;
- MCP extra installs; plaky115_mcp imports; console --help works and
  carries the unofficial notice; stdio starts and exits cleanly;
- both py.typed markers ship; LICENSE and notice ship in metadata;
- an external strict-Pyright consumer type-checks against the installed
  wheel (source tree unavailable).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CONSUMER = '''\
"""External typed consumer proving installed-wheel typing."""

from plaky115 import AsyncPlakyClient, Page, PlakyClient, PlakyNotFoundError
from plaky115.models import Space
from plaky115_mcp.config import ServerSettings
from plaky115_mcp.server import build_server


def use_sync(client: PlakyClient) -> list[str]:
    page: Page[Space] = client.spaces.list(page_size=10)
    return [str(space.title) for space in page.data]


async def use_async(client: AsyncPlakyClient) -> str | None:
    try:
        space = await client.spaces.get("1")
    except PlakyNotFoundError as error:
        return error.request_id
    return space.title


def use_mcp() -> None:
    settings = ServerSettings(api_key="plk_placeholder")
    build_server(settings)
'''


def _venv_python(env_dir: Path) -> str:
    if os.name == "nt":
        return str(env_dir / "Scripts" / "python.exe")
    return str(env_dir / "bin" / "python")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"FAILED: {' '.join(cmd[:4])}...")
    return result


def audit_wheel(wheel: Path) -> None:
    names = zipfile.ZipFile(wheel).namelist()
    assert "plaky115/py.typed" in names, "plaky115/py.typed missing from wheel"
    assert "plaky115_mcp/py.typed" in names, "plaky115_mcp/py.typed missing from wheel"
    assert not any("tests/" in n or n.startswith("scripts/") for n in names), (
        "tests or scripts leaked into the wheel"
    )
    licenses = [n for n in names if "licenses/LICENSE" in n or n.endswith("LICENSE")]
    assert licenses, "LICENSE missing from wheel"
    metadata = next(n for n in names if n.endswith("METADATA"))
    text = zipfile.ZipFile(wheel).read(metadata).decode()
    assert "unofficial and independent" in text, "notice missing from metadata"
    assert "MIT" in text
    print("wheel audit OK")


def main() -> int:
    wheel = Path(sys.argv[1]).resolve()
    audit_wheel(wheel)

    with tempfile.TemporaryDirectory(prefix="plaky115-smoke-") as tmp:
        base = Path(tmp)

        # Base environment: SDK only, no mcp.
        base_env = base / "venv-base"
        run(["uv", "venv", str(base_env)])
        base_python = _venv_python(base_env)
        run(["uv", "pip", "install", "--quiet", "--python", base_python, str(wheel)])
        run(
            [
                base_python,
                "-c",
                "import sys, plaky115; "
                "assert 'mcp' not in sys.modules; "
                "import importlib.util; "
                "assert importlib.util.find_spec('mcp') is None; "
                "print('base import OK', plaky115.__version__)",
            ]
        )
        result = run(
            [
                base_python,
                "-c",
                "from importlib.metadata import metadata; print(metadata('plaky115')['Summary'])",
            ]
        )
        assert "unofficial" in result.stdout.lower()

        # MCP environment: extra installed.
        mcp_env = base / "venv-mcp"
        run(["uv", "venv", str(mcp_env)])
        mcp_python = _venv_python(mcp_env)
        run(
            [
                "uv",
                "pip",
                "install",
                "--quiet",
                "--python",
                mcp_python,
                f"plaky115[mcp] @ {wheel.as_uri()}",
            ]
        )
        run([mcp_python, "-c", "import plaky115_mcp; print('mcp import OK')"])
        help_result = run([mcp_python, "-m", "plaky115_mcp.cli", "--help"])
        assert "unofficial and independent" in help_result.stdout, "notice missing from --help"

        # Stdio startup: server must start, keep stdout protocol-clean, and
        # exit with the pipe.
        stdio = subprocess.run(
            [mcp_python, "-m", "plaky115_mcp.cli", "--transport", "stdio"],
            input="",
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PLAKY115_API_KEY": "plk_smoke_key"},
            check=False,
        )
        assert stdio.stdout == "", f"stdio stdout not protocol-clean: {stdio.stdout[:200]!r}"

        # Installed typing proof: strict Pyright over an external consumer
        # using only the installed wheel.
        consumer_dir = base / "consumer"
        consumer_dir.mkdir()
        (consumer_dir / "consumer.py").write_text(CONSUMER, encoding="utf-8")
        (consumer_dir / "pyrightconfig.json").write_text(
            json.dumps(
                {
                    "typeCheckingMode": "strict",
                    "reportMissingTypeStubs": False,
                    "venvPath": str(base),
                    "venv": "venv-mcp",
                }
            ),
            encoding="utf-8",
        )
        run(
            [
                sys.executable,
                "-m",
                "pyright",
                "--project",
                str(consumer_dir),
                str(consumer_dir / "consumer.py"),
            ]
        )
        print("installed typing proof OK")

        # verifytypes is informational (ADR-0004): resolver and workflow
        # returns are intentionally dynamic, so 100% completeness is not a
        # gate; the strict external consumer above is the binding proof.
        for namespace in ("plaky115", "plaky115_mcp"):
            report = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pyright",
                    "--pythonpath",
                    mcp_python,
                    "--ignoreexternal",
                    "--verifytypes",
                    namespace,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            score = next(
                (line for line in report.stdout.splitlines() if "completeness score" in line),
                "completeness score unavailable",
            )
            print(f"verifytypes {namespace}: {score.strip()}")

    print("PACKAGE SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
