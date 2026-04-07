#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import git_output, repo_root

SCAN_EXTENSIONS = {
    ".md",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
}

SCAN_PATHS = (
    "README.md",
    "CHANGELOG.md",
    "docs",
    "apps/web",
    "config/public",
)

EXCLUDED_PREFIXES = (
    ".git/",
    ".runtime-cache/",
    ".agents/",
    "docs/generated/",
)

FORBIDDEN_NEEDLES = (
    ("available in one controlled local environment", "forbidden secret-presence wording"),
    ("validated provider configuration", "forbidden secret-rotation narrative"),
    ("provider credential", "forbidden secret-rotation narrative"),
    ("secure operator credential flow", "forbidden operator-secret-store wording"),
    ("secure operator environment", "forbidden operator-environment wording"),
    ("~/.cache/sourceharbor", "forbidden direct home-cache path"),
    ("$HOME/.cache/sourceharbor", "forbidden direct home-cache path"),
    ("~/.sourceharbor", "forbidden direct home-cache path"),
    ("$HOME/.sourceharbor", "forbidden direct home-cache path"),
    ("chrome-user-data", "forbidden direct browser-root fragment"),
    ("Profile 1", "forbidden direct browser-profile fragment"),
)


def _tracked_text_paths(root: Path) -> list[Path]:
    tracked = git_output("ls-files").splitlines()
    collected: list[Path] = []
    for rel in tracked:
        rel = rel.strip()
        if not rel:
            continue
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        if not any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in SCAN_PATHS):
            continue
        path = root / rel
        if path.is_dir():
            continue
        if path.suffix and path.suffix not in SCAN_EXTENSIONS:
            continue
        collected.append(path)
    return collected


def _scan_text(text: str, *, rel_path: str) -> list[str]:
    errors: list[str] = []
    lowered_needles = tuple((needle, needle.lower(), label) for needle, label in FORBIDDEN_NEEDLES)
    for lineno, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        for needle, lowered_needle, label in lowered_needles:
            if lowered_needle not in lowered:
                continue
            snippet = line.strip()
            errors.append(
                f"{rel_path}:{lineno}: {label} `{needle}`" + (f" | {snippet}" if snippet else "")
            )
    return errors


def scan_repo(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _tracked_text_paths(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        errors.extend(_scan_text(text, rel_path=rel))
    return errors


def main() -> int:
    errors = scan_repo(repo_root())
    if errors:
        print("[public-sensitive-surface] FAIL")
        for item in errors:
            print(f"  - {item}")
        print(
            "  - remediation: keep outward docs and UI copy on neutral contract language; do not publish secret-existence state, winner-key narratives, operator-store wording, or direct home-cache/profile paths"
        )
        return 1

    print("[public-sensitive-surface] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
