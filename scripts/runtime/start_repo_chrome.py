#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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
    MAX_MACHINE_CHROME_INSTANCES,
    build_launch_command,
    cdp_url,
    default_cdp_port,
    default_profile_dir,
    default_profile_name,
    default_repo_user_data_dir,
    is_cdp_alive,
    list_actual_chrome_processes,
    list_repo_chrome_processes,
    resolve_chrome_binary,
    resolve_repo_runtime,
    wait_for_cdp,
)


def _report_path(repo_root: Path) -> Path:
    return repo_root / ".runtime-cache" / "reports" / "runtime" / "repo-chrome-start.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start SourceHarbor's dedicated Chrome instance on the repo-owned isolated user data root."
    )
    parser.add_argument("--user-data-dir", default="")
    parser.add_argument("--profile-dir", default=default_profile_dir())
    parser.add_argument("--profile-name", default=default_profile_name())
    parser.add_argument("--cdp-port", default=str(default_cdp_port()))
    parser.add_argument("--chrome-binary", default="")
    parser.add_argument("--start-url", default="about:blank")
    parser.add_argument("--allow-over-cap", action="store_true")
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
        if existing_processes:
            if not is_cdp_alive(port):
                raise RuntimeError(
                    "repo Chrome instance already exists but CDP endpoint is not responding; refuse to second-launch"
                )
            report = {
                "version": 1,
                "generated_at": datetime.now(UTC)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "repo_root": str(repo_root),
                "status": "already-running",
                "pid_candidates": [process["pid"] for process in existing_processes],
                "cdp_url": cdp_url(port),
                "user_data_dir": str(user_data_dir),
                "profile_dir": runtime_payload["profile_dir"],
                "profile_name": runtime_payload["profile_name"],
            }
            write_json_artifact(
                _report_path(repo_root),
                report,
                source_entrypoint="scripts/runtime/start_repo_chrome.py",
                verification_scope="repo-chrome-start",
                source_run_id="repo-chrome-start",
                freshness_window_hours=24,
            )
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print("[start-repo-chrome] ALREADY RUNNING")
                print(f"  - cdp={report['cdp_url']}")
            return 0

        machine_browser_processes = list_actual_chrome_processes()
        if (
            len(machine_browser_processes) > MAX_MACHINE_CHROME_INSTANCES
            and not args.allow_over_cap
        ):
            raise RuntimeError(
                "refusing to launch a new repo Chrome instance because the machine already has more than "
                f"{MAX_MACHINE_CHROME_INSTANCES} Chrome instances; wait for other repo workflows to release browser resources first"
            )

        chrome_binary = resolve_chrome_binary(args.chrome_binary)
        command = build_launch_command(
            chrome_binary=chrome_binary,
            user_data_dir=user_data_dir,
            profile_dir=runtime_payload["profile_dir"],
            cdp_port=port,
            start_url=args.start_url,
        )
        process = subprocess.Popen(  # noqa: S603
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
        cdp_version = wait_for_cdp(port, timeout_seconds=20.0)
    except RuntimeError as exc:
        print(f"[start-repo-chrome] FAIL\n  - {exc}", file=sys.stderr)
        return 1

    report = {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_root": str(repo_root),
        "status": "started",
        "pid": process.pid,
        "cdp_url": cdp_url(port),
        "cdp_version": cdp_version,
        "chrome_binary": chrome_binary,
        "user_data_dir": str(user_data_dir),
        "profile_dir": runtime_payload["profile_dir"],
        "profile_name": runtime_payload["profile_name"],
        "allow_over_cap": args.allow_over_cap,
    }
    write_json_artifact(
        _report_path(repo_root),
        report,
        source_entrypoint="scripts/runtime/start_repo_chrome.py",
        verification_scope="repo-chrome-start",
        source_run_id="repo-chrome-start",
        freshness_window_hours=24,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("[start-repo-chrome] PASS")
        print(f"  - pid={process.pid}")
        print(f"  - cdp={report['cdp_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
