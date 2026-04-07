#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import git_output, repo_root

SCAN_EXTENSIONS = {
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".service",
    ".conf",
    ".toml",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
}

SCAN_PATHS = (
    "README.md",
    "NOTICE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".env.example",
    ".devcontainer/devcontainer.json",
    "docs",
    "scripts",
    "config",
    "contracts",
    "evals",
    "infra",
    "apps",
)

EXCLUDED_PREFIXES = (
    ".git/",
    ".runtime-cache/",
    ".agents/",
    "docs/plans/",
    "docs/vendor/",
    "docs/governance/final-form.md",
    "infra/migrations/",
)

ALLOWED_SUBSTRINGS = (
    "/workspace",
    "/tmp/sourceharbor",
    "/private/tmp/sourceharbor",
    "/tmp/sourceharbor",
    "/private/tmp/sourceharbor",
    "/Users/<name>/",
    "/home/<name>/",
    "/home/ubuntu/actions-runner/",
    "$HOME/.cache/sourceharbor",
    "~/.cache/sourceharbor",
    "$HOME/.sourceharbor",
    "~/.sourceharbor",
    ".runtime-cache/tmp/",
)

_USERS_PREFIX_PATTERN = "/" + "Users" + r"/[^/\s\"'`]+"
_HOME_PREFIX_PATTERN = "/" + "home" + r"/[^/\s\"'`]+"
_WORKSPACES_PATTERN = "/" + "workspaces" + "/"
_OLD_WORKSPACE_PREFIX = "VS Code" + "/1_Personal_Project"
_PERSONAL_EMAIL_PATTERN = r"\b[A-Z0-9._%+-]+@(?:gmail|outlook|hotmail|icloud)\.com\b"

FORBIDDEN_PATTERNS = (
    re.compile(_USERS_PREFIX_PATTERN),
    re.compile(_HOME_PREFIX_PATTERN),
    re.compile(_WORKSPACES_PATTERN),
    re.compile(_OLD_WORKSPACE_PREFIX),
)

FORBIDDEN_PERSONAL_EMAIL = re.compile(_PERSONAL_EMAIL_PATTERN, re.IGNORECASE)


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


def _allowed_context(line: str, start: int) -> bool:
    return any(token in line[max(0, start - 80) : start + 160] for token in ALLOWED_SUBSTRINGS)


def _mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    visible = local[:2] if len(local) >= 2 else local[:1]
    return f"{visible}***@{domain}"


def _scan_text(text: str, *, rel_path: str) -> list[str]:
    errors: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(line):
                if _allowed_context(line, match.start()):
                    continue
                snippet = line.strip()
                errors.append(
                    f"{rel_path}:{lineno}: forbidden host-specific path reference `{match.group(0)}`"
                    + (f" | {snippet}" if snippet else "")
                )
        for match in FORBIDDEN_PERSONAL_EMAIL.finditer(line):
            snippet = line.strip()
            errors.append(
                f"{rel_path}:{lineno}: forbidden personal-email reference `{_mask_email(match.group(0))}`"
                + (f" | {snippet}" if snippet else "")
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
    root = repo_root()
    errors = scan_repo(root)
    if errors:
        print("[host-path-governance] FAIL")
        for item in errors:
            print(f"  - {item}")
        print(
            "  - remediation: keep only controlled execution paths like /workspace or /tmp/sourceharbor* in public canonical surfaces; remove maintainer-specific absolute paths, old workspace prefixes, and personal email addresses"
        )
        return 1

    print("[host-path-governance] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
