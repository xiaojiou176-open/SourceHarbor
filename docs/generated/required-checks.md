<!-- generated: docs governance control plane -->
# Required Checks

These are the deterministic GitHub Actions checks currently documented as the repository's pull-request path.

Local Git hooks may rerun overlapping checks, but they are contributor-side guardrails rather than remote required checks.

| Check | Workflow | Why it exists |
| --- | --- | --- |
| `python-tests` | `ci.yml` | Verifies API, worker, and MCP Python surfaces with the documented in-memory SQLite test path. |
| `web-lint` | `ci.yml` | Keeps the web command center lint-clean. |
| `pre-commit` | `pre-commit.yml` | Runs the all-files hygiene gate for YAML, secrets, Ruff, Biome, Markdown, ShellCheck, and Actionlint. |
