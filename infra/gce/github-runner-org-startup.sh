#!/usr/bin/env bash
set -euo pipefail

log() { echo "[runner-org-only] $*"; }

REPO_PATTERN='actions.runner.xiaojiou176-open-ui-pressure-test-private.pool-*.service'
ORG_PATTERN='actions.runner.xiaojiou176-open.pool-*.service'
WAIT_SECONDS="${RUNNER_STOP_WAIT_SECONDS:-20}"

list_units() {
  local pattern="$1"
  systemctl list-unit-files "$pattern" --no-legend 2>/dev/null | awk '{print $1}' || true
}

stop_units() {
  local units="$1"
  [[ -n "$units" ]] || return 0
  while IFS= read -r unit; do
    [[ -z "$unit" ]] && continue
    systemctl stop "$unit" || true
    systemctl disable "$unit" >/dev/null 2>&1 || true
  done <<<"$units"
}

enable_and_start_units() {
  local units="$1"
  [[ -n "$units" ]] || return 0
  while IFS= read -r unit; do
    [[ -z "$unit" ]] && continue
    systemctl reset-failed "$unit" >/dev/null 2>&1 || true
    systemctl enable "$unit" >/dev/null 2>&1 || true
    systemctl start "$unit"
  done <<<"$units"
}

merge_units() {
  local first="$1"
  local second="$2"
  printf '%s\n%s\n' "$first" "$second" | awk 'NF && !seen[$0]++'
}

wait_for_units_to_stop() {
  local units="$1"
  local waited=0
  while (( waited < WAIT_SECONDS )); do
    local found=0
    while IFS= read -r unit; do
      [[ -z "$unit" ]] && continue
      if systemctl is-active --quiet "$unit"; then
        found=1
        break
      fi
    done <<<"$units"
    if (( found == 0 )); then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done

  return 1
}

force_kill_units() {
  local units="$1"
  [[ -n "$units" ]] || return 0
  while IFS= read -r unit; do
    [[ -z "$unit" ]] && continue
    systemctl kill --signal=SIGKILL --kill-who=all "$unit" >/dev/null 2>&1 || true
  done <<<"$units"
}

log_unit_snapshot() {
  local units="$1"
  [[ -n "$units" ]] || return 0
  while IFS= read -r unit; do
    [[ -z "$unit" ]] && continue
    systemctl show "$unit" --property=Id,ActiveState,SubState,MainPID,ControlPID --no-pager || true
  done <<<"$units"
}

main() {
  log "start: $(date -Is)"

  local repo_svcs org_svcs all_svcs
  repo_svcs="$(list_units "$REPO_PATTERN")"
  org_svcs="$(list_units "$ORG_PATTERN")"
  all_svcs="$(merge_units "$repo_svcs" "$org_svcs")"

  stop_units "$repo_svcs"
  stop_units "$org_svcs"

  if ! wait_for_units_to_stop "$all_svcs"; then
    log "runner services still active after ${WAIT_SECONDS}s, escalating with unit-scoped SIGKILL"
    force_kill_units "$all_svcs"
    wait_for_units_to_stop "$all_svcs" || true
  fi

  if [[ -z "$org_svcs" ]]; then
    log "no org services found"
    exit 1
  fi

  enable_and_start_units "$org_svcs"
  sleep 5

  log "service snapshot"
  systemctl list-units "$ORG_PATTERN" --all --no-pager || true
  log "unit state snapshot"
  log_unit_snapshot "$org_svcs"
  log "done: $(date -Is)"
}

main "$@"
