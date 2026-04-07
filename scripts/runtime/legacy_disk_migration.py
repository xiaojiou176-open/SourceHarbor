#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from disk_space_common import (
    collect_legacy_compatibility,
    expand_policy_path,
    human_bytes,
    load_policy,
    lsof_hits,
    parse_env_assignments,
    repo_root,
    size_bytes,
    update_env_assignments,
    write_report,
)
from report_disk_space import build_report

SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm")


def _canonical_entry_map(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("name") or ""): entry
        for entry in policy.get("migration_variables", [])
        if str(entry.get("name") or "").strip()
    }


def _legacy_roots_for_target(target: Path, *, root: Path, policy: dict[str, Any]) -> list[Path]:
    canonical_paths = dict(policy.get("canonical_paths", {}))
    candidate_roots: list[Path] = []
    for canonical_key, legacy_keys in (
        ("user_state_root", ("legacy_state_root",)),
        ("user_cache_root", ("legacy_cache_root",)),
    ):
        canonical_root_raw = str(canonical_paths.get(canonical_key) or "").strip()
        if not canonical_root_raw:
            continue
        canonical_root = expand_policy_path(canonical_root_raw, root=root)
        try:
            target.relative_to(canonical_root)
        except ValueError:
            continue
        for legacy_key in legacy_keys:
            legacy_raw = str(canonical_paths.get(legacy_key) or "").strip()
            if not legacy_raw:
                continue
            legacy_root = expand_policy_path(legacy_raw, root=root)
            if legacy_root not in candidate_roots:
                candidate_roots.append(legacy_root)
        for legacy_raw in policy.get("legacy_extra_roots", []):
            text = str(legacy_raw or "").strip()
            if not text:
                continue
            legacy_root = expand_policy_path(text, root=root)
            if legacy_root not in candidate_roots:
                candidate_roots.append(legacy_root)
    return candidate_roots


def _orphan_sidecar_paths(
    *,
    target: Path,
    root: Path,
    policy: dict[str, Any],
) -> list[dict[str, str | int]]:
    candidates: list[dict[str, str | int]] = []
    candidate_roots = _legacy_roots_for_target(target, root=root, policy=policy)
    for legacy_root in candidate_roots:
        try:
            relative_target = target.relative_to(
                expand_policy_path(str(policy["canonical_paths"]["user_state_root"]), root=root)
            )
        except ValueError:
            try:
                relative_target = target.relative_to(
                    expand_policy_path(str(policy["canonical_paths"]["user_cache_root"]), root=root)
                )
            except ValueError:
                continue
        legacy_target = legacy_root / relative_target
        if legacy_target.exists():
            continue
        for legacy_sidecar, target_sidecar in zip(
            _sidecar_paths(legacy_target),
            _sidecar_paths(target),
            strict=False,
        ):
            if not legacy_sidecar.exists():
                continue
            candidates.append(
                {
                    "kind": legacy_sidecar.name.removeprefix(legacy_target.name),
                    "source": str(legacy_sidecar),
                    "target": str(target_sidecar),
                    "size_bytes": size_bytes(legacy_sidecar),
                }
            )
    return candidates


def _build_plan(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    env_path = root / ".env"
    env_assignments = parse_env_assignments(env_path)
    legacy_status = collect_legacy_compatibility(root, policy)
    variables: list[dict[str, Any]] = []
    source_to_keys: dict[str, list[str]] = defaultdict(list)
    canonical_map = _canonical_entry_map(policy)

    for name, entry in canonical_map.items():
        canonical_raw = str(entry["canonical_path"])
        target_path = expand_policy_path(canonical_raw, root=root)
        current_value = env_assignments.get(name)
        source_path = expand_policy_path(current_value, root=root) if current_value else None
        if source_path is not None:
            source_to_keys[str(source_path)].append(name)
        variables.append(
            {
                "name": name,
                "current_value": current_value,
                "source_path": None if source_path is None else str(source_path),
                "source_exists": False if source_path is None else source_path.exists(),
                "canonical_value": canonical_raw,
                "target_path": str(target_path),
                "target_exists": target_path.exists(),
                "path_kind": str(entry["path_kind"]),
                "allow_existing_target": bool(entry.get("allow_existing_target", False)),
                "existing_target_verify_command": list(
                    entry.get("existing_target_verify_command", [])
                ),
                "retire_source_on_migrate": bool(entry.get("retire_source_on_migrate", True)),
                "ownership": str(entry.get("ownership") or ""),
                "orphan_sidecars": [],
            }
        )

    for item in variables:
        reasons: list[str] = []
        source_path = item["source_path"]
        target_path = item["target_path"]
        target = Path(target_path)
        orphan_sidecars = (
            _orphan_sidecar_paths(target=target, root=root, policy=policy)
            if item["path_kind"] == "file" and target.exists()
            else []
        )
        item["orphan_sidecars"] = orphan_sidecars
        if not item["current_value"]:
            reasons.append("missing-local-env-value")
            recommended_action = "missing-local-env-value"
        elif source_path == target_path:
            recommended_action = (
                "retire-legacy-sidecars" if orphan_sidecars else "already-canonical"
            )
        elif item["target_exists"] and not item["allow_existing_target"]:
            reasons.append("target-already-exists")
            recommended_action = "blocked-target-exists"
        elif item["target_exists"] and item["allow_existing_target"]:
            recommended_action = "env-only"
        elif not item["source_exists"]:
            reasons.append("missing-source-path")
            recommended_action = "blocked-missing-source"
        else:
            recommended_action = "move"

        shared_source_keys = source_to_keys.get(str(source_path), []) if source_path else []
        if source_path and len(shared_source_keys) > 1:
            if item["path_kind"] == "directory":
                reasons.append("shared-directory-source")
                recommended_action = "blocked-shared-directory-source"
            else:
                recommended_action = "copy"

        item["shared_source_keys"] = shared_source_keys
        item["recommended_action"] = recommended_action
        item["eligible_for_apply"] = bool(item["current_value"]) and not reasons
        item["reasons"] = reasons

    return {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_root": str(root),
        "env_path": str(env_path),
        "mode": "dry-run",
        "audit_report_path": str(expand_policy_path(str(policy["report_path"]), root=root)),
        "canonical_paths": policy.get("canonical_paths", {}),
        "legacy_compatibility": legacy_status,
        "canonical_capacity": {
            "user_state_root": {
                "path": str(
                    expand_policy_path(str(policy["canonical_paths"]["user_state_root"]), root=root)
                ),
                "exists": expand_policy_path(
                    str(policy["canonical_paths"]["user_state_root"]), root=root
                ).exists(),
            },
            "user_cache_root": {
                "path": str(
                    expand_policy_path(str(policy["canonical_paths"]["user_cache_root"]), root=root)
                ),
                "exists": expand_policy_path(
                    str(policy["canonical_paths"]["user_cache_root"]), root=root
                ).exists(),
            },
        },
        "variables": variables,
    }


def _parse_mapping_specs(raw_values: list[str], root: Path) -> dict[str, tuple[Path, Path]]:
    parsed: dict[str, tuple[Path, Path]] = {}
    for raw in raw_values:
        if "=" not in raw or "::" not in raw:
            raise ValueError(f"invalid mapping `{raw}`; expected KEY=SOURCE::TARGET")
        key, remainder = raw.split("=", 1)
        source_raw, target_raw = remainder.split("::", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid mapping `{raw}`; missing key")
        parsed[key] = (
            expand_policy_path(source_raw.strip(), root=root),
            expand_policy_path(target_raw.strip(), root=root),
        )
    return parsed


def _default_mappings_from_plan(
    plan: dict[str, Any],
    *,
    root: Path,
) -> dict[str, tuple[Path, Path]]:
    mappings: dict[str, tuple[Path, Path]] = {}
    for item in plan["variables"]:
        current_value = str(item.get("current_value") or "").strip()
        source_path = str(item.get("source_path") or "").strip()
        target_path = str(item.get("target_path") or "").strip()
        if not current_value or not source_path or not target_path:
            continue
        if source_path == target_path and not item.get("orphan_sidecars"):
            continue
        mappings[str(item["name"])] = (
            expand_policy_path(current_value, root=root),
            expand_policy_path(target_path, root=root),
        )
    return mappings


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    if not command:
        return (True, "")
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    detail = "\n".join(
        part for part in (result.stdout.strip(), result.stderr.strip()) if part
    ).strip()
    return (result.returncode == 0, detail)


def _stage_path(target: Path) -> Path:
    return target.parent / f".{target.name}.migration-stage-{uuid4().hex}"


def _sidecar_paths(path: Path) -> list[Path]:
    return [Path(f"{path}{suffix}") for suffix in SQLITE_SIDECAR_SUFFIXES]


def _rollback_migration(
    *,
    promoted_ops: list[dict[str, Any]],
    staged_ops: list[dict[str, Any]],
) -> None:
    for operation in reversed(promoted_ops):
        for item in reversed(list(operation.get("paths") or [])):
            target = Path(item["target"])
            source = Path(item["source"])
            if target.exists():
                if source.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink(missing_ok=True)
                else:
                    target.replace(source)
    for operation in reversed(staged_ops):
        for item in reversed(list(operation.get("paths") or [])):
            staging = Path(item["staging"])
            source = Path(item["source"])
            if staging.exists():
                if source.exists():
                    if staging.is_dir():
                        shutil.rmtree(staging)
                    else:
                        staging.unlink(missing_ok=True)
                else:
                    staging.replace(source)


def _prune_empty_dir(path: Path, *, stop_before: Path) -> None:
    current = path
    while current != stop_before and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _prune_empty_tree(root_path: Path) -> None:
    if not root_path.exists() or not root_path.is_dir():
        return
    for child in sorted(root_path.rglob("*"), reverse=True):
        if not child.is_dir():
            continue
        try:
            child.rmdir()
        except OSError:
            continue
    try:
        root_path.rmdir()
    except OSError:
        return


def _cleanup_orphan_sqlite_sidecars(
    *,
    root: Path,
    policy: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    canonical_sqlite_targets: dict[str, tuple[str, Path]] = {}
    for item in plan["variables"]:
        if str(item.get("path_kind")) != "file":
            continue
        target_path = Path(str(item.get("target_path") or ""))
        if not target_path.name.endswith(".db"):
            continue
        canonical_sqlite_targets[target_path.name] = (str(item["name"]), target_path)

    if not canonical_sqlite_targets:
        return []

    legacy_roots: list[Path] = []
    canonical_paths = dict(policy.get("canonical_paths") or {})
    for key in ("legacy_state_root", "legacy_cache_root"):
        value = str(canonical_paths.get(key) or "").strip()
        if not value:
            continue
        path = expand_policy_path(value, root=root)
        if path not in legacy_roots:
            legacy_roots.append(path)
    for raw in policy.get("legacy_extra_roots", []):
        value = str(raw or "").strip()
        if not value:
            continue
        path = expand_policy_path(value, root=root)
        if path not in legacy_roots:
            legacy_roots.append(path)

    actions: list[dict[str, Any]] = []
    for legacy_root in legacy_roots:
        if not legacy_root.exists():
            continue
        for suffix in SQLITE_SIDECAR_SUFFIXES:
            for sidecar in legacy_root.rglob(f"*{suffix}"):
                sqlite_name = sidecar.name.removesuffix(suffix)
                target_entry = canonical_sqlite_targets.get(sqlite_name)
                if target_entry is None:
                    continue
                variable, canonical_target = target_entry
                if not canonical_target.exists():
                    actions.append(
                        {
                            "variable": variable,
                            "status": "kept-orphan-sidecar-missing-canonical-target",
                            "path": str(sidecar),
                            "canonical_target": str(canonical_target),
                        }
                    )
                    continue

                lsof_state, lsof_lines = lsof_hits(sidecar.parent)
                if lsof_state != "clear":
                    actions.append(
                        {
                            "variable": variable,
                            "status": "kept-orphan-sidecar-busy",
                            "path": str(sidecar),
                            "canonical_target": str(canonical_target),
                            "lsof_state": lsof_state,
                            "lsof_detail": "; ".join(lsof_lines),
                        }
                    )
                    continue

                sidecar.unlink(missing_ok=True)
                actions.append(
                    {
                        "variable": variable,
                        "status": "deleted-orphan-sidecar",
                        "path": str(sidecar),
                        "canonical_target": str(canonical_target),
                        "kind": suffix.removeprefix("-"),
                    }
                )
                _prune_empty_dir(sidecar.parent, stop_before=legacy_root.parent)
        _prune_empty_tree(legacy_root)
    return actions


def _build_apply_operations(
    *,
    root: Path,
    plan: dict[str, Any],
    mappings: dict[str, tuple[Path, Path]],
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    seen_targets: set[Path] = set()
    for item in plan["variables"]:
        name = str(item["name"])
        if name not in mappings:
            continue
        source, target = mappings[name]
        if str(source) != str(item["source_path"]):
            raise RuntimeError(f"{name}: mapping source does not match current .env value")
        if str(target) != str(item["target_path"]):
            raise RuntimeError(f"{name}: mapping target does not match canonical target")
        if target in seen_targets:
            raise RuntimeError(f"{name}: duplicate target path is not allowed: {target}")
        seen_targets.add(target)

        shared_source_keys = list(item.get("shared_source_keys") or [])
        if len(shared_source_keys) > 1:
            if set(shared_source_keys) == {"SQLITE_PATH", "SQLITE_STATE_PATH"}:
                raise RuntimeError(
                    "shared SQLite source is not safe to auto-split; migrate it manually with an explicit runbook"
                )
            raise RuntimeError(
                f"{name}: shared source is not supported for automatic migration ({', '.join(shared_source_keys)})"
            )

        if not item["current_value"]:
            raise RuntimeError(f"{name}: missing local .env value")

        if str(source) == str(target):
            orphan_sidecars = list(item.get("orphan_sidecars") or [])
            if orphan_sidecars:
                operation_paths = []
                for orphan in orphan_sidecars:
                    target_sidecar = Path(str(orphan["target"]))
                    if target_sidecar.exists():
                        raise RuntimeError(
                            f"{name}: target sidecar already exists: {target_sidecar}"
                        )
                    operation_paths.append(
                        {
                            "kind": str(orphan["kind"]),
                            "source": str(orphan["source"]),
                            "target": str(orphan["target"]),
                            "staging": str(_stage_path(target_sidecar)),
                            "size_bytes": int(orphan["size_bytes"]),
                        }
                    )
                operations.append(
                    {
                        "variable": name,
                        "mode": "retire-legacy-sidecars",
                        "source": str(source),
                        "target": str(target),
                        "canonical_value": str(item["canonical_value"]),
                        "source_size_bytes": 0,
                        "path_kind": str(item["path_kind"]),
                        "paths": operation_paths,
                    }
                )
            else:
                operations.append(
                    {
                        "variable": name,
                        "mode": "already-canonical",
                        "source": str(source),
                        "target": str(target),
                        "canonical_value": str(item["canonical_value"]),
                    }
                )
            continue

        if not source.exists():
            raise RuntimeError(f"{name}: source path is missing: {source}")

        verify_command = list(item.get("existing_target_verify_command") or [])
        if item["target_exists"]:
            if not bool(item["allow_existing_target"]):
                raise RuntimeError(f"{name}: target already exists: {target}")
            ok, detail = _run_command(
                verify_command,
                cwd=root,
                extra_env={
                    "TARGET_PATH": str(target),
                    "TARGET_VALUE": str(item["canonical_value"]),
                },
            )
            if not ok:
                raise RuntimeError(
                    f"{name}: existing target failed healthcheck: {detail or 'verification command failed'}"
                )
            operations.append(
                {
                    "variable": name,
                    "mode": "env-only-existing-target",
                    "source": str(source),
                    "target": str(target),
                    "canonical_value": str(item["canonical_value"]),
                    "verification_command": verify_command,
                }
            )
            continue

        operations.append(
            {
                "variable": name,
                "mode": "move",
                "source": str(source),
                "target": str(target),
                "canonical_value": str(item["canonical_value"]),
                "source_size_bytes": size_bytes(source),
                "path_kind": str(item["path_kind"]),
                "paths": [
                    {
                        "kind": "primary",
                        "source": str(source),
                        "target": str(target),
                        "staging": str(_stage_path(target)),
                        "size_bytes": size_bytes(source),
                    }
                ],
            }
        )
        if str(item["path_kind"]) == "file":
            for source_sidecar, target_sidecar in zip(
                _sidecar_paths(source),
                _sidecar_paths(target),
                strict=False,
            ):
                if not source_sidecar.exists():
                    continue
                if target_sidecar.exists():
                    raise RuntimeError(f"{name}: target sidecar already exists: {target_sidecar}")
                operations[-1]["paths"].append(
                    {
                        "kind": source_sidecar.name.removeprefix(source.name),
                        "source": str(source_sidecar),
                        "target": str(target_sidecar),
                        "staging": str(_stage_path(target_sidecar)),
                        "size_bytes": size_bytes(source_sidecar),
                    }
                )
    return operations


def _apply_plan(
    *,
    root: Path,
    policy: dict[str, Any],
    plan: dict[str, Any],
    mappings: dict[str, tuple[Path, Path]],
) -> tuple[bool, list[dict[str, Any]]]:
    audit_report_path = Path(str(plan["audit_report_path"]))
    if not audit_report_path.is_file():
        raise RuntimeError("disk-space migration requires an existing disk-space audit report")
    required_keys = {
        item["name"]
        for item in plan["variables"]
        if item["current_value"] and item["source_path"] != item["target_path"]
    }
    missing = sorted(required_keys - set(mappings))
    if missing:
        raise RuntimeError("missing explicit mappings for: " + ", ".join(missing))

    operations = _build_apply_operations(root=root, plan=plan, mappings=mappings)
    actions: list[dict[str, Any]] = []
    env_updates: dict[str, str] = {}
    staged_ops: list[dict[str, Any]] = []
    promoted_ops: list[dict[str, Any]] = []
    try:
        for operation in operations:
            env_updates[operation["variable"]] = operation["canonical_value"]
            if operation["mode"] in {"env-only-existing-target", "already-canonical"}:
                actions.append(
                    {
                        "variable": operation["variable"],
                        "status": operation["mode"],
                        "source": operation["source"],
                        "target": operation["target"],
                    }
                )
                continue

            for path_op in operation.get("paths") or []:
                staging = Path(path_op["staging"])
                source_path = Path(path_op["source"])
                if staging.exists():
                    raise RuntimeError(
                        f"{operation['variable']}: staging path already exists: {staging}"
                    )
                staging.parent.mkdir(parents=True, exist_ok=True)
                source_path.replace(staging)
            staged_ops.append(operation)

        for operation in staged_ops:
            for path_op in operation.get("paths") or []:
                staging = Path(path_op["staging"])
                target = Path(path_op["target"])
                if target.exists():
                    raise RuntimeError(
                        f"{operation['variable']}: target already exists during promote: {target}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                staging.replace(target)
            promoted_ops.append(operation)
            actions.append(
                {
                    "variable": operation["variable"],
                    "status": (
                        "retired-legacy-sidecars"
                        if operation["mode"] == "retire-legacy-sidecars"
                        else "moved"
                    ),
                    "source": operation["source"],
                    "target": operation["target"],
                    "size_human": human_bytes(int(operation["source_size_bytes"])),
                    "moved_companions": [
                        {
                            "kind": str(path_op["kind"]),
                            "target": str(path_op["target"]),
                            "size_human": human_bytes(int(path_op["size_bytes"])),
                        }
                        for path_op in (operation.get("paths") or [])
                        if str(path_op["kind"]) != "primary"
                    ],
                }
            )

        update_env_assignments(root / ".env", env_updates)
        actions.extend(_cleanup_orphan_sqlite_sidecars(root=root, policy=policy, plan=plan))
    except Exception:
        _rollback_migration(promoted_ops=promoted_ops, staged_ops=staged_ops)
        raise

    refreshed_plan = _build_plan(root, policy)
    plan["legacy_compatibility"] = refreshed_plan["legacy_compatibility"]
    plan["canonical_capacity"] = refreshed_plan["canonical_capacity"]
    return (True, actions)


def _render_text(report: dict[str, Any]) -> str:
    lines = [
        "[disk-space-legacy-migration] " + ("APPLY" if report["mode"] == "apply" else "DRY-RUN"),
        "legacy-retirement-blocked: "
        + str(report["legacy_compatibility"]["legacy_retirement_blocked"]).lower(),
    ]
    for item in report["variables"]:
        lines.append(
            f"variable: {item['name']} | action={item['recommended_action']} | eligible={str(item['eligible_for_apply']).lower()}"
        )
        if item["current_value"]:
            lines.append(f"  source: {item['current_value']}")
        lines.append(f"  target: {item['canonical_value']}")
        if item["reasons"]:
            lines.append("  reasons: " + ", ".join(item["reasons"]))
    for action in report.get("actions", []):
        lines.append(
            "action: "
            + action.get("variable", action.get("source", "unknown"))
            + f" | status={action['status']}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect or migrate legacy SourceHarbor disk paths into canonical roots."
    )
    parser.add_argument("--repo-root", default=str(repo_root()))
    parser.add_argument("--policy", default="")
    parser.add_argument("--mapping", action="append", default=[])
    parser.add_argument(
        "--auto-mappings",
        action="store_true",
        help="Use the current .env values as migration sources and canonical targets from policy.",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", default="")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    policy = load_policy(root, args.policy or None)
    report = _build_plan(root, policy)

    if args.apply:
        if not args.yes:
            parser.error("--apply requires --yes")
        try:
            if args.mapping:
                mappings = _parse_mapping_specs(list(args.mapping), root)
            elif args.auto_mappings:
                mappings = _default_mappings_from_plan(report, root=root)
            else:
                raise ValueError("apply mode requires --mapping ... or --auto-mappings")
        except ValueError as exc:
            print(f"[disk-space-legacy-migration] FAIL: {exc}", file=sys.stderr)
            return 1
        report["mode"] = "apply"
        try:
            ok, actions = _apply_plan(root=root, policy=policy, plan=report, mappings=mappings)
        except RuntimeError as exc:
            print(f"[disk-space-legacy-migration] FAIL: {exc}", file=sys.stderr)
            return 1
        report["actions"] = actions
        refreshed_audit = build_report(root, policy)
        audit_path = str(policy["report_path"])
        write_report(root, audit_path, refreshed_audit, scope="report_disk_space")
        report["legacy_compatibility"] = refreshed_audit["legacy_compatibility"]
        report["governance"] = refreshed_audit["governance"]
        report["audit_report_path"] = str(expand_policy_path(audit_path, root=root))
        output_path = args.write_report or str(policy["migration_report_path"])
        write_report(root, output_path, report, scope="legacy_disk_migration")
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(_render_text(report))
        return 0 if ok else 1

    output_path = args.write_report or str(policy["migration_report_path"])
    write_report(root, output_path, report, scope="legacy_disk_migration")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
