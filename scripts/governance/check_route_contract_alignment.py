#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_API_ORIGIN = "http://127.0.0.1:9000"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node, deep: bool = False):
    mapping = {}
    duplicates: list[tuple[str, int]] = []
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            duplicates.append((str(key), key_node.start_mark.line + 1))
        mapping[key] = loader.construct_object(value_node, deep=deep)

    if duplicates:
        duplicate_note = ", ".join(f"{key}@L{line}" for key, line in duplicates)
        raise ValueError(f"duplicate YAML keys detected: {duplicate_note}")
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def main() -> int:
    failures: list[str] = []

    openapi = _read("contracts/source/openapi.yaml")
    try:
        yaml.load(openapi, Loader=_UniqueKeyLoader)
    except ValueError as exc:
        failures.append(f"contracts/source/openapi.yaml contains duplicate keys ({exc})")
    if f"- url: {EXPECTED_API_ORIGIN}" not in openapi:
        failures.append("openapi default server drifted from canonical 9000 local origin")

    mcp_server = _read("apps/mcp/server.py")
    if (
        f'base_url=os.getenv("SOURCE_HARBOR_API_BASE_URL", "{EXPECTED_API_ORIGIN}")'
        not in mcp_server
    ):
        failures.append("apps/mcp/server.py fallback base URL drifted")
    if "register_report_tools(mcp, api_call)" not in mcp_server:
        failures.append("apps/mcp/server.py is missing reports tool registration")

    web_url = _read("apps/web/lib/api/url.ts")
    if f'return "{EXPECTED_API_ORIGIN}";' not in web_url:
        failures.append("apps/web/lib/api/url.ts local fallback drifted")

    dev_api = _read("scripts/runtime/dev_api.sh")
    if 'API_PORT="9000"' not in dev_api:
        failures.append("scripts/runtime/dev_api.sh API_PORT default drifted")
    if "default: 9000" not in dev_api:
        failures.append("scripts/runtime/dev_api.sh help text drifted from canonical 9000")

    start_here = _read("docs/start-here.md")
    if f"{EXPECTED_API_ORIGIN}/healthz" not in start_here:
        failures.append("docs/start-here.md local API health URL drifted")

    if failures:
        print("[route-contract-alignment] FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("[route-contract-alignment] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
