#!/usr/bin/env bash
set -euo pipefail

sourceharbor_uuid() {
  python3 - <<'PY'
import uuid
print(uuid.uuid4().hex)
PY
}

sourceharbor_log_init() {
  local channel="$1"
  local component="$2"
  local path="${3:-}"

  sourceharbor_log_channel="$channel"
  sourceharbor_log_component="$component"
  sourceharbor_log_run_id="${sourceharbor_log_run_id:-$(sourceharbor_uuid)}"
  sourceharbor_log_repo_commit="${sourceharbor_log_repo_commit:-$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf unknown)}"
  sourceharbor_log_entrypoint="${sourceharbor_log_entrypoint:-$component}"
  sourceharbor_log_env_profile="${sourceharbor_log_env_profile:-${ENV_PROFILE:-unknown}}"
  if [[ "${channel}" == "tests" && -z "${sourceharbor_test_run_id:-}" ]]; then
    sourceharbor_test_run_id="$sourceharbor_log_run_id"
  fi
  if [[ "${channel}" == "governance" && -z "${sourceharbor_gate_run_id:-}" ]]; then
    sourceharbor_gate_run_id="$sourceharbor_log_run_id"
  fi
  if [[ -n "$path" ]]; then
    sourceharbor_log_path="$path"
  else
    sourceharbor_log_path="$ROOT_DIR/.runtime-cache/logs/${channel}/${sourceharbor_log_run_id}.jsonl"
  fi
  mkdir -p "$(dirname "$sourceharbor_log_path")"
}

sourceharbor_log_json_only() {
  local severity="$1"
  local event="$2"
  shift 2
  local message="$*"
  local source_kind="${sourceharbor_log_source_kind:-}"
  if [[ -z "$source_kind" ]]; then
    case "${sourceharbor_log_channel:-}" in
      tests) source_kind="test" ;;
      governance) source_kind="governance" ;;
      infra) source_kind="infra" ;;
      upstreams) source_kind="upstream" ;;
      *) source_kind="app" ;;
    esac
  fi
  python3 "$ROOT_DIR/scripts/runtime/log_jsonl_event.py" \
    --path "${sourceharbor_log_path:?}" \
    --run-id "${sourceharbor_log_run_id:?}" \
    --trace-id "${sourceharbor_trace_id:-}" \
    --request-id "${sourceharbor_request_id:-${sourceharbor_log_run_id:-}}" \
    --service "${sourceharbor_log_service:-${sourceharbor_log_component:?}}" \
    --component "${sourceharbor_log_component:?}" \
    --channel "${sourceharbor_log_channel:?}" \
    --source-kind "$source_kind" \
    --test-id "${sourceharbor_test_id:-}" \
    --test-run-id "${sourceharbor_test_run_id:-}" \
    --gate-run-id "${sourceharbor_gate_run_id:-}" \
    --upstream-id "${sourceharbor_upstream_id:-}" \
    --upstream-operation "${sourceharbor_upstream_operation:-}" \
    --upstream-contract-surface "${sourceharbor_upstream_contract_surface:-}" \
    --failure-class "${sourceharbor_failure_class:-}" \
    --entrypoint "${sourceharbor_log_entrypoint:-${sourceharbor_log_component:?}}" \
    --env-profile "${sourceharbor_log_env_profile:-unknown}" \
    --repo-commit "${sourceharbor_log_repo_commit:-unknown}" \
    --event "$event" \
    --severity "$severity" \
    --message "$message" >/dev/null 2>&1 || true
}

sourceharbor_log() {
  local severity="$1"
  local event="$2"
  shift 2
  local message="$*"
  printf '[%s] %s\n' "${sourceharbor_log_component:-unknown_component}" "$message" >&2
  sourceharbor_log_json_only "$severity" "$event" "$message"
}
