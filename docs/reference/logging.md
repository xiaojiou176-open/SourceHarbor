# Logging Contract

SourceHarbor keeps runtime and governance logs under `.runtime-cache/logs/`.

## Required Vocabulary

- `run_id`: ties together one local or CI execution.
- `trace_id`: follows a request or command through the system.
- `request_id`: identifies a single API or task request.
- `upstream_contract_surface`: marks whether an upstream interaction is `public` or `internal`.

## Channel Layout

- app logs: `.runtime-cache/logs/app`
- component logs: `.runtime-cache/logs/components`
- test logs: `.runtime-cache/logs/tests`
- governance logs: `.runtime-cache/logs/governance`
- infra logs: `.runtime-cache/logs/infra`
- upstream logs: `.runtime-cache/logs/upstreams`

## Runtime Evidence Sidecars

- Runtime evidence written under `.runtime-cache/evidence/**` must carry a sibling `.meta.json` sidecar.
- The sidecar must include:
  - `artifact_path`
  - `created_at`
  - `source_entrypoint`
  - `source_run_id`
  - `verification_scope`
- Evidence-bearing run stores such as UI audit receipts must also register the artifact in `.runtime-cache/reports/evidence-index/<run_id>.json` so governance checks can trace the run without a later backfill pass.

## Failure Receipts

- Long-running helpers that start background services must emit a durable failure receipt before returning non-zero.
- For `full_stack` failures, `.runtime-cache/run/full-stack/last_failure_reason` is the SSOT failure marker.
- If a worker/web/api rollback runs after a failed start or readiness gate, the rollback must remove the corresponding `*.pid` receipt instead of leaving stale process markers behind.

## Why This Exists

The goal is simple: when a run fails, operators should be able to trace it with receipts instead of guesswork.
