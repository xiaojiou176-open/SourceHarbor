# Contributing

Thank you for contributing to SourceHarbor.

## Development Workflow

1. Sync dependencies:

```bash
set -a
source .env
set +a
UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$SOURCE_HARBOR_CACHE_ROOT/project-venv}" \
  uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci
```

1. Prepare environment files from `env/`.
2. Run targeted tests before opening a pull request.
3. Keep docs aligned with user-visible behavior and operator workflows.

## Pull Request Expectations

- Use focused commits.
- Include tests or a clear rationale when tests are not practical.
- Avoid committing secrets, runtime artifacts, or local agent workspaces.
- Keep public documentation concise and accurate.
- Route open-ended product questions and workflow ideas through GitHub Discussions before turning them into large pull requests.

## Required Checks

At minimum, contributors should run:

```bash
python3 scripts/governance/check_env_contract.py --strict
python3 scripts/governance/check_test_assertions.py
npm --prefix apps/web run lint
bash scripts/ci/python_tests.sh
```
