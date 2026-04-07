#!/usr/bin/env bash
set -euo pipefail

load_env_file() {
  local env_path="${1:-}"
  local caller="${2:-env_loader}"

  if [[ -z "$env_path" ]]; then
    printf '[%s] Env file path is empty, skipping.\n' "$caller" >&2
    return 0
  fi

  if [[ -f "$env_path" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_path"
    set +a
    printf '[%s] Loaded env file: %s\n' "$caller" "$env_path" >&2
    return 0
  fi

  printf '[%s] Env file not found, continuing with current shell env: %s\n' "$caller" "$env_path" >&2
}

load_env_files() {
  local caller="${1:-env_loader}"
  shift || true
  local env_path
  for env_path in "$@"; do
    load_env_file "$env_path" "$caller"
  done
}

sourceharbor_default_cache_root() {
  printf '%s\n' "${SOURCE_HARBOR_CACHE_ROOT:-$HOME/.cache/sourceharbor}"
}

sourceharbor_legacy_state_root() {
  printf '%s\n' "$HOME/.sourceharbor"
}

_normalize_sourceharbor_repo_owned_path() {
  local current_value="${1:-}"
  local canonical_value="${2:-}"
  local legacy_value="${3:-}"

  if [[ -z "$current_value" ]]; then
    printf '%s\n' "$canonical_value"
    return 0
  fi

  if [[ "$current_value" == "$legacy_value" ]]; then
    printf '%s\n' "$canonical_value"
    return 0
  fi

  printf '%s\n' "$current_value"
}

ensure_sourceharbor_cache_contract() {
  local root_dir="${1:-}"
  local cache_root
  cache_root="$(sourceharbor_default_cache_root)"
  export SOURCE_HARBOR_CACHE_ROOT="$cache_root"

  local legacy_root
  legacy_root="$(sourceharbor_legacy_state_root)"

  local normalized_pipeline_artifact_root
  normalized_pipeline_artifact_root="$(
    _normalize_sourceharbor_repo_owned_path \
      "${PIPELINE_ARTIFACT_ROOT:-}" \
      "$cache_root/artifacts" \
      "$legacy_root/artifacts"
  )"
  export PIPELINE_ARTIFACT_ROOT="$normalized_pipeline_artifact_root"

  local normalized_pipeline_workspace_dir
  normalized_pipeline_workspace_dir="$(
    _normalize_sourceharbor_repo_owned_path \
      "${PIPELINE_WORKSPACE_DIR:-}" \
      "$cache_root/workspace" \
      "$legacy_root/workspace"
  )"
  export PIPELINE_WORKSPACE_DIR="$normalized_pipeline_workspace_dir"

  local normalized_sqlite_path
  normalized_sqlite_path="$(
    _normalize_sourceharbor_repo_owned_path \
      "${SQLITE_PATH:-}" \
      "$cache_root/state/worker_state.db" \
      "$legacy_root/state/worker_state.db"
  )"
  export SQLITE_PATH="$normalized_sqlite_path"

  local normalized_sqlite_state_path
  normalized_sqlite_state_path="$(
    _normalize_sourceharbor_repo_owned_path \
      "${SQLITE_STATE_PATH:-}" \
      "$cache_root/state/api_state.db" \
      "$legacy_root/state/api_state.db"
  )"
  export SQLITE_STATE_PATH="$normalized_sqlite_state_path"

  local normalized_uv_project_environment
  normalized_uv_project_environment="$(
    _normalize_sourceharbor_repo_owned_path \
      "${UV_PROJECT_ENVIRONMENT:-}" \
      "$cache_root/project-venv" \
      "$legacy_root/project-venv"
  )"
  export UV_PROJECT_ENVIRONMENT="$normalized_uv_project_environment"

  if [[ -n "$root_dir" ]]; then
    export SOURCE_HARBOR_REPO_ROOT="${SOURCE_HARBOR_REPO_ROOT:-$root_dir}"
  fi
}

run_sourceharbor_external_cache_maintenance_if_due() {
  local root_dir="${1:-}"
  [[ -n "$root_dir" ]] || return 0
  command -v python3 >/dev/null 2>&1 || return 0

  if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
    return 0
  fi
  if [[ "${SOURCE_HARBOR_AUTO_MAINTAIN_EXTERNAL_CACHE:-1}" == "0" ]]; then
    return 0
  fi
  local script_path="$root_dir/scripts/runtime/maintain_external_cache.py"
  [[ -f "$script_path" ]] || return 0

  python3 "$script_path" --auto --apply >/dev/null 2>&1 || true
}

snapshot_process_env() {
  local snapshot_path="${1:-}"
  [[ -n "$snapshot_path" ]] || return 1
  python3 - <<'PY' > "$snapshot_path"
import os
import shlex

for key, value in os.environ.items():
    if value == "":
        continue
    print(f"export {key}={shlex.quote(value)}")
PY
}

restore_process_env() {
  local snapshot_path="${1:-}"
  [[ -f "$snapshot_path" ]] || return 0
  # shellcheck disable=SC1090
  source "$snapshot_path"
  rm -f "$snapshot_path"
}

load_env_file_preserve_process_env() {
  local env_path="${1:-}"
  local caller="${2:-env_loader}"
  local shell_snapshot
  shell_snapshot="$(mktemp)"
  snapshot_process_env "$shell_snapshot"
  load_env_file "$env_path" "$caller"
  restore_process_env "$shell_snapshot"
}

get_runtime_resolved_env_path() {
  local root_dir="${1:-}"
  if [[ -z "$root_dir" ]]; then
    return 1
  fi
  printf '%s\n' "$root_dir/.runtime-cache/run/full-stack/resolved.env"
}

read_env_value_from_file() {
  local env_path="${1:-}"
  local key="${2:-}"
  if [[ -z "$env_path" || -z "$key" || ! -f "$env_path" ]]; then
    return 0
  fi

  python3 - "$env_path" "$key" <<'PY'
import os
import re
from pathlib import Path
import shlex
import sys

env_path = Path(sys.argv[1])
target_key = sys.argv[2]
env_ref_re = re.compile(r"\$(\w+)|\$\{([^}]+)\}")
resolved = {}

def expand_value(raw: str) -> str:
    merged = dict(os.environ)
    merged.update(resolved)

    def repl(match):
        name = match.group(1) or match.group(2) or ""
        return merged.get(name, match.group(0))

    value = raw
    for _ in range(5):
        expanded = env_ref_re.sub(repl, value)
        expanded = os.path.expanduser(expanded)
        if expanded == value:
            return expanded
        value = expanded
    return value

for raw_line in env_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[len("export "):].strip()
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() != target_key:
        continue
    token = value.strip()
    try:
        parts = shlex.split(token, posix=True)
        normalized = parts[0] if len(parts) == 1 else token
    except ValueError:
        normalized = token.strip("'\"")
    expanded = expand_value(normalized)
    resolved[key.strip()] = expanded
    if key.strip() == target_key:
        print(expanded)
        raise SystemExit(0)
PY
}

write_runtime_resolved_env() {
  local root_dir="${1:-}"
  local caller="${2:-env_loader}"
  shift 2 || true
  if [[ -z "$root_dir" ]]; then
    printf '[%s] root_dir is empty, cannot write resolved env.\n' "$caller" >&2
    return 1
  fi

  local resolved_path
  resolved_path="$(get_runtime_resolved_env_path "$root_dir")" || return 1
  mkdir -p "$(dirname "$resolved_path")"

  {
    printf '# generated by %s at %s\n' "$caller" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    local pair key value
    for pair in "$@"; do
      [[ "$pair" == *=* ]] || continue
      key="${pair%%=*}"
      value="${pair#*=}"
      printf 'export %s=%q\n' "$key" "$value"
    done
  } > "$resolved_path"

  printf '[%s] Wrote runtime resolved env: %s\n' "$caller" "$resolved_path" >&2
}

resolve_runtime_route_value() {
  local root_dir="${1:-}"
  local key="${2:-}"
  local cli_value="${3:-}"
  local default_value="${4:-}"

  if [[ -n "$cli_value" ]]; then
    printf '%s\n' "$cli_value"
    return 0
  fi

  local process_value="${!key:-}"
  if [[ -n "$process_value" ]]; then
    printf '%s\n' "$process_value"
    return 0
  fi

  local resolved_path resolved_value repo_value
  resolved_path="$(get_runtime_resolved_env_path "$root_dir" 2>/dev/null || true)"
  resolved_value="$(read_env_value_from_file "$resolved_path" "$key")"
  if [[ -n "$resolved_value" ]]; then
    printf '%s\n' "$resolved_value"
    return 0
  fi

  repo_value="$(read_env_value_from_file "$root_dir/.env" "$key")"
  if [[ -n "$repo_value" ]]; then
    printf '%s\n' "$repo_value"
    return 0
  fi

  printf '%s\n' "$default_value"
}

resolve_runtime_route_value_with_sources() {
  local root_dir="${1:-}"
  local key="${2:-}"
  local cli_value="${3:-}"
  local inherited_value="${4:-}"
  local loaded_value="${5:-}"
  local default_value="${6:-}"

  if [[ -n "$cli_value" ]]; then
    printf '%s\n' "$cli_value"
    return 0
  fi

  if [[ -n "$inherited_value" ]]; then
    printf '%s\n' "$inherited_value"
    return 0
  fi

  local resolved_path resolved_value repo_value
  resolved_path="$(get_runtime_resolved_env_path "$root_dir" 2>/dev/null || true)"
  resolved_value="$(read_env_value_from_file "$resolved_path" "$key")"
  if [[ -n "$resolved_value" ]]; then
    printf '%s\n' "$resolved_value"
    return 0
  fi

  repo_value="$(read_env_value_from_file "$root_dir/.env" "$key")"
  if [[ -n "$repo_value" ]]; then
    printf '%s\n' "$repo_value"
    return 0
  fi

  if [[ -n "$loaded_value" ]]; then
    printf '%s\n' "$loaded_value"
    return 0
  fi

  printf '%s\n' "$default_value"
}

normalize_env_profile() {
  local profile="${1:-local}"
  if [[ -z "$profile" ]]; then
    printf 'local\n'
    return 0
  fi
  if [[ "$profile" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf '%s\n' "$profile"
    return 0
  fi
  printf 'local\n'
}

get_repo_env_files() {
  local root_dir="${1:-}"
  local profile="${2:-${ENV_PROFILE:-local}}"
  profile="$(normalize_env_profile "$profile")"

  if [[ -z "$root_dir" ]]; then
    return 0
  fi

  local core_file="$root_dir/env/core.env"
  local core_example_file="$root_dir/env/core.env.example"
  local profile_file="$root_dir/env/profiles/${profile}.env"
  local repo_env_file="$root_dir/.env"

  if [[ -f "$core_file" ]]; then
    printf '%s\n' "$core_file"
  elif [[ -f "$core_example_file" ]]; then
    printf '%s\n' "$core_example_file"
  fi

  if [[ -f "$profile_file" ]]; then
    printf '%s\n' "$profile_file"
  fi

  if [[ -f "$repo_env_file" ]]; then
    printf '%s\n' "$repo_env_file"
  fi
}

load_repo_env() {
  local root_dir="${1:-}"
  local caller="${2:-env_loader}"
  local requested_profile="${3:-${ENV_PROFILE:-local}}"
  local profile
  profile="$(normalize_env_profile "$requested_profile")"

  if [[ -z "$root_dir" ]]; then
    printf '[%s] root_dir is empty, skipping repo env load.\n' "$caller" >&2
    return 0
  fi

  local shell_snapshot
  shell_snapshot="$(mktemp)"
  snapshot_process_env "$shell_snapshot"

  local -a env_files=()
  local env_file
  while IFS= read -r env_file; do
    [[ -z "$env_file" ]] && continue
    env_files+=("$env_file")
  done < <(get_repo_env_files "$root_dir" "$profile")

  if (( ${#env_files[@]} > 0 )); then
    load_env_files "$caller" "${env_files[@]}"
  else
    printf '[%s] No env files found under %s (profile=%s), using current shell env only.\n' "$caller" "$root_dir" "$profile" >&2
  fi

  # Inherited process environment has the highest priority.
  restore_process_env "$shell_snapshot"

  export ENV_PROFILE="$profile"
  ensure_sourceharbor_cache_contract "$root_dir"
  run_sourceharbor_external_cache_maintenance_if_due "$root_dir"
}
