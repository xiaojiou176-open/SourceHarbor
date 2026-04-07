# Why SourceHarbor Stands Out

SourceHarbor is not trying to be "another summarizer repo."

It is stronger when you read it as a productized knowledge pipeline.

## Comparison Matrix

| Capability | Transcript-only tool | Summary-only script | Internal dashboard | **SourceHarbor** |
| :-- | :--: | :--: | :--: | :--: |
| Continuous source intake | No | No | Partial | **Yes** |
| Job-level trace and retries | No | No | Partial | **Yes** |
| Digest feed for operators | No | Partial | Yes | **Yes** |
| Retrieval over generated artifacts | No | Partial | Partial | **Yes** |
| Notifications and digest delivery | No | Partial | Partial | **Gated** |
| MCP surface for agents | No | No | No | **Yes** |
| Public proof path | Rare | Rare | Rare | **Yes** |

Notifications and digest delivery are implemented, but live send claims still
depend on sender identity, mailbox, and provider readiness.

## The Differentiator

Most repositories stop after "generate a summary."

SourceHarbor continues:

1. **Capture** sources repeatedly through a source-universe intake front door
2. **Run** a job-backed pipeline
3. **Write** artifacts you can inspect later
4. **Search** those artifacts
5. **Track** repeated themes as watchlists instead of ad-hoc tabs
6. **Merge** repeated runs into trends, briefings, and a shared Ask story payload
7. **Deliver** them through notifications
8. **Reuse** the same system through MCP

## Front-Door Line

The product line is stronger when you read the doors in order:

1. **Subscriptions** widens source intake honestly
2. **Watchlists** saves the tracking object
3. **Trends** becomes the compounder front door
4. **Briefings** lowers cognitive load with one current story
5. **Ask** carries that story context into answer, changes, and evidence
6. **MCP** reuses the same truth for Codex, Claude Code, and other agent clients

## Trade-Offs

SourceHarbor is a better fit when you want:

- a durable intake-to-artifact flow
- operator visibility
- agent integrations
- a source-first system you can inspect deeply

It is a worse fit when you want:

- a tiny copy-paste summarizer snippet
- a zero-infrastructure hosted tool
- a repo with no operator or orchestration layer

## Why This Matters For GitHub Discovery

This differentiation gives the repo a stronger public label:

> SourceHarbor is the GitHub-native control tower for long-form knowledge pipelines.

That label is easier to remember, easier to share, and easier to star than a vague "AI information hub" description.

## Ecosystem Fit

| Ecosystem | Fit level | Why |
| --- | --- | --- |
| **MCP** | **Primary** | real, shipped surface today through `./bin/dev-mcp` and `apps/mcp/server.py` |
| **Packaged public CLI** | **Primary** | `packages/sourceharbor-cli` is now a thin installable wrapper that delegates into repo-local `bin/sourceharbor` when a checkout is present |
| **Public TypeScript SDK** | **Primary** | `packages/sourceharbor-sdk` now exposes the same typed HTTP client/url/type substrate that the web app uses |
| **Public starter surface** | **First-cut** | `starter-packs/` is the public entry directory, with `docs/public-skills.md`, `docs/compat/*`, `templates/public-skills/*`, and `examples/*` acting as companion starter assets |
| **Codex** | **Primary** | strong fit for source-first local workflows that want to use MCP or HTTP against the same operator truth |
| **Claude Code** | **Primary** | same fit pattern as Codex: local, MCP-aware, API-capable, and proof-first |
| **OpenHands** | Secondary / comparison | adjacent as an agent-runtime ecosystem, but SourceHarbor is not a generic software-task agent |
| **OpenCode** | Secondary / comparison | adjacent as a coding/automation workflow surface, but not a primary product identity here |
| **OpenClaw** | First-cut local pack | the shared MCP / HTTP substrate is real and the repo now ships a local starter pack, but it still should not be sold as a SourceHarbor plugin-first identity or primary front door |

Here, **First-cut** means the starter layer is real and usable today, but it is
still a public entry surface rather than a fully hardened standalone ecosystem
product.
