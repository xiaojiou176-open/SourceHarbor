#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import current_git_commit, write_json_artifact


def _run(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _repo_slug() -> str:
    remote = _run("git", "config", "--get", "remote.origin.url", check=True).stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$", remote)
    if not match:
        raise SystemExit(
            f"unable to derive GitHub repository slug from remote.origin.url: {remote}"
        )
    return f"{match.group('owner')}/{match.group('repo')}"


def _json_or_error(command: list[str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    result = _run(*command)
    if result.returncode == 0:
        return json.loads(result.stdout), None
    return None, {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _evaluate_release_readiness(
    release_dir: Path, prechecks_path: Path
) -> tuple[dict[str, Any], list[str]]:
    state: dict[str, Any] = {
        "release_prechecks_path": _display_path(prechecks_path),
        "rollback_gate_status": "missing",
        "rollback_drill_valid": False,
        "failed_required_prechecks": [],
    }
    errors: list[str] = []

    rollback_report_path = release_dir / "rollback" / "db-rollback-readiness.json"
    rollback_payload = _load_json_object(rollback_report_path)
    if rollback_payload is None:
        errors.append(
            "rollback readiness report unreadable: " + _display_path(rollback_report_path)
        )
    else:
        summary = rollback_payload.get("summary")
        if not isinstance(summary, dict):
            summary = {}
        gate_status = str(summary.get("gate_status") or "missing")
        state["rollback_gate_status"] = gate_status
        if gate_status != "pass":
            errors.append(f"rollback readiness gate_status must be pass (got `{gate_status}`)")

        drill = rollback_payload.get("drill_evidence")
        if not isinstance(drill, dict):
            drill = {}
        drill_valid = drill.get("valid") is True
        state["rollback_drill_valid"] = drill_valid
        if not drill_valid:
            drill_errors = drill.get("errors")
            if not isinstance(drill_errors, list):
                drill_errors = []
            detail = ", ".join(str(item) for item in drill_errors) if drill_errors else "unknown"
            errors.append(f"rollback drill evidence must be valid ({detail})")

    prechecks_payload = _load_json_object(prechecks_path)
    if prechecks_payload is None:
        errors.append("release prechecks report unreadable: " + _display_path(prechecks_path))
    else:
        checks = prechecks_payload.get("checks")
        if not isinstance(checks, list):
            errors.append("release prechecks report must contain a `checks` list")
        else:
            failed_required_prechecks = sorted(
                str(item.get("name") or "<unknown>")
                for item in checks
                if isinstance(item, dict)
                and item.get("required") is True
                and str(item.get("status") or "") != "pass"
            )
            state["failed_required_prechecks"] = failed_required_prechecks
            if failed_required_prechecks:
                errors.append(
                    "required release prechecks failing: " + ", ".join(failed_required_prechecks)
                )

    return state, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release evidence attestation readiness.")
    parser.add_argument("--release-tag", required=True)
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/release/release-evidence-attest-readiness.json",
    )
    parser.add_argument("--repo", default="")
    args = parser.parse_args()

    repo = args.repo.strip() or _repo_slug()
    release_dir = ROOT / "artifacts" / "releases" / args.release_tag
    prechecks_path = ROOT / ".runtime-cache" / "reports" / "release-readiness" / "prechecks.json"
    required_files = [
        release_dir / "manifest.json",
        release_dir / "checksums.sha256",
        release_dir / "rollback" / "db-rollback-readiness.json",
        release_dir / "rollback" / "drill.json",
    ]
    missing = [
        str(path.relative_to(ROOT).as_posix()) for path in required_files if not path.is_file()
    ]

    actor_payload, actor_error = _json_or_error(["gh", "api", "user"])
    artifacts_payload, artifacts_error = _json_or_error(
        ["gh", "api", f"repos/{repo}/actions/artifacts?per_page=1"]
    )

    quota_status = "unknown"
    if artifacts_payload is not None:
        quota_status = "artifact-api-readable"
    elif artifacts_error is not None:
        quota_status = "artifact-api-unreadable"

    status = "ready"
    blocker_type = ""
    errors: list[str] = []
    readiness_state: dict[str, Any] = {
        "release_prechecks_path": _display_path(prechecks_path),
        "rollback_gate_status": "missing",
        "rollback_drill_valid": False,
        "failed_required_prechecks": [],
    }
    if missing:
        status = "blocked"
        blocker_type = "repo-evidence-missing"
        errors.append("missing release evidence files: " + ", ".join(missing))
    else:
        readiness_state, readiness_errors = _evaluate_release_readiness(release_dir, prechecks_path)
        if readiness_errors:
            status = "blocked"
            blocker_type = "release-readiness-gate-failed"
            errors.extend(readiness_errors)

    report = {
        "version": 1,
        "status": status,
        "blocker_type": blocker_type,
        "repo": repo,
        "release_tag": args.release_tag,
        "source_commit": current_git_commit(),
        "actor": (actor_payload or {}).get("login", ""),
        "actor_error": actor_error,
        "required_files": [str(path.relative_to(ROOT).as_posix()) for path in required_files],
        "missing_files": missing,
        "artifact_quota_status": quota_status,
        "artifacts_api_error": artifacts_error,
        "release_prechecks_path": readiness_state["release_prechecks_path"],
        "rollback_gate_status": readiness_state["rollback_gate_status"],
        "rollback_drill_valid": readiness_state["rollback_drill_valid"],
        "failed_required_prechecks": readiness_state["failed_required_prechecks"],
        "errors": errors,
    }
    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/release/check_release_evidence_attest_readiness.py",
        verification_scope="release-evidence-attest-readiness",
        source_run_id="release-evidence-attest-readiness",
        freshness_window_hours=24,
        extra={"report_kind": "release-evidence-attest-readiness"},
    )

    if status != "ready":
        print("[release-evidence-attest-readiness] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[release-evidence-attest-readiness] READY")
    if quota_status != "artifact-api-readable":
        print("  - artifact quota status unavailable; recorded as unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
