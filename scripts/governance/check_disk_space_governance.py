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

from common import repo_root

ALLOWED_CLEANUP_LAYERS = {"repo-internal", "repo-external-repo-owned"}
ALLOWED_CLEANUP_OWNERSHIP = {"repo-exclusive", "repo-primary"}
REQUIRED_MIGRATION_NAMES = {
    "PIPELINE_ARTIFACT_ROOT",
    "PIPELINE_WORKSPACE_DIR",
    "SQLITE_PATH",
    "SQLITE_STATE_PATH",
    "UV_PROJECT_ENVIRONMENT",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_legacy_root(value: str, legacy_roots: set[str]) -> bool:
    lowered = value.strip().lower()
    return any(root and root in lowered for root in legacy_roots)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate SourceHarbor disk-space governance contract and canonical defaults."
    )
    parser.add_argument("--repo-root", default=str(repo_root()))
    parser.add_argument("--policy", default="config/governance/disk-space-governance.json")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = (root / policy_path).resolve()
    policy = _load_json(policy_path)
    errors: list[str] = []

    required_top_level = {
        "version",
        "report_path",
        "cleanup_report_path",
        "migration_report_path",
        "legacy_retirement_quiet_minutes",
        "canonical_paths",
        "legacy_extra_roots",
        "duplicate_env_policy",
        "migration_variables",
        "legacy_reference_files",
        "audit_targets",
        "docker_named_volumes",
        "docker_hygiene",
        "cleanup_waves",
        "external_cache_maintenance",
        "excluded_paths",
    }
    missing = sorted(required_top_level - set(policy))
    if missing:
        errors.append("disk-space-governance.json missing required fields: " + ", ".join(missing))

    quiet_minutes = policy.get("legacy_retirement_quiet_minutes")
    if not isinstance(quiet_minutes, int) or quiet_minutes <= 0:
        errors.append(
            "disk-space-governance.json must declare positive legacy_retirement_quiet_minutes"
        )

    duplicate_env_policy = policy.get("duplicate_env_policy")
    if not isinstance(duplicate_env_policy, dict):
        errors.append("disk-space-governance.json duplicate_env_policy must be an object")
    else:
        canonical_mainline_path = str(
            duplicate_env_policy.get("canonical_mainline_path") or ""
        ).strip()
        duplicate_glob = str(duplicate_env_policy.get("duplicate_glob") or "").strip()
        reference_files = duplicate_env_policy.get("reference_files")
        required_duplicate_reference_files = {
            ".env",
            ".env.example",
            "scripts/lib/standard_env.sh",
            "infra/systemd/sourceharbor-api.service",
            "infra/systemd/sourceharbor-worker.service",
        }
        if canonical_mainline_path != "$HOME/.cache/sourceharbor/project-venv":
            errors.append(
                "duplicate_env_policy.canonical_mainline_path must be $HOME/.cache/sourceharbor/project-venv"
            )
        if duplicate_glob != "$HOME/.cache/sourceharbor/project-venv*":
            errors.append(
                "duplicate_env_policy.duplicate_glob must be $HOME/.cache/sourceharbor/project-venv*"
            )
        if not isinstance(reference_files, list):
            errors.append("duplicate_env_policy.reference_files must be a list")
        else:
            missing_duplicate_refs = sorted(
                required_duplicate_reference_files - {str(item) for item in reference_files}
            )
            if missing_duplicate_refs:
                errors.append(
                    "duplicate_env_policy.reference_files missing required entries: "
                    + ", ".join(missing_duplicate_refs)
                )

    migration_variables = list(policy.get("migration_variables", []))
    seen_migration_names: set[str] = set()
    for entry in migration_variables:
        name = str(entry.get("name") or "").strip()
        canonical_path = str(entry.get("canonical_path") or "").strip()
        path_kind = str(entry.get("path_kind") or "").strip()
        ownership = str(entry.get("ownership") or "").strip()
        existing_target_verify_command = list(entry.get("existing_target_verify_command") or [])
        if not name:
            errors.append("migration_variables entries must declare `name`")
            continue
        seen_migration_names.add(name)
        if not canonical_path:
            errors.append(f"migration variable `{name}` missing canonical_path")
        if "video-digestor" in canonical_path:
            errors.append(
                f"migration variable `{name}` must not point at legacy video-digestor paths"
            )
        if path_kind not in {"file", "directory"}:
            errors.append(f"migration variable `{name}` must use path_kind file|directory")
        if ownership not in {"repo-primary", "repo-exclusive"}:
            errors.append(f"migration variable `{name}` uses unsupported ownership `{ownership}`")
        if entry.get("allow_existing_target") and not existing_target_verify_command:
            errors.append(
                f"migration variable `{name}` allows existing target but is missing existing_target_verify_command"
            )
    missing_migration_names = sorted(REQUIRED_MIGRATION_NAMES - seen_migration_names)
    if missing_migration_names:
        errors.append(
            "disk-space-governance.json missing migration variables: "
            + ", ".join(missing_migration_names)
        )

    external_cache_maintenance = policy.get("external_cache_maintenance")
    if not isinstance(external_cache_maintenance, dict):
        errors.append("disk-space-governance.json external_cache_maintenance must be an object")
    else:
        if not str(external_cache_maintenance.get("report_path") or "").strip():
            errors.append("external_cache_maintenance.report_path is required")
        if not str(external_cache_maintenance.get("stamp_path") or "").strip():
            errors.append("external_cache_maintenance.stamp_path is required")
        auto_interval_minutes = external_cache_maintenance.get("auto_interval_minutes")
        if not isinstance(auto_interval_minutes, int) or auto_interval_minutes <= 0:
            errors.append(
                "external_cache_maintenance.auto_interval_minutes must be a positive integer"
            )
        groups = external_cache_maintenance.get("groups")
        required_groups = {
            "project-venv",
            "state",
            "duplicate-envs",
            "workspace",
            "artifacts",
            "tmp",
        }
        if not isinstance(groups, dict):
            errors.append("external_cache_maintenance.groups must be an object")
        else:
            missing_groups = sorted(required_groups - set(groups))
            if missing_groups:
                errors.append(
                    "external_cache_maintenance.groups missing required entries: "
                    + ", ".join(missing_groups)
                )

    docker_hygiene = policy.get("docker_hygiene")
    if not isinstance(docker_hygiene, dict):
        errors.append("disk-space-governance.json docker_hygiene must be an object")
    else:
        if not str(docker_hygiene.get("report_path") or "").strip():
            errors.append("docker_hygiene.report_path is required")
        for field in (
            "repo_container_prefixes",
            "repo_network_prefixes",
            "repo_named_volumes",
            "repo_local_debug_images",
        ):
            value = docker_hygiene.get(field)
            if not isinstance(value, list):
                errors.append(f"docker_hygiene.{field} must be a list")
        quiet_hours = docker_hygiene.get("local_debug_image_quiet_hours")
        if not isinstance(quiet_hours, int) or quiet_hours <= 0:
            errors.append("docker_hygiene.local_debug_image_quiet_hours must be a positive integer")

    env_example = _read(root / ".env.example")
    if (
        'SOURCE_HARBOR_CACHE_ROOT="${SOURCE_HARBOR_CACHE_ROOT:-$HOME/.cache/sourceharbor}"'
        not in env_example
    ):
        errors.append(
            ".env.example must declare SOURCE_HARBOR_CACHE_ROOT with the canonical ~/.cache/sourceharbor fallback"
        )
    for expected in (
        "${PIPELINE_ARTIFACT_ROOT:-$SOURCE_HARBOR_CACHE_ROOT/artifacts}",
        "${PIPELINE_WORKSPACE_DIR:-$SOURCE_HARBOR_CACHE_ROOT/workspace}",
        "${SQLITE_PATH:-$SOURCE_HARBOR_CACHE_ROOT/state/worker_state.db}",
        "${SQLITE_STATE_PATH:-$SOURCE_HARBOR_CACHE_ROOT/state/api_state.db}",
        "${UV_PROJECT_ENVIRONMENT:-$SOURCE_HARBOR_CACHE_ROOT/project-venv}",
    ):
        if expected not in env_example:
            errors.append(
                f".env.example missing SOURCE_HARBOR_CACHE_ROOT-derived default `{expected}`"
            )
    if "$HOME/.sourceharbor" in env_example or "~/.sourceharbor" in env_example:
        errors.append(".env.example must not default to legacy `.sourceharbor` paths")
    if "video-digestor" in env_example:
        errors.append(".env.example must not default to legacy `video-digestor` paths")
    if ".runtime/artifacts" in env_example or ".runtime/workspace" in env_example:
        errors.append(".env.example must not default runtime persistence into `.runtime/`")
    expected_web_runtime = ".runtime-cache/tmp/web-runtime/workspace/apps/web"
    for key in ("WEB_RUNTIME_WEB_DIR", "WEB_E2E_RUNTIME_WEB_DIR"):
        expected_line = f"export {key}={expected_web_runtime}"
        quoted_line = f'export {key}="{expected_web_runtime}"'
        if expected_line not in env_example and quoted_line not in env_example:
            errors.append(f".env.example missing canonical web runtime default for `{key}`")
    if ".runtime/web" in env_example:
        errors.append(".env.example must not default web runtime into `.runtime/web`")
    for expected in (
        "${SOURCE_HARBOR_CHROME_USER_DATA_DIR:-$SOURCE_HARBOR_CACHE_ROOT/browser/chrome-user-data}",
        "${SOURCE_HARBOR_CHROME_PROFILE_DIR:-Profile 1}",
        "${SOURCE_HARBOR_CHROME_CDP_PORT:-9339}",
    ):
        if expected not in env_example:
            errors.append(f".env.example missing Chrome runtime default `{expected}`")

    services = [
        root / "infra" / "systemd" / "sourceharbor-api.service",
        root / "infra" / "systemd" / "sourceharbor-worker.service",
    ]
    for path in services:
        text = _read(path)
        if "/var/cache/sourceharbor/project-venv" in text:
            errors.append(f"{path.name} still points at /var/cache/sourceharbor/project-venv")
        if ".cache/sourceharbor/project-venv" not in text:
            errors.append(
                f"{path.name} missing canonical .cache/sourceharbor/project-venv fallback"
            )

    docs = {
        root / "docs" / "reference" / "runtime-cache-retention.md",
        root / "docs" / "reference" / "disk-space-governance.md",
    }
    for path in docs:
        if not path.is_file():
            errors.append(f"missing governance doc: {path.relative_to(root).as_posix()}")

    runtime_doc = root / "docs" / "reference" / "runtime-cache-retention.md"
    if runtime_doc.is_file():
        text = _read(runtime_doc)
        if "## Canonical Compartments" not in text:
            errors.append(
                "docs/reference/runtime-cache-retention.md missing `Canonical Compartments` section"
            )

    shared_layer_paths = {
        str(item.get("path") or item.get("path_glob") or "")
        for item in policy.get("audit_targets", [])
        if str(item.get("layer") or "") == "shared-layer"
    }
    canonical_paths = dict(policy.get("canonical_paths", {}))
    user_state_root = str(canonical_paths.get("user_state_root") or "").strip()
    user_cache_root = str(canonical_paths.get("user_cache_root") or "").strip()
    if user_state_root:
        user_state_root_counted = any(
            str(item.get("path") or "").strip() == user_state_root
            and str(item.get("layer") or "").strip() == "repo-external-repo-owned"
            and bool(item.get("count_in_layer_total", False))
            for item in policy.get("audit_targets", [])
        )
        if not user_state_root_counted:
            errors.append(
                "disk-space-governance.json must count canonical user_state_root in audit_targets repo-external-repo-owned totals"
            )
    if user_state_root != "$HOME/.cache/sourceharbor":
        errors.append("canonical_paths.user_state_root must be $HOME/.cache/sourceharbor")
    if user_cache_root != "$HOME/.cache/sourceharbor":
        errors.append("canonical_paths.user_cache_root must be $HOME/.cache/sourceharbor")
    browser_audit_targets = [
        item
        for item in policy.get("audit_targets", [])
        if str(item.get("id") or "") == "external-sourceharbor-browser-root"
    ]
    if not browser_audit_targets:
        errors.append(
            "disk-space-governance.json must keep audit target `external-sourceharbor-browser-root`"
        )
    else:
        browser_target_path = str(browser_audit_targets[0].get("path") or "").strip()
        if browser_target_path != "$HOME/.cache/sourceharbor/browser/chrome-user-data":
            errors.append(
                "external-sourceharbor-browser-root must point at $HOME/.cache/sourceharbor/browser/chrome-user-data"
            )
    legacy_extra_roots = policy.get("legacy_extra_roots")
    if not isinstance(legacy_extra_roots, list) or "$HOME/.sourceharbor" not in {
        str(item) for item in legacy_extra_roots or []
    }:
        errors.append(
            "disk-space-governance.json must keep $HOME/.sourceharbor in legacy_extra_roots as a migration input root"
        )
    legacy_roots = {
        str(canonical_paths.get("legacy_state_root") or "").strip().lower(),
        str(canonical_paths.get("legacy_cache_root") or "").strip().lower(),
        *{str(item).strip().lower() for item in (legacy_extra_roots or [])},
        "video-digestor",
    }
    excluded_paths = {str(item) for item in policy.get("excluded_paths", [])}
    audit_target_paths = {str(item.get("path") or "") for item in policy.get("audit_targets", [])}
    if (
        "$HOME/.cache/sourceharbor/browser/chrome-user-data" in audit_target_paths
        and "$HOME/.cache/sourceharbor/browser/chrome-user-data" not in excluded_paths
    ):
        errors.append(
            "disk-space-governance.json must exclude $HOME/.cache/sourceharbor/browser/chrome-user-data from cleanup execution"
        )
    for wave_name, wave in policy.get("cleanup_waves", {}).items():
        for candidate in wave.get("candidates", []):
            candidate_layer = str(candidate.get("layer") or "")
            candidate_ownership = str(candidate.get("ownership") or "")
            raw_path = str(candidate.get("path") or candidate.get("path_glob") or "")
            if candidate_layer not in ALLOWED_CLEANUP_LAYERS:
                errors.append(
                    f"cleanup wave `{wave_name}` candidate `{candidate.get('id')}` uses forbidden layer `{candidate_layer}`"
                )
            if candidate_ownership not in ALLOWED_CLEANUP_OWNERSHIP:
                errors.append(
                    f"cleanup wave `{wave_name}` candidate `{candidate.get('id')}` uses forbidden ownership `{candidate_ownership}`"
                )
            if raw_path in excluded_paths:
                errors.append(
                    f"cleanup wave `{wave_name}` candidate `{candidate.get('id')}` reuses excluded path `{raw_path}`"
                )
            if raw_path in shared_layer_paths:
                errors.append(
                    f"cleanup wave `{wave_name}` candidate `{candidate.get('id')}` points at shared-layer path `{raw_path}`"
                )
            if wave_name == "repo-tmp":
                for marker in candidate.get("lock_markers", []):
                    marker_text = str(marker)
                    if any(token in marker_text for token in ("*", "?", "[")):
                        errors.append(
                            f"cleanup wave `repo-tmp` candidate `{candidate.get('id')}` must not use broad lock_markers `{marker_text}`"
                        )
            if wave_name == "external-history":
                for equivalent in candidate.get("equivalent_paths", []):
                    equivalent_text = str(equivalent)
                    if _contains_legacy_root(equivalent_text, legacy_roots):
                        errors.append(
                            f"cleanup wave `external-history` candidate `{candidate.get('id')}` must not use legacy equivalent path `{equivalent_text}`"
                        )
                for token in candidate.get("verify_command", []):
                    token_text = str(token)
                    if _contains_legacy_root(token_text, legacy_roots):
                        errors.append(
                            f"cleanup wave `external-history` candidate `{candidate.get('id')}` must not verify against legacy mainline `{token_text}`"
                        )

    for report_field in ("report_path", "cleanup_report_path", "migration_report_path"):
        report_path = str(policy.get(report_field) or "")
        if not report_path.startswith(".runtime-cache/reports/governance/"):
            errors.append(f"{report_field} must live under `.runtime-cache/reports/governance/`")

    if errors:
        print("[disk-space-governance] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[disk-space-governance] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
