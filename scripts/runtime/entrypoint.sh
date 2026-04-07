#!/usr/bin/env bash
set -euo pipefail

sourceharbor_entrypoint_bootstrap() {
  local channel="$1"
  local entrypoint_name="$2"
  local explicit_log_path="${3:-}"
  local argv_json="[]"
  shift 3

  if [[ "${SOURCE_HARBOR_SKIP_WORKSPACE_HYGIENE:-0}" != "1" ]]; then
    bash "$ROOT_DIR/bin/workspace-hygiene" --normalize --quiet
  fi

  export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
  export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$ROOT_DIR/.runtime-cache/tmp/pycache}"
  argv_json="$(
    python3 - <<'PY' "$@"
import json
import sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
PY
  )"

  # shellcheck source=./scripts/runtime/logging.sh
  source "$ROOT_DIR/scripts/runtime/logging.sh"
  sourceharbor_log_entrypoint="$entrypoint_name"
  sourceharbor_log_init "$channel" "$entrypoint_name" "$explicit_log_path"
  sourceharbor_log info entrypoint_bootstrap "bootstrap entrypoint=${entrypoint_name} channel=${channel}"

  export sourceharbor_log_channel
  export sourceharbor_log_component
  export sourceharbor_log_run_id
  export sourceharbor_log_repo_commit
  export sourceharbor_log_entrypoint
  export sourceharbor_log_env_profile
  export sourceharbor_log_path
  export sourceharbor_test_run_id
  export sourceharbor_gate_run_id

  python3 "$ROOT_DIR/scripts/runtime/write_run_manifest.py" \
    --run-id "$sourceharbor_log_run_id" \
    --entrypoint "$entrypoint_name" \
    --channel "$channel" \
    --argv-json "$argv_json"
}
