# Codex Compatibility

This is the shortest honest Codex adoption path for SourceHarbor.

## Pick Your Door

| If you want to... | Use this | Why |
| --- | --- | --- |
| inspect the same state the operator UI sees | MCP | strongest source-first path for agent reuse |
| integrate from code | `@sourceharbor/sdk` | typed HTTP surface without copying operator logic |
| run quick terminal probes | `@sourceharbor/cli` | thin shell doorway into search, Ask, jobs, and templates |
| manage the full local runtime in a clone | `./bin/sourceharbor` | repo-local operator/runtime commands stay here |

## Fastest Path

1. Read [docs/mcp-quickstart.md](../mcp-quickstart.md).
2. If you already have a running API, start with `@sourceharbor/sdk` or
   `@sourceharbor/cli`.
3. If you need a full local stack first, follow [docs/start-here.md](../start-here.md).

## Starter Template

Use [templates/public-skills/codex/sourceharbor-watchlist-briefing.md](../../templates/public-skills/codex/sourceharbor-watchlist-briefing.md)
when you want Codex to turn a watchlist, Ask, and MCP context into a repeatable
workflow.

## Plugin-Grade Bundle

If you want a stronger, plugin-shaped handoff than a bare prompt template, use:

- [starter-packs/codex/sourceharbor-codex-plugin/README.md](../../starter-packs/codex/sourceharbor-codex-plugin/README.md)
- [starter-packs/codex/sourceharbor-codex-plugin/.codex-plugin/plugin.json](../../starter-packs/codex/sourceharbor-codex-plugin/.codex-plugin/plugin.json)
- [starter-packs/codex/sourceharbor-codex-plugin/.mcp.json](../../starter-packs/codex/sourceharbor-codex-plugin/.mcp.json)
- [starter-packs/codex/sourceharbor-codex-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md](../../starter-packs/codex/sourceharbor-codex-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md)

This bundle is the strongest official-docs-supported public distribution surface
for Codex today:

- use it in a repo marketplace or personal marketplace
- keep calling it `Codex-compatible`
- do not call it an official Codex Plugin Directory listing yet

## Honest Boundary

- Codex is a **ship-now fit** through MCP + HTTP API + the new public SDK/CLI
  starter layer.
- SourceHarbor now ships a Codex-compatible plugin bundle, but that does **not**
  mean SourceHarbor is listed in the official Codex Plugin Directory.
- This does **not** turn internal `.agents/skills` into a public support
  promise.
