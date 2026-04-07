# Hosted Readiness Spike

Status: design spike only. This document is a readiness assessment, not proof
that SourceHarbor is already a hosted or managed product.

## 1. Executive Verdict

Think of this document like a building inspection, not a sales brochure.
SourceHarbor already has real rooms, working plumbing, and a front door. It does
**not** yet have the hotel-grade locks, operations desk, and service contracts a
hosted team workspace would need.

Short answer:

- Full hosted team workspace: **no-go now**
- Thin single-owner managed evaluation slice: **possible later**
- Current strongest position: **source-first, local-proof-first, inspectable**

That current position is a product strength. Turning it into a hosted story too
early would make the promise larger than the proof.

## 2. Decision Memo

### Current go / no-go

| Question | Verdict | Why |
| --- | --- | --- |
| Can SourceHarbor honestly be described today as a hosted SaaS? | No | the public proof model still centers local runtime truth and explicit secret ownership |
| Is there enough product shape to study a managed slice later? | Yes | search, ask, MCP, ops, bundles, and playground already look like a coherent product surface |
| Should the first hosted-shaped experiment be a shared team workspace? | No | multi-tenant auth, isolation, custody, and remote support are not ready |
| Is there a smaller hosted-shaped slice worth exploring? | Yes, conditionally | a read-only or single-owner evaluation layer could improve activation without breaking source-first honesty |

### What this spike recommends

1. Keep the public promise anchored on local proof and inspectability.
2. Treat hosted work as a **bounded evaluation slice**, not a product repositioning.
3. Reopen the hosted track only after identity, secret custody, and remote
   runtime proof move from implied gaps to explicit contracts.

## 3. Current Capability Matrix

These are the surfaces that already feel product-like today and what they mean
for a future managed slice.

| Surface | Current repo truth | Evidence anchors | Managed-readiness signal |
| --- | --- | --- | --- |
| Front door | Search, Ask, MCP, Ops, and compounder pages already describe a coherent result path | `README.md`, `docs/start-here.md`, `apps/web/app/search`, `apps/web/app/ask`, `apps/web/app/mcp`, `apps/web/app/ops` | good product shape |
| Operator workflow | command center, jobs, feed, watchlists, trends, settings, and bundles are visible product rooms instead of hidden scripts | `apps/web/app/page.tsx`, `apps/web/app/jobs`, `apps/web/app/watchlists`, `apps/web/app/trends`, `artifacts/releases/README.md` | good operator-facing foundation |
| Agent workflow | MCP server exists on top of the same system rather than a fake parallel stack | `apps/mcp/server.py`, `docs/mcp-quickstart.md` | good agent-facing foundation |
| Local runtime orchestration | repo-managed boot path, doctor path, compose stack, and systemd examples already exist | `docs/start-here.md`, `infra/compose/core-services.compose.yml`, `infra/systemd/sourceharbor-api.service` | useful ops building blocks, but still self-host shaped |
| Proof and trust surfaces | proof ladder, runtime truth map, and public positioning already reject overclaim | `docs/proof.md`, `docs/reference/project-positioning.md`, `config/public/github-profile.json` | strong honesty layer |
| No-boot evaluation | playground, sample corpus, and use-case pages already support product evaluation without full setup | `docs/samples/README.md`, `apps/web/app/playground`, `apps/web/app/use-cases` | good seed for a managed evaluation slice |

## 4. What Is Not Hosted-Ready Yet

This is the real gap table. In plain language: these are the parts where
"someone else runs it for me" becomes much harder than "the code can run."

| Area | Current truth | Why it blocks a hosted workspace promise |
| --- | --- | --- |
| Identity and isolation | there is no tenant model, tenant-aware auth contract, or workspace partitioning surface | a hosted team workspace needs strong separation between users, data, and actions |
| Secret custody | notifications, Gemini-backed review, and some live-provider flows depend on operator-held secrets | a managed offering would need clear rules for secret storage, rotation, exposure, and abuse containment |
| Runtime proof boundary | public proof explicitly distinguishes local proof from remote proof | the current repo is honest because it does **not** pretend remote reliability is already proven |
| Onboarding model | docs still start from clone, `.env`, `uv sync`, Docker/compose, and local route snapshots | that is repo-native onboarding, not hosted-native onboarding |
| Operational durability | API, worker, Temporal, and Postgres are real, but not documented as an SLO-backed managed service | hosted users would expect uptime, restart behavior, retention, and support boundaries |
| Artifact and data policy | evidence bundles and job artifacts exist, but hosted retention, privacy, and storage lifecycle are not a documented contract | managed storage is not just "save files somewhere"; it needs policy |
| External-provider dependence | YouTube, notifications, and Gemini-backed lanes still rely on provider and secret availability | a hosted product would inherit provider outages and quota pressure as product responsibility |

## 5. Why The Current Position Is Still Correct

SourceHarbor is strongest today as:

- a source-first repository
- a local-proof-first product
- an inspectable operator-and-agent system

That matters because the current trust story is: "you can verify the machine
yourself." A hosted story changes the sentence to: "trust our managed
operations." That is a much bigger contract.

## 6. Smallest Honest Managed Slice

If SourceHarbor later experiments with hosted delivery, the first slice should
be:

> **managed evaluation and observability for a single-owner environment, not a shared hosted workspace**

Recommended first slice:

| Included | Why it is small enough to stay honest |
| --- | --- |
| hosted front door and docs handoff | helps discovery without claiming full hosted operation |
| hosted sample playground | gives faster product understanding without taking arbitrary user inputs |
| hosted proof / docs / MCP quickstart handoff | makes the learn-before-install path smoother |
| read-only job trace / log viewer for demo or single-owner runs | shows operational visibility without crossing into multi-tenant execution |
| managed bootstrap diagnostics | helps activation without promising full platform operations |

Explicitly out of scope for the first slice:

- multi-user shared workspace
- self-serve signup that implies general availability
- arbitrary user-provided secrets executed by the platform
- autonomous outbound sends
- remote write paths presented as broadly production-ready

## 7. Reopen Conditions

Do not reopen full hosted workspace work until these are true:

1. identity and workspace isolation have a real contract
2. secret custody has a documented storage and rotation policy
3. remote runtime proof exists as something stronger than local smoke
4. artifact retention and data-boundary rules are written down
5. operator support expectations are defined instead of implied

## 8. Official Constraints That Bound This Spike

These sources matter because they describe the difference between "an app can
run" and "a managed system can be trusted."

- FastAPI deployment concepts: <https://fastapi.tiangolo.com/deployment/concepts/>
  - process model, restarts, replication, and memory shape are part of deployment truth
- Temporal workflow docs: <https://docs.temporal.io/workflows>
  - durable workflows are powerful, but they raise the bar for managed operations and failure recovery

SourceHarbor implication:

- a hosted promise must cover process management, failure recovery, and secret-bearing execution
- a landing page, playground, or UI polish does **not** equal hosted readiness

## 9. Go / No-Go Recommendation

| Direction | Recommendation | Meaning |
| --- | --- | --- |
| Full hosted team workspace | **No-go now** | do not promise shared managed operation |
| Thin managed evaluation slice | **Conditional go later** | only as a single-owner or read-only bridge into the real local product |
| Hosted-flavored landing or docs surfaces | **Go with honesty** | safe only if they keep pointing back to source-first and proof-first truth |

## 10. Stop Conditions

Stop the hosted track immediately if any of these happen:

- the work starts requiring tenant isolation before identity exists
- docs or landing pages begin implying online signup or general hosted availability
- the project starts weakening local-proof-first trust just to sound more like SaaS
- secret-heavy execution becomes the main value story before custody is solved

## 11. Anti-Overclaim Rules

Do not say:

- SourceHarbor is hosted-ready
- SourceHarbor already offers a managed workspace
- the current public routes imply remote reliability proof

Do say:

- SourceHarbor already has product-shaped surfaces that could support a smaller managed evaluation slice later
- the current truth is still source-first and local-proof-first
- hosted readiness is a deferred direction, not a shipped capability

## 12. Handoff For The Next L1 / PM

If someone reopens this topic later, they should answer these questions first:

1. Is the goal faster evaluation, or true hosted operation?
2. Is the first slice read-only, single-owner, or multi-user?
3. Which secret-bearing lanes are intentionally excluded?
4. What exact remote proof would be required before public hosted language changes?

Until those answers exist, keep the public promise where it is:

- AI knowledge pipeline and MCP server
- source-first
- inspectable
- runnable locally
