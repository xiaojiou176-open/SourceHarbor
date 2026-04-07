#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPO_ROOT / "config" / "public" / "github-profile.json"


def run(*args: str) -> str:
    result = subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def load_current_topics(repo: str) -> set[str]:
    raw = run(
        "gh",
        "repo",
        "view",
        repo,
        "--json",
        "repositoryTopics",
    )
    payload = json.loads(raw or "{}")
    nodes = payload.get("repositoryTopics") or []
    return {
        node["name"]
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("name"), str)
    }


def load_current_profile(repo: str) -> dict[str, object]:
    raw = run("gh", "api", f"repos/{repo}")
    payload = json.loads(raw or "{}")
    return {
        "description": str(payload.get("description") or ""),
        "homepage": str(payload.get("homepage") or ""),
        "has_discussions": bool(payload.get("has_discussions")),
    }


def verify_profile(repo: str) -> int:
    profile = load_profile()
    desired_topics = set(profile.get("topics") or [])
    current_topics = load_current_topics(repo)
    current_profile = load_current_profile(repo)

    mismatches: list[str] = []
    if current_profile["description"] != str(profile["description"]):
        mismatches.append("description")
    if current_profile["homepage"] != str(profile["homepage"]):
        mismatches.append("homepage")
    if bool(current_profile["has_discussions"]) != bool(profile.get("enable_discussions")):
        mismatches.append("discussions")
    if current_topics != desired_topics:
        mismatches.append("topics")

    if mismatches:
        print("[github-profile] FAIL")
        print(f"repo: {repo}")
        print("mismatches: " + ", ".join(mismatches))
        print(f"description.current: {current_profile['description']}")
        print(f"description.desired: {profile['description']}")
        print(f"homepage.current: {current_profile['homepage']}")
        print(f"homepage.desired: {profile['homepage']}")
        print(
            "discussions.current: "
            + ("enabled" if current_profile["has_discussions"] else "disabled")
        )
        print(
            "discussions.desired: "
            + ("enabled" if profile.get("enable_discussions") else "disabled")
        )
        print("topics.current: " + ", ".join(sorted(current_topics)))
        print("topics.desired: " + ", ".join(sorted(desired_topics)))
        print(
            "social_preview_asset: "
            f"{profile.get('social_preview_asset', 'not specified')} "
            "(manual GitHub Settings verification still required)"
        )
        return 1

    print("[github-profile] PASS")
    print(f"repo: {repo}")
    print(
        "social_preview_asset: "
        f"{profile.get('social_preview_asset', 'not specified')} "
        "(manual GitHub Settings verification still required)"
    )
    return 0


def main() -> int:
    args = sys.argv[1:]
    verify_only = False
    if "--verify" in args:
        verify_only = True
        args = [arg for arg in args if arg != "--verify"]
    repo = args[0] if args else "xiaojiou176-open/sourceharbor"
    if verify_only:
        return verify_profile(repo)

    profile = load_profile()
    desired_topics = set(profile.get("topics") or [])
    current_topics = load_current_topics(repo)

    command = [
        "gh",
        "repo",
        "edit",
        repo,
        "--description",
        str(profile["description"]),
        "--homepage",
        str(profile["homepage"]),
    ]

    if profile.get("enable_discussions"):
        command.append("--enable-discussions")

    for topic in sorted(desired_topics - current_topics):
        command.extend(["--add-topic", topic])
    for topic in sorted(current_topics - desired_topics):
        command.extend(["--remove-topic", topic])

    subprocess.run(command, cwd=REPO_ROOT, check=True)

    print("Applied GitHub public profile")
    print(f"repo: {repo}")
    print(f"description: {profile['description']}")
    print(f"homepage: {profile['homepage']}")
    print(f"topics: {', '.join(sorted(desired_topics))}")
    print(f"discussions: {'enabled' if profile.get('enable_discussions') else 'unchanged'}")
    print(
        "social_preview_asset: "
        f"{profile.get('social_preview_asset', 'not specified')} "
        "(upload in GitHub Settings > General > Social preview; then run `python3 scripts/github/apply_public_profile.py --verify`)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
