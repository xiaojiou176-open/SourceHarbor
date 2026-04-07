from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READER_ENV = ROOT / "env" / "profiles" / "reader.env"
ALLOWED_VALUES = {
    "MINIFLUX_DB_PASSWORD": {"change_me"},
    "MINIFLUX_ADMIN_USERNAME": {"admin"},
    "MINIFLUX_ADMIN_PASSWORD": {"change_me"},
    "MINIFLUX_BASE_URL": {"http://127.0.0.1:8080"},
    "NEXTFLUX_PORT": {"3000"},
    "MINIFLUX_POLLING_FREQUENCY": {"30"},
    "MINIFLUX_CLEANUP_ARCHIVE_READ_DAYS": {"30"},
    "MINIFLUX_CLEANUP_REMOVE_SESSIONS_DAYS": {"30"},
}
OPTIONAL_BLANK_KEYS = {"MINIFLUX_API_TOKEN"}


def main() -> int:
    if not READER_ENV.is_file():
        print(f"reader env template missing: {READER_ENV}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for raw_line in READER_ENV.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in OPTIONAL_BLANK_KEYS:
            continue
        allowed = ALLOWED_VALUES.get(key)
        if allowed is None:
            errors.append(f"reader env template contains unmanaged key: {key}")
            continue
        if value not in allowed:
            errors.append(
                f"reader env template must keep placeholder value for {key}; got {value!r}"
            )

    if errors:
        print(
            "reader env template must stay placeholder-only for the tracked public tree:",
            file=sys.stderr,
        )
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        print(
            "put real reader secrets in an untracked local copy or inject them via the current shell",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
