# Repository Collaboration Contract

This repository is a public, source-first engineering project. The public surface MUST stay thin, truthful, and easy to navigate.

## Core Rules

1. `README.md` is the front door.
2. `docs/start-here.md` is the quickstart and operator entrypoint.
3. `docs/architecture.md` is the system map.
4. `docs/testing.md` is the testing and CI contract.
5. Runtime, cache, logs, and agent workspaces MUST stay out of the tracked public surface.
6. Root documentation MUST stay concise and public-facing. Internal audit logs, rehearsal notes, and execution ledgers MUST NOT return.
7. AI agents MUST read before editing, prefer surgical changes, and verify meaningful behavior with real commands.
8. Commits, branch rewrites, and force-pushes are allowed only when explicitly authorized by the human maintainer.

## Source Of Truth

Priority order:

1. `docs/start-here.md`
2. `docs/architecture.md`
3. `docs/testing.md`
4. `README.md`

If docs and code drift, update the lower-priority surface to match the higher-priority truth.

## Public Navigation

- `README.md`
- `docs/start-here.md`
- `docs/architecture.md`
- `docs/testing.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`

## Safety Boundaries

- Never commit secrets, private credentials, or customer data.
- Never track `.agents/`, `.agent/`, `.codex/`, `.claude/`, `.runtime-cache/`, `logs/`, `log/`, or `*.log`.
- Never treat generated runtime reports as durable documentation.
- Never describe the repository as fully verified for external distribution unless the live remote workflows prove it for the current `main` head.

## Delivery Format

Execution updates SHOULD include:

1. Changed files
2. Executed commands
3. Results
4. Risks and follow-up
