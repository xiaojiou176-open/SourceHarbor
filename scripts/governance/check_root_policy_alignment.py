#!/usr/bin/env python3
from __future__ import annotations

import re
import sys

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root

DOCS_REQUIRING_MANAGED_UV = [
    "README.md",
    "CONTRIBUTING.md",
    "docs/start-here.md",
    "docs/runbook-local.md",
]
DOCS_REQUIRING_MANAGED_PYTHON_GATE = [
    "CONTRIBUTING.md",
    "docs/runbook-local.md",
    "docs/testing.md",
]
WORKFLOW_OR_HOOKS_REQUIRING_MANAGED_UV = [
    ".github/workflows/ci.yml",
    ".github/workflows/pre-commit.yml",
    ".githooks/pre-push",
]
RAW_PYTHON_TEST_GATE = re.compile(
    r"PYTHONPATH=\"\\$PWD:\\$PWD/apps/worker\" DATABASE_URL='sqlite\\+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q"
)


def main() -> int:
    root = repo_root()
    runtime_outputs = load_governance_json("runtime-outputs.json")
    root_policy = load_governance_json("root-runtime-policy.json")
    forbidden = {str(item) for item in runtime_outputs.get("root_forbidden", [])}
    errors: list[str] = []
    if str(root_policy.get("runtime_root") or "") != str(runtime_outputs.get("runtime_root") or ""):
        errors.append("root-runtime-policy.json runtime_root drifted from runtime-outputs.json")
    if {str(item) for item in root_policy.get("forbidden_root_virtualenvs", [])} != {
        ".venv",
        "venv",
    }:
        errors.append(
            "root-runtime-policy.json must declare `.venv` and `venv` as forbidden root virtualenvs"
        )

    residue_text = (root / "scripts/runtime/clean_source_runtime_residue.py").read_text(
        encoding="utf-8"
    )
    allowed_roots_match = re.search(
        r"ALLOWED_ROOTS\s*=\s*\{(?P<body>.*?)\n\}",
        residue_text,
        re.DOTALL,
    )
    allowed_roots_block = allowed_roots_match.group("body") if allowed_roots_match else ""
    for entry in sorted({".venv", "venv"} & forbidden):
        if f'ROOT / "{entry}"' in allowed_roots_block:
            errors.append(f"residue cleaner still whitelists forbidden root path `{entry}`")

    gitignore_lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".agents/" not in {line.strip() for line in gitignore_lines}:
        errors.append("`.agents/` must be ignored wholesale as a local agent workspace root")

    raw_uv_sync = re.compile(r"(?m)^uv sync --frozen --extra dev --extra e2e$")
    for rel in DOCS_REQUIRING_MANAGED_UV:
        text = (root / rel).read_text(encoding="utf-8")
        if raw_uv_sync.search(text):
            errors.append(
                f"{rel}: raw `uv sync --frozen --extra dev --extra e2e` still appears without managed UV_PROJECT_ENVIRONMENT"
            )

    for rel in DOCS_REQUIRING_MANAGED_PYTHON_GATE:
        text = (root / rel).read_text(encoding="utf-8")
        if RAW_PYTHON_TEST_GATE.search(text):
            errors.append(
                f"{rel}: raw repo-side python gate still appears instead of the managed `scripts/ci/python_tests.sh` entrypoint"
            )

    for rel in WORKFLOW_OR_HOOKS_REQUIRING_MANAGED_UV:
        text = (root / rel).read_text(encoding="utf-8")
        if raw_uv_sync.search(text) and "UV_PROJECT_ENVIRONMENT" not in text:
            errors.append(
                f"{rel}: raw `uv sync --frozen --extra dev --extra e2e` still appears without managed UV_PROJECT_ENVIRONMENT"
            )
        if RAW_PYTHON_TEST_GATE.search(text) and "scripts/ci/python_tests.sh" not in text:
            errors.append(
                f"{rel}: raw repo-side python gate still appears instead of the managed `scripts/ci/python_tests.sh` entrypoint"
            )

    if errors:
        print("[root-policy-alignment] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[root-policy-alignment] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
