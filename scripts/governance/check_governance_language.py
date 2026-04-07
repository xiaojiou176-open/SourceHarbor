#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from common import repo_root

# Keep the enforced surface scoped to the repository's real public and
# governance-facing docs. The older list drifted into historical or aspirational
# files that do not exist in this checkout, which turned this gate into a
# phantom-file detector instead of a language-quality check.
CHECK_PATHS = [
    "README.md",
    "docs/architecture.md",
    "docs/proof.md",
    "docs/start-here.md",
    "docs/testing.md",
    "docs/runbook-local.md",
    "docs/testing-slo.md",
]

CHECK_GLOBS = [
    "docs/deploy/*.md",
    "docs/reference/*.md",
]

STRICT_ENGLISH_PATHS = [
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "NOTICE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/index.md",
    "docs/architecture.md",
    "docs/proof.md",
    "docs/start-here.md",
    "docs/testing.md",
    "docs/runbook-local.md",
    "docs/testing-slo.md",
    "evals/rubric.md",
    "evals/README.md",
    "artifacts/releases/README.md",
    "contracts/AGENTS.md",
    "contracts/CLAUDE.md",
    "contracts/README.md",
    "apps/worker/worker/pipeline/steps/llm_prompts.py",
]

STRICT_ENGLISH_GLOBS = [
    "docs/deploy/*.md",
    "docs/reference/*.md",
]

FORBIDDEN_SNIPPETS = [
    "\u517c\u5bb9\u65e7\u884c\u4e3a",
    "\u517c\u5bb9\u5386\u53f2",
    "\u8fc1\u79fb\u671f\u4fdd\u7559",
    "\u8fc7\u6e21\u671f",
    "legacy env \u4ec5\u517c\u5bb9",
]

PRODUCT_OUTPUT_LOCALE_ALLOWLIST_PATHS = [
    "apps/worker/worker/pipeline/steps/artifacts.py",
    "apps/worker/worker/pipeline/runner_rendering.py",
    "apps/worker/templates/digest.md.mustache",
]

HAN_RE = re.compile(r"[\u4e00-\u9fff]")


def _resolve_paths(root: Path, explicit_paths: list[str], globs: list[str]) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()

    for rel in explicit_paths:
        if rel not in seen:
            seen.add(rel)
            resolved.append(rel)

    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            resolved.append(rel)

    return resolved


def _scan_forbidden_snippets(root: Path, errors: list[str]) -> None:
    for rel in _resolve_paths(root, CHECK_PATHS, CHECK_GLOBS):
        path = root / rel
        if not path.is_file():
            # Optional targets should not fail-close the whole governance gate.
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in content:
                errors.append(f"{rel}: contains forbidden governance legacy phrase `{snippet}`")


def _scan_strict_english(root: Path, errors: list[str]) -> None:
    for rel in _resolve_paths(root, STRICT_ENGLISH_PATHS, STRICT_ENGLISH_GLOBS):
        path = root / rel
        if not path.is_file():
            # Some strict-English surfaces are optional in this checkout family.
            continue
        content = path.read_text(encoding="utf-8")
        if HAN_RE.search(content):
            errors.append(
                f"{rel}: contains non-English governance/runtime text on a strict-English surface"
            )


def _scan_product_output_allowlist(root: Path, advisories: list[str]) -> None:
    for rel in PRODUCT_OUTPUT_LOCALE_ALLOWLIST_PATHS:
        path = root / rel
        if not path.is_file():
            advisories.append(f"{rel}: missing product-output locale allowlist target")
            continue
        content = path.read_text(encoding="utf-8")
        if HAN_RE.search(content):
            advisories.append(
                f"{rel}: contains Chinese content inside the explicit product-output locale allowlist; do not let this exception leak back into contributor/runtime/governance surfaces"
            )


def main() -> int:
    root = repo_root()
    errors: list[str] = []
    advisories: list[str] = []

    _scan_forbidden_snippets(root, errors)
    _scan_strict_english(root, errors)
    _scan_product_output_allowlist(root, advisories)

    if errors:
        print("[governance-language] FAIL")
        for item in errors:
            print(f"  - {item}")
        if advisories:
            print("[governance-language] ADVISORY")
            for item in advisories:
                print(f"  - {item}")
        return 1

    print("[governance-language] PASS")
    if advisories:
        print("[governance-language] ADVISORY")
        for item in advisories:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
