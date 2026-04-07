#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from render_public_asset_provenance import DOC_PATH, load_config, render_markdown

REQUIRED_FIELDS = {
    "path",
    "asset_kind",
    "surface_role",
    "public_surfaces",
    "provenance_status",
    "rights_basis",
    "sanitization_status",
    "public_distribution_status",
    "follow_up_required",
    "notes",
}


def main() -> int:
    payload = load_config()
    errors: list[str] = []
    assets = payload.get("assets")
    if not isinstance(assets, list):
        print("[public-asset-provenance] FAIL")
        print("  - config/public/assets-provenance.json: `assets` must be a list")
        return 1

    declared_paths: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            errors.append(
                "config/public/assets-provenance.json: all `assets` entries must be objects"
            )
            continue
        missing = sorted(REQUIRED_FIELDS - set(asset))
        if missing:
            errors.append(
                "config/public/assets-provenance.json: "
                f"`{asset.get('path', '<unknown>')}` missing fields: {', '.join(missing)}"
            )
            continue
        path = str(asset["path"])
        asset_path = ROOT / path
        if path in declared_paths:
            errors.append(f"config/public/assets-provenance.json: duplicate asset path `{path}`")
        declared_paths.add(path)
        if not asset_path.is_file():
            errors.append(
                f"config/public/assets-provenance.json: asset path missing on disk: `{path}`"
            )
        public_surfaces = asset.get("public_surfaces")
        if not isinstance(public_surfaces, list) or not public_surfaces:
            errors.append(
                f"config/public/assets-provenance.json: `{path}` must list at least one public surface"
            )
        else:
            for surface in public_surfaces:
                if not isinstance(surface, str) or not surface.strip():
                    errors.append(
                        f"config/public/assets-provenance.json: `{path}` has an invalid public surface entry"
                    )
                    continue
                surface_path = ROOT / surface
                if surface.startswith("config/"):
                    if not surface_path.is_file():
                        errors.append(
                            f"config/public/assets-provenance.json: missing config surface `{surface}`"
                        )
                elif not surface_path.exists():
                    errors.append(
                        f"config/public/assets-provenance.json: missing public surface `{surface}`"
                    )

    for asset_path in sorted((ROOT / "docs" / "assets").glob("*")):
        if asset_path.is_file():
            rel = asset_path.relative_to(ROOT).as_posix()
            if rel not in declared_paths:
                errors.append(f"docs/assets file missing provenance entry: `{rel}`")

    profile_path = ROOT / "config" / "public" / "github-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    social_preview = str(profile.get("social_preview_asset") or "").strip()
    if social_preview and social_preview not in declared_paths:
        errors.append(
            "config/public/github-profile.json: "
            f"social_preview_asset `{social_preview}` is missing from config/public/assets-provenance.json"
        )

    expected_doc = render_markdown(payload) + "\n"
    current_doc = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    if current_doc != expected_doc:
        errors.append(
            "docs/reference/public-assets-provenance.md is stale; run render_public_asset_provenance.py"
        )

    if errors:
        print("[public-asset-provenance] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[public-asset-provenance] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
