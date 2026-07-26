#!/usr/bin/env python3
"""Validate the built inter-agent-claude-code Python artifacts.

Standard library only. Reports filename/rule classifications and never prints
artifact contents. Exits non-zero on any boundary violation.

Usage: validate-artifacts.py <python.whl> <python.tar.gz>
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

EXPECTED_NAME = "inter-agent-claude-code"
EXPECTED_VERSION = "0.2.0"
EXPECTED_CORE_DEP = "inter-agent-core==0.2.0"
EXPECTED_WS_DEP = "websockets==16.0"

SHARE_ROOT = "share/inter-agent-claude-code"
REQUIRED_WHEEL_DATA = {
    f"{SHARE_ROOT}/.claude-plugin/plugin.json",
    f"{SHARE_ROOT}/.claude-plugin/marketplace.json",
    f"{SHARE_ROOT}/skills/inter-agent/SKILL.md",
    f"{SHARE_ROOT}/skills/inter-agent/bootstrap.md",
    f"{SHARE_ROOT}/skills/inter-agent/bin/inter-agent-claude",
    f"{SHARE_ROOT}/skills/inter-agent/bin/bootstrap-runtime",
}

# Forbidden anywhere in either artifact (matched as path fragments).
FORBIDDEN_FRAGMENTS = (
    "inter_agent/core/",
    "inter_agent/adapters/",
    "inter_agent_pi/",
    "tests/",
    "conftest.py",
    "uv.lock",
    ".venv/",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def wheel_metadata(whl: Path) -> str:
    with zipfile.ZipFile(whl) as z:
        meta = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        return z.read(meta).decode("utf-8")


def wheel_entry_points(whl: Path) -> str:
    with zipfile.ZipFile(whl) as z:
        ep = next((n for n in z.namelist() if n.endswith("entry_points.txt")), None)
        return z.read(ep).decode("utf-8") if ep else ""


def validate_wheel(whl: Path) -> None:
    print(f"== python wheel: {whl.name} ==")
    with zipfile.ZipFile(whl) as z:
        names = z.namelist()
    meta = wheel_metadata(whl)
    if f"Name: {EXPECTED_NAME}" not in meta:
        fail(f"wheel Name not {EXPECTED_NAME!r}")
    if f"Version: {EXPECTED_VERSION}" not in meta:
        fail(f"wheel Version not {EXPECTED_VERSION!r}")
    if EXPECTED_CORE_DEP not in meta:
        fail(f"wheel missing Requires-Dist {EXPECTED_CORE_DEP!r}")
    if EXPECTED_WS_DEP not in meta:
        fail(f"wheel missing Requires-Dist {EXPECTED_WS_DEP!r}")
    for bad in (
        "file://",
        "../../tmp",
        "Requires-Dist: inter-agent ==",
        "Requires-Dist: inter-agent==",
    ):
        if bad in meta:
            fail(f"wheel metadata contains forbidden string {bad!r}")

    ep = wheel_entry_points(whl)
    if "inter-agent-claude = inter_agent_claude.cli:main" not in ep:
        fail(f"wheel entry points missing child script: {ep!r}")
    core_scripts = [
        ln for ln in ep.splitlines() if "inter_agent.core" in ln or "inter_agent_pi" in ln
    ]
    if core_scripts:
        fail(f"wheel leaked non-child scripts: {core_scripts!r}")

    py_files = [n for n in names if n.startswith("inter_agent_claude/") and n.endswith(".py")]
    if not py_files:
        fail("wheel has no inter_agent_claude source")

    missing = sorted(req for req in REQUIRED_WHEEL_DATA if not any(req in n for n in names))
    if missing:
        fail(f"wheel missing required data files: {missing!r}")

    for n in names:
        low = n.lower()
        if low.endswith(".ts") or low.endswith(".lock") or low.endswith(".tgz"):
            fail(f"wheel shipped non-python file: {n}")
        for frag in FORBIDDEN_FRAGMENTS:
            if frag in low:
                fail(f"wheel leaked forbidden path: {n}")
    print("  wheel OK")


def validate_sdist(sdist: Path) -> None:
    print(f"== python sdist: {sdist.name} ==")
    with tarfile.open(sdist, "r:gz") as tar:
        members = tar.getmembers()
        names = [m.name for m in members if m.isfile()]
        pkginfo = next((m for m in members if m.name.endswith("PKG-INFO")), None)
        body = tar.extractfile(pkginfo).read().decode("utf-8") if pkginfo else ""  # type: ignore[union-attr]
    if f"Name: {EXPECTED_NAME}" not in body:
        fail(f"sdist Name not {EXPECTED_NAME!r}")
    if f"Version: {EXPECTED_VERSION}" not in body:
        fail(f"sdist Version not {EXPECTED_VERSION!r}")
    if not any(n.endswith("inter_agent_claude/__init__.py") for n in names):
        fail("sdist has no inter_agent_claude source")

    required_src = {
        "pyproject.toml",
        "README.md",
        "CHANGELOG.md",
        "LICENSE.md",
        "MANIFEST.in",
    }
    name_set = {n.split("/", 1)[1] if "/" in n else n for n in names}
    missing = sorted(required_src - name_set)
    if missing:
        fail(f"sdist missing required source files: {missing!r}")
    required_assets = {
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "skills/inter-agent/SKILL.md",
        "skills/inter-agent/bootstrap.md",
        "skills/inter-agent/bin/inter-agent-claude",
        "skills/inter-agent/bin/bootstrap-runtime",
        "scripts/run-checks.sh",
        "scripts/validate-artifacts.py",
    }
    missing_assets = sorted(required_assets - {n.split("/", 1)[1] for n in names})
    # Required assets live under the package prefix; match by suffix.
    missing_assets = sorted(a for a in required_assets if not any(n.endswith(a) for n in names))
    if missing_assets:
        fail(f"sdist missing required assets: {missing_assets!r}")

    for n in names:
        low = n.lower()
        if low.endswith(".ts") or low.endswith(".lock") or low.endswith(".tgz"):
            fail(f"sdist shipped non-python file: {n}")
        for frag in FORBIDDEN_FRAGMENTS:
            if frag in low:
                fail(f"sdist leaked forbidden path: {n}")
    print("  sdist OK")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate-artifacts.py <python.whl> <python.tar.gz>", file=sys.stderr)
        return 2
    whl, sdist = (Path(p) for p in argv)
    for p in (whl, sdist):
        if not p.is_file():
            fail(f"missing artifact: {p}")
    validate_wheel(whl)
    validate_sdist(sdist)
    print("== all artifacts OK ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
