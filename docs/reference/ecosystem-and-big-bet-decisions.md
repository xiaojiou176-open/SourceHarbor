# Ecosystem And Big-Bet Decisions

This page is the durable decision ledger for the parts of SourceHarbor that are
easy to oversell.

Think of it like the route board at an airport:

- **ship-now** means the gate is open today
- **first-cut** means the gate is open today, but the surface is still an early
  public starter layer rather than a fully hardened ecosystem product
- **later** means the route is plausible, but not a current product promise
- **no-go** means do not position the repo around it in the current cycle
- **spike-only** means it is worth a bounded study, not a shipped capability

## Ecosystem Productization Buckets

| Surface | Bucket | Current truth | Revisit when |
| --- | --- | --- | --- |
| Codex / Claude Code through MCP + HTTP API | **ship-now** | this is already a real fit: the repo exposes MCP, a public HTTP contract, and builder-facing docs without inventing a second business-logic stack | keep tightening only if the current MCP/API contract changes |
| Repo-local CLI/help facade | **ship-now** | `./bin/sourceharbor` is the current honest command surface for discovery; it routes to repo-owned `bin/*` entrypoints and does not pretend to be a packaged public CLI | extend only as a thin facade over existing entrypoints |
| Packaged public CLI bridge | **ship-now** | `packages/sourceharbor-cli` now provides the installable public bridge while still delegating into repo-local `bin/sourceharbor` when a checkout is present | keep the command set thin and docs-first |
| Public TypeScript SDK | **ship-now** | `packages/sourceharbor-sdk` now provides the first contract-first SDK surface over the existing HTTP contract | harden package boundaries as external consumers appear |
| OpenClaw compatibility path | **first-cut** | the repo now ships `docs/compat/openclaw.md` plus a first-cut local OpenClaw starter pack, which is enough for a real compatibility path but still not enough to justify plugin-first positioning or a primary front-door label | revisit only if a repo-proven OpenClaw-specific workflow grows beyond the generic MCP / HTTP substrate |
| Python SDK | **later** | there is no public Python package surface today, and packaging it now would overclaim builder maturity | revisit after the TypeScript path hardens and real external builder demand exists |
| Public Skills / workflow packs | **first-cut** | `docs/public-skills.md`, `docs/compat/*`, `templates/public-skills/*`, and `examples/*` now form the first public starter distribution surface without exporting raw internal `.agents/skills`, but they still need more hardening before they count as a fully mature ecosystem product | deepen only if the workflow contracts stay stable across releases |
| Plugin-first or marketplace-first positioning | **no-go** | SourceHarbor is strongest as a source-first control tower with API/MCP/CLI reuse, not as a plugin marketplace | reconsider only if packaged CLI/SDK surfaces are stable and there is strong third-party integrator pull |

## Big-Bet Buckets

| Direction | Bucket | Current truth | Revisit when |
| --- | --- | --- | --- |
| Thin managed evaluation slice | **later** | a narrow hosted-shaped bridge may become useful, but only after it can stay subordinate to the source-first and local-proof-first truth model | revisit after auth, isolation, approval, and remote-proof layers are stronger |
| Full hosted / managed workspace | **no-go** | do not market this as a current capability; the repo is not ready for the larger multi-tenant promise | revisit only after identity, custody, support, and remote-proof contracts exist for real |
| Agent Autopilot / approval-first research ops | **spike-only** | human-approved orchestration is the most honest next slice; silent autonomy is not a current product promise | revisit after approval gates, auditability, rollback, and operator trust surfaces are stronger |
| Full autonomous agent workflow | **no-go** | silent autonomy would overrun the current approval and rollback boundaries | revisit only if the spike earns evidence that operators trust it and the guardrails are first-class |
| Public SDK platform expansion | **later** | builder packaging should grow only after the existing API/MCP/CLI truths stop moving | revisit after SourceHarbor has repeatable external builder adoption and stable packaging boundaries |
| Growth / discovery / moat strategy | **ship-now** | the current moat is already the source-first, proof-first, builder-facing position: one control tower, one operator truth, and multiple honest entry points | deepen this only through clearer docs, GitHub discovery, proof surfaces, and reproducible operator value rather than speculative new surfaces |
| Switchyard integration for provider runtime | **no-go for the current cycle** | keep it out of the current build surface; it is a long-term idea, not the current execution surface | revisit only after current repo-side truth, external proof, and packaging decisions stay stable for more than one release/current-main cycle |

## Guardrails

- Do not treat a spike artifact as a shipped capability.
- Do not relabel repo-local helper surfaces as public packaged products.
- Do not let marketplace or hosted language replace the current source-first and local-proof-first contract.
- Do not use this page to justify speculative implementation scope in the current cycle.
