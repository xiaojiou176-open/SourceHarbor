#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "public" / "assets-provenance.json"
DOC_PATH = ROOT / "docs" / "reference" / "public-assets-provenance.md"
GENERATED_HEADER = (
    "<!-- generated: scripts/governance/render_public_asset_provenance.py; do not edit directly -->"
)


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def render_markdown(payload: dict[str, object]) -> str:
    assets = payload.get("assets", [])
    lines = [
        GENERATED_HEADER,
        "",
        "# Public Asset Provenance",
        "",
        "This file is the machine-rendered file-level ledger for public presentation assets that ship with the repository.",
        "",
        "The goal is simple:",
        "",
        "- make every tracked public presentation asset addressable by path",
        "- record the current provenance granularity instead of assuming it",
        "- keep public readers from confusing `tracked in the repo` with `fully documented rights chain`",
        "",
        "## Current Asset Ledger",
        "",
        "| Asset | Kind | Role | Public Surfaces | Provenance Status | Rights Basis | Sanitization | Published Status | Follow-up |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        surfaces = "<br>".join(f"`{item}`" for item in asset.get("public_surfaces", [])) or "-"
        lines.append(
            "| "
            f"`{asset.get('path', '')}` | "
            f"`{asset.get('asset_kind', '')}` | "
            f"`{asset.get('surface_role', '')}` | "
            f"{surfaces} | "
            f"`{asset.get('provenance_status', '')}` | "
            f"`{asset.get('rights_basis', '')}` | "
            f"`{asset.get('sanitization_status', '')}` | "
            f"`{asset.get('public_distribution_status', '')}` | "
            f"`{'yes' if asset.get('follow_up_required') else 'no'}` |"
        )
    lines.extend(
        [
            "",
            "## Reading Notes",
            "",
            "- `repository-tracked-source-file` means the asset source file is present in the repository today.",
            "- `maintainer-assertion-required` means this ledger still needs an explicit maintainer-backed rights statement before broader redistribution claims should rely on it.",
            "- `non-runtime-illustration` means the asset is a deliberate presentation illustration rather than a captured runtime artifact.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render_markdown(load_config())
    if not rendered.endswith("\n"):
        rendered += "\n"
    current = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""

    if args.check:
        if current != rendered:
            print("[public-asset-provenance] FAIL")
            print("  - stale generated file: docs/reference/public-assets-provenance.md")
            print("  - run: python3 scripts/governance/render_public_asset_provenance.py")
            return 1
        print("[public-asset-provenance] PASS")
        return 0

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(rendered, encoding="utf-8")
    print("[public-asset-provenance] rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
