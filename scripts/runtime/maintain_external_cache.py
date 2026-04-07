#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from disk_space_common import (
    collect_reference_hits,
    expand_policy_path,
    human_bytes,
    is_quiet_for_minutes,
    load_policy,
    lsof_hits,
    path_size_and_latest_mtime,
    remove_path,
    repo_root,
    resolve_candidate_paths,
)

ROOT = repo_root()

if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_json_artifact


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _age_hours(latest_mtime: float | None) -> float | None:
    if latest_mtime is None:
        return None
    return max(0.0, (_now().timestamp() - latest_mtime) / 3600.0)


def _load_maintenance_config(policy: dict[str, Any]) -> dict[str, Any]:
    payload = dict(policy.get("external_cache_maintenance") or {})
    groups = payload.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise RuntimeError("disk-space-governance.json missing external_cache_maintenance.groups")
    return payload


def _stamp_path(root: Path, config: dict[str, Any]) -> Path:
    raw = str(config.get("stamp_path") or "").strip()
    if not raw:
        raise RuntimeError("external_cache_maintenance.stamp_path is required")
    return expand_policy_path(raw, root=root)


def _report_path(root: Path, config: dict[str, Any]) -> Path:
    raw = str(config.get("report_path") or "").strip()
    if not raw:
        raise RuntimeError("external_cache_maintenance.report_path is required")
    return expand_policy_path(raw, root=root)


def _reference_hits_for_duplicate_env(root: Path, path: Path, policy: dict[str, Any]) -> list[str]:
    duplicate_policy = dict(policy.get("duplicate_env_policy") or {})
    reference_files = [str(item) for item in duplicate_policy.get("reference_files", [])]
    if not reference_files:
        return []
    markers = {
        path.name,
        str(path),
    }
    home = str(Path.home())
    raw_path = str(path)
    if raw_path.startswith(home):
        markers.add(raw_path.replace(home, "$HOME", 1))
        markers.add(raw_path.replace(home, "~", 1))
    return collect_reference_hits(root, sorted(markers), reference_files)


def _collect_group_entries(
    *,
    root: Path,
    policy: dict[str, Any],
    group_name: str,
    group_config: dict[str, Any],
) -> dict[str, Any]:
    kind = str(group_config.get("kind") or group_name)
    ttl_days = int(group_config.get("ttl_days") or 0)
    ttl_hours = ttl_days * 24
    quiet_minutes = int(group_config.get("quiet_minutes") or 0)
    max_total_size_mb = int(group_config.get("max_total_size_mb") or 0)
    budget_bytes = max_total_size_mb * 1024 * 1024 if max_total_size_mb > 0 else None
    requires_lsof_clear = bool(group_config.get("requires_lsof_clear"))
    path_value = str(group_config.get("path") or "").strip()
    path_glob = str(group_config.get("path_glob") or "").strip()

    if path_value:
        raw_paths = [expand_policy_path(path_value, root=root)]
    elif path_glob:
        raw_paths = resolve_candidate_paths(path_glob, root=root)
    else:
        raise RuntimeError(f"external cache group `{group_name}` missing path/path_glob")

    entries: list[dict[str, Any]] = []
    for path in raw_paths:
        if not path.exists():
            continue

        size_bytes, latest_mtime = path_size_and_latest_mtime(path)
        age_hours = _age_hours(latest_mtime)
        quiet_ok = True
        quiet_detail = ""
        if quiet_minutes > 0:
            quiet_ok, age_minutes = is_quiet_for_minutes(path, quiet_minutes)
            quiet_detail = "" if age_minutes is None else f"{age_minutes:.1f}m since latest change"

        lsof_state = "not-required"
        lsof_detail = ""
        lsof_ok = True
        if requires_lsof_clear:
            lsof_state, lsof_lines = lsof_hits(path)
            lsof_ok = lsof_state == "clear"
            lsof_detail = "" if not lsof_lines else "; ".join(lsof_lines)

        reference_hits: list[str] = []
        reference_clear = True
        if kind == "duplicate-env":
            reference_hits = _reference_hits_for_duplicate_env(root, path, policy)
            reference_clear = not reference_hits

        ttl_expired = bool(age_hours is not None and ttl_hours > 0 and age_hours >= ttl_hours)
        budget_eviction_eligible = quiet_ok and lsof_ok and reference_clear
        ttl_delete_eligible = ttl_expired and budget_eviction_eligible

        entries.append(
            {
                "path": str(path),
                "size_bytes": size_bytes,
                "size_human": human_bytes(size_bytes),
                "latest_mtime": None
                if latest_mtime is None
                else _iso(datetime.fromtimestamp(latest_mtime, UTC)),
                "age_hours": age_hours,
                "ttl_days": ttl_days if ttl_days > 0 else None,
                "quiet_minutes": quiet_minutes if quiet_minutes > 0 else None,
                "quiet_ok": quiet_ok,
                "quiet_detail": quiet_detail,
                "lsof_state": lsof_state,
                "lsof_ok": lsof_ok,
                "lsof_detail": lsof_detail,
                "reference_hits": reference_hits,
                "reference_clear": reference_clear,
                "ttl_expired": ttl_expired,
                "ttl_delete_eligible": ttl_delete_eligible,
                "budget_eviction_eligible": budget_eviction_eligible,
                "selected_reason": None,
            }
        )

    entries.sort(
        key=lambda item: (
            item["age_hours"] is None,
            item["age_hours"] if item["age_hours"] is not None else -1,
            item["path"],
        ),
        reverse=True,
    )

    total_size = sum(int(item["size_bytes"]) for item in entries)
    remaining_size = total_size
    selected_paths: set[str] = set()
    for item in entries:
        if item["ttl_delete_eligible"]:
            item["selected_reason"] = "ttl-expired"
            remaining_size -= int(item["size_bytes"])
            selected_paths.add(str(item["path"]))

    if budget_bytes is not None and remaining_size > budget_bytes:
        for item in entries:
            if remaining_size <= budget_bytes:
                break
            if str(item["path"]) in selected_paths or not item["budget_eviction_eligible"]:
                continue
            item["selected_reason"] = "budget-eviction"
            remaining_size -= int(item["size_bytes"])
            selected_paths.add(str(item["path"]))

    protected = kind in {"protected-mainline", "protected-state"}
    status = "pass"
    if (
        protected
        and budget_bytes is not None
        and total_size > budget_bytes
        or any(item["selected_reason"] for item in entries)
    ):
        status = "warn"

    return {
        "kind": kind,
        "path": path_value or path_glob,
        "protected": protected,
        "ttl_days": ttl_days if ttl_days > 0 else None,
        "quiet_minutes": quiet_minutes if quiet_minutes > 0 else None,
        "requires_lsof_clear": requires_lsof_clear,
        "budget_bytes": budget_bytes,
        "budget_human": human_bytes(budget_bytes),
        "total_size_bytes": total_size,
        "total_size_human": human_bytes(total_size),
        "status": status,
        "entries": entries,
    }


def _apply_group_actions(groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for group_name, payload in groups.items():
        for item in payload.get("entries", []):
            reason = item.get("selected_reason")
            if not reason:
                continue
            path = Path(str(item["path"]))
            if not path.exists():
                actions.append({"group": group_name, "path": str(path), "status": "missing"})
                continue
            remove_path(path)
            actions.append(
                {
                    "group": group_name,
                    "path": str(path),
                    "status": "deleted",
                    "reason": reason,
                }
            )
    return actions


def _write_stamp(path: Path, *, report_path: Path, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_run_at": _iso(_now()),
                "mode": mode,
                "report_path": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _auto_run_allowed(stamp_path: Path, interval_minutes: int) -> bool:
    if not stamp_path.is_file():
        return True
    try:
        payload = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return True
    last_run_at = str(payload.get("last_run_at") or "").strip()
    if not last_run_at:
        return True
    last_dt = datetime.fromisoformat(last_run_at.replace("Z", "+00:00")).astimezone(UTC)
    age_minutes = max(0.0, (_now() - last_dt).total_seconds() / 60.0)
    return age_minutes >= interval_minutes


def _render_report(
    *,
    root: Path,
    policy: dict[str, Any],
    config: dict[str, Any],
    mode: str,
    skipped_auto: bool,
    groups: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    total_selected_bytes = 0
    for payload in groups.values():
        for item in payload.get("entries", []):
            if item.get("selected_reason"):
                total_selected_bytes += int(item["size_bytes"])
    cache_root = expand_policy_path(str(policy["canonical_paths"]["user_cache_root"]), root=root)
    return {
        "version": 1,
        "generated_at": _iso(_now()),
        "repo_root": str(root),
        "cache_root": str(cache_root),
        "mode": mode,
        "skipped_auto": skipped_auto,
        "selected_total_bytes": total_selected_bytes,
        "selected_total_human": human_bytes(total_selected_bytes),
        "groups": groups,
        "actions": actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit and optionally maintain repo-owned external cache/state under ~/.cache/sourceharbor."
    )
    parser.add_argument("--repo-root", default=str(repo_root()))
    parser.add_argument("--policy", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    policy = load_policy(root, args.policy or None)
    config = _load_maintenance_config(policy)
    report_path = _report_path(root, config)
    stamp_path = _stamp_path(root, config)

    if args.auto:
        interval_minutes = int(config.get("auto_interval_minutes") or 60)
        if not _auto_run_allowed(stamp_path, interval_minutes):
            print("[external-cache-maintenance] SKIP")
            print("  - reason=throttled")
            return 0

    groups: dict[str, dict[str, Any]] = {}
    for group_name, group_config in dict(config.get("groups") or {}).items():
        groups[group_name] = _collect_group_entries(
            root=root,
            policy=policy,
            group_name=str(group_name),
            group_config=dict(group_config or {}),
        )

    actions: list[dict[str, Any]] = []
    mode = "apply" if args.apply else "dry-run"
    if args.apply:
        actions = _apply_group_actions(groups)

    report = _render_report(
        root=root,
        policy=policy,
        config=config,
        mode=mode,
        skipped_auto=False,
        groups=groups,
        actions=actions,
    )
    write_json_artifact(
        report_path,
        report,
        source_entrypoint="scripts/runtime/maintain_external_cache.py",
        verification_scope="external-cache-maintenance",
        source_run_id="external-cache-maintenance",
        freshness_window_hours=24,
        extra={"report_kind": "external-cache-maintenance", "mode": mode},
    )
    if args.apply or args.auto:
        _write_stamp(stamp_path, report_path=report_path, mode=mode)

    status = "PASS"
    if any(payload.get("status") == "warn" for payload in groups.values()):
        status = "WARN"

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"[external-cache-maintenance] {status}")
    print(f"  - report={report_path}")
    print(f"  - selected_total={report['selected_total_human']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
