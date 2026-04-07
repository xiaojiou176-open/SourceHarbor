#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

usage() {
  cat <<EOF
Usage:
  ${SCRIPT_NAME} [options]

Description:
  Configure RSSHub base URL and batch upsert subscriptions to local API.

Options:
  --base-url URL             RSSHub base URL (fallback when RSSHUB_BASE_URL is empty)
  --bili-uids CSV            Comma-separated Bilibili UIDs, e.g. "123,456"
  --yt-channel-ids CSV       Comma-separated YouTube channel IDs, e.g. "UCxxx,UCyyy"
  --poll                     Trigger POST /api/v1/ingest/poll after upsert
  --help, -h                 Show this help message

Environment variables:
  RSSHUB_BASE_URL            Preferred RSSHub base URL
  SOURCE_HARBOR_API_BASE_URL            API base URL (default: http://127.0.0.1:9000)

Examples:
  ${SCRIPT_NAME} --base-url "https://rsshub.example.com" --bili-uids "123,456"
  RSSHUB_BASE_URL="https://rsshub.example.com" ${SCRIPT_NAME} --yt-channel-ids "UCxxx,UCyyy" --poll
EOF
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

normalize_base_url() {
  local value="$1"
  while [[ "$value" == */ ]]; do
    value="${value%/}"
  done
  printf '%s' "$value"
}

preview_body() {
  local file="$1"
  local content
  content="$(tr '\n' ' ' < "$file" | sed -E 's/[[:space:]]+/ /g' | cut -c1-240)"
  printf '%s' "${content:-<empty>}"
}

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "$value"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  fi
}

probe_rsshub_route() {
  local base_url="$1"
  local route_path="$2"
  local expected_label="$3"
  local probe_url="${base_url}${route_path}"

  if ! python3 - "$probe_url" "$expected_label" <<'PY'
from __future__ import annotations

import sys

import httpx

probe_url = sys.argv[1]
expected_label = sys.argv[2]

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

try:
    with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as client:
        resp = client.get(probe_url)
except Exception as exc:
    print(f"ERROR: RSSHub probe failed (network error): {probe_url} [{type(exc).__name__}: {exc}]", file=sys.stderr)
    raise SystemExit(1)

body = resp.text or ""
content_type = (resp.headers.get("content-type") or "").lower()
body_preview = " ".join(body.split())[:240] or "<empty>"

if not (200 <= resp.status_code < 300):
    print(f"ERROR: RSSHub probe returned HTTP {resp.status_code}: {probe_url}", file=sys.stderr)
    print(f"Body preview: {body_preview}", file=sys.stderr)
    raise SystemExit(1)

if "<rss" not in body.lower():
    print(
        f"ERROR: RSSHub probe for {expected_label} did not return RSS content: {probe_url}",
        file=sys.stderr,
    )
    print(f"content-type: {content_type or '<missing>'}", file=sys.stderr)
    print(f"Body preview: {body_preview}", file=sys.stderr)
    raise SystemExit(1)
PY
  then
    exit 1
  fi

  echo "RSSHub probe passed (${expected_label}): ${probe_url}"
}

post_subscription() {
  local api_base="$1"
  local platform="$2"
  local source_type="$3"
  local source_value="$4"

  local body_file status_code payload escaped_value
  body_file="$(mktemp)"
  escaped_value="$(json_escape "$source_value")"
  payload="$(printf '{"platform":"%s","source_type":"%s","source_value":"%s","enabled":true}' "$platform" "$source_type" "$escaped_value")"

  local curl_args=(
    -H 'Accept: application/json'
    -H 'Content-Type: application/json'
  )
  if [[ -n "${SOURCE_HARBOR_API_KEY:-}" ]]; then
    curl_args+=(-H "X-API-Key: ${SOURCE_HARBOR_API_KEY}")
    curl_args+=(-H "Authorization: Bearer ${SOURCE_HARBOR_API_KEY}")
  fi
  if [[ -n "${WEB_ACTION_SESSION_TOKEN:-}" ]]; then
    curl_args+=(-H "X-Web-Session: ${WEB_ACTION_SESSION_TOKEN}")
  fi

  if ! status_code="$(
    curl -sS -o "$body_file" -w '%{http_code}' \
      "${curl_args[@]}" \
      -X POST "${api_base}/api/v1/subscriptions" \
      --data "$payload"
  )"; then
    echo "FAIL  ${platform}/${source_value}: network error" >&2
    rm -f "$body_file"
    return 1
  fi

  if [[ "$status_code" -ge 200 && "$status_code" -lt 300 ]]; then
    echo "OK    ${platform}/${source_value} (HTTP ${status_code})"
    rm -f "$body_file"
    return 0
  fi

  echo "FAIL  ${platform}/${source_value} (HTTP ${status_code}) body=$(preview_body "$body_file")" >&2
  rm -f "$body_file"
  return 1
}

trigger_poll() {
  local api_base="$1"
  local body_file status_code
  body_file="$(mktemp)"

  local curl_args=(
    -H 'Accept: application/json'
    -H 'Content-Type: application/json'
  )
  if [[ -n "${SOURCE_HARBOR_API_KEY:-}" ]]; then
    curl_args+=(-H "X-API-Key: ${SOURCE_HARBOR_API_KEY}")
    curl_args+=(-H "Authorization: Bearer ${SOURCE_HARBOR_API_KEY}")
  fi
  if [[ -n "${WEB_ACTION_SESSION_TOKEN:-}" ]]; then
    curl_args+=(-H "X-Web-Session: ${WEB_ACTION_SESSION_TOKEN}")
  fi

  if ! status_code="$(
    curl -sS -o "$body_file" -w '%{http_code}' \
      "${curl_args[@]}" \
      -X POST "${api_base}/api/v1/ingest/poll" \
      --data '{}'
  )"; then
    echo "FAIL  ingest/poll: network error" >&2
    rm -f "$body_file"
    return 1
  fi

  if [[ "$status_code" -ge 200 && "$status_code" -lt 300 ]]; then
    echo "OK    ingest/poll (HTTP ${status_code})"
    rm -f "$body_file"
    return 0
  fi

  echo "FAIL  ingest/poll (HTTP ${status_code}) body=$(preview_body "$body_file")" >&2
  rm -f "$body_file"
  return 1
}

require_command curl

if [[ -z "${SOURCE_HARBOR_API_KEY:-}" && -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]]; then
  export SOURCE_HARBOR_API_KEY="sourceharbor-local-dev-token"
fi
if [[ -z "${WEB_ACTION_SESSION_TOKEN:-}" && -n "${SOURCE_HARBOR_API_KEY:-}" ]]; then
  export WEB_ACTION_SESSION_TOKEN="$SOURCE_HARBOR_API_KEY"
fi

BILI_UIDS_CSV=""
YT_CHANNEL_IDS_CSV=""
ARG_BASE_URL=""
SHOULD_POLL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      [[ $# -ge 2 ]] || { echo "ERROR: --base-url requires a value" >&2; exit 1; }
      ARG_BASE_URL="$2"
      shift 2
      ;;
    --bili-uids)
      [[ $# -ge 2 ]] || { echo "ERROR: --bili-uids requires a value" >&2; exit 1; }
      BILI_UIDS_CSV="$2"
      shift 2
      ;;
    --yt-channel-ids)
      [[ $# -ge 2 ]] || { echo "ERROR: --yt-channel-ids requires a value" >&2; exit 1; }
      YT_CHANNEL_IDS_CSV="$2"
      shift 2
      ;;
    --poll)
      SHOULD_POLL=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

RSSHUB_BASE_URL="${RSSHUB_BASE_URL:-}"
if [[ -z "$RSSHUB_BASE_URL" ]]; then
  RSSHUB_BASE_URL="$ARG_BASE_URL"
fi
RSSHUB_BASE_URL="$(trim "$RSSHUB_BASE_URL")"
if [[ -z "$RSSHUB_BASE_URL" ]]; then
  echo "ERROR: RSSHub base URL is required. Set RSSHUB_BASE_URL or pass --base-url." >&2
  usage >&2
  exit 1
fi
RSSHUB_BASE_URL="$(normalize_base_url "$RSSHUB_BASE_URL")"

API_BASE_URL="${SOURCE_HARBOR_API_BASE_URL:-http://127.0.0.1:9000}"
API_BASE_URL="$(normalize_base_url "$API_BASE_URL")"

declare -a BILI_UIDS=()
declare -a YT_CHANNEL_IDS=()
if [[ -n "$BILI_UIDS_CSV" ]]; then
  IFS=',' read -r -a raw_bili <<< "$BILI_UIDS_CSV"
  for uid in "${raw_bili[@]}"; do
    uid="$(trim "$uid")"
    if [[ -n "$uid" ]]; then
      BILI_UIDS+=("$uid")
    fi
  done
fi

if [[ -n "$YT_CHANNEL_IDS_CSV" ]]; then
  IFS=',' read -r -a raw_yt <<< "$YT_CHANNEL_IDS_CSV"
  for channel_id in "${raw_yt[@]}"; do
    channel_id="$(trim "$channel_id")"
    if [[ -n "$channel_id" ]]; then
      YT_CHANNEL_IDS+=("$channel_id")
    fi
  done
fi

if [[ "${#BILI_UIDS[@]}" -eq 0 && "${#YT_CHANNEL_IDS[@]}" -eq 0 ]]; then
  echo "ERROR: no subscriptions provided. Use --bili-uids and/or --yt-channel-ids." >&2
  usage >&2
  exit 1
fi

echo "RSSHub base: ${RSSHUB_BASE_URL}"
echo "API base: ${API_BASE_URL}"

if [[ "${#BILI_UIDS[@]}" -gt 0 ]]; then
  probe_rsshub_route "$RSSHUB_BASE_URL" "/bilibili/user/video/${BILI_UIDS[0]}" "bilibili"
fi
if [[ "${#YT_CHANNEL_IDS[@]}" -gt 0 ]]; then
  probe_rsshub_route "$RSSHUB_BASE_URL" "/youtube/channel/${YT_CHANNEL_IDS[0]}" "youtube"
fi

success_count=0
failure_count=0
total_count=0

if [[ "${#BILI_UIDS[@]}" -gt 0 ]]; then
  for uid in "${BILI_UIDS[@]}"; do
    total_count=$((total_count + 1))
    if post_subscription "$API_BASE_URL" "bilibili" "bilibili_uid" "$uid"; then
      success_count=$((success_count + 1))
    else
      failure_count=$((failure_count + 1))
    fi
  done
fi

if [[ "${#YT_CHANNEL_IDS[@]}" -gt 0 ]]; then
  for channel_id in "${YT_CHANNEL_IDS[@]}"; do
    total_count=$((total_count + 1))
    if post_subscription "$API_BASE_URL" "youtube" "youtube_channel_id" "$channel_id"; then
      success_count=$((success_count + 1))
    else
      failure_count=$((failure_count + 1))
    fi
  done
fi

echo "Summary: total=${total_count}, success=${success_count}, failed=${failure_count}"

if [[ "$SHOULD_POLL" -eq 1 ]]; then
  if trigger_poll "$API_BASE_URL"; then
    :
  else
    failure_count=$((failure_count + 1))
  fi
fi

if [[ "$failure_count" -gt 0 ]]; then
  exit 1
fi
