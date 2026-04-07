#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
    copy_profile_into_repo_root,
    default_profile_dir,
    default_profile_name,
    default_repo_user_data_dir,
    default_source_user_data_dir,
    list_default_root_chrome_processes,
    resolve_source_profile_dir,
)


def _report_path(repo_root: Path) -> Path:
    return repo_root / ".runtime-cache" / "reports" / "runtime" / "repo-chrome-bootstrap.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap SourceHarbor's dedicated Chrome user data root by copying a single source profile into the repo-owned cache root."
    )
    parser.add_argument("--source-user-data-dir", default="")
    parser.add_argument("--source-profile-name", default=default_profile_name())
    parser.add_argument("--source-profile-dir", default="")
    parser.add_argument("--target-user-data-dir", default="")
    parser.add_argument("--target-profile-dir", default=default_profile_dir())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo_root = ROOT
    source_user_data_dir = Path(
        args.source_user_data_dir.strip() or default_source_user_data_dir()
    ).expanduser()
    target_user_data_dir = Path(
        args.target_user_data_dir.strip() or default_repo_user_data_dir()
    ).expanduser()

    chrome_processes = list_default_root_chrome_processes(source_user_data_dir)
    if chrome_processes:
        message = (
            "refusing bootstrap because Chrome processes are still using the default Chrome root; "
            "close default-root Chrome windows first"
        )
        print(f"[bootstrap-repo-chrome] FAIL\n  - {message}", file=sys.stderr)
        for process in chrome_processes[:10]:
            print(
                f"  - pid={process['pid']} command={process['command']}",
                file=sys.stderr,
            )
        return 1

    try:
        source_profile_dir = resolve_source_profile_dir(
            user_data_dir=source_user_data_dir,
            profile_name=args.source_profile_name,
            profile_dir=args.source_profile_dir,
        )
        payload = copy_profile_into_repo_root(
            source_user_data_dir=source_user_data_dir,
            source_profile_dir=source_profile_dir,
            target_user_data_dir=target_user_data_dir,
            target_profile_dir=args.target_profile_dir,
            profile_name=args.source_profile_name,
        )
    except RuntimeError as exc:
        print(f"[bootstrap-repo-chrome] FAIL\n  - {exc}", file=sys.stderr)
        return 1

    report = {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_root": str(repo_root),
        "source_user_data_dir": str(source_user_data_dir),
        "source_profile_dir": source_profile_dir,
        "target_user_data_dir": str(target_user_data_dir),
        "target_profile_dir": args.target_profile_dir,
        "profile_name": args.source_profile_name,
        "copied_state_markers": payload["copied_state_markers"],
        "status": "pass",
    }
    write_json_artifact(
        _report_path(repo_root),
        report,
        source_entrypoint="scripts/runtime/bootstrap_repo_chrome.py",
        verification_scope="repo-chrome-bootstrap",
        source_run_id="repo-chrome-bootstrap",
        freshness_window_hours=24,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("[bootstrap-repo-chrome] PASS")
        print(f"  - target={target_user_data_dir}")
        print(f"  - profile={args.target_profile_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
