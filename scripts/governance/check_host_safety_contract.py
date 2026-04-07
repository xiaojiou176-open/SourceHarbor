#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

from common import git_tracked_paths, rel_path, repo_root

ROOT = repo_root()
TRACKED_PATHS = git_tracked_paths()
SELF_PATH = "scripts/governance/check_host_safety_contract.py"
SCANNED_PREFIXES = ("apps/", "bin/", "infra/", "scripts/", ".github/", ".githooks/")
SCANNED_SUFFIXES = (
    ".py",
    ".pyi",
    ".sh",
    ".bash",
    ".js",
    ".cjs",
    ".mjs",
    ".ts",
    ".tsx",
    ".yml",
    ".yaml",
)
IGNORED_PARTS = {".git", "node_modules", ".cache", ".runtime-cache", "__pycache__"}


@dataclass(frozen=True)
class Rule:
    label: str
    pattern: re.Pattern[str]
    reason: str


FORBIDDEN_RULES = (
    Rule(
        label="pkill",
        pattern=re.compile(r"\bpkill\b"),
        reason="broad process matching is forbidden; act on exact repo-owned units or recorded child handles only",
    ),
    Rule(
        label="killall",
        pattern=re.compile(r"\bkillall\b"),
        reason="process-name-wide termination is forbidden; act on exact repo-owned units or recorded child handles only",
    ),
    Rule(
        label="shell-kill-9",
        pattern=re.compile(r"\bkill\s+-9\b"),
        reason="broad SIGKILL shell cleanup is forbidden; use bounded timeout helpers instead",
    ),
    Rule(
        label="osascript",
        pattern=re.compile(r"\bosascript\b"),
        reason="repo-tracked automation must not drive host-wide AppleScript control paths",
    ),
    Rule(
        label="system-events",
        pattern=re.compile(r"System Events"),
        reason="repo-tracked automation must not use global GUI event injection",
    ),
    Rule(
        label="loginwindow",
        pattern=re.compile(r"\bloginwindow\b"),
        reason="host session control paths are forbidden in repo-tracked automation",
    ),
    Rule(
        label="show-force-quit-panel",
        pattern=re.compile(r"showForceQuitPanel"),
        reason="Force Quit panel control paths are forbidden in repo-tracked automation",
    ),
    Rule(
        label="negative-kill",
        pattern=re.compile(r"\b(?:process|os)\.kill\(\s*-\d"),
        reason="negative-PID signaling is forbidden",
    ),
    Rule(
        label="zero-kill",
        pattern=re.compile(r"\b(?:process|os)\.kill\(\s*0(?:\s*[,)]|$)"),
        reason="PID 0 signaling is forbidden",
    ),
)


def should_scan(path: Path) -> bool:
    relative = rel_path(path)
    if relative == SELF_PATH or relative not in TRACKED_PATHS:
        return False
    if any(part in IGNORED_PARTS for part in path.parts):
        return False
    if not any(relative.startswith(prefix) for prefix in SCANNED_PREFIXES):
        return False
    return path.suffix in SCANNED_SUFFIXES or relative.startswith(".githooks/")


def iter_scanned_paths() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*") if path.is_file() and should_scan(path))


def main() -> int:
    failures: list[str] = []

    for path in iter_scanned_paths():
        relative = rel_path(path)
        content = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for rule in FORBIDDEN_RULES:
                if rule.pattern.search(line):
                    failures.append(f"{relative}:{lineno}: {rule.label}: {rule.reason}")

    if failures:
        print("[host-safety-contract] FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("[host-safety-contract] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
