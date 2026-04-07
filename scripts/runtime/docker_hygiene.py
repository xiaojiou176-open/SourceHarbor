#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from disk_space_common import load_policy, repo_root

ROOT = repo_root()
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_json_artifact


def _docker_path() -> str | None:
    return shutil.which("docker")


def _run_docker(*args: str) -> subprocess.CompletedProcess[str]:
    docker_path = _docker_path()
    if docker_path is None:
        raise RuntimeError("docker binary missing")
    return subprocess.run(
        [docker_path, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _docker_ready() -> tuple[bool, str]:
    docker_path = _docker_path()
    if docker_path is None:
        return False, "docker_binary_missing"
    result = _run_docker("info")
    if result.returncode != 0:
        detail = " ".join(result.stderr.split()) or "docker daemon unavailable"
        return False, detail
    return True, ""


def _parse_json_list(text: str) -> list[dict[str, Any]]:
    payload = json.loads(text)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _parse_timestamp(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _age_hours(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return max(0.0, (datetime.now(UTC) - dt).total_seconds() / 3600.0)


def _collect_containers(prefixes: list[str]) -> list[dict[str, Any]]:
    result = _run_docker(
        "ps",
        "-a",
        "--format",
        "{{json .}}",
    )
    if result.returncode != 0:
        return []
    containers: list[dict[str, Any]] = []
    for raw_line in result.stdout.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        names = str(payload.get("Names") or "")
        if not any(names.startswith(prefix) for prefix in prefixes):
            continue
        containers.append(
            {
                "id": str(payload.get("ID") or ""),
                "name": names,
                "image": str(payload.get("Image") or ""),
                "status": str(payload.get("Status") or ""),
                "state": str(payload.get("State") or ""),
                "created_at": str(payload.get("CreatedAt") or ""),
            }
        )
    return containers


def _collect_networks(prefixes: list[str]) -> list[dict[str, Any]]:
    result = _run_docker("network", "ls", "--format", "{{json .}}")
    if result.returncode != 0:
        return []
    networks: list[dict[str, Any]] = []
    for raw_line in result.stdout.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        name = str(payload.get("Name") or "")
        if not any(name.startswith(prefix) for prefix in prefixes):
            continue
        inspect = _run_docker("network", "inspect", name)
        attached_count = None
        if inspect.returncode == 0:
            try:
                network_payload = _parse_json_list(inspect.stdout)
                containers = (
                    dict(network_payload[0].get("Containers") or {}) if network_payload else {}
                )
                attached_count = len(containers)
            except Exception:
                attached_count = None
        networks.append(
            {
                "id": str(payload.get("ID") or ""),
                "name": name,
                "driver": str(payload.get("Driver") or ""),
                "attached_container_count": attached_count,
            }
        )
    return networks


def _collect_attached_containers(*, filter_value: str, filter_kind: str) -> list[dict[str, Any]]:
    result = _run_docker(
        "ps",
        "-a",
        "--filter",
        f"{filter_kind}={filter_value}",
        "--format",
        "{{json .}}",
    )
    if result.returncode != 0:
        return []
    attached: list[dict[str, Any]] = []
    for raw_line in result.stdout.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        attached.append(
            {
                "id": str(payload.get("ID") or ""),
                "name": str(payload.get("Names") or ""),
                "image": str(payload.get("Image") or ""),
                "status": str(payload.get("Status") or ""),
                "state": str(payload.get("State") or ""),
                "created_at": str(payload.get("CreatedAt") or ""),
            }
        )
    return attached


def _collect_volumes(volume_names: list[str]) -> list[dict[str, Any]]:
    volumes: list[dict[str, Any]] = []
    for volume_name in volume_names:
        result = _run_docker("volume", "inspect", volume_name)
        if result.returncode != 0:
            volumes.append(
                {
                    "name": volume_name,
                    "exists": False,
                    "cleanup_policy": "verify-first-report-only",
                    "cleanup_eligible": False,
                }
            )
            continue

        payload = _parse_json_list(result.stdout)
        data = payload[0] if payload else {}
        attached = _collect_attached_containers(filter_value=volume_name, filter_kind="volume")
        volumes.append(
            {
                "name": volume_name,
                "exists": True,
                "mountpoint": str(data.get("Mountpoint") or ""),
                "created_at": str(data.get("CreatedAt") or ""),
                "labels": dict(data.get("Labels") or {}),
                "attached_containers": attached,
                "attached_container_count": len(attached),
                "cleanup_policy": "verify-first-report-only",
                "cleanup_eligible": False,
                "cleanup_blockers": (
                    ["named-volume-cleanup-not-enabled"]
                    + (["attached-containers-present"] if attached else [])
                ),
            }
        )
    return volumes


def _collect_images(image_refs: list[str], *, quiet_hours: int) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    for image_ref in image_refs:
        result = _run_docker("image", "inspect", image_ref)
        if result.returncode != 0:
            images.append(
                {
                    "ref": image_ref,
                    "exists": False,
                    "cleanup_eligible": False,
                    "cleanup_blockers": ["image-missing"],
                }
            )
            continue
        payload = _parse_json_list(result.stdout)
        image_payload = payload[0] if payload else {}
        repo_tags = list(image_payload.get("RepoTags") or [])
        created_at = _parse_timestamp(str(image_payload.get("Created") or ""))
        metadata = dict(image_payload.get("Metadata") or {})
        last_tag_time = _parse_timestamp(str(metadata.get("LastTagTime") or ""))
        attached = _collect_attached_containers(filter_value=image_ref, filter_kind="ancestor")
        latest_activity = max(
            [dt for dt in (created_at, last_tag_time) if dt is not None],
            default=None,
        )
        latest_activity_age_hours = _age_hours(latest_activity)
        quiet_ok = bool(
            latest_activity_age_hours is not None and latest_activity_age_hours >= quiet_hours
        )
        cleanup_blockers: list[str] = []
        if attached:
            cleanup_blockers.append("referenced-by-container")
        if latest_activity is None:
            cleanup_blockers.append("missing-image-activity-timestamp")
        elif not quiet_ok:
            cleanup_blockers.append("image-quiet-window-not-reached")
        images.append(
            {
                "ref": image_ref,
                "exists": True,
                "repo_tags": repo_tags,
                "created_at": _iso(created_at),
                "last_tag_time": _iso(last_tag_time),
                "latest_activity_at": _iso(latest_activity),
                "latest_activity_age_hours": latest_activity_age_hours,
                "quiet_hours": quiet_hours,
                "quiet_ok": quiet_ok,
                "attached_containers": attached,
                "attached_container_count": len(attached),
                "cleanup_eligible": not cleanup_blockers,
                "cleanup_blockers": cleanup_blockers,
            }
        )
    return images


def _apply_cleanup(
    containers: list[dict[str, Any]],
    networks: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for container in containers:
        if container.get("state") == "running":
            continue
        result = _run_docker("rm", "-f", str(container["id"]))
        actions.append(
            {
                "kind": "container",
                "target": container["name"],
                "status": "deleted" if result.returncode == 0 else "failed",
                "detail": (result.stderr or result.stdout).strip(),
            }
        )
    for network in networks:
        attached = network.get("attached_container_count")
        if attached not in {0, None}:
            continue
        result = _run_docker("network", "rm", str(network["name"]))
        actions.append(
            {
                "kind": "network",
                "target": network["name"],
                "status": "deleted" if result.returncode == 0 else "failed",
                "detail": (result.stderr or result.stdout).strip(),
            }
        )
    for image in images:
        if not image.get("exists") or not image.get("cleanup_eligible"):
            continue
        result = _run_docker("image", "rm", "-f", str(image["ref"]))
        actions.append(
            {
                "kind": "image",
                "target": image["ref"],
                "status": "deleted" if result.returncode == 0 else "failed",
                "detail": (result.stderr or result.stdout).strip(),
            }
        )
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report or clean repo-owned Docker residue for SourceHarbor without touching global Docker cache."
    )
    parser.add_argument("--repo-root", default=str(repo_root()))
    parser.add_argument("--policy", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    policy = load_policy(root, args.policy or None)
    config = dict(policy.get("docker_hygiene") or {})
    report_path = root / str(
        config.get("report_path") or ".runtime-cache/reports/governance/docker-hygiene.json"
    )
    prefixes = [str(item) for item in config.get("repo_container_prefixes", [])]
    network_prefixes = [str(item) for item in config.get("repo_network_prefixes", [])]
    image_refs = [str(item) for item in config.get("repo_local_debug_images", [])]
    volume_names = [
        str(item)
        for item in config.get("repo_named_volumes", policy.get("docker_named_volumes", []))
    ]
    local_debug_image_quiet_hours = int(config.get("local_debug_image_quiet_hours") or 24)

    ok, detail = _docker_ready()
    report: dict[str, Any] = {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_root": str(root),
        "mode": "apply" if args.apply else "audit",
        "status": "pass",
        "docker_ready": ok,
        "detail": detail,
        "containers": [],
        "networks": [],
        "volumes": [],
        "images": [],
        "actions": [],
    }

    if ok:
        report["containers"] = _collect_containers(prefixes)
        report["networks"] = _collect_networks(network_prefixes)
        report["volumes"] = _collect_volumes(volume_names)
        report["images"] = _collect_images(
            image_refs,
            quiet_hours=local_debug_image_quiet_hours,
        )
        if args.apply:
            report["actions"] = _apply_cleanup(
                report["containers"], report["networks"], report["images"]
            )
        if any(item.get("state") == "running" for item in report["containers"]):
            report["status"] = "warn"
    else:
        report["status"] = "unverified"

    write_json_artifact(
        report_path,
        report,
        source_entrypoint="scripts/runtime/docker_hygiene.py",
        verification_scope="docker-hygiene",
        source_run_id="docker-hygiene",
        freshness_window_hours=24,
        extra={"report_kind": "docker-hygiene", "mode": report["mode"]},
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"[docker-hygiene] {report['status'].upper()}")
    print(f"  - report={report_path}")
    if detail:
        print(f"  - detail={detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
