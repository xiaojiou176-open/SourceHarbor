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
9. Browser automation MUST stay repo-scoped, state-aware, and cleanup-first: do not accumulate extra Chrome/Chromium/Safari instances, cloned profiles, or large tab sets, and do not borrow browser state opened by other repos or other L1s on the same machine.
10. Docker and runtime residue MUST stay governed: do not leave disposable containers, caches, or duplicate runtime workspaces behind after verification when they are no longer needed.
11. External-account writes stay opt-in only: never change GitHub profile settings, browser-signed-in account state, Resend/Google account settings, or other third-party account data unless the human maintainer explicitly authorizes that exact write.
12. Login-state probing MUST stay bounded: if the repo-scoped real browser profile is still not logged in after one or two focused checks, record a blocker and stop escalating browser churn.
13. Browser focus and machine-wide resource contention MUST be respected: avoid stealing desktop focus when possible, and if the machine already has more than six browser instances open, wait for other repo workflows to release resources before opening another one.
14. Current-cycle branch, worktree, and PR residue MUST be closed out before declaring completion: merge active work into `main`, or evidence-close and delete branches that are already fully absorbed.
15. Release truth and current-`main` truth MUST be stated separately and honestly: if the latest release lags current `main`, document that gap explicitly instead of implying they are the same snapshot.

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
- Treat `.agents/Plans/` as a local execution ledger compatibility bridge, not as a durable public repository surface.
- Never treat generated runtime reports as durable documentation.
- Never describe the repository as fully verified for external distribution unless the live remote workflows prove it for the current `main` head.
- Do not leave human-created branch, worktree, or PR residue behind after current-cycle closeout when Git evidence shows the work has already landed or been fully subsumed by `main`.
- Before using Chrome/Chromium/Safari automation, confirm which repo owns the live browser/process/profile state and open only the repo-scoped state you need for the current task.
- Close unnecessary browser tabs/windows and clean repo-cloned browser profiles after verification so other repos and other L1s do not inherit or collide with this repo's state.
- Treat login-state absence as a fast blocker, not an invitation to spin up endless browser retries: one or two repo-scoped checks are enough before you stop and report it.
- Do not open a new browser instance when the machine is already carrying more than six browser instances; wait for other repo workflows to clean up first.
- Prefer background or non-focus-stealing browser operations whenever the tool supports them so repo work does not hijack the whole desktop.
- Treat Docker containers, copied runtimes, and large caches as governed runtime state: measure them, keep them attributable, and clean disposable residue instead of letting it accumulate across repos.
- Keep release truth, current `main` truth, and external proof truth in separate ledgers so docs and outward claims never imply a release is current when it is only the latest historical tag.
- Treat third-party services and signed-in web accounts as read-only by default; explicit human approval is required before any write action.

## Host Safety Contract

- `worker-safe` is the default mode for this repository.
- Repo-tracked automation must never use `pkill`, `killall`, `killpg(...)`, shell `kill -9`, `process.kill(...)` / `os.kill(...)` with `pid <= 0`, `osascript`, `System Events`, `loginwindow`, or Force Quit control paths.
- Cleanup must stay exact-scope: recorded child handles, exact `systemd` unit names, repo-owned browser roots, and repo-owned Docker labels only.
- Exact child-process teardown is allowed only when the same function or fixture created that child and still holds the live handle; broad host cleanup by pattern is forbidden.
- Detached browser/runtime launch is review-required only and must stay inside repo-owned browser roots or directly held child handles.
- Host-safety drift is enforced by `python3 scripts/governance/check_host_safety_contract.py` in pre-commit, pre-push, and CI.

## Delivery Format

Execution updates SHOULD include:

1. Changed files
2. Executed commands
3. Results
4. Risks and follow-up
