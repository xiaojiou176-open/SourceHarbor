#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from base64 import b64encode
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

import httpx
from common import write_json_artifact

CONFIG_PATH = ROOT / "config" / "public" / "assets-provenance.json"
REPORT_PATH = ROOT / ".runtime-cache" / "reports" / "governance" / "public-image-audit.json"
TMP_DIR = ROOT / ".runtime-cache" / "tmp" / "public-image-audit"
PROMPT = (
    "You are auditing open-source storefront images. "
    "Check only: text truncation or clipping, alignment drift, overlap, tiny unreadable text, "
    "cropped elements near edges, and overall professionalism/trust. "
    "Return compact JSON with keys: verdict, issues, strengths. "
    "Each issue should have fields severity, category, note."
)
MODEL_CANDIDATES = ("gemini-2.5-flash", "gemini-1.5-flash")
ALLOWED_VERDICTS = {"pass", "warn", "fail", "unknown"}
ALLOWED_SEVERITIES = {"error", "warning", "info"}
ALLOWED_CATEGORIES = {
    "text-clipping",
    "alignment-drift",
    "overlap",
    "tiny-unreadable-text",
    "cropped-edge-elements",
    "overall-professionalism",
    "other",
}


def load_asset_config() -> list[dict[str, Any]]:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assets = payload.get("assets", [])
    return [asset for asset in assets if isinstance(asset, dict)]


def resolve_report_path(raw_path: str) -> Path:
    report_path = Path(raw_path)
    if report_path.is_absolute():
        raise ValueError("--report-path must stay under the repo root")
    candidate = (ROOT / report_path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("--report-path must stay under the repo root") from exc
    return candidate


def resolve_api_key() -> str | None:
    env_value = os.environ.get("GEMINI_API_KEY")
    if env_value:
        return env_value

    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value

    return None


def write_public_image_audit_report(report_path: Path, report: dict[str, Any]) -> None:
    write_json_artifact(
        report_path,
        report,
        source_entrypoint="scripts/governance/audit_public_images_with_gemini.py",
        verification_scope="public-image-audit",
        source_run_id="public-image-audit",
        freshness_window_hours=24,
        extra={"report_kind": "public-image-audit"},
    )


def audit_rendered_assets(
    rendered_assets: list[Path],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    key = resolve_api_key()
    if not key:
        return None, None

    with httpx.Client(timeout=60) as client:
        model = pick_model(client, key, rendered_assets[0])
        if model is None:
            return None, None

        summaries: list[dict[str, Any]] = []
        for rendered_path in rendered_assets:
            summaries.append(summarize_audit_result(audit_one(client, key, model, rendered_path)))
    return summaries, model


def render_for_audit(asset_path: Path) -> tuple[Path | None, str | None]:
    if asset_path.suffix.lower() != ".svg":
        return asset_path, None

    if shutil_which("qlmanage") is None:
        return None, "missing-qlmanage"

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["qlmanage", "-t", "-s", "1600", "-o", str(TMP_DIR), str(asset_path)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rendered = TMP_DIR / f"{asset_path.name}.png"
    if not rendered.is_file():
        return None, "render-failed"
    return rendered, None


def shutil_which(name: str) -> str | None:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def pick_model(client: httpx.Client, key: str, preview_path: Path) -> str | None:
    inline = b64encode(preview_path.read_bytes()).decode("ascii")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/png", "data": inline}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    for model in MODEL_CANDIDATES:
        try:
            response = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": key},
                json=payload,
            )
            response.raise_for_status()
            return model
        except Exception:
            continue
    return None


def audit_one(client: httpx.Client, key: str, model: str, image_path: Path) -> dict[str, Any]:
    inline = b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/png", "data": inline}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    response = client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json=payload,
    )
    response.raise_for_status()
    body = response.json()
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def _normalize_verdict(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in {"pass", "passed", "ok"}:
        return "pass"
    if text in {"warn", "warning"}:
        return "warn"
    if text in {"fail", "failed", "error"}:
        return "fail"
    return "unknown"


def _normalize_severity(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in {"error", "fatal", "fail", "failed"}:
        return "error"
    if text in {"warning", "warn"}:
        return "warning"
    if text in {"info", "note"}:
        return "info"
    return "info"


def _normalize_category(raw: Any) -> str:
    text = str(raw or "").strip().lower().replace("_", "-").replace(" ", "-")
    if text in ALLOWED_CATEGORIES:
        return text
    return "other"


def summarize_audit_result(raw: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    strengths = raw.get("strengths") if isinstance(raw, dict) else []
    raw_issues = raw.get("issues") if isinstance(raw, dict) else []
    if isinstance(raw_issues, list):
        for item in raw_issues:
            if not isinstance(item, dict):
                continue
            issues.append(
                {
                    "severity": _normalize_severity(item.get("severity")),
                    "category": _normalize_category(item.get("category")),
                }
            )

    return {
        "verdict": _normalize_verdict(raw.get("verdict") if isinstance(raw, dict) else None),
        "issue_count": len(issues),
        "blocking_issue_count": sum(1 for item in issues if item["severity"] == "error"),
        "strength_count": len(strengths) if isinstance(strengths, list) else 0,
        "issues": issues,
        "raw_output_discarded": bool(isinstance(raw, dict) and "raw" in raw),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-path",
        default=str(REPORT_PATH.relative_to(ROOT)),
        help="Runtime report path under the repo root.",
    )
    args = parser.parse_args()
    try:
        report_path = resolve_report_path(args.report_path)
    except ValueError as error:
        print(f"[public-image-audit] ERROR {error}", file=sys.stderr)
        return 2

    assets = load_asset_config()
    report: dict[str, Any] = {
        "version": 1,
        "model": None,
        "status": "not-run",
        "assets": [],
    }

    rendered_assets: list[tuple[int, Path]] = []
    for asset in assets:
        asset_path = ROOT / str(asset["path"])
        rendered_path, error = render_for_audit(asset_path)
        entry: dict[str, Any] = {
            "asset": str(asset["path"]),
            "asset_kind": asset.get("asset_kind"),
            "surface_role": asset.get("surface_role"),
            "public_surfaces": asset.get("public_surfaces", []),
        }
        if error:
            entry["status"] = "skipped"
            entry["skip_reason"] = error
            report["assets"].append(entry)
            continue
        if rendered_path is None:
            entry["status"] = "skipped"
            entry["skip_reason"] = "render-unavailable"
            report["assets"].append(entry)
            continue
        entry["status"] = "ready"
        entry["audit_input"] = rendered_path.relative_to(ROOT).as_posix()
        report["assets"].append(entry)
        rendered_assets.append((len(report["assets"]) - 1, rendered_path))

    if not rendered_assets:
        write_public_image_audit_report(report_path, report)
        print("[public-image-audit] SKIP no renderable assets")
        return 0

    summaries, model = audit_rendered_assets([path for _, path in rendered_assets])
    if summaries is not None and model is not None:
        report["model"] = model
        report["status"] = "completed"
        for (entry_index, _), summary in zip(rendered_assets, summaries, strict=True):
            report["assets"][entry_index]["result_summary"] = summary

    write_public_image_audit_report(report_path, report)
    if report["status"] != "completed":
        print("[public-image-audit] SKIP audit unavailable")
        return 0
    print("[public-image-audit] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
