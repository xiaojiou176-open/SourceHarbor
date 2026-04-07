#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

ROOT = RUNTIME_DIR.parents[1]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_json_artifact  # noqa: E402
from sourceharbor_chrome import (  # noqa: E402
    default_cdp_port,
    default_profile_dir,
    default_profile_name,
    default_repo_user_data_dir,
    is_cdp_alive,
    list_repo_chrome_processes,
    remove_ephemeral_artifacts,
    resolve_repo_runtime,
)


def _report_path(repo_root: Path) -> Path:
    return repo_root / ".runtime-cache" / "reports" / "runtime" / "repo-chrome-stop.json"


def _wait_until_stopped(
    *, user_data_dir: Path, port: int, timeout_seconds: float
) -> tuple[bool, list[dict[str, str]]]:
    deadline = time.time() + timeout_seconds
    remaining = list_repo_chrome_processes(user_data_dir)
    while time.time() < deadline:
        remaining = list_repo_chrome_processes(user_data_dir)
        if not remaining and not is_cdp_alive(port):
            return True, []
        time.sleep(0.25)
    remaining = list_repo_chrome_processes(user_data_dir)
    return not remaining and not is_cdp_alive(port), remaining


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stop SourceHarbor's dedicated Chrome instance on the repo-owned isolated user data root."
    )
    parser.add_argument("--user-data-dir", default="")
    parser.add_argument("--profile-dir", default=default_profile_dir())
    parser.add_argument("--profile-name", default=default_profile_name())
    parser.add_argument("--cdp-port", default=str(default_cdp_port()))
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo_root = ROOT
    user_data_dir = Path(args.user_data_dir.strip() or default_repo_user_data_dir()).expanduser()

    try:
        runtime_payload = resolve_repo_runtime(
            user_data_dir=str(user_data_dir),
            profile_name=args.profile_name,
            profile_dir=args.profile_dir,
            cdp_port=args.cdp_port,
        )
        port = int(runtime_payload["cdp_port"])
        existing_processes = list_repo_chrome_processes(user_data_dir)
        if not existing_processes and not is_cdp_alive(port):
            report = {
                "version": 1,
                "generated_at": datetime.now(UTC)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "repo_root": str(repo_root),
                "status": "already-stopped",
                "cdp_url": runtime_payload["cdp_url"],
                "user_data_dir": str(user_data_dir),
                "profile_dir": runtime_payload["profile_dir"],
                "profile_name": runtime_payload["profile_name"],
                "terminated_pids": [],
                "force_killed_pids": [],
            }
            write_json_artifact(
                _report_path(repo_root),
                report,
                source_entrypoint="scripts/runtime/stop_repo_chrome.py",
                verification_scope="repo-chrome-stop",
                source_run_id="repo-chrome-stop",
                freshness_window_hours=24,
            )
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print("[stop-repo-chrome] ALREADY STOPPED")
            return 0

        terminated_pids: list[str] = []
        for process in existing_processes:
            pid = int(process["pid"])
            os.kill(pid, signal.SIGTERM)
            terminated_pids.append(process["pid"])

        stopped, remaining_processes = _wait_until_stopped(
            user_data_dir=user_data_dir,
            port=port,
            timeout_seconds=args.timeout_seconds,
        )
        force_killed_pids: list[str] = []
        if not stopped and remaining_processes:
            for process in remaining_processes:
                pid = int(process["pid"])
                os.kill(pid, signal.SIGKILL)
                force_killed_pids.append(process["pid"])
            stopped, remaining_processes = _wait_until_stopped(
                user_data_dir=user_data_dir,
                port=port,
                timeout_seconds=3.0,
            )
        if not stopped:
            raise RuntimeError(
                "repo Chrome processes did not stop cleanly; remaining pids="
                + ",".join(process["pid"] for process in remaining_processes)
            )
        remove_ephemeral_artifacts(user_data_dir, runtime_payload["profile_dir"])
    except RuntimeError as exc:
        print(f"[stop-repo-chrome] FAIL\n  - {exc}", file=sys.stderr)
        return 1

    report = {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_root": str(repo_root),
        "status": "stopped",
        "cdp_url": runtime_payload["cdp_url"],
        "user_data_dir": str(user_data_dir),
        "profile_dir": runtime_payload["profile_dir"],
        "profile_name": runtime_payload["profile_name"],
        "terminated_pids": terminated_pids,
        "force_killed_pids": force_killed_pids,
    }
    write_json_artifact(
        _report_path(repo_root),
        report,
        source_entrypoint="scripts/runtime/stop_repo_chrome.py",
        verification_scope="repo-chrome-stop",
        source_run_id="repo-chrome-stop",
        freshness_window_hours=24,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("[stop-repo-chrome] PASS")
        print(f"  - cdp={report['cdp_url']}")
        print(f"  - terminated={','.join(terminated_pids) if terminated_pids else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
