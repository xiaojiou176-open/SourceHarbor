#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import repo_root


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_total(name: str, payload: object, *, allow_null: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"disk-space audit report totals.{name} must be an object"]
    size_bytes = payload.get("size_bytes")
    size_human = payload.get("size_human")
    if allow_null:
        if size_bytes is not None and not isinstance(size_bytes, int):
            errors.append(
                f"disk-space audit report totals.{name}.size_bytes must be integer or null"
            )
    else:
        if not isinstance(size_bytes, int):
            errors.append(f"disk-space audit report totals.{name}.size_bytes must be integer")
    if not isinstance(size_human, str):
        errors.append(f"disk-space audit report totals.{name}.size_human must be string")
    return errors


def _validate_repo_internal_residue(payload: object) -> list[str]:
    errors: list[str] = []
    expected_buckets = {
        "proof_scratch",
        "active_logs",
        "local_private_ledgers",
        "tracked_release_evidence",
        "orphan_residue",
    }
    if not isinstance(payload, dict):
        return ["disk-space audit report governance.repo_internal_residue must be an object"]
    for bucket in expected_buckets:
        if bucket not in payload:
            errors.append(
                f"disk-space audit report missing governance.repo_internal_residue.{bucket}"
            )
            continue
        bucket_payload = payload[bucket]
        if not isinstance(bucket_payload, dict):
            errors.append(
                f"disk-space audit report governance.repo_internal_residue.{bucket} must be an object"
            )
            continue
        if not isinstance(bucket_payload.get("size_bytes"), int):
            errors.append(
                f"disk-space audit report governance.repo_internal_residue.{bucket}.size_bytes must be integer"
            )
        if not isinstance(bucket_payload.get("size_human"), str):
            errors.append(
                f"disk-space audit report governance.repo_internal_residue.{bucket}.size_human must be string"
            )
        paths = bucket_payload.get("paths")
        if not isinstance(paths, list):
            errors.append(
                f"disk-space audit report governance.repo_internal_residue.{bucket}.paths must be list"
            )
            continue
        for idx, entry in enumerate(paths):
            if not isinstance(entry, dict):
                errors.append(
                    f"disk-space audit report governance.repo_internal_residue.{bucket}.paths[{idx}] must be object"
                )
                continue
            if not isinstance(entry.get("path"), str):
                errors.append(
                    f"disk-space audit report governance.repo_internal_residue.{bucket}.paths[{idx}].path must be string"
                )
            if not isinstance(entry.get("exists"), bool):
                errors.append(
                    f"disk-space audit report governance.repo_internal_residue.{bucket}.paths[{idx}].exists must be bool"
                )
            if not isinstance(entry.get("size_bytes"), int):
                errors.append(
                    f"disk-space audit report governance.repo_internal_residue.{bucket}.paths[{idx}].size_bytes must be integer"
                )
            if not isinstance(entry.get("size_human"), str):
                errors.append(
                    f"disk-space audit report governance.repo_internal_residue.{bucket}.paths[{idx}].size_human must be string"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the generated disk-space audit report structure."
    )
    parser.add_argument("--repo-root", default=str(repo_root()))
    parser.add_argument("--policy", default="config/governance/disk-space-governance.json")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = (root / policy_path).resolve()
    policy = _load_json(policy_path)
    report_path = Path(args.report) if args.report else root / str(policy["report_path"])
    if not report_path.is_absolute():
        report_path = (root / report_path).resolve()

    errors: list[str] = []
    if not report_path.is_file():
        errors.append(f"missing disk-space audit report: {report_path}")
    else:
        payload = _load_json(report_path)
        totals = dict(payload.get("totals", {}))
        for key in (
            "repo-internal",
            "repo-external-repo-owned",
            "shared-layer",
            "unverified-layer",
            "confirmed_total",
        ):
            if key not in totals:
                errors.append(f"disk-space audit report missing totals.{key}")
        if "repo-internal" in totals:
            errors.extend(
                _validate_total("repo-internal", totals["repo-internal"], allow_null=False)
            )
        if "repo-external-repo-owned" in totals:
            errors.extend(
                _validate_total(
                    "repo-external-repo-owned", totals["repo-external-repo-owned"], allow_null=False
                )
            )
        if "shared-layer" in totals:
            errors.extend(_validate_total("shared-layer", totals["shared-layer"], allow_null=False))
        if "unverified-layer" in totals:
            errors.extend(
                _validate_total("unverified-layer", totals["unverified-layer"], allow_null=True)
            )
        if "confirmed_total" in totals:
            errors.extend(
                _validate_total("confirmed_total", totals["confirmed_total"], allow_null=False)
            )
        legacy = dict(payload.get("legacy_compatibility", {}))
        for key in (
            "active_markers_detected",
            "legacy_paths_detected",
            "legacy_paths_recently_active",
            "legacy_paths_referenced_by_local_env",
            "legacy_retirement_blocked",
        ):
            if key not in legacy:
                errors.append(f"disk-space audit report missing legacy_compatibility.{key}")
        governance = dict(payload.get("governance", {}))
        for key in (
            "runtime_tmp_over_budget",
            "legacy_default_write_drift",
            "unexpected_repo_external_paths",
            "repo_internal_residue",
        ):
            if key not in governance:
                errors.append(f"disk-space audit report missing governance.{key}")
        if "repo_internal_residue" in governance:
            errors.extend(_validate_repo_internal_residue(governance["repo_internal_residue"]))

    if errors:
        print("[disk-space-audit-report] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[disk-space-audit-report] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
