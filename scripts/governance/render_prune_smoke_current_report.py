#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import parse_iso8601, read_runtime_metadata, rel_path, write_text_artifact

GENERATED_HEADER = "<!-- runtime-generated: prune-smoke-current-report; do not edit directly -->\n"
MAINTENANCE_REPORT = (
    ROOT / ".runtime-cache" / "reports" / "governance" / "runtime-cache-maintenance.json"
)
SMOKE_JSONL = ROOT / ".runtime-cache" / "logs" / "tests" / "api-real-smoke-local.jsonl"
OUTPUT_PATH = ROOT / ".runtime-cache" / "reports" / "governance" / "prune-smoke-current-report.md"

SMOKE_MILESTONES = (
    "verifying postgres connectivity",
    "creating isolated smoke database",
    "applying migrations to isolated smoke database",
    "detected reachable temporal server",
    "starting API smoke server",
    "starting temporary worker for cleanup workflow probe",
    "temporary worker is online for task queue",
    "running integration smoke tests with API_INTEGRATION_SMOKE_STRICT=1",
    "running API -> Temporal -> worker cleanup workflow closure probe",
    "api -> temporal -> worker cleanup workflow closure probe passed",
    "real postgres integration smoke passed",
)


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _load_jsonl_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    events: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _latest_run_id(events: list[dict]) -> str:
    for event in reversed(events):
        run_id = str(event.get("run_id") or event.get("test_run_id") or "").strip()
        if run_id:
            return run_id
    return ""


def _select_smoke_run(events: list[dict], metadata: dict | None) -> tuple[str, list[dict]]:
    metadata = metadata or {}
    selected_run_id = str(metadata.get("source_run_id") or "").strip()
    if not selected_run_id:
        selected_run_id = _latest_run_id(events)
    if not selected_run_id:
        return "", []
    selected_events = [
        event
        for event in events
        if str(event.get("run_id") or event.get("test_run_id") or "").strip() == selected_run_id
    ]
    return selected_run_id, selected_events


def _format_duration_seconds(seconds: float) -> str:
    total_seconds = int(round(seconds))
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, remaining_seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:02d}s"
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours}h {remaining_minutes:02d}m"


def _format_timestamp(value: str) -> str:
    return parse_iso8601(value).strftime("%Y-%m-%d %H:%M:%SZ")


def _bytes_to_human(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB")
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{int(size_bytes)}B"


def _collect_smoke_summary(events: list[dict]) -> tuple[str, list[str], list[tuple[str, str]]]:
    messages: list[str] = []
    error_messages: list[str] = []
    timeline: list[tuple[str, str]] = []
    seen_timeline_messages: set[str] = set()

    for event in events:
        message = str(event.get("message") or "").strip()
        if not message:
            continue
        messages.append(message)
        severity = str(event.get("severity") or "").strip().lower()
        event_name = str(event.get("event") or "").strip().lower()
        if severity == "error" or event_name.endswith("_error") or "failure_kind=" in message:
            error_messages.append(message)
        if (
            any(marker in message for marker in SMOKE_MILESTONES)
            and message not in seen_timeline_messages
        ):
            timestamp = str(event.get("ts") or "").strip()
            timeline.append((timestamp, message))
            seen_timeline_messages.add(message)

    smoke_passed = any("real postgres integration smoke passed" in message for message in messages)
    status = (
        "pass" if smoke_passed and not error_messages else "fail" if error_messages else "unknown"
    )
    return status, error_messages, timeline


def _maintenance_ok(report: dict | None) -> bool:
    return isinstance(report, dict) and str(report.get("status") or "").strip() == "pass"


def render_report() -> Path:
    maintenance_report = _load_json(MAINTENANCE_REPORT)
    maintenance_meta = read_runtime_metadata(MAINTENANCE_REPORT)
    smoke_meta = read_runtime_metadata(SMOKE_JSONL)
    smoke_events = _load_jsonl_events(SMOKE_JSONL)
    smoke_run_id, selected_smoke_events = _select_smoke_run(smoke_events, smoke_meta)
    smoke_status, smoke_errors, smoke_timeline = _collect_smoke_summary(selected_smoke_events)

    maintenance_commit = str((maintenance_meta or {}).get("source_commit") or "").strip()
    smoke_commit = str((smoke_meta or {}).get("source_commit") or "").strip()
    commit_aligned = bool(
        maintenance_commit and smoke_commit and maintenance_commit == smoke_commit
    )

    maintenance_created_at = str((maintenance_meta or {}).get("created_at") or "").strip()
    smoke_created_at = str((smoke_meta or {}).get("created_at") or "").strip()
    same_batch_note = "unknown"
    if maintenance_created_at and smoke_created_at:
        delta_seconds = (
            parse_iso8601(smoke_created_at) - parse_iso8601(maintenance_created_at)
        ).total_seconds()
        if delta_seconds >= 0:
            same_batch_note = (
                f"smoke artifact followed maintenance by {_format_duration_seconds(delta_seconds)}"
            )
        else:
            same_batch_note = (
                "maintenance artifact was refreshed after smoke by "
                f"{_format_duration_seconds(abs(delta_seconds))}; read this as same-commit closure evidence, "
                "not strict execution order"
            )

    issues: list[str] = []
    if maintenance_report is None:
        issues.append("missing runtime-cache maintenance report")
    if maintenance_meta is None:
        issues.append("missing runtime-cache maintenance metadata")
    if smoke_meta is None:
        issues.append("missing api-real-smoke-local jsonl metadata")
    if not smoke_run_id:
        issues.append("no current smoke run id could be selected from jsonl metadata or log lines")
    if smoke_status != "pass":
        if smoke_errors:
            issues.extend(smoke_errors[:3])
        else:
            issues.append("current smoke run does not contain a pass marker")
    if not commit_aligned and maintenance_commit and smoke_commit:
        issues.append("maintenance and smoke artifacts do not point to the same commit")

    if issues:
        overall_status = "fail" if any("missing" not in issue for issue in issues) else "partial"
    else:
        overall_status = (
            "pass"
            if _maintenance_ok(maintenance_report) and smoke_status == "pass" and commit_aligned
            else "partial"
        )

    lines = [
        GENERATED_HEADER.rstrip(),
        "# Prune -> Smoke Current Report",
        "",
        "This runtime-owned report closes the current `runtime-cache-maintenance/prune -> api-real-smoke-local` chain using only existing `.runtime-cache/**` artifacts. It does not invent a new receipt and it does not summarize historical runs by hand.",
        "",
        "## Verdict",
        "",
        f"- overall_status: `{overall_status}`",
        f"- maintenance_status: `{str((maintenance_report or {}).get('status') or 'missing')}`",
        f"- smoke_status: `{smoke_status}`",
        f"- same_commit: `{str(commit_aligned).lower()}`",
        f"- batch_note: {same_batch_note}",
        "- smoke selection rule: use `.runtime-cache/logs/tests/api-real-smoke-local.jsonl.meta.json` `source_run_id` as the current run anchor so older historical lines in the shared jsonl file do not leak into this report",
        "- maintenance reading rule: `runtime-cache-maintenance.json` is the prune/maintenance inventory receipt; freshness pass/fail still comes from `check_runtime_cache_freshness.py`",
    ]

    if maintenance_created_at:
        lines.append(f"- maintenance_created_at: `{_format_timestamp(maintenance_created_at)}`")
    if smoke_created_at:
        lines.append(f"- smoke_created_at: `{_format_timestamp(smoke_created_at)}`")
    if maintenance_commit:
        lines.append(f"- maintenance_commit: `{maintenance_commit}`")
    if smoke_commit:
        lines.append(f"- smoke_commit: `{smoke_commit}`")
    if smoke_run_id:
        lines.append(f"- smoke_run_id: `{smoke_run_id}`")

    if issues:
        lines.extend(["", "## Issues", ""])
        for issue in issues:
            lines.append(f"- {issue}")

    lines.extend(["", "## Maintenance Snapshot", ""])
    if isinstance(maintenance_report, dict):
        subdirectories = maintenance_report.get("subdirectories") or {}
        if not isinstance(subdirectories, dict) or not subdirectories:
            lines.append("- maintenance report does not declare any subdirectory snapshots")
        for name in sorted(subdirectories):
            subreport = subdirectories.get(name) or {}
            if not isinstance(subreport, dict):
                continue
            lines.append(
                "- "
                f"`{name}`: status inherits maintenance=`{maintenance_report.get('status', 'unknown')}`, "
                f"files={int(subreport.get('file_count') or 0)}, "
                f"size={_bytes_to_human(int(subreport.get('size_bytes') or 0))}, "
                f"expired={int(subreport.get('expired_count') or 0)}, "
                f"stale={int(subreport.get('stale_count') or 0)}"
            )
    else:
        lines.append("- maintenance report is missing")

    lines.extend(["", "## Smoke Timeline", ""])
    if smoke_timeline:
        for timestamp, message in smoke_timeline:
            prefix = f"`{_format_timestamp(timestamp)}` " if timestamp else ""
            lines.append(f"- {prefix}{message}")
    else:
        lines.append("- current smoke timeline could not be reconstructed from the selected run")

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- maintenance report: `{rel_path(MAINTENANCE_REPORT)}`",
            f"- maintenance metadata: `{rel_path(MAINTENANCE_REPORT.with_name(MAINTENANCE_REPORT.name + '.meta.json'))}`",
            f"- smoke jsonl: `{rel_path(SMOKE_JSONL)}`",
            f"- smoke metadata: `{rel_path(SMOKE_JSONL.with_name(SMOKE_JSONL.name + '.meta.json'))}`",
            f"- raw smoke log: `{rel_path(ROOT / '.runtime-cache' / 'logs' / 'tests' / 'api-real-smoke-local.log')}`",
        ]
    )

    write_text_artifact(
        OUTPUT_PATH,
        "\n".join(lines) + "\n",
        source_entrypoint="scripts/governance/render_prune_smoke_current_report.py",
        verification_scope="runtime-cache-current-report",
        source_run_id=smoke_run_id or "runtime-cache-current-report",
        freshness_window_hours=24,
        extra={"report_kind": "prune-smoke-current-report", "overall_status": overall_status},
    )
    return OUTPUT_PATH


def main() -> int:
    output_path = render_report()
    print(f"[prune-smoke-current-report] wrote {rel_path(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
