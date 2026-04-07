#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import current_git_commit, write_json_artifact


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _plan_search_roots() -> list[Path]:
    config_path = ROOT / "config" / "governance" / "local-private-ledgers.json"
    roots: list[Path] = []
    if config_path.is_file():
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        for ledger in payload.get("ledgers", []):
            authoritative = str(ledger.get("authoritative_target_path") or "").strip()
            if authoritative:
                roots.append((ROOT / authoritative).resolve())
            for compat in ledger.get("compatibility_paths", []):
                compat_text = str(compat).strip()
                if compat_text:
                    roots.append((ROOT / compat_text).resolve())
    if not roots:
        roots = [
            (ROOT / ".runtime-cache" / "evidence" / "ai-ledgers").resolve(),
            (ROOT / ".agents" / "Plans").resolve(),
        ]
    deduped: list[Path] = []
    for path in roots:
        if path not in deduped:
            deduped.append(path)
    return deduped


def _latest_plan_path(explicit: str) -> Path:
    if explicit:
        return (ROOT / explicit).resolve()
    for plans_dir in _plan_search_roots():
        candidates = sorted(
            plans_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True
        )
        if candidates:
            return candidates[0]
    searched = " or ".join(path.relative_to(ROOT).as_posix() for path in _plan_search_roots())
    raise SystemExit(f"no plan file found under {searched}")


def _find_latest_plan_path(explicit: str) -> Path | None:
    if explicit:
        candidate = (ROOT / explicit).resolve()
        return candidate if candidate.is_file() else None
    for plans_dir in _plan_search_roots():
        if not plans_dir.is_dir():
            continue
        candidates = sorted(
            plans_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True
        )
        if candidates:
            return candidates[0]
    return None


def _tracked_dirty_files() -> list[str]:
    result = _run("git", "status", "--short")
    if result.returncode != 0:
        raise SystemExit(f"git status failed: {result.stderr.strip() or result.stdout.strip()}")
    dirty: list[str] = []
    for raw in result.stdout.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        path = line[3:]
        if path and path not in dirty:
            dirty.append(path)
    return dirty


def _extract_declared_dirty_sets(plan_text: str) -> tuple[list[str], list[str]]:
    in_scope: list[str] = []
    out_of_scope: list[str] = []
    mode: str | None = None

    backtick_pattern = re.compile(r"`([^`]+)`")

    for raw_line in plan_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("- current dirty sets:"):
            mode = "awaiting"
            continue
        if mode == "awaiting":
            if stripped.startswith("- in-scope:"):
                mode = "in_scope"
                in_scope.extend(backtick_pattern.findall(line))
                continue
            if stripped.startswith("- out-of-scope existing drift:"):
                mode = "out_of_scope"
                out_of_scope.extend(backtick_pattern.findall(line))
                continue
        if mode == "in_scope":
            if stripped.startswith("- out-of-scope existing drift:"):
                mode = "out_of_scope"
                out_of_scope.extend(backtick_pattern.findall(line))
                continue
            if line.startswith(("- ", "### ", "## ")):
                break
            in_scope.extend(backtick_pattern.findall(line))
        elif mode == "out_of_scope":
            if line.startswith(("- ", "### ", "## ")):
                break
            out_of_scope.extend(backtick_pattern.findall(line))

    return sorted(dict.fromkeys(in_scope)), sorted(dict.fromkeys(out_of_scope))


def _recommended_commit_groups(
    in_scope: list[str], out_of_scope: list[str]
) -> list[dict[str, object]]:
    docs_and_policies: list[str] = []
    tests_and_tooling: list[str] = []
    external_truth_tooling: list[str] = []

    for path in in_scope:
        if path.startswith("apps/worker/tests/"):
            tests_and_tooling.append(path)
        elif path.startswith(("scripts/governance/", "scripts/lib/standard_env.sh")):
            if path in {
                "scripts/governance/probe_remote_platform_truth.py",
                "scripts/governance/render_current_state_summary.py",
                "scripts/governance/report_worktree_status.py",
            }:
                external_truth_tooling.append(path)
            else:
                docs_and_policies.append(path)
        else:
            docs_and_policies.append(path)

    groups: list[dict[str, object]] = []
    if docs_and_policies:
        groups.append(
            {
                "name": "docs-public-governance",
                "rationale": "public/docs/language/governance surface changes that belong in the main repo-side documentation batch",
                "paths": docs_and_policies,
            }
        )
    if tests_and_tooling:
        groups.append(
            {
                "name": "repo-side-contract-tests",
                "rationale": "tests that lock the repo-side governance and external-proof semantics introduced in this round",
                "paths": tests_and_tooling,
            }
        )
    if external_truth_tooling:
        groups.append(
            {
                "name": "external-truth-tooling",
                "rationale": "runtime truth helpers for actor-aware platform probing and worktree closure reporting",
                "paths": external_truth_tooling,
            }
        )
    if out_of_scope:
        groups.append(
            {
                "name": "out-of-scope-existing-drift",
                "rationale": "tracked drift that is intentionally not part of the current mainline patch set",
                "paths": out_of_scope,
            }
        )
    return groups


def _build_report(
    *,
    plan_path: Path | None,
    declared_in_scope: list[str],
    declared_out_of_scope: list[str],
    dirty_files: list[str],
) -> dict[str, object]:
    declared_all = set(declared_in_scope) | set(declared_out_of_scope)
    dirty_set = set(dirty_files)
    plan_missing = plan_path is None

    return {
        "version": 1,
        "status": "partial"
        if plan_missing
        else ("pass" if dirty_set <= declared_all else "partial"),
        "plan_path": None if plan_path is None else str(plan_path.relative_to(ROOT)),
        "plan_missing": plan_missing,
        "searched_plan_roots": [path.relative_to(ROOT).as_posix() for path in _plan_search_roots()],
        "source_commit": current_git_commit(),
        "tracked_dirty_files": dirty_files,
        "declared_in_scope": declared_in_scope,
        "declared_out_of_scope": declared_out_of_scope,
        "undeclared_dirty_files": sorted(dirty_set if plan_missing else (dirty_set - declared_all)),
        "declared_but_clean_files": [] if plan_missing else sorted(declared_all - dirty_set),
        "summary": {
            "tracked_dirty_count": len(dirty_files),
            "in_scope_count": len(declared_in_scope),
            "out_of_scope_count": len(declared_out_of_scope),
            "undeclared_dirty_count": len(
                dirty_set if plan_missing else (dirty_set - declared_all)
            ),
            "declared_but_clean_count": 0 if plan_missing else len(declared_all - dirty_set),
        },
        "recommended_commit_groups": []
        if plan_missing
        else _recommended_commit_groups(declared_in_scope, declared_out_of_scope),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report dirty tracked worktree status against the authoritative plan."
    )
    parser.add_argument(
        "--plan",
        default="",
        help="Plan path relative to repo root. Defaults to authoritative ai-ledgers, then falls back to .agents/Plans.",
    )
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/worktree-status-closure.json",
        help="Output path relative to repo root.",
    )
    args = parser.parse_args()

    dirty_files = _tracked_dirty_files()
    plan_path = _find_latest_plan_path(args.plan)
    if plan_path is None:
        declared_in_scope: list[str] = []
        declared_out_of_scope: list[str] = []
    else:
        plan_text = plan_path.read_text(encoding="utf-8")
        declared_in_scope, declared_out_of_scope = _extract_declared_dirty_sets(plan_text)

    report = _build_report(
        plan_path=plan_path,
        declared_in_scope=declared_in_scope,
        declared_out_of_scope=declared_out_of_scope,
        dirty_files=dirty_files,
    )

    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/governance/report_worktree_status.py",
        verification_scope="worktree-status-closure",
        source_run_id="worktree-status-closure",
        freshness_window_hours=24,
        extra={"report_kind": "worktree-status-closure"},
    )

    print("[worktree-status-closure] " + report["status"].upper())
    if report["plan_path"] is None:
        print("  - plan=missing")
        print("  - reason=missing_authoritative_plan")
    else:
        print(f"  - plan={report['plan_path']}")
    print(f"  - tracked_dirty_count={report['summary']['tracked_dirty_count']}")
    print(f"  - undeclared_dirty_count={report['summary']['undeclared_dirty_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
