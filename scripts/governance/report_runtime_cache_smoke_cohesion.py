#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import current_git_commit, read_runtime_metadata, write_json_artifact


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind runtime-cache maintenance and api-real-smoke-local into one current cohesion report."
    )
    parser.add_argument(
        "--maintenance-report",
        default=".runtime-cache/reports/governance/runtime-cache-maintenance.json",
        help="Runtime-cache maintenance report path.",
    )
    parser.add_argument(
        "--smoke-log-meta",
        default=".runtime-cache/logs/tests/api-real-smoke-local.jsonl.meta.json",
        help="api-real-smoke-local log metadata path.",
    )
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/cache-prune-smoke-cohesion.json",
        help="Output report path.",
    )
    args = parser.parse_args()

    maintenance_path = ROOT / args.maintenance_report
    smoke_meta_path = ROOT / args.smoke_log_meta
    errors: list[str] = []

    if not maintenance_path.is_file():
        errors.append(f"missing maintenance report: {args.maintenance_report}")
    if not smoke_meta_path.is_file():
        errors.append(f"missing smoke log metadata: {args.smoke_log_meta}")

    maintenance_report: dict = {}
    maintenance_meta: dict | None = None
    smoke_meta: dict = {}
    if not errors:
        maintenance_report = _load_json(maintenance_path)
        maintenance_meta = read_runtime_metadata(maintenance_path)
        smoke_meta = _load_json(smoke_meta_path)
        if maintenance_report.get("status") != "pass":
            errors.append("runtime-cache maintenance report must be pass")
        if maintenance_meta is None:
            errors.append("runtime-cache maintenance report missing runtime metadata")
        if str(smoke_meta.get("source_commit") or "") != current_git_commit():
            errors.append(
                "api-real-smoke-local log metadata source_commit does not match current HEAD"
            )
        if (
            maintenance_meta
            and str(maintenance_meta.get("source_commit") or "") != current_git_commit()
        ):
            errors.append(
                "runtime-cache maintenance report source_commit does not match current HEAD"
            )

    report = {
        "version": 1,
        "status": "pass" if not errors else "fail",
        "source_commit": current_git_commit(),
        "maintenance_report": args.maintenance_report,
        "maintenance_status": maintenance_report.get("status", "missing"),
        "maintenance_created_at": (maintenance_meta or {}).get("created_at", ""),
        "maintenance_source_run_id": (maintenance_meta or {}).get("source_run_id", ""),
        "smoke_log_meta": args.smoke_log_meta,
        "smoke_created_at": str(smoke_meta.get("created_at") or ""),
        "smoke_source_run_id": str(smoke_meta.get("source_run_id") or ""),
        "smoke_entrypoint": str(smoke_meta.get("source_entrypoint") or ""),
        "conditions": {
            "maintenance_report_present": maintenance_path.is_file(),
            "maintenance_report_pass": maintenance_report.get("status") == "pass",
            "maintenance_report_current_head": (maintenance_meta or {}).get("source_commit")
            == current_git_commit(),
            "smoke_meta_present": smoke_meta_path.is_file(),
            "smoke_current_head": str(smoke_meta.get("source_commit") or "")
            == current_git_commit(),
        },
        "errors": errors,
        "notes": [
            "This report proves the current workspace has both a current maintenance pass and a current api-real-smoke-local run.",
            "It is a cohesion report, not a claim that both artifacts share the same source_run_id.",
        ],
    }

    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/governance/report_runtime_cache_smoke_cohesion.py",
        verification_scope="cache-prune-smoke-cohesion",
        source_run_id="cache-prune-smoke-cohesion",
        freshness_window_hours=24,
        extra={"report_kind": "cache-prune-smoke-cohesion"},
    )

    if errors:
        print("[cache-prune-smoke-cohesion] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[cache-prune-smoke-cohesion] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
