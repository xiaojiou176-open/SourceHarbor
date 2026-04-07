#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import repo_root, write_json_artifact


def _load_config(root: Path) -> dict[str, Any]:
    path = root / "config" / "governance" / "local-private-ledgers.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_local_private_ledger_migration(root: Path) -> dict[str, Any]:
    payload = _load_config(root)
    ledgers = payload.get("ledgers", [])
    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    for ledger in ledgers if isinstance(ledgers, list) else []:
        if not isinstance(ledger, dict):
            errors.append("ledger entry must be an object")
            continue
        name = str(ledger.get("name") or "<unknown>")
        authoritative_rel = str(ledger.get("authoritative_target_path") or "").strip()
        if not authoritative_rel:
            errors.append(f"{name}: missing authoritative_target_path")
            continue

        authoritative_root = (root / authoritative_rel).resolve()
        receipts_path = authoritative_root / ".migration-receipts.json"
        try:
            receipts_payload = (
                json.loads(receipts_path.read_text(encoding="utf-8"))
                if receipts_path.is_file()
                else {"entries": {}}
            )
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            receipts_payload = {"entries": {}}
            errors.append(f"{name}: invalid migration receipts at {_rel_path(root, receipts_path)}")
        receipt_entries = receipts_payload.get("entries")
        if not isinstance(receipt_entries, dict):
            receipt_entries = {}
            errors.append(f"{name}: migration receipts must expose an object `entries` map")

        compatibility_paths = ledger.get("compatibility_paths", [])
        discovered_sources: list[Path] = []
        if isinstance(compatibility_paths, list):
            for rel in compatibility_paths:
                compat_root = (root / str(rel)).resolve()
                if compat_root.is_dir():
                    discovered_sources.extend(sorted(compat_root.glob("*.md")))

        if discovered_sources and not authoritative_root.is_dir():
            errors.append(
                f"{name}: authoritative target `{authoritative_rel}` missing while compatibility sources still exist"
            )

        ledger_row = {
            "name": name,
            "authoritative_target_path": authoritative_rel,
            "receipts_path": _rel_path(root, receipts_path),
            "compatibility_paths": [str(item) for item in compatibility_paths]
            if isinstance(compatibility_paths, list)
            else [],
            "discovered_source_files": [_rel_path(root, path) for path in discovered_sources],
            "status": "pass",
        }

        for source in discovered_sources:
            source_rel = _rel_path(root, source)
            target = authoritative_root / source.name
            target_rel = _rel_path(root, target)
            source_stat = source.stat()
            source_signature = {
                "size_bytes": int(source_stat.st_size),
                "mtime_ns": int(source_stat.st_mtime_ns),
                "sha256": _sha256(source),
            }
            receipt = receipt_entries.get(source_rel)
            if not target.is_file():
                errors.append(
                    f"{name}: authoritative ledger missing for `{source_rel}` -> `{target_rel}`"
                )
                ledger_row["status"] = "fail"
                continue

            target_signature = {
                "size_bytes": int(target.stat().st_size),
                "mtime_ns": int(target.stat().st_mtime_ns),
                "sha256": _sha256(target),
            }
            if source_signature["sha256"] != target_signature["sha256"]:
                errors.append(
                    f"{name}: authoritative ledger `{target_rel}` content drifted from compatibility source `{source_rel}`"
                )
                ledger_row["status"] = "fail"

            if not isinstance(receipt, dict):
                errors.append(f"{name}: migration receipt missing for `{source_rel}`")
                ledger_row["status"] = "fail"
                continue

            if str(receipt.get("target_path") or "").strip() != target_rel:
                errors.append(
                    f"{name}: receipt target mismatch for `{source_rel}` (expected `{target_rel}`)"
                )
                ledger_row["status"] = "fail"

            if int(receipt.get("source_size_bytes") or -1) != source_signature["size_bytes"]:
                errors.append(f"{name}: receipt source_size_bytes stale for `{source_rel}`")
                ledger_row["status"] = "fail"
            if int(receipt.get("source_mtime_ns") or -1) != source_signature["mtime_ns"]:
                errors.append(f"{name}: receipt source_mtime_ns stale for `{source_rel}`")
                ledger_row["status"] = "fail"

        rows.append(ledger_row)

    report = {
        "version": 1,
        "status": "pass" if not errors else "fail",
        "ledgers": rows,
        "errors": errors,
    }
    write_json_artifact(
        root
        / ".runtime-cache"
        / "reports"
        / "governance"
        / "local-private-ledger-migration-check.json",
        report,
        source_entrypoint="scripts/governance/check_local_private_ledger_migration.py",
        verification_scope="local-private-ledger-migration-check",
        source_run_id="local-private-ledger-migration-check",
        freshness_window_hours=24,
        extra={"report_kind": "local-private-ledger-migration-check"},
    )
    return report


def main() -> int:
    root = repo_root()
    report = evaluate_local_private_ledger_migration(root)
    if report["status"] != "pass":
        print("[local-private-ledger-migration-check] FAIL")
        for item in report["errors"]:
            print(f"  - {item}")
        return 1

    print("[local-private-ledger-migration-check] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
