# Program Closeout Matrix

This document is the exhaustive closeout ledger for the Prompt 1-5 program.

It maps archive intent to current repo truth, current local runtime truth, and the final classification used for closeout.

Truth rules:

- `repo truth` means code and tracked docs in this workspace
- `local runtime truth` means fresh commands run on this machine during the Prompt 1-5 program
- `remote truth` still requires live GitHub / release / secret-backed verification and is never inferred from local code alone
- seeded local demo proof is useful local evidence, but it is not remote production proof

Classification meanings:

- `Verified and ready`: implemented and backed by fresh evidence at the intended scope
- `Implemented`: shipped in repo, but proof is weaker than fully ready or bounded to a narrower scope
- `Implemented but still risky`: implemented, but still limited by quality gaps, runtime instability, or narrow proof
- `Partially implemented`: meaningful pieces landed, but the intended value is not yet closed
- `Deferred by design`: intentionally left for a later phase
- `Blocked by genuine external dependency`: cannot finish honestly without secrets, accounts, or external platform access
- `Rejected / intentionally not pursued`: consciously not the direction for the current product truth

Wave column rule:

- `Wave` in this matrix records the wave or spike where the item was finally delivered, explicitly closed, or deliberately deferred during Prompt 1-5.
- It does not try to preserve the original proposed-wave column verbatim.

## 1. Infrastructure / Stability / First-run / Full-stack / Smoke

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` contract on `postgresql+psycopg://...` | R3-R4 | `.env.example`, bootstrap, runtime scripts, tests all aligned on psycopg dialect | `.env.example`, `scripts/runtime/bootstrap_full_stack.sh`, `scripts/runtime/full_stack.sh`, `python3 scripts/governance/check_env_contract.py --strict` | Wave 0 | Verified and ready | Keep old local `.env` files from drifting back |
| host-vs-container Postgres split-brain reduction | R4 | Clean path is container-first on `CORE_POSTGRES_PORT=15432`; docs and doctor explain the split | `docs/start-here.md`, `docs/testing.md`, `docs/runtime-truth.md`, `./bin/doctor` | Wave 0 | Verified and ready | Follow `.runtime-cache/run/full-stack/resolved.env` when local ports move |
| worker signature mismatch false-negative | R4 | full-stack no longer depends on repo-root string in worker cmdline | `scripts/runtime/full_stack.sh`, worker regression tests in `apps/worker/tests/test_full_stack_env_runtime_regression.py` | Wave 0 | Verified and ready | None |
| clean-path `bootstrap -> up -> smoke` | R3-R4 | fresh 2026-04-01 re-audit re-proved `bootstrap -> up -> status -> doctor` with API on `9000` and web re-homed to `13000` when `3000` was occupied; the remaining long live-smoke lane is external rather than repo-local drift | `./bin/bootstrap-full-stack --install-deps 0`, `./bin/full-stack up`, `./bin/full-stack status`, `./bin/doctor --json`, `curl http://127.0.0.1:9000/healthz`, `curl http://127.0.0.1:13000/ops` | Wave 0 | Verified and ready | Long live smoke still depends on YouTube provider preflight and sender configuration |
| first-run self-diagnosis flow | R2 | real `bin/doctor` plus runtime doctor implementation and tests are present | `bin/doctor`, `scripts/runtime/doctor.py`, `apps/api/tests/test_runtime_doctor.py` | Wave 2 | Verified and ready | Does not replace full smoke |
| runtime residue / hygiene | R1 | workspace hygiene and governance checks exist and are part of the local contract | `scripts/runtime/workspace_hygiene.sh`, `python3 scripts/governance/check_env_contract.py --strict`, `python3 scripts/governance/check_docs_governance.py`, `python3 scripts/governance/check_test_assertions.py` | Wave 0 | Implemented | Continue to keep runtime residue out of tracked public surfaces |
| `TEMPORAL_TASK_QUEUE` naming alignment | R1 | public and runtime defaults aligned on `sourceharbor-worker` | `.env.example`, bootstrap/full-stack scripts, worker env logs | Wave 0 | Verified and ready | None |

## 2. Data Truth / Runtime Truth

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| explicit Postgres / SQLite / artifacts truth map | R1 | published as public docs and linked from front-door surfaces | `docs/runtime-truth.md`, `README.md`, `docs/start-here.md`, `docs/proof.md` | Wave 2 | Verified and ready | Keep remote proof separate from local truth |
| promote `IngestRun`, `Job`, `KnowledgeCard` as operator-visible truth objects | R1-R2 | visible in jobs/feed/ops/watchlists/trends surfaces, but not every object has an equally mature front-door narrative | `apps/web/app/jobs/page.tsx`, `apps/web/app/ops/page.tsx`, `apps/web/app/trends/page.tsx` | Waves 1-3 | Partially implemented | keep improving the object model in docs and UX, not just route count |

## 3. Core Product Enhancements

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| operator-facing Search console | R2, R7 | real `/search` route over retrieval API | `apps/web/app/search/page.tsx`, web Vitest, README/docs front door | Wave 1 | Verified and ready | route is real; retrieval quality remains a separate corpus-proof question |
| Ask-your-sources front door | R7 | truthful MVP exists as grounded retrieval-first shell | `apps/web/app/search/page.tsx` with ask intent, `docs/blueprints/2026-03-31-ask-your-sources-grounded-answer-contract.md` | Wave 1 | Implemented but still risky | answer-layer backend contract is still intentionally absent |
| ops inbox / exception inbox | R2 | real API + Web inbox landed | `apps/api/app/routers/ops.py`, `apps/api/app/services/ops.py`, `apps/web/app/ops/page.tsx`, tests | Wave 2 | Verified and ready | gate contents still reflect external blockers truthfully |
| evidence / share bundle | R2 | real bundle route exists and returns internal collaboration payloads | `apps/api/app/routers/jobs.py`, `apps/api/app/services/jobs.py`, `apps/api/tests/test_jobs_bundle_route.py`, fresh local bundle probe | Wave 3 | Verified and ready | scope is internal bundle, not public release proof |
| stronger knowledge-layer product narrative | R1 | Search / Ask / Knowledge / Watchlists / Trends now expose the knowledge layer as a product idea | `README.md`, `apps/web/app/page.tsx`, `apps/web/app/search/page.tsx`, `apps/web/app/watchlists/page.tsx` | Waves 1-3 | Implemented | keep tying this narrative to grounded evidence rather than generic AI copy |

## 4. AI Capability Enhancements

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| tighten Knowledge Cards + retrieval integration | R5 | cards exist in DB, jobs, trends, and bundles; retrieval path exists but keyword proof is still thin on the current sample corpus | `apps/api/app/services/retrieval.py`, `apps/api/app/services/knowledge.py`, jobs bundle and trend payloads | Waves 1-4 | Partially implemented | artifact-level retrieval quality proof still needs stronger real corpus validation |
| move UI audit / computer use into controlled capability | R5 | both services and routes exist; readiness gates are visible in ops | `apps/api/app/services/ui_audit.py`, `apps/api/app/services/computer_use.py`, `/api/v1/ops/inbox` | Wave 2 | Implemented but still risky | still bounded by input contract quality and Gemini secrets |
| live validation for UI audit | R4 | base audit path was proven; Gemini review remains optional and secret-gated | `ui_audit` service, prior live-hardening evidence, ops gate | Wave 2 | Implemented but still risky | `GEMINI_API_KEY` still required for Gemini review layer |
| live validation for computer use | R4 | service is real; maintainer-local proof reached the provider, but the lane still depends on valid screenshot/input quality and env-dependent Gemini access | `computer_use` service, ops gate, maintainer-local smoke evidence | Wave 2 | Implemented but still risky | keep it env-dependent and input-contract-bound, not a universal no-secret promise |
| Agent Autopilot research ops | R2 | supporting primitives exist, but the productized flow is still a Bet | workflows router, MCP workflows tools, notifications, Prompt 5 spike artifact | Prompt 5 spike | Deferred by design | only pursue as human-in-the-loop MVP, not autonomous mode |

## 5. MCP Enhancements / Front-door

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| dedicated MCP quickstart / MCP page | R7 | landed in docs and Web | `docs/mcp-quickstart.md`, `apps/web/app/mcp/page.tsx`, `apps/mcp/server.py` | Wave 1 | Verified and ready | advanced tools still inherit their own secret/runtime gates |
| MCP tool maturity labeling | R5 | partially addressed through docs honesty, but no formal tier system yet | README/docs/ops gates | Wave 2 | Partially implemented | add explicit maturity tiers only if it helps and stays honest |
| higher-level research-task MCP flows | R5 | workflows tools exist, but no polished research-opinionated orchestration layer | `apps/mcp/tools/workflows.py`, `apps/api/app/routers/workflows.py` | Waves 2-5 | Partially implemented | Autopilot spike defines the safe next slice |

## 6. Web / UI / Operator Console

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| Search in main navigation | R2, R7 | landed | sidebar / route-transition tests, `apps/web/components/sidebar.tsx` | Wave 1 | Verified and ready | None |
| homepage reframed as AI knowledge / research front door | R7 | landed | `apps/web/app/page.tsx`, README hero copy | Wave 1 | Verified and ready | keep copy aligned with proof boundary |
| explicit MCP / operator use-case pages | R7 | MCP page and use-case pages exist | `/mcp`, `/use-cases/[slug]`, `apps/web/lib/demo-content.ts` | Waves 1-3 | Implemented | use-case coverage can expand without overclaiming hosted readiness |

## 7. Docs / Proof / Truth Surface

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| align first-run truth / runtime truth / proof truth | R1, R3-R4 | done across README/start-here/testing/proof/runtime-truth | front-door docs + governance checks | Waves 0-2 | Verified and ready | keep remote proof claims explicit |
| remove legacy naming residue | R1 | some residue still exists in internals such as `video_digest_v1` | models/routes/services still use legacy kind names | Wave 2 | Partially implemented | change only when contract migration is worth the churn |
| align release surface and current `main` | R4 | public docs now distinguish release-side proof from local proof; current `main` also has fresh successful CI/pre-commit/manual external-lane runs, but latest release still lags current `main` | `docs/proof.md`, `artifacts/releases/README.md`, GitHub Actions runs on `4a59b462c6d624985b5ca5ae58c527ba95a1f0f3` | Waves 2-5 | Implemented but still risky | cut a new release only when you need release-aligned remote proof for current `main` |

## 8. Search / Ask / Knowledge Assets

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| retrieval operator UI | R2, R7 | real UI exists | `/search`, web tests, README/docs | Wave 1 | Implemented but still risky | local keyword probe on the current sample corpus still needs stronger quality proof |
| Ask with citations | R7 | truthful retrieval-first Ask landed | ask front door + contract blueprint | Wave 1 | Implemented but still risky | no answer-layer synthesis yet |
| retrieval live quality validation with non-empty corpus | R4 | local seeded corpus and jobs exist, but search quality is not fully closed | local seeded jobs/cards/artifacts, fresh keyword probe still weak | Waves 2-5 | Partially implemented | needs better artifact-shape and semantic/hybrid evaluation with realistic corpus |
| sample corpus / playground | R7 | landed with explicit sample labeling | `docs/samples/README.md`, `docs/samples/sourceharbor-demo-corpus.json`, `/playground` | Wave 3 | Verified and ready | keep sample/live boundary explicit |

## 9. Notifications / Reports / Operability

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| topic watchlists / alert rules | R2 | persisted watchlists and trend follow-through exist; external alert delivery is not proven | watchlists API/service/page, fresh direct write-path proof, trends payload | Waves 3-5 | Implemented but still risky | external alert delivery still depends on `RESEND_*` |
| live notification / daily report delivery validation | R4 | config and send paths exist but real delivery is still secret-gated | notifications service, ops inbox gate | Wave 2 | Blocked by genuine external dependency | needs `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and a target mailbox |
| operator-facing reports / notifications surface | R2, R4 | settings, reports routes, and ops gates exist | notifications routes, settings UI, ops inbox | Wave 2 | Partially implemented | final proof still needs live external delivery |

## 10. Growth / Brand / Naming / SEO / Landing Pages

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| keep `SourceHarbor` as product name, use `sourceharbor.ai` only as marketing domain if needed | R6 | current repo follows this recommendation | README, project-positioning, GitHub profile intent | Waves 3-5 | Deferred by design | only revisit when there is a real hosted story |
| avoid `bot` / `claw` / `open xxx` rename drift | R7 | current repo does not pursue those rename paths | README / docs / repo name | Wave 4 | Rejected / intentionally not pursued | keep the main brand stable |
| rewrite hero / subtitle / README / GitHub description around AI knowledge pipeline + MCP server | R7 | local repo copy is ahead, but live GitHub metadata is still intentionally kept on a safer remote-main wording because the newer local front doors are not landed remotely yet | README, docs front door, `config/public/github-profile.json`, `gh repo view`, remote-file negative checks on `main` | Waves 1-4 | Implemented but still risky | land current local closure work on remote `main` before promoting the newer wording live |
| optimize GitHub topics for MCP / AI research / knowledge-base | R7 | tracked intent is richer than the safer live topic set for the same reason: local closure work is still ahead of remote `main` | `config/public/github-profile.json`, `gh repo view`, remote-file negative checks on `main` | Wave 4 | Implemented but still risky | promote the richer topic set only after the matching code/docs land on remote `main` |
| add site-specific landing pages | R7 | initial use-case pages landed | `/use-cases/youtube`, `/use-cases/bilibili`, `/use-cases/rss`, `/use-cases/mcp-use-cases`, `/use-cases/research-pipeline` | Wave 3 | Implemented | keep them discoverability-only, not hosted promises |

## 11. Mid-term Compounders

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| cross-run trend / diff view | R2 | landed with local seeded proof | watchlists trend API + `/trends` + fresh local trend payload | Wave 3 | Implemented but still risky | current proof is local-seeded, not production analytics proof |
| demo dataset / example jobs / playground | R7 | landed | sample corpus + playground + use-case pages | Wave 3 | Verified and ready | preserve labels and proof boundary |
| expand sources / sites only after front door and truth surface mature | R7 | intentionally not advanced yet | backlog status + current source set | Post-Wave 4 | Deferred by design | do not reopen until compounders and proof stay stable |

## 12. High-risk Bets

| Item | Archive source | Current repo status | Evidence | Wave | Final classification | Remaining blocker / next step |
| --- | --- | --- | --- | --- | --- | --- |
| Hosted Team Workspace | R2 | still a Bet; Prompt 5 reduces it to a hosted-readiness spike | project-positioning, proof boundary, Prompt 5 hosted-readiness spike | Prompt 5 spike | Deferred by design | only consider a thin managed slice, not a full hosted workspace promise |
| full agent / autopilot / productized hosted readiness | R2, R7 | still a Bet; Prompt 5 reduces it to a human-in-the-loop Autopilot spike | workflows/MCP/notifications capability map + Prompt 5 Autopilot spike | Prompt 5 spike | Deferred by design | only proceed if approval-first MVP proves signal over noise |

## Restart From Here

If a future prompt continues this program, the highest-value restart points are:

1. retrieval quality proof on a realistic non-empty corpus
2. real external notification delivery with `RESEND_*`
3. Gemini-backed UI audit / computer-use live validation with `GEMINI_API_KEY`
4. explicit MVP validation for the two high-risk spikes in this folder:
   - `2026-03-31-agent-autopilot-spike.md`
   - `2026-03-31-hosted-readiness-spike.md`
