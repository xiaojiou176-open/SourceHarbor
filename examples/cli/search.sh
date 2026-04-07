#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# If you just booted the repo-managed stack locally, first run:
# source .runtime-cache/run/full-stack/resolved.env
SOURCE_HARBOR_API_BASE_URL="${SOURCE_HARBOR_API_BASE_URL:-http://127.0.0.1:${API_PORT:-9000}}" \
node "$ROOT_DIR/packages/sourceharbor-cli/bin/sourceharbor.js" search "agent workflows"
