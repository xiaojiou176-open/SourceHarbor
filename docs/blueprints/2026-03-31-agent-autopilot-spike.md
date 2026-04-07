# Agent Autopilot Spike

Status: design spike only. This is a **Bet / high-risk bucket**, not proof that
SourceHarbor already has a production-ready autopilot.

## 1. Decision In Plain English

Worth doing only as a **human-in-the-loop research-ops MVP**.

Not worth doing yet as:

- fully autonomous agent operations
- hidden background automation that sends user-visible outputs without review
- a public claim that SourceHarbor already runs its own research loop end to end

Why:

- the repo already has enough primitives to assemble candidate workflows
- the repo does **not** yet have enough approval, auth, rollback, or provider
  readiness to justify silent execution
- external-secret lanes such as notifications and Gemini-backed review are still
  gated

Think of the current repo like a warehouse that already has shelves, barcodes,
and forklifts. It does **not** yet have a trusted dispatcher who can send a
truck out without a human checking the manifest first.

## 2. Go / No-Go Verdict

| Question | Verdict | Reason |
| --- | --- | --- |
| Should SourceHarbor pursue Agent Autopilot now? | **Yes, but only as a bounded spike** | the repo already has workflows, MCP, retrieval, and evidence surfaces |
| Should it promise autonomous research ops now? | **No** | approval, identity, audit, and rollback are not strong enough yet |
| Should the first cut execute actions automatically? | **No** | the honest MVP is proposal-first, approval-first |
| Should computer-use or UI automation be core to MVP? | **No** | that would add fragility before basic Autopilot signal quality is proven |

## 3. Current Capability Map

These are the repo capabilities that make the spike worth exploring at all.

| Capability | Current repo truth | Why it matters |
| --- | --- | --- |
| Workflow execution | `apps/api/app/routers/workflows.py` starts bounded Temporal workflows such as `poll_feeds`, `daily_digest`, and `notification_retry` | the system already has a real execution lane instead of needing a fake Autopilot runner |
| MCP doorway | `apps/mcp/server.py` registers workflow, retrieval, report, notification, job, and UI-audit tools | agents already have one operator-facing control plane instead of needing a second orchestration stack |
| Retrieval evidence | `apps/api/app/services/retrieval.py` supports keyword, semantic, and hybrid search over digests, transcripts, and knowledge cards | an Autopilot proposal can point to grounded evidence instead of hand-wavy reasoning |
| Notification lane | `apps/api/app/services/notifications.py` already models delivery creation and send paths | outbound actions can stay inside an existing service contract rather than inventing a new lane |
| UI audit surface | `apps/api/app/services/ui_audit.py` can collect artifacts and findings, including Gemini-assisted review when configured | useful as a secondary inspection surface, not as the core Autopilot dependency |
| Computer-use surface | `apps/api/app/services/computer_use.py` exists with explicit confirmation and blocked-action safety | this is a guarded specialist tool, not a default Autopilot primitive |
| Evidence bundles | `GET /api/v1/jobs/{job_id}/bundle` already exposes reusable job evidence | proposal review can link to an evidence packet instead of raw log scraping |
| Public truth boundary | `README.md`, `docs/start-here.md`, `docs/architecture.md`, and `docs/proof.md` already say Autopilot is a spike only | the repo already protects against accidental overclaim if this document stays honest |

## 4. What Is Still Missing

These are the layers that make full autonomy a no-go today.

| Missing layer | Why it blocks full Autopilot | What the MVP must do instead |
| --- | --- | --- |
| Proposal persistence | no durable `proposal` object exists yet | persist suggestions before any execution happens |
| Approval identity | no shipped approval queue or operator approval actor contract exists | require explicit approval metadata before a workflow can run |
| Rollback hooks | current repo has workflow start, but no shipped Autopilot kill switch or proposal revoke lane | limit MVP to allowlisted actions and require disable/reject controls |
| Reliable outbound readiness | notifications and Gemini-backed paths still depend on real secrets and provider availability | treat provider-gated lanes as risk flags, not default actions |
| Action scoping | MCP is broad, but Autopilot should not be allowed to do arbitrary mutation | allow only a narrow action list for the first MVP |
| Audit completeness | jobs and bundles exist, but there is no proposal-to-approval-to-execution ledger yet | record evidence, risk flags, approver, and result per proposal |
| Operator trust signal | no data yet shows operators actually want or trust Autopilot proposals | stop the spike quickly if approval quality is weak |

## 5. Official Constraints That Matter

These sources shape the spike boundary:

- MCP official docs: <https://modelcontextprotocol.io/docs/getting-started/intro>
  - SourceHarbor should keep using MCP as the agent-facing doorway into the
    existing system, not as a second business-logic stack.
- Temporal workflows docs: <https://docs.temporal.io/workflows>
  - Temporal is a good fit for bounded, retryable orchestration that should
    survive process failure.

SourceHarbor implication:

- use MCP + workflow routes as the control plane
- use jobs / bundles / retrieval / ops risk surfaces as the audit plane
- do **not** promise autonomous execution unless approval, logging, and rollback
  are first-class

## 6. Recommended MVP Slice

The safest MVP is:

> **Agent prepares a candidate run or report draft. Human approves before any outward action happens.**

Concrete slice:

1. Agent reads subscriptions, watchlists, retrieval evidence, and ops signals
   through MCP or API.
2. Agent proposes exactly one allowlisted action:
   - `poll_feeds`
   - `daily_digest`
   - `notification_retry`
3. Agent attaches a grounded draft:
   - why this action should happen now
   - what evidence it used
   - what will happen if approved
   - what risks or provider gates apply
4. Human approves or rejects.
5. Only after approval does SourceHarbor execute the workflow or send the
   report.

This is the product cut that is small enough to be honest. It is more like
"suggest and confirm" than "self-driving agent."

## 7. MVP Contract Blueprint

This spike recommends a future contract like:

| Field | Meaning |
| --- | --- |
| `proposal_id` | durable ID for one agent suggestion |
| `proposal_kind` | `workflow_run`, `daily_report_draft`, `notification_draft` |
| `action_name` | allowlisted workflow or report action to trigger on approval |
| `inputs` | subscriptions, watchlists, retrieval queries, job IDs, or dates used |
| `evidence` | citations into jobs, cards, feed items, bundles, or ops inbox entries |
| `risk_flags` | `secret_required`, `provider_blocked`, `empty_corpus`, `degraded_state`, `runtime_unhealthy` |
| `approval_state` | `pending`, `approved`, `rejected`, `expired`, `executed`, `cancelled` |
| `approved_by` | operator identity if approval happened |
| `approved_at` | approval timestamp |
| `execution_result` | workflow ID, delivery ID, bundle ID, or error payload |
| `audit_notes` | short operator or system notes for why it was rejected or stopped |

## 8. Safety Rails For The First Real Cut

The first implementation should not start unless these rules are part of the
contract:

1. **Approval-first only**
   - no hidden background execution
   - no "auto-send" path
2. **Allowlist only**
   - only existing workflow/report actions may execute
   - no arbitrary prompt-generated mutation targets
3. **Evidence required**
   - every proposal must cite retrieval hits, job evidence, or bundle links
4. **Risk flags required**
   - provider-gated, secret-gated, empty-corpus, and degraded-state proposals
     must surface their blockers before approval
5. **No core dependency on computer-use**
   - UI automation is optional research, not required to make the MVP work
6. **Operator-visible audit trail**
   - proposal creation, approval/rejection, execution result, and failure reason
     must be inspectable

## 9. Audit Trail Expectations

If this spike becomes implementation work later, the MVP should record:

- what the agent read
- what action it suggested
- what evidence supported the suggestion
- what risk flags were raised
- who approved or rejected it
- what workflow or notification execution followed
- what bundle, report, or error payload came out

The simplest honest review surface would be an **approval queue** plus links to
existing jobs, bundles, and ops pages.

## 10. Rollback And Kill-Switch Expectations

This spike should **not** move to implementation unless rollback is designed up
front.

Minimum rollback shape for a future MVP:

- a global feature flag that disables new proposal generation
- a separate execution toggle that prevents approved proposals from launching
  workflows
- proposal expiry so stale suggestions do not execute later by accident
- operator cancel / reject actions that leave an audit note
- no irreversible side effects before approval

If rollback cannot be described in one page, the spike is still too large.

## 11. Stop Conditions

Stop the Autopilot track if any of these happen:

- operators mostly reject proposals
- proposal quality is noisy because retrieval evidence is too weak
- secret-gated lanes remain the main bottleneck
- the agent needs UI automation or computer-use just to complete basic loops
- the system cannot explain *why* it proposed a run in grounded evidence
- the only way to keep it running is to weaken source-first or proof-first
  boundaries

## 12. Anti-Overclaim Rules

Do not say:

- SourceHarbor already has Agent Autopilot
- the system can autonomously monitor and send reports end to end
- MCP + workflows automatically mean safe autonomy
- this blueprint proves production readiness

Do say:

- SourceHarbor already has the primitives for an approval-first Autopilot spike
- the safest next step is proposal-first, approval-first research ops
- external sends and Gemini-gated actions remain separate readiness gates
- this remains a Bet until approval quality and audit behavior are proven

## 13. Recommended Implementation Order

If a later prompt reopens this track, the smallest honest implementation order
is:

1. **Contract slice**
   - persist `proposal` objects
   - add risk flags and evidence links
   - no execution yet
2. **Operator slice**
   - render an approval queue
   - allow approve / reject / expire
   - show proposal evidence and ops blockers
3. **Execution slice**
   - approval triggers only allowlisted workflow/report actions
   - capture execution result and bundle/report references
4. **Measurement slice**
   - track approval rate, reject reasons, and noisy proposal patterns

If step 1 or 2 already feels too large, stop there. That still counts as a good
spike outcome.

## 14. Handoff Checklist For The Next Executor

A zero-context executor should start with this checklist:

1. Confirm the public docs still describe Autopilot as a spike only.
2. Re-read:
   - `apps/mcp/server.py`
   - `apps/mcp/tools/workflows.py`
   - `apps/api/app/routers/workflows.py`
   - `apps/api/app/services/retrieval.py`
   - `apps/api/app/services/notifications.py`
   - `apps/api/app/services/ui_audit.py`
   - `apps/api/app/services/computer_use.py`
3. Keep the first MVP limited to approval-first research ops.
4. Do not introduce free-form agent mutation or background execution.
5. Refuse any prompt that tries to turn this spike into a hosted-ready or
   fully autonomous claim without new proof.

## 15. Final Recommendation

Go / no-go: **Go for a small approval-first spike. No-go for full autonomy.**

Best next implementation prompt:

- persist `proposal` objects
- render an operator approval queue
- attach grounded evidence and ops risk flags
- allow approval to trigger a workflow, not free-form arbitrary actions
- keep notifications, Gemini-gated review, and computer-use outside the default
  success path
