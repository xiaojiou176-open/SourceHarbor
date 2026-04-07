<!-- generated: docs governance control plane -->
# CI Topology

Current deterministic PR-facing CI in this repository is intentionally small and local-proof-first.

- root allowlist entries: `44`
- runtime root: `.runtime-cache`
- CI jobs in `.github/workflows/ci.yml`: `python-tests`, `web-lint`
- Pre-commit workflow jobs in `.github/workflows/pre-commit.yml`: `pre-commit`
- canonical python-tests command: `bash scripts/ci/python_tests.sh`
- pre-push is a contributor-side parity hook: it reruns env contract, placebo assertion guard, `bash scripts/ci/python_tests.sh`, and web lint locally after a deterministic `npm ci` refresh when tracked web manifests drift or `apps/web/node_modules/.bin/next` is missing.
- advisory security workflows: `codeql.yml`, `dependency-review.yml`, `zizmor.yml`, `trivy.yml`, `trufflehog.yml`
- GHCR image publish workflow runs on `ubuntu-latest` and sets up Docker Buildx before calling `scripts/ci/build_standard_image.sh`
- release evidence attestation stays in `.github/workflows/release-evidence-attest.yml`.
