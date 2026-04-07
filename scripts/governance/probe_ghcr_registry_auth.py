#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import write_json_artifact

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT / ".runtime-cache" / "reports" / "governance" / "ghcr-registry-auth-probe.json"
)
CONTRACT_PATH = ROOT / "infra" / "config" / "strict_ci_contract.json"


def _read_expected_repository() -> str:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return str(payload["standard_image"]["repository"])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe GHCR auth and upload boundaries.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to the JSON artifact output. Defaults to the governance runtime report path.",
    )
    parser.add_argument(
        "--repository",
        default="",
        help="Explicit GHCR repository, for example ghcr.io/org/package. Overrides --owner/--package and contract default.",
    )
    parser.add_argument(
        "--owner",
        default="",
        help="Optional GHCR owner/org when constructing the target repository from --owner + --package.",
    )
    parser.add_argument(
        "--package",
        default="",
        help="Optional GHCR package name when constructing the target repository from --owner + --package.",
    )
    return parser.parse_args()


def _run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _discover_accounts() -> list[dict[str, str]]:
    code, stdout, _ = _run(["gh", "auth", "status"])
    accounts: list[dict[str, str]] = []

    env_candidates = [
        (
            os.getenv("GITHUB_ACTOR", "").strip(),
            os.getenv("GITHUB_TOKEN", "").strip(),
            "env:github-actions-token",
            "unknown",
        ),
        (
            os.getenv("GHCR_WRITE_USERNAME", "").strip(),
            os.getenv("GHCR_WRITE_TOKEN", "").strip(),
            "env:ghcr-write-token",
            "unknown",
        ),
        (
            os.getenv("GHCR_USERNAME", "").strip(),
            os.getenv("GHCR_TOKEN", "").strip(),
            "env:ghcr-token",
            "unknown",
        ),
    ]
    seen: set[tuple[str, str]] = set()
    for login, token, source, scopes in env_candidates:
        if not login or not token:
            continue
        key = (login, source)
        if key in seen:
            continue
        seen.add(key)
        accounts.append(
            {
                "login": login,
                "active": "false",
                "scopes": scopes,
                "source": source,
                "token": token,
            }
        )

    if code != 0:
        return accounts

    blocks = [block.strip() for block in stdout.split("\n\n") if block.strip()]
    for block in blocks:
        login_match = re.search(r"Logged in to github\.com account (?P<login>[^\s]+)", block)
        if not login_match:
            continue
        login = login_match.group("login")
        active = "- Active account: true" in block
        token_cmd = ["gh", "auth", "token"]
        if not active:
            token_cmd += ["--user", login]
        token_code, token_stdout, _ = _run(token_cmd)
        if token_code != 0 or not token_stdout.strip():
            continue
        scope_match = re.search(r"- Token scopes: (?P<scopes>.+)", block)
        scopes = scope_match.group("scopes").strip() if scope_match else ""
        source = "gh-auth-active" if active else "gh-auth-cached"
        key = (login, source)
        if key in seen:
            continue
        seen.add(key)
        accounts.append(
            {
                "login": login,
                "active": "true" if active else "false",
                "scopes": scopes,
                "source": source,
                "token": token_stdout.strip(),
            }
        )
    return accounts


def _http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> dict[str, object]:
    request = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            return {
                "status": response.getcode(),
                "headers": dict(response.headers),
                "body": body[:500],
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": exc.code,
            "headers": dict(exc.headers),
            "body": exc.read().decode("utf-8", "replace")[:500],
        }
    except Exception as exc:  # pragma: no cover - network probe surface
        return {
            "status": 0,
            "headers": {},
            "body": str(exc),
        }


def _exchange_registry_token(
    *, login: str, token: str, repository_path: str, challenge_scope: str
) -> dict[str, object]:
    requested_scope = f"repository:{repository_path}:pull,push"
    basic = base64.b64encode(f"{login}:{token}".encode()).decode("ascii")
    params = urllib.parse.urlencode({"service": "ghcr.io", "scope": requested_scope})
    response = _http_request(
        f"https://ghcr.io/token?{params}",
        headers={"Authorization": f"Basic {basic}"},
    )
    payload: dict[str, object] = {
        "challenge_scope": challenge_scope,
        "requested_scope": requested_scope,
        "status": response["status"],
        "body": str(response["body"]),
    }
    body_text = str(response["body"])
    bearer_token = ""
    if response["status"] == 200:
        try:
            body_json = json.loads(body_text)
        except json.JSONDecodeError:
            body_json = {}
        payload["token_keys"] = sorted(body_json.keys())
        bearer_token = str(body_json.get("token") or body_json.get("access_token") or "")
        payload["token_length"] = len(bearer_token)
        payload["body"] = "<redacted: registry bearer token issued>"
    if bearer_token:
        upload = _http_request(
            f"https://ghcr.io/v2/{repository_path}/blobs/uploads/",
            method="POST",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        payload["upload_probe"] = {
            "status": upload["status"],
            "headers": upload["headers"],
            "body": upload["body"],
        }
    else:
        payload["upload_probe"] = {
            "status": 0,
            "headers": {},
            "body": "token exchange did not yield a bearer token",
        }
    return payload


def main() -> int:
    args = _parse_args()
    output_path = Path(args.output)
    expected_repository = _read_expected_repository()
    if args.repository:
        expected_repository = args.repository.strip()
    elif args.owner and args.package:
        expected_repository = f"ghcr.io/{args.owner.strip()}/{args.package.strip()}"
    repository_path = expected_repository.removeprefix("ghcr.io/").strip("/")

    anonymous_challenge = _http_request(
        f"https://ghcr.io/v2/{repository_path}/blobs/uploads/",
        method="POST",
    )
    challenge_header = str(anonymous_challenge.get("headers", {}).get("www-authenticate", ""))
    challenge_scope_match = re.search(r'scope="([^"]+)"', challenge_header)
    challenge_scope = challenge_scope_match.group(1) if challenge_scope_match else ""

    payload: dict[str, object] = {
        "version": 1,
        "expected_repository": expected_repository,
        "repository_path": repository_path,
        "anonymous_challenge": {
            "status": anonymous_challenge["status"],
            "www_authenticate": challenge_header,
            "body": anonymous_challenge["body"],
        },
        "accounts": [],
    }

    for account in _discover_accounts():
        payload["accounts"].append(
            {
                "login": account["login"],
                "active": account["active"] == "true",
                "scopes": account["scopes"],
                "source": account.get("source", "unknown"),
                "registry_exchange": _exchange_registry_token(
                    login=account["login"],
                    token=account["token"],
                    repository_path=repository_path,
                    challenge_scope=challenge_scope,
                ),
            }
        )

    write_json_artifact(
        output_path,
        payload,
        source_entrypoint="scripts/governance/probe_ghcr_registry_auth.py",
        verification_scope="ghcr-registry-auth-probe",
        source_run_id="ghcr-registry-auth-probe",
        freshness_window_hours=24,
        extra={"report_kind": "ghcr-registry-auth-probe"},
    )
    print(f"[ghcr-registry-auth-probe] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
