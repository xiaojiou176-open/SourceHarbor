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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import current_git_commit, write_json_artifact


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _repo_slug_from_remote(remote: str) -> str:
    patterns = [
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    raise SystemExit(f"unable to derive GitHub repository slug from remote.origin.url: {remote}")


def _repo_slug() -> str:
    remote = _run("git", "config", "--get", "remote.origin.url").stdout.strip()
    return _repo_slug_from_remote(remote)


def _json_or_none(command: list[str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    result = _run(*command, check=False)
    if result.returncode == 0:
        return json.loads(result.stdout), None
    error = {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    return None, error


def _current_actor() -> str:
    payload, _ = _json_or_none(["gh", "api", "user"])
    return str((payload or {}).get("login") or "").strip()


def _discover_logged_in_accounts() -> list[str]:
    result = _run("gh", "auth", "status", check=False)
    if result.returncode != 0:
        return []
    accounts: list[str] = []
    for line in result.stdout.splitlines():
        match = re.search(r"Logged in to github\.com account (?P<login>[^\s]+)", line)
        if match:
            login = match.group("login").strip()
            if login and login not in accounts:
                accounts.append(login)
    return accounts


def _switch_actor(login: str) -> None:
    result = _run("gh", "auth", "switch", "-u", login, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"unable to switch GitHub actor to `{login}`: {detail}")


def _load_required_checks() -> list[str]:
    path = ROOT / "docs" / "generated" / "required-checks.md"
    pattern = re.compile(r"^\|\s*`(?P<name>[^`]+)`\s*\|")
    non_check_rows = {"pull_request", "push", "workflow_dispatch", "schedule"}
    checks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw.strip())
        if match:
            name = match.group("name")
            if name not in non_check_rows:
                checks.append(name)
    return sorted(set(checks))


def _actual_required_checks(branch_payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(branch_payload, dict):
        return []
    required = branch_payload.get("required_status_checks")
    if not isinstance(required, dict):
        return []
    contexts = required.get("contexts")
    if isinstance(contexts, list):
        return sorted({str(item) for item in contexts if str(item).strip()})
    checks = required.get("checks")
    if isinstance(checks, list):
        values: set[str] = set()
        for item in checks:
            if isinstance(item, dict) and str(item.get("context") or "").strip():
                values.add(str(item["context"]))
        return sorted(values)
    return []


def _private_vulnerability_reporting_status(value: Any) -> str:
    if value is True:
        return "enabled"
    if value is False:
        return "disabled"
    return "unverified"


def _private_vulnerability_reporting_probe(slug: str) -> dict[str, Any]:
    payload, error = _json_or_none(["gh", "api", f"repos/{slug}/private-vulnerability-reporting"])
    if payload is not None:
        raw_enabled = payload.get("enabled")
        return {
            "status": _private_vulnerability_reporting_status(raw_enabled),
            "value": raw_enabled,
            "reason": "dedicated private-vulnerability-reporting endpoint returned explicit enabled flag",
        }
    return {
        "status": "unverified",
        "value": None,
        "reason": (
            "dedicated private-vulnerability-reporting endpoint unavailable"
            if error is None
            else "dedicated private-vulnerability-reporting endpoint did not return a readable state"
        ),
    }


def _security_and_analysis_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "unverified", "features": {}}
    features: dict[str, Any] = {}
    for key, raw_value in sorted(payload.items()):
        if isinstance(raw_value, dict):
            status = str(raw_value.get("status") or "").strip() or "unverified"
            features[key] = {"status": status}
        else:
            features[key] = {"status": "unverified"}
    overall_status = "unverified" if not features else "observed"
    return {"status": overall_status, "features": features}


def _probe_repo_platform_truth(slug: str, expected_required_checks: list[str]) -> dict[str, Any]:
    actor_result = _run("gh", "api", "user", check=False)
    actor = ""
    actor_error: dict[str, Any] | None = None
    if actor_result.returncode == 0:
        actor = json.loads(actor_result.stdout).get("login", "")
    else:
        actor_error = {
            "returncode": actor_result.returncode,
            "stdout": actor_result.stdout.strip(),
            "stderr": actor_result.stderr.strip(),
        }

    repo_payload, repo_error = _json_or_none(
        ["gh", "repo", "view", slug, "--json", "name,owner,visibility,defaultBranchRef,isPrivate"]
    )
    raw_repo_payload, raw_repo_error = _json_or_none(["gh", "api", f"repos/{slug}"])
    actions_payload, actions_error = _json_or_none(
        ["gh", "api", f"repos/{slug}/actions/permissions"]
    )
    workflow_permissions_payload, workflow_permissions_error = _json_or_none(
        ["gh", "api", f"repos/{slug}/actions/permissions/workflow"]
    )
    branch_payload, branch_error = _json_or_none(
        ["gh", "api", f"repos/{slug}/branches/main/protection"]
    )

    actual_required_checks = _actual_required_checks(branch_payload)
    missing_checks = sorted(set(expected_required_checks) - set(actual_required_checks))
    extra_checks = sorted(set(actual_required_checks) - set(expected_required_checks))

    overall_status = "pass"
    blocker_type = ""
    if repo_error:
        overall_status = "blocked"
        blocker_type = "repo-readability"
    elif branch_error or str((repo_payload or {}).get("visibility") or "") != "PUBLIC":
        overall_status = "blocked"
        blocker_type = "branch-protection-platform-boundary"
    elif missing_checks or extra_checks:
        overall_status = "blocked"
        blocker_type = "required-check-integrity-mismatch"

    private_vulnerability_reporting = {
        "status": "unverified",
        "value": None,
        "reason": "raw repo API unavailable",
    }
    security_and_analysis = {"status": "unverified", "features": {}}
    if raw_repo_payload:
        raw_pvr = raw_repo_payload.get("private_vulnerability_reporting")
        private_vulnerability_reporting = {
            "status": _private_vulnerability_reporting_status(raw_pvr),
            "value": raw_pvr,
            "reason": (
                "raw repo API returned explicit boolean"
                if isinstance(raw_pvr, bool)
                else "raw repo API returned null or omitted the field"
            ),
        }
        security_and_analysis = _security_and_analysis_summary(
            raw_repo_payload.get("security_and_analysis")
        )
        if private_vulnerability_reporting["status"] == "unverified":
            private_vulnerability_reporting = _private_vulnerability_reporting_probe(slug)

    return {
        "status": overall_status,
        "blocker_type": blocker_type,
        "actor": actor,
        "actor_error": actor_error,
        "repo_view": repo_payload,
        "repo_view_error": repo_error,
        "raw_repo_api": raw_repo_payload,
        "raw_repo_api_error": raw_repo_error,
        "actions_permissions": actions_payload,
        "actions_permissions_error": actions_error,
        "workflow_permissions": workflow_permissions_payload,
        "workflow_permissions_error": workflow_permissions_error,
        "branch_protection": branch_payload,
        "branch_protection_error": branch_error,
        "private_vulnerability_reporting": private_vulnerability_reporting,
        "security_and_analysis": security_and_analysis,
        "required_checks": {
            "expected": expected_required_checks,
            "actual": actual_required_checks,
            "missing": missing_checks,
            "extra": extra_checks,
            "match": not missing_checks and not extra_checks,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe remote GitHub repository/platform truth for the current repo."
    )
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/remote-platform-truth.json",
        help="Report output path under repo root.",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="Explicit GitHub repository slug (owner/repo). Defaults to origin remote.",
    )
    parser.add_argument(
        "--actor",
        default="",
        help="Optional gh account login to switch to for the probe.",
    )
    args = parser.parse_args()

    previous_actor = _current_actor()
    requested_actor = args.actor.strip()
    selected_actor = previous_actor
    actor_probe_attempts: list[dict[str, Any]] = []
    if requested_actor and requested_actor != previous_actor:
        _switch_actor(requested_actor)
        selected_actor = requested_actor

    try:
        slug = args.repo.strip() or _repo_slug()
        expected_required_checks = _load_required_checks()
        probe = _probe_repo_platform_truth(slug, expected_required_checks)
        actor_probe_attempts.append(
            {
                "actor": probe.get("actor") or selected_actor or previous_actor,
                "status": probe.get("status"),
                "blocker_type": probe.get("blocker_type"),
            }
        )

        if (
            not requested_actor
            and probe["status"] == "blocked"
            and probe["blocker_type"] == "branch-protection-platform-boundary"
        ):
            for actor_name in _discover_logged_in_accounts():
                if actor_name == (probe.get("actor") or previous_actor):
                    continue
                _switch_actor(actor_name)
                selected_actor = actor_name
                candidate = _probe_repo_platform_truth(slug, expected_required_checks)
                actor_probe_attempts.append(
                    {
                        "actor": candidate.get("actor") or actor_name,
                        "status": candidate.get("status"),
                        "blocker_type": candidate.get("blocker_type"),
                    }
                )
                if candidate["status"] == "pass":
                    probe = candidate
                    break
            else:
                selected_actor = probe.get("actor") or previous_actor

        report = {
            "version": 2,
            "status": probe["status"],
            "blocker_type": probe["blocker_type"],
            "repo": slug,
            "actor": probe["actor"],
            "requested_actor": requested_actor,
            "previous_actor": previous_actor,
            "actor_error": probe["actor_error"],
            "actor_probe_attempts": actor_probe_attempts,
            "source_commit": current_git_commit(),
            "repo_view": probe["repo_view"],
            "repo_view_error": probe["repo_view_error"],
            "raw_repo_api": probe["raw_repo_api"],
            "raw_repo_api_error": probe["raw_repo_api_error"],
            "actions_permissions": probe["actions_permissions"],
            "actions_permissions_error": probe["actions_permissions_error"],
            "workflow_permissions": probe["workflow_permissions"],
            "workflow_permissions_error": probe["workflow_permissions_error"],
            "branch_protection": probe["branch_protection"],
            "branch_protection_error": probe["branch_protection_error"],
            "private_vulnerability_reporting": probe["private_vulnerability_reporting"],
            "security_and_analysis": probe["security_and_analysis"],
            "required_checks": probe["required_checks"],
        }

        write_json_artifact(
            ROOT / args.output,
            report,
            source_entrypoint="scripts/governance/probe_remote_platform_truth.py",
            verification_scope="remote-platform-truth",
            source_run_id="remote-platform-truth-probe",
            freshness_window_hours=24,
            extra={"report_kind": "remote-platform-truth"},
        )

        if probe["status"] == "pass":
            print("[remote-platform-truth] PASS")
            print(f"  - repo={slug}")
            print(f"  - actor={probe['actor'] or '<unknown>'}")
            print(
                "  - private_vulnerability_reporting="
                f"{probe['private_vulnerability_reporting']['status']}"
            )
            return 0

        print("[remote-platform-truth] BLOCKED")
        print(f"  - repo={slug}")
        print(f"  - actor={probe['actor'] or '<unknown>'}")
        print(f"  - blocker_type={probe['blocker_type']}")
        print(
            "  - private_vulnerability_reporting="
            f"{probe['private_vulnerability_reporting']['status']}"
        )
        if probe["branch_protection_error"]:
            err = probe["branch_protection_error"]
            print(f"  - branch_protection_error={err.get('stderr') or err.get('stdout')}")
        elif probe["repo_view_error"]:
            err = probe["repo_view_error"]
            print(f"  - repo_view_error={err.get('stderr') or err.get('stdout')}")
        elif probe["required_checks"]["missing"] or probe["required_checks"]["extra"]:
            print(f"  - missing_checks={','.join(probe['required_checks']['missing']) or '<none>'}")
            print(f"  - extra_checks={','.join(probe['required_checks']['extra']) or '<none>'}")
        return 0
    finally:
        if selected_actor and previous_actor and selected_actor != previous_actor:
            _switch_actor(previous_actor)


if __name__ == "__main__":
    raise SystemExit(main())
