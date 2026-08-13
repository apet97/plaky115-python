"""Four-scope secret scan: tracked source, git history, artifacts, evidence.

Reports file/category/count without printing matched values.

Usage: uv run python scripts/secret_scan.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# plk_ keys with a plausible secret tail; the short test placeholders used
# in fixtures (plk_x, plk_test...) are non-secrets by construction.
PATTERNS: dict[str, re.Pattern[bytes]] = {
    "plaky-api-key": re.compile(rb"plk_[A-Za-z0-9_-]{20,}"),
    "pypi-token": re.compile(rb"pypi-AgE[A-Za-z0-9_-]{20,}"),
    "github-token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "github-fine-grained-pat": re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    "private-key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "signed-url": re.compile(rb"X-Amz-Signature=[A-Za-z0-9]{16,}"),
}

ALLOWLIST_FILES = {
    "tests/fixtures/security/plaky-api-key-cases.json",  # split parts, no whole keys
}


def scan_bytes(data: bytes, origin: str, findings: list[tuple[str, str, int]]) -> None:
    for category, pattern in PATTERNS.items():
        count = len(pattern.findall(data))
        if count:
            findings.append((origin, category, count))


def scan_tracked() -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []
    files = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True
    ).stdout.split(b"\0")
    for raw in files:
        if not raw:
            continue
        rel = raw.decode()
        if rel in ALLOWLIST_FILES:
            continue
        path = REPO / rel
        if path.is_file():
            scan_bytes(path.read_bytes(), f"tracked:{rel}", findings)
    return findings


def scan_history() -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []
    revs = subprocess.run(
        ["git", "rev-list", "--all"], cwd=REPO, capture_output=True, check=True, text=True
    ).stdout.split()
    for rev in revs:
        patch = subprocess.run(
            ["git", "show", "--format=", rev],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout
        scan_bytes(patch, f"history:{rev[:12]}", findings)
    return findings


def scan_artifacts() -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []
    dist = REPO / "dist"
    if not dist.is_dir():
        return findings
    for artifact in sorted(dist.iterdir()):
        if artifact.suffix == ".whl":
            with zipfile.ZipFile(artifact) as bundle:
                for name in bundle.namelist():
                    scan_bytes(bundle.read(name), f"artifact:{artifact.name}:{name}", findings)
        elif artifact.suffixes[-2:] == [".tar", ".gz"]:
            import tarfile

            with tarfile.open(artifact) as bundle:
                for member in bundle.getmembers():
                    if member.isfile():
                        extracted = bundle.extractfile(member)
                        if extracted is not None:
                            scan_bytes(
                                extracted.read(),
                                f"artifact:{artifact.name}:{member.name}",
                                findings,
                            )
    return findings


def scan_evidence() -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []
    evidence = REPO / "evidence"
    if not evidence.is_dir():
        return findings
    for path in sorted(evidence.rglob("*")):
        if path.is_file():
            scan_bytes(path.read_bytes(), f"evidence:{path.relative_to(REPO)}", findings)
    return findings


def main() -> int:
    scopes = {
        "tracked": scan_tracked(),
        "history": scan_history(),
        "artifacts": scan_artifacts(),
        "evidence": scan_evidence(),
    }
    failed = False
    for scope, findings in scopes.items():
        if findings:
            failed = True
            print(f"SECRET SCAN [{scope}]: {len(findings)} finding(s)")
            for origin, category, count in findings:
                print(f"  - {origin}: {category} x{count}")
        else:
            print(f"SECRET SCAN [{scope}]: clean")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
