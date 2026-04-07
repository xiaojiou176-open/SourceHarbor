#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

EPHEMERAL_ROOT_FILES = {
    "SingletonLock",
    "SingletonCookie",
    "SingletonSocket",
    "DevToolsActivePort",
}
EPHEMERAL_PROFILE_FILES = {
    "LOCK",
}
DEFAULT_PROFILE_NAME = "sourceharbor"
DEFAULT_PROFILE_DIR = "Profile 1"
DEFAULT_CDP_PORT = 9339
MAX_MACHINE_CHROME_INSTANCES = 6
ACTUAL_CHROME_MARKERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "Google Chrome.app/Contents/MacOS/Google Chrome",
)


def _env_value(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    return raw.strip() if raw and raw.strip() else default


def default_source_user_data_dir() -> Path:
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    if sys_platform() == "linux":
        return Path.home() / ".config" / "google-chrome"
    if sys_platform() == "win32":
        return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    raise RuntimeError("unable to infer default Chrome user data dir for this platform")


def default_repo_user_data_dir(cache_root: str = "") -> Path:
    resolved_cache_root = cache_root.strip() or _env_value(
        "SOURCE_HARBOR_CACHE_ROOT", str(Path.home() / ".cache" / "sourceharbor")
    )
    return Path(resolved_cache_root).expanduser() / "browser" / "chrome-user-data"


def default_profile_dir() -> str:
    return _env_value("SOURCE_HARBOR_CHROME_PROFILE_DIR", DEFAULT_PROFILE_DIR)


def default_profile_name() -> str:
    return _env_value("SOURCE_HARBOR_CHROME_PROFILE_NAME", DEFAULT_PROFILE_NAME)


def default_cdp_port() -> int:
    raw = _env_value("SOURCE_HARBOR_CHROME_CDP_PORT", str(DEFAULT_CDP_PORT))
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"invalid SOURCE_HARBOR_CHROME_CDP_PORT `{raw}`") from exc
    if port <= 0:
        raise RuntimeError(f"invalid SOURCE_HARBOR_CHROME_CDP_PORT `{raw}`")
    return port


def sys_platform() -> str:
    return os.sys.platform


def read_local_state(user_data_dir: Path) -> dict[str, Any]:
    local_state_path = user_data_dir / "Local State"
    if not local_state_path.is_file():
        raise RuntimeError(f"Chrome Local State missing: {local_state_path}")
    try:
        payload = json.loads(local_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"unable to parse Chrome Local State: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Chrome Local State must be a JSON object")
    return payload


def write_local_state(user_data_dir: Path, payload: dict[str, Any]) -> Path:
    local_state_path = user_data_dir / "Local State"
    local_state_path.parent.mkdir(parents=True, exist_ok=True)
    local_state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return local_state_path


def profile_info_cache(user_data_dir: Path) -> dict[str, Any]:
    payload = read_local_state(user_data_dir)
    profile = payload.get("profile") or {}
    if not isinstance(profile, dict):
        raise RuntimeError("Chrome Local State missing profile section")
    info_cache = profile.get("info_cache") or {}
    if not isinstance(info_cache, dict):
        raise RuntimeError("Chrome Local State missing profile.info_cache")
    return info_cache


def resolve_source_profile_dir(
    *,
    user_data_dir: Path,
    profile_name: str,
    profile_dir: str = "",
) -> str:
    explicit_dir = profile_dir.strip()
    if explicit_dir:
        path = user_data_dir / explicit_dir
        if not path.is_dir():
            raise RuntimeError(f"Chrome profile dir does not exist: {path}")
        return explicit_dir

    target_name = profile_name.strip().lower()
    if not target_name:
        raise RuntimeError("SOURCE_HARBOR_CHROME_PROFILE_NAME is empty")
    matches: list[str] = []
    for candidate_dir, payload in profile_info_cache(user_data_dir).items():
        if not isinstance(payload, dict):
            continue
        display_name = str(payload.get("name") or "").strip().lower()
        if display_name == target_name:
            matches.append(str(candidate_dir))
    if not matches:
        raise RuntimeError(
            f"unable to resolve Chrome profile name `{profile_name}` under {user_data_dir}"
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"Chrome profile name `{profile_name}` is ambiguous under {user_data_dir}: {', '.join(matches)}"
        )
    return matches[0]


def rewrite_local_state_for_target(
    *,
    source_payload: dict[str, Any],
    source_profile_dir: str,
    target_profile_dir: str,
    profile_name: str,
) -> dict[str, Any]:
    payload = deepcopy(source_payload)
    profile = payload.setdefault("profile", {})
    if not isinstance(profile, dict):
        payload["profile"] = {}
        profile = payload["profile"]

    info_cache = profile.get("info_cache") or {}
    if not isinstance(info_cache, dict):
        info_cache = {}
    source_info = info_cache.get(source_profile_dir) or {}
    if not isinstance(source_info, dict):
        source_info = {}
    target_info = deepcopy(source_info)
    target_info["name"] = profile_name

    profile["info_cache"] = {target_profile_dir: target_info}
    profile["last_used"] = target_profile_dir
    profile["last_active_profiles"] = [target_profile_dir]
    if "profiles_order" in profile:
        profile["profiles_order"] = [target_profile_dir]
    return payload


def _copy_ignore(_: str, names: list[str]) -> set[str]:
    ignored = EPHEMERAL_ROOT_FILES | EPHEMERAL_PROFILE_FILES
    return {name for name in names if name in ignored}


def remove_ephemeral_artifacts(target_user_data_dir: Path, target_profile_dir: str) -> None:
    for file_name in EPHEMERAL_ROOT_FILES:
        (target_user_data_dir / file_name).unlink(missing_ok=True)
    for file_name in EPHEMERAL_PROFILE_FILES:
        (target_user_data_dir / target_profile_dir / file_name).unlink(missing_ok=True)


def copy_profile_into_repo_root(
    *,
    source_user_data_dir: Path,
    source_profile_dir: str,
    target_user_data_dir: Path,
    target_profile_dir: str,
    profile_name: str,
) -> dict[str, Any]:
    if target_user_data_dir.exists() and any(target_user_data_dir.iterdir()):
        raise RuntimeError(f"target Chrome user data dir is not empty: {target_user_data_dir}")

    source_profile_path = source_user_data_dir / source_profile_dir
    if not source_profile_path.is_dir():
        raise RuntimeError(f"source Chrome profile dir does not exist: {source_profile_path}")

    source_payload = read_local_state(source_user_data_dir)
    target_user_data_dir.mkdir(parents=True, exist_ok=True)
    target_profile_path = target_user_data_dir / target_profile_dir
    shutil.copytree(
        source_profile_path,
        target_profile_path,
        ignore=_copy_ignore,
    )
    target_payload = rewrite_local_state_for_target(
        source_payload=source_payload,
        source_profile_dir=source_profile_dir,
        target_profile_dir=target_profile_dir,
        profile_name=profile_name,
    )
    write_local_state(target_user_data_dir, target_payload)
    remove_ephemeral_artifacts(target_user_data_dir, target_profile_dir)
    copied_markers = {
        name: (target_profile_path / name).exists()
        for name in ("Cookies", "Login Data", "Preferences", "Extensions")
    }
    return {
        "source_user_data_dir": str(source_user_data_dir),
        "source_profile_dir": source_profile_dir,
        "target_user_data_dir": str(target_user_data_dir),
        "target_profile_dir": target_profile_dir,
        "target_profile_path": str(target_profile_path),
        "copied_state_markers": copied_markers,
    }


def _parse_ps_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        rows.append({"pid": parts[0], "command": parts[1]})
    return rows


def list_actual_chrome_processes() -> list[dict[str, str]]:
    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    rows = _parse_ps_rows(result.stdout)
    return [
        row for row in rows if any(marker in row["command"] for marker in ACTUAL_CHROME_MARKERS)
    ]


def list_repo_chrome_processes(user_data_dir: Path) -> list[dict[str, str]]:
    needle = f"--user-data-dir={user_data_dir}"
    return [row for row in list_actual_chrome_processes() if needle in row["command"]]


def list_default_root_chrome_processes(default_user_data_dir: Path) -> list[dict[str, str]]:
    explicit_needle = f"--user-data-dir={default_user_data_dir}"
    default_root_processes: list[dict[str, str]] = []
    for row in list_actual_chrome_processes():
        command = row["command"]
        if "--user-data-dir=" not in command or explicit_needle in command:
            default_root_processes.append(row)
    return default_root_processes


def cdp_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def fetch_cdp_version(port: int, timeout_seconds: float = 2.0) -> dict[str, Any]:
    with urllib.request.urlopen(  # noqa: S310
        f"{cdp_url(port)}/json/version",
        timeout=timeout_seconds,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("CDP version endpoint must return a JSON object")
    return payload


def is_cdp_alive(port: int, timeout_seconds: float = 1.0) -> bool:
    try:
        fetch_cdp_version(port, timeout_seconds=timeout_seconds)
    except (OSError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return False
    return True


def wait_for_cdp(port: int, timeout_seconds: float = 20.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            return fetch_cdp_version(port)
        except (
            OSError,
            RuntimeError,
            urllib.error.URLError,
            urllib.error.HTTPError,
            ValueError,
        ) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise RuntimeError(
        f"CDP endpoint did not become ready on {cdp_url(port)} within {timeout_seconds:.1f}s"
        + (f": {last_error}" if last_error else "")
    )


def resolve_repo_runtime(
    *,
    user_data_dir: str,
    profile_name: str,
    profile_dir: str,
    cdp_port: int | str,
) -> dict[str, Any]:
    resolved_user_data_dir = Path(user_data_dir).expanduser()
    if not resolved_user_data_dir.is_dir():
        raise RuntimeError(f"repo Chrome user data dir does not exist: {resolved_user_data_dir}")
    resolved_profile_dir = profile_dir.strip() or DEFAULT_PROFILE_DIR
    resolved_profile_path = resolved_user_data_dir / resolved_profile_dir
    if not resolved_profile_path.is_dir():
        raise RuntimeError(f"repo Chrome profile dir does not exist: {resolved_profile_path}")

    info_cache = profile_info_cache(resolved_user_data_dir)
    payload = info_cache.get(resolved_profile_dir) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"repo Chrome Local State missing info_cache entry for `{resolved_profile_dir}`"
        )
    display_name = str(payload.get("name") or "").strip()
    if display_name != profile_name:
        raise RuntimeError(
            f"repo Chrome profile `{resolved_profile_dir}` has display name `{display_name}`, expected `{profile_name}`"
        )

    resolved_cdp_port = int(cdp_port)
    if resolved_cdp_port <= 0:
        raise RuntimeError(f"invalid CDP port `{cdp_port}`")
    return {
        "chrome_channel": "chrome",
        "user_data_dir": str(resolved_user_data_dir),
        "profile_dir": resolved_profile_dir,
        "profile_path": str(resolved_profile_path),
        "profile_name": profile_name,
        "cdp_port": resolved_cdp_port,
        "cdp_url": cdp_url(resolved_cdp_port),
    }


def resolve_chrome_binary(explicit_binary: str = "") -> str:
    if explicit_binary.strip():
        candidate = Path(explicit_binary).expanduser()
        if not candidate.is_file():
            raise RuntimeError(f"Chrome binary does not exist: {candidate}")
        return str(candidate)

    mac_binary = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if mac_binary.is_file():
        return str(mac_binary)

    for candidate in (
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ):
        if candidate:
            return candidate
    raise RuntimeError("unable to locate Google Chrome binary")


def build_launch_command(
    *,
    chrome_binary: str,
    user_data_dir: Path,
    profile_dir: str,
    cdp_port: int,
    start_url: str,
) -> list[str]:
    return [
        chrome_binary,
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_dir}",
        f"--remote-debugging-port={cdp_port}",
        "--remote-debugging-address=127.0.0.1",
        "--no-first-run",
        "--no-default-browser-check",
        start_url,
    ]
