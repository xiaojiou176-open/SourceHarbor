#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import repo_root, write_json_artifact


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _run_gitleaks(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        command,
        cwd=repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        text=False,
        capture_output=True,
        check=True,
    )
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def _materialize_tracked_snapshot(root: Path, destination: Path) -> None:
    for rel_path in _tracked_files(root):
        source = root / rel_path
        target = destination / rel_path
        if source.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            target.symlink_to(source.readlink())
            continue
        if not source.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _write_report(
    *,
    path: Path,
    mode: str,
    command: list[str],
    returncode: int,
    stdout: str,
    stderr: str,
    findings: list[dict[str, Any]],
) -> None:
    if returncode == 0:
        status = "pass"
    elif returncode == 1:
        status = "fail"
    else:
        status = "error"

    payload = {
        "version": 1,
        "mode": mode,
        "status": status,
        "command": command,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "finding_count": len(findings),
        "findings": findings,
    }
    write_json_artifact(
        path,
        payload,
        source_entrypoint="scripts/governance/generate_open_source_audit_reports.py",
        verification_scope=f"open-source-audit-{mode}",
        source_run_id=f"open-source-audit-{mode}",
        freshness_window_hours=24,
        extra={"report_kind": f"open-source-audit-{mode}"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate local open-source audit receipts for history and working tree gitleaks scans."
    )
    parser.add_argument(
        "--out-dir",
        default=".runtime-cache/reports/open-source-audit",
        help="Output directory relative to repo root.",
    )
    args = parser.parse_args()

    root = repo_root()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="sourceharbor-gitleaks-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        history_json = tmp_root / "gitleaks-history.json"
        working_tree_json = tmp_root / "gitleaks-working-tree.json"
        tracked_snapshot_root = tmp_root / "tracked-worktree"
        _materialize_tracked_snapshot(root, tracked_snapshot_root)

        history_cmd = [
            "gitleaks",
            "git",
            "--redact",
            "--report-format",
            "json",
            "--report-path",
            str(history_json),
            "--config",
            str(root / ".gitleaks.toml"),
            str(root),
        ]
        history_code, history_stdout, history_stderr = _run_gitleaks(history_cmd)
        history_findings = _load_json_list(history_json)
        _write_report(
            path=out_dir / "gitleaks-history.json",
            mode="history",
            command=history_cmd,
            returncode=history_code,
            stdout=history_stdout,
            stderr=history_stderr,
            findings=history_findings,
        )

        working_tree_cmd = [
            "gitleaks",
            "detect",
            "--source",
            str(tracked_snapshot_root),
            "--no-git",
            "--redact",
            "--report-format",
            "json",
            "--report-path",
            str(working_tree_json),
            "--config",
            str(root / ".gitleaks.toml"),
        ]
        worktree_code, worktree_stdout, worktree_stderr = _run_gitleaks(working_tree_cmd)
        worktree_findings = _load_json_list(working_tree_json)
        _write_report(
            path=out_dir / "gitleaks-working-tree.json",
            mode="working-tree",
            command=working_tree_cmd,
            returncode=worktree_code,
            stdout=worktree_stdout,
            stderr=worktree_stderr,
            findings=worktree_findings,
        )

    if history_code not in {0, 1}:
        print("[open-source-audit-generate] FAIL")
        print("  - gitleaks history scan command error")
        return 1
    if worktree_code not in {0, 1}:
        print("[open-source-audit-generate] FAIL")
        print("  - gitleaks working-tree scan command error")
        return 1

    print("[open-source-audit-generate] PASS")
    print(f"  - history_status={'pass' if history_code == 0 else 'fail'}")
    print(f"  - worktree_status={'pass' if worktree_code == 0 else 'fail'} (tracked files only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
