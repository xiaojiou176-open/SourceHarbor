#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from sourceharbor_chrome import (  # noqa: E402
    default_cdp_port,
    default_profile_dir,
    default_profile_name,
    default_repo_user_data_dir,
    default_source_user_data_dir,
    resolve_chrome_binary,
    resolve_repo_runtime,
    resolve_source_profile_dir,
)


def resolve_chrome_profile(
    *,
    user_data_dir: str,
    profile_name: str,
    profile_dir: str,
) -> dict[str, str]:
    """Backward-compatible helper for source-profile resolution."""
    user_data_path = Path(user_data_dir).expanduser()
    if not user_data_path.is_dir():
        raise RuntimeError(f"Chrome user data dir does not exist: {user_data_path}")
    resolved_profile_dir = resolve_source_profile_dir(
        user_data_dir=user_data_path,
        profile_name=profile_name,
        profile_dir=profile_dir,
    )
    profile_path = user_data_path / resolved_profile_dir
    return {
        "chrome_channel": "chrome",
        "user_data_dir": str(user_data_path),
        "profile_dir": resolved_profile_dir,
        "profile_path": str(profile_path),
    }


def _shell_exports(payload: dict[str, Any]) -> str:
    lines = []
    ordered = (
        ("SOURCE_HARBOR_CHROME_CHANNEL", payload.get("chrome_channel", "chrome")),
        ("SOURCE_HARBOR_CHROME_USER_DATA_DIR", payload["user_data_dir"]),
        ("SOURCE_HARBOR_CHROME_PROFILE_DIR", payload["profile_dir"]),
        ("SOURCE_HARBOR_CHROME_PROFILE_PATH", payload["profile_path"]),
    )
    for key, value in ordered:
        lines.append(f"export {key}={shlex.quote(str(value))}")
    if "profile_name" in payload:
        lines.append(
            "export SOURCE_HARBOR_CHROME_PROFILE_NAME=" + shlex.quote(str(payload["profile_name"]))
        )
    if "cdp_port" in payload:
        lines.append(
            "export SOURCE_HARBOR_CHROME_CDP_PORT=" + shlex.quote(str(payload["cdp_port"]))
        )
    if "cdp_url" in payload:
        lines.append("export SOURCE_HARBOR_CHROME_CDP_URL=" + shlex.quote(str(payload["cdp_url"])))
    if "chrome_binary" in payload:
        lines.append(
            "export SOURCE_HARBOR_CHROME_BINARY=" + shlex.quote(str(payload["chrome_binary"]))
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve SourceHarbor Chrome profile info for migration-source or repo-runtime modes."
    )
    parser.add_argument(
        "--mode",
        choices=("source-profile", "repo-runtime"),
        default="repo-runtime",
    )
    parser.add_argument("--user-data-dir", default="")
    parser.add_argument("--profile-name", default=default_profile_name())
    parser.add_argument("--profile-dir", default="")
    parser.add_argument("--cdp-port", default=str(default_cdp_port()))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--shell-exports", action="store_true")
    args = parser.parse_args()

    try:
        if args.mode == "source-profile":
            user_data_dir = args.user_data_dir.strip() or str(default_source_user_data_dir())
            payload: dict[str, Any] = resolve_chrome_profile(
                user_data_dir=user_data_dir,
                profile_name=args.profile_name,
                profile_dir=args.profile_dir,
            )
        else:
            user_data_dir = args.user_data_dir.strip() or str(default_repo_user_data_dir())
            payload = resolve_repo_runtime(
                user_data_dir=user_data_dir,
                profile_name=args.profile_name,
                profile_dir=args.profile_dir or default_profile_dir(),
                cdp_port=args.cdp_port,
            )
            payload["chrome_binary"] = resolve_chrome_binary()
    except RuntimeError as exc:
        print(f"[resolve-chrome-profile] FAIL\n  - {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.shell_exports:
        print(_shell_exports(payload))
    else:
        print(payload["profile_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
