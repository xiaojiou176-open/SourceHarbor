#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from common import (
    current_git_commit,
    find_forbidden_runtime_entries,
    load_governance_json,
    read_runtime_metadata,
    rel_path,
    repo_root,
    top_level_entries,
    write_json_artifact,
)


def _snapshot() -> list[str]:
    return [path.name for path in top_level_entries()]


def _tolerated_local_private_entries() -> set[str]:
    payload = load_governance_json("root-allowlist.json")
    return {
        str(item["path"])
        for item in payload.get("local_private_root_tolerations", [])
        if isinstance(item, dict) and item.get("path")
    }


def _nested_boundary_notes() -> list[str]:
    payload = load_governance_json("root-allowlist.json")
    notes: list[str] = []
    for item in payload.get("tracked_root_allowlist", []):
        if not isinstance(item, dict):
            continue
        for hint in item.get("nested_boundary_hints", []):
            if not isinstance(hint, dict):
                continue
            path = str(hint.get("path") or "").strip()
            if not path:
                continue
            candidate = repo_root() / path
            if candidate.exists():
                notes.append(
                    f"{path} ({hint.get('current_tracking_state', 'unknown')} -> {hint.get('target_tracking_state', 'unknown')})"
                )
    return sorted(dict.fromkeys(notes))


def _hygiene_violations() -> list[str]:
    payload = load_governance_json("runtime-outputs.json")
    violations: list[str] = []
    for item in payload.get("root_forbidden", []):
        candidate = repo_root() / str(item)
        if candidate.exists():
            violations.append(str(item))
    violations.extend(
        find_forbidden_runtime_entries([str(item) for item in payload.get("nested_forbidden", [])])
    )
    return sorted(dict.fromkeys(violations))


def _runtime_root_unknown_children() -> list[str]:
    payload = load_governance_json("runtime-outputs.json")
    runtime_root = repo_root() / str(payload["runtime_root"])
    allowed_subdirs = set(payload.get("subdirectories", {}).keys())
    if not runtime_root.exists():
        return []
    return sorted(
        str(Path(".runtime-cache") / child.name)
        for child in runtime_root.iterdir()
        if child.name not in allowed_subdirs
    )


def _resolve_runtime_report_path(path: Path) -> Path:
    payload = load_governance_json("runtime-outputs.json")
    candidate = path if path.is_absolute() else repo_root() / path
    resolved = candidate.resolve()
    runtime_root = (repo_root() / str(payload["runtime_root"])).resolve()
    try:
        relative_path = resolved.relative_to(runtime_root)
    except ValueError as exc:
        raise SystemExit(
            "--write-report must point to a path under the .runtime-cache root"
        ) from exc
    if not relative_path.parts:
        raise SystemExit(
            "--write-report must point to a file under a declared .runtime-cache subdirectory"
        )
    allowed_subdirs = set(payload.get("subdirectories", {}).keys())
    if relative_path.parts[0] not in allowed_subdirs:
        allowed = ", ".join(sorted(allowed_subdirs))
        raise SystemExit(
            f"--write-report must stay under a declared .runtime-cache subdirectory: {allowed}"
        )
    return resolved


def _build_compare_report(
    *,
    snapshot_path: Path,
    saved_entries: list[str],
    current_entries: list[str],
    tolerated_entries: list[str],
    new_entries: list[str],
    hygiene_violations: list[str],
    runtime_root_unknown_children: list[str],
    nested_boundary_notes: list[str],
) -> dict[str, Any]:
    blocker_details: list[str] = []
    if new_entries:
        blocker_details.append("new top-level entries after task")
    if hygiene_violations:
        blocker_details.append("forbidden hygiene residue present")
    if runtime_root_unknown_children:
        blocker_details.append("runtime root contains undeclared direct children")

    resolved_snapshot_path = (
        snapshot_path if snapshot_path.is_absolute() else repo_root() / snapshot_path
    )
    snapshot_metadata = read_runtime_metadata(resolved_snapshot_path)
    status = "pass" if not blocker_details else "fail"
    return {
        "version": 1,
        "status": status,
        "source_commit": current_git_commit(),
        "compared_snapshot": rel_path(resolved_snapshot_path),
        "snapshot_created_at": (snapshot_metadata or {}).get("created_at"),
        "snapshot_verification_scope": (snapshot_metadata or {}).get("verification_scope"),
        "saved_entries": saved_entries,
        "current_entries": current_entries,
        "tolerated_entries": tolerated_entries,
        "new_entries": new_entries,
        "hygiene_violations": hygiene_violations,
        "runtime_root_unknown_children": runtime_root_unknown_children,
        "nested_boundary_notes": nested_boundary_notes,
        "failure_reasons": blocker_details,
        "summary": {
            "saved_entry_count": len(saved_entries),
            "current_entry_count": len(current_entries),
            "tolerated_entry_count": len(tolerated_entries),
            "new_entry_count": len(new_entries),
            "hygiene_violation_count": len(hygiene_violations),
            "runtime_root_unknown_child_count": len(runtime_root_unknown_children),
            "nested_boundary_note_count": len(nested_boundary_notes),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture or compare root-level top directory state."
    )
    parser.add_argument(
        "--write-snapshot", type=Path, help="Write the current root snapshot JSON to this path."
    )
    parser.add_argument(
        "--compare-snapshot", type=Path, help="Compare current root state against a saved snapshot."
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        help="When comparing, write a JSON runtime report under the .runtime-cache root.",
    )
    args = parser.parse_args()

    if bool(args.write_snapshot) == bool(args.compare_snapshot):
        raise SystemExit("must pass exactly one of --write-snapshot or --compare-snapshot")
    if args.write_snapshot and args.write_report:
        raise SystemExit("--write-report can only be used together with --compare-snapshot")

    if args.write_snapshot:
        target = args.write_snapshot
        write_json_artifact(
            target,
            {"version": 1, "entries": _snapshot()},
            source_entrypoint="scripts/governance/check_root_dirtiness_after_tasks.py",
            verification_scope="root-dirtiness-snapshot",
            source_run_id="root-dirtiness-snapshot",
            freshness_window_hours=24,
            extra={"report_kind": "root-dirtiness-snapshot"},
        )
        try:
            rendered_target = target.relative_to(repo_root()).as_posix()
        except ValueError:
            rendered_target = str(target)
        print(f"[root-dirtiness] wrote snapshot to {rendered_target}")
        return 0

    raw_payload = json.loads(args.compare_snapshot.read_text(encoding="utf-8"))
    if isinstance(raw_payload, dict) and isinstance(raw_payload.get("entries"), list):
        saved = raw_payload["entries"]
    else:
        saved = raw_payload
    before = set(saved)
    current_entries = _snapshot()
    after = set(current_entries)
    tolerated_entries = sorted(_tolerated_local_private_entries())
    tolerated_entry_set = set(tolerated_entries)
    new_entries = sorted((after - before) - tolerated_entry_set)
    hygiene_violations = _hygiene_violations()
    runtime_root_unknown_children = _runtime_root_unknown_children()
    nested_boundary_notes = _nested_boundary_notes()
    if args.write_report:
        report_path = _resolve_runtime_report_path(args.write_report)
        write_json_artifact(
            report_path,
            _build_compare_report(
                snapshot_path=args.compare_snapshot,
                saved_entries=sorted(before),
                current_entries=current_entries,
                tolerated_entries=tolerated_entries,
                new_entries=new_entries,
                hygiene_violations=hygiene_violations,
                runtime_root_unknown_children=runtime_root_unknown_children,
                nested_boundary_notes=nested_boundary_notes,
            ),
            source_entrypoint="scripts/governance/check_root_dirtiness_after_tasks.py",
            verification_scope="root-dirtiness-compare",
            source_run_id="root-dirtiness-compare",
            freshness_window_hours=24,
            extra={"report_kind": "root-dirtiness-compare"},
        )
    if new_entries:
        print("[root-dirtiness] FAIL")
        print("  - new top-level entries after task: " + ", ".join(new_entries))
        return 1
    if hygiene_violations:
        print("[root-dirtiness] FAIL")
        print("  - forbidden hygiene residue present: " + ", ".join(hygiene_violations))
        return 1
    if runtime_root_unknown_children:
        print("[root-dirtiness] FAIL")
        print(
            "  - runtime root contains undeclared direct children: "
            + ", ".join(runtime_root_unknown_children)
        )
        return 1
    if nested_boundary_notes:
        print(
            "[root-dirtiness] note: nested boundary migration targets present="
            + ", ".join(nested_boundary_notes)
        )
    print("[root-dirtiness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
