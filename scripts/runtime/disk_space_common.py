#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in os.sys.path:
    os.sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import rel_path, write_json_artifact

SCAN_REFERENCE_SUFFIXES = {
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".service",
    ".conf",
    ".toml",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    "",
}

ENV_ASSIGN_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
ENV_REF_RE = re.compile(r"\$(\w+)|\$\{([^}]+)\}")


def repo_root() -> Path:
    return ROOT


def _expand_env_value(raw_value: str, resolved: dict[str, str]) -> str:
    merged = dict(os.environ)
    merged.update(resolved)

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1) or match.group(2) or ""
        return merged.get(key, match.group(0))

    value = raw_value
    for _ in range(5):
        expanded = ENV_REF_RE.sub(_replace, value)
        expanded = os.path.expanduser(expanded)
        if expanded == value:
            return expanded
        value = expanded
    return value


def expand_policy_path(raw_path: str, *, root: Path) -> Path:
    expanded = os.path.expandvars(raw_path)
    expanded = os.path.expanduser(expanded)
    candidate = Path(expanded)
    if candidate.is_absolute():
        return candidate.resolve()
    return (root / candidate).resolve()


def has_glob_tokens(raw_path: str) -> bool:
    return any(token in raw_path for token in ("*", "?", "["))


def resolve_candidate_paths(
    raw_path: str,
    *,
    root: Path,
    exclude_globs: list[str] | None = None,
) -> list[Path]:
    exclude_globs = exclude_globs or []
    expanded = os.path.expandvars(raw_path)
    expanded = os.path.expanduser(expanded)
    raw = Path(expanded)
    if not has_glob_tokens(expanded):
        resolved = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
        return [resolved]

    pattern = expanded if raw.is_absolute() else str(root / expanded)
    matches = sorted(Path(path).resolve() for path in glob.glob(pattern, recursive=True))
    filtered: list[Path] = []
    for path in matches:
        rel = rel_path(path)
        if any(fnmatch(rel, glob) for glob in exclude_globs):
            continue
        filtered.append(path)
    return filtered


def resolve_explicit_paths(raw_paths: list[str], *, root: Path) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw_path in raw_paths:
        for path in resolve_candidate_paths(raw_path, root=root):
            if path in seen:
                continue
            seen.add(path)
            resolved.append(path)
    return resolved


def rel_path_from(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def safe_stat(path: Path) -> os.stat_result | None:
    try:
        return path.stat()
    except OSError:
        return None


def path_size_and_latest_mtime(path: Path) -> tuple[int, float | None]:
    if not path.exists():
        return 0, None
    stat = safe_stat(path)
    if stat is None:
        return 0, None
    latest = stat.st_mtime
    if path.is_symlink() or path.is_file():
        return int(stat.st_size), latest

    total = 0
    for item in path.rglob("*"):
        item_stat = safe_stat(item)
        if item_stat is None:
            continue
        latest = max(latest, item_stat.st_mtime)
        if item.is_symlink() or item.is_dir():
            continue
        total += int(item_stat.st_size)
    return total, latest


def latest_mtime(path: Path) -> float | None:
    _, latest = path_size_and_latest_mtime(path)
    return latest


def isoformat_mtime(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return (
        datetime.fromtimestamp(timestamp, UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def size_bytes(path: Path) -> int:
    total, _ = path_size_and_latest_mtime(path)
    return total


def human_bytes(total_bytes: int | None) -> str:
    if total_bytes is None:
        return "unknown"
    value = float(total_bytes)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} TiB"


def load_policy(root: Path, policy_path: str | None = None) -> dict[str, Any]:
    resolved = (
        expand_policy_path(policy_path, root=root)
        if policy_path
        else root / "config" / "governance" / "disk-space-governance.json"
    )
    return json.loads(resolved.read_text(encoding="utf-8"))


def parse_env_assignments(path: Path) -> dict[str, str]:
    assignments: dict[str, str] = {}
    if not path.is_file():
        return assignments
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = ENV_ASSIGN_RE.match(raw_line)
        if match is None:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        try:
            parts = shlex.split(value, posix=True)
        except ValueError:
            assignments[key] = _expand_env_value(value, assignments)
            continue
        normalized = parts[0] if len(parts) == 1 else value
        assignments[key] = _expand_env_value(normalized, assignments)
    return assignments


def render_env_export(name: str, value: str) -> str:
    return f"export {name}={json.dumps(value)}"


def update_env_assignments(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    rewritten: list[str] = []
    seen: set[str] = set()
    for line in lines:
        match = ENV_ASSIGN_RE.match(line)
        if match is None:
            rewritten.append(line)
            continue
        key = match.group(1)
        if key not in updates:
            rewritten.append(line)
            continue
        rewritten.append(render_env_export(key, updates[key]))
        seen.add(key)
    for key, value in updates.items():
        if key not in seen:
            rewritten.append(render_env_export(key, value))
    content = "\n".join(rewritten) + ("\n" if rewritten else "")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def layer_totals(entries: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for item in entries:
        layer = str(item["layer"])
        totals[layer] = totals.get(layer, 0) + int(item.get("size_bytes") or 0)
    return totals


def write_report(root: Path, path_value: str, payload: dict[str, Any], *, scope: str) -> Path:
    path = expand_policy_path(path_value, root=root)
    return write_json_artifact(
        path,
        payload,
        source_entrypoint=f"scripts/runtime/{scope}.py",
        verification_scope=scope,
        source_run_id=f"{scope}-report",
        freshness_window_hours=24,
        extra={"report_kind": scope},
    )


def _legacy_markers(policy: dict[str, Any]) -> list[str]:
    markers = ["video-digestor"]
    canonical_paths = dict(policy.get("canonical_paths", {}))
    for key in ("legacy_state_root", "legacy_cache_root"):
        value = str(canonical_paths.get(key) or "").strip()
        if value:
            markers.append(value)
    for value in policy.get("legacy_extra_roots", []):
        text = str(value or "").strip()
        if text:
            markers.append(text)
    return markers


def collect_legacy_compatibility(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    canonical_paths = dict(policy.get("canonical_paths", {}))
    quiet_minutes = int(policy.get("legacy_retirement_quiet_minutes", 1440) or 1440)
    legacy_roots: list[Path] = []
    for key in ("legacy_state_root", "legacy_cache_root"):
        value = str(canonical_paths.get(key) or "").strip()
        if not value:
            continue
        path = expand_policy_path(value, root=root)
        if path not in legacy_roots:
            legacy_roots.append(path)
    for raw_path in policy.get("legacy_extra_roots", []):
        value = str(raw_path or "").strip()
        if not value:
            continue
        path = expand_policy_path(value, root=root)
        if path not in legacy_roots:
            legacy_roots.append(path)

    detected: list[str] = []
    recent: list[str] = []
    for path in legacy_roots:
        if not path.exists():
            continue
        detected.append(rel_path_from(root, path))
        newest = latest_mtime(path)
        if newest is None:
            continue
        age_minutes = max(0.0, (datetime.now(UTC).timestamp() - newest) / 60.0)
        if age_minutes < quiet_minutes:
            recent.append(rel_path_from(root, path))

    markers = _legacy_markers(policy)
    lowered = [marker.lower() for marker in markers]
    env_assignments = parse_env_assignments(root / ".env")
    local_env_refs: list[dict[str, str]] = []
    for key, value in env_assignments.items():
        if not value:
            continue
        if any(marker in value.lower() for marker in lowered):
            local_env_refs.append({"variable": key, "value": value})

    reference_hits = collect_reference_hits(
        root,
        markers,
        list(policy.get("legacy_reference_files", [])),
    )
    non_env_reference_hits = [hit for hit in reference_hits if hit != ".env"]
    return {
        "active_markers_detected": bool(detected or reference_hits),
        "legacy_paths_detected": detected,
        "legacy_paths_recently_active": recent,
        "legacy_paths_referenced_by_local_env": local_env_refs,
        "legacy_reference_hits": reference_hits,
        "legacy_reference_hits_non_env": non_env_reference_hits,
        "legacy_retirement_blocked": bool(recent or local_env_refs or non_env_reference_hits),
        "quiet_minutes": quiet_minutes,
    }


def collect_disk_governance_signals(
    root: Path,
    policy: dict[str, Any],
    entries: list[dict[str, Any]],
    legacy_status: dict[str, Any],
) -> dict[str, Any]:
    runtime_outputs_path = root / "config" / "governance" / "runtime-outputs.json"
    runtime_tmp_budget_bytes: int | None = None
    if runtime_outputs_path.is_file():
        runtime_outputs = json.loads(runtime_outputs_path.read_text(encoding="utf-8"))
        tmp_config = dict(runtime_outputs.get("subdirectories", {}).get("tmp", {}))
        max_total_size_mb = tmp_config.get("max_total_size_mb")
        if isinstance(max_total_size_mb, int):
            runtime_tmp_budget_bytes = max_total_size_mb * 1024 * 1024

    runtime_tmp_entry = next(
        (item for item in entries if str(item.get("id")) == "repo-runtime-tmp"),
        None,
    )
    runtime_tmp_size = (
        int(runtime_tmp_entry.get("size_bytes") or 0) if runtime_tmp_entry is not None else 0
    )

    env_assignments = parse_env_assignments(root / ".env")
    allowed_roots: list[Path] = []
    canonical_paths = dict(policy.get("canonical_paths", {}))
    for key in ("user_state_root", "user_cache_root", "legacy_state_root", "legacy_cache_root"):
        value = str(canonical_paths.get(key) or "").strip()
        if not value:
            continue
        resolved = expand_policy_path(value, root=root)
        if resolved not in allowed_roots:
            allowed_roots.append(resolved)
    unexpected_paths: list[dict[str, str]] = []
    for entry in policy.get("migration_variables", []):
        key = str(entry.get("name") or "").strip()
        value = env_assignments.get(key)
        if not key or not value:
            continue
        resolved = expand_policy_path(value, root=root)
        if not resolved.is_absolute():
            continue
        if any(resolved == allowed or allowed in resolved.parents for allowed in allowed_roots):
            continue
        if str(resolved).startswith(str(root)):
            continue
        unexpected_paths.append({"variable": key, "path": str(resolved)})

    return {
        "runtime_tmp_over_budget": {
            "detected": (
                runtime_tmp_budget_bytes is not None and runtime_tmp_size > runtime_tmp_budget_bytes
            ),
            "size_bytes": runtime_tmp_size,
            "size_human": human_bytes(runtime_tmp_size),
            "budget_bytes": runtime_tmp_budget_bytes,
            "budget_human": human_bytes(runtime_tmp_budget_bytes),
        },
        "legacy_default_write_drift": {
            "detected": bool(legacy_status.get("legacy_reference_hits_non_env")),
            "reference_hits": list(legacy_status.get("legacy_reference_hits_non_env", [])),
        },
        "unexpected_repo_external_paths": {
            "detected": bool(unexpected_paths),
            "paths": unexpected_paths,
        },
    }


def detect_docker_named_volumes(volume_names: list[str]) -> dict[str, Any]:
    docker_path = shutil.which("docker")
    if docker_path is None:
        return {
            "status": "unverified",
            "reason": "docker_binary_missing",
            "volumes": [{"name": name, "status": "unverified"} for name in volume_names],
        }

    info = subprocess.run(
        [docker_path, "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    if info.returncode != 0:
        detail = " ".join(info.stderr.split()) or "docker daemon unavailable"
        return {
            "status": "unverified",
            "reason": "docker_daemon_unavailable",
            "detail": detail,
            "volumes": [{"name": name, "status": "unverified"} for name in volume_names],
        }

    volumes: list[dict[str, Any]] = []
    for name in volume_names:
        inspect = subprocess.run(
            [docker_path, "volume", "inspect", name],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspect.returncode != 0:
            volumes.append({"name": name, "status": "missing"})
            continue
        try:
            payload = json.loads(inspect.stdout)
            mountpoint = str(payload[0].get("Mountpoint") or "")
        except (IndexError, ValueError, KeyError):
            volumes.append({"name": name, "status": "unverified", "reason": "inspect_parse_failed"})
            continue
        size = size_bytes(Path(mountpoint)) if mountpoint else None
        volumes.append(
            {
                "name": name,
                "status": "present",
                "mountpoint": mountpoint,
                "size_bytes": size,
                "size_human": human_bytes(size),
            }
        )
    return {"status": "ok", "volumes": volumes}


def collect_reference_hits(
    root: Path, candidate_markers: list[str], reference_files: list[str]
) -> list[str]:
    hits: list[str] = []
    lowered = [marker.lower() for marker in candidate_markers]
    for rel in reference_files:
        path = expand_policy_path(rel, root=root)
        if not path.exists() or path.is_dir():
            continue
        if path.suffix not in SCAN_REFERENCE_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
        if any(marker in content for marker in lowered):
            hits.append(rel_path_from(root, path))
    return hits


def collect_duplicate_env_groups(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    duplicate_policy = dict(policy.get("duplicate_env_policy") or {})
    canonical_raw = str(duplicate_policy.get("canonical_mainline_path") or "").strip()
    duplicate_glob = str(duplicate_policy.get("duplicate_glob") or "").strip()
    reference_files = [str(item) for item in duplicate_policy.get("reference_files", [])]
    if not canonical_raw or not duplicate_glob:
        return {
            "total_duplicate_size_bytes": 0,
            "total_duplicate_size_human": human_bytes(0),
            "groups": [],
        }

    groups: list[dict[str, Any]] = []
    total_duplicate_size = 0
    canonical_path = expand_policy_path(canonical_raw, root=root)
    entries: list[dict[str, Any]] = []
    duplicate_entries: list[dict[str, Any]] = []
    duplicate_size = 0

    for path in resolve_candidate_paths(duplicate_glob, root=root):
        if not path.exists() or not path.is_dir():
            continue
        is_canonical = path.resolve() == canonical_path.resolve()
        expanded_path = str(path)
        reference_markers = {
            path.name,
            expanded_path,
        }
        home = str(Path.home())
        if expanded_path.startswith(home):
            reference_markers.add(expanded_path.replace(home, "$HOME", 1))
            reference_markers.add(expanded_path.replace(home, "~", 1))
        reference_hits = collect_reference_hits(root, sorted(reference_markers), reference_files)
        reference_status = "canonical-mainline"
        if not is_canonical:
            reference_status = (
                "still-referenced" if reference_hits else "unreferenced-by-known-entrypoints"
            )

        size, latest = path_size_and_latest_mtime(path)
        payload = {
            "path": rel_path_from(root, path),
            "exists": True,
            "size_bytes": size,
            "size_human": human_bytes(size),
            "latest_mtime": isoformat_mtime(latest),
            "is_canonical": is_canonical,
            "reference_status": reference_status,
            "reference_hits": reference_hits,
        }
        entries.append(payload)
        if not is_canonical:
            duplicate_entries.append(payload)
            duplicate_size += size

    if entries:
        total_duplicate_size += duplicate_size
        groups.append(
            {
                "id": "sourceharbor-project-venvs",
                "label": "SourceHarbor project environments",
                "canonical_path": rel_path_from(root, canonical_path),
                "status": "duplicates-detected" if duplicate_entries else "canonical-only",
                "duplicate_size_bytes": duplicate_size,
                "duplicate_size_human": human_bytes(duplicate_size),
                "entries": sorted(
                    entries,
                    key=lambda item: (
                        not bool(item["is_canonical"]),
                        -int(item["size_bytes"]),
                        str(item["path"]),
                    ),
                ),
            }
        )

    return {
        "total_duplicate_size_bytes": total_duplicate_size,
        "total_duplicate_size_human": human_bytes(total_duplicate_size),
        "groups": groups,
    }


def is_quiet_for_minutes(path: Path, minutes: int) -> tuple[bool, float | None]:
    newest = latest_mtime(path)
    if newest is None:
        return False, None
    age_minutes = max(0.0, (datetime.now(UTC).timestamp() - newest) / 60.0)
    return age_minutes >= minutes, age_minutes


def lock_marker_hits(path: Path, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    if not path.exists():
        return hits
    for item in path.iterdir():
        if any(fnmatch(item.name, pattern) for pattern in patterns):
            hits.append(rel_path(item))
    return hits


def explicit_lock_path_hits(raw_paths: list[str], *, root: Path) -> list[str]:
    hits: list[str] = []
    for path in resolve_explicit_paths(raw_paths, root=root):
        if path.exists():
            hits.append(rel_path_from(root, path))
    return hits


def lsof_hits(path: Path) -> tuple[str, list[str]]:
    lsof_path = shutil.which("lsof")
    if lsof_path is None:
        return ("unverified", [])
    result = subprocess.run(
        [lsof_path, "+D", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in {0, 1}:
        return ("unverified", [])
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return ("clear", [])
    return ("busy", lines[1:11])


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path)
