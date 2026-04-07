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
    ".github",
    "README.md",
    "NOTICE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
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
    "infra/migrations/",
)

ALLOWED_EXACT_EMAILS = {
    "git@github.com",
}

ALLOWED_DOMAINS = {
    "example.com",
    "example.invalid",
}

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")


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


def _is_allowed(email: str) -> bool:
    lowered = email.lower()
    if lowered in ALLOWED_EXACT_EMAILS:
        return True
    _, _, domain = lowered.partition("@")
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in ALLOWED_DOMAINS)


def _looks_like_url_credential(line: str, start: int, end: int) -> bool:
    window_start = max(0, start - 32)
    prefix = line[window_start:start]
    suffix = line[end : min(len(line), end + 8)]
    return "://" in prefix and suffix.startswith(("/", ":"))


def scan_repo(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _tracked_text_paths(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in EMAIL_PATTERN.finditer(line):
                email = match.group(0)
                if _looks_like_url_credential(line, match.start(), match.end()):
                    continue
                if _is_allowed(email):
                    continue
                errors.append(f"{rel}:{lineno}: non-placeholder public email reference `{email}`")
    return errors


def main() -> int:
    errors = scan_repo(repo_root())
    if errors:
        print("[public-personal-email-references] FAIL")
        for item in errors:
            print(f"  - {item}")
        print(
            "  - remediation: keep tracked public surfaces on example.com/example.invalid placeholders or a repo-owned non-personal inbox, never maintainer personal addresses"
        )
        return 1

    print("[public-personal-email-references] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
