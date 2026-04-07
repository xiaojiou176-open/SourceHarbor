#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="run_db_rollback_drill"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RELEASE_TAG="${1:-$(git -C "$ROOT_DIR" describe --tags --abbrev=0 2>/dev/null || echo v0.0.0)}"
OUTPUT_PATH="${2:-$ROOT_DIR/artifacts/releases/$RELEASE_TAG/rollback/drill.json}"
CONTAINER_NAME="sourceharbor-rollback-drill-$$"
DB_NAME="postgres"
DB_USER="postgres"
DB_PASSWORD="postgres"

mkdir -p "$(dirname "$OUTPUT_PATH")"

cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --health-cmd="pg_isready -U $DB_USER -d $DB_NAME" \
  --health-interval=2s \
  --health-timeout=3s \
  --health-retries=60 \
  -e POSTGRES_USER="$DB_USER" \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  postgres:16-alpine >/dev/null

for _ in $(seq 1 120); do
  health_status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  if [[ "$health_status" == "healthy" ]]; then
    break
  fi
  if [[ "$health_status" == "exited" ]]; then
    break
  fi
  sleep 1
done

if ! docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
  docker logs "$CONTAINER_NAME" | tail -n 50 >&2 || true
  echo "[$SCRIPT_NAME] postgres container failed to become ready" >&2
  exit 1
fi

psql_file() {
  local sql_path="$1"
  docker exec -i "$CONTAINER_NAME" psql \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB_NAME" < "$sql_path"
}

psql_query() {
  local query="$1"
  docker exec "$CONTAINER_NAME" psql \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Atqc "$query"
}

psql_file "$ROOT_DIR/infra/migrations/20260221_000001_init.sql"
psql_file "$ROOT_DIR/infra/migrations/20260308_000016_content_type.sql"

column_exists_before="$(psql_query "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'videos' AND column_name = 'content_type';")"
if [[ "$column_exists_before" != "1" ]]; then
  echo "[$SCRIPT_NAME] expected content_type column after up migration" >&2
  exit 1
fi

psql_query "INSERT INTO videos (platform, video_uid, source_url, title, content_type) VALUES ('youtube', 'rollback-drill', 'https://example.test/rollback-drill', 'rollback drill', 'article');" >/dev/null
row_count_before="$(psql_query "SELECT COUNT(*) FROM videos WHERE video_uid = 'rollback-drill';")"

psql_file "$ROOT_DIR/infra/migrations/down/20260308_000016_content_type.down.sql"

column_exists_after="$(psql_query "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'videos' AND column_name = 'content_type';")"
row_count_after="$(psql_query "SELECT COUNT(*) FROM videos WHERE video_uid = 'rollback-drill';")"

if [[ "$column_exists_after" != "0" ]]; then
  echo "[$SCRIPT_NAME] content_type column still present after down migration" >&2
  exit 1
fi

if [[ "$row_count_before" != "$row_count_after" ]]; then
  echo "[$SCRIPT_NAME] row count changed across rollback drill" >&2
  exit 1
fi

python3 - "$OUTPUT_PATH" "$RELEASE_TAG" "$row_count_after" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

output_path = Path(sys.argv[1])
release_tag = sys.argv[2]
row_count_after = int(sys.argv[3])

payload = {
    "release_tag": release_tag,
    "executed_at": datetime.now(UTC).isoformat(),
    "executor": "scripts/release/run_db_rollback_drill.sh",
    "strategy": "temporary-postgres-up-down-drill",
    "result": "success",
    "migrations_checked": ["20260308_000016_content_type.sql"],
    "notes": (
        "Executed init -> content_type up -> content_type down on a temporary PostgreSQL container. "
        "Verified the content_type column exists after the up migration, is removed by the down migration, "
        f"and the drill row count remains {row_count_after} after rollback. "
        "This confirms schema restoration while content_type data is dropped by design."
    ),
}
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output_path)
PY
