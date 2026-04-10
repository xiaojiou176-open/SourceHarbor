# GitHub Copilot Compatibility

This is the shortest honest GitHub Copilot adoption path for SourceHarbor.

## Pick Your Door

| If you want to... | Use this | Why |
| --- | --- | --- |
| give GitHub Copilot governed access to jobs, retrieval, and artifacts | MCP | same control-tower truth the operator surfaces use |
| call SourceHarbor from scripts or tools | `@sourceharbor/sdk` | typed HTTP client for the public contract |
| do quick terminal inspection | `@sourceharbor/cli` | thin CLI over the current API |
| boot and manage the whole repo locally | `./bin/sourceharbor` | repo-local runtime management stays in the clone |

## Fastest Path

1. Start with [docs/builders.md](../builders.md).
2. Choose MCP if you want agent reuse, or CLI/SDK if you want builder reuse.
3. Follow [docs/start-here.md](../start-here.md) only when you need the full
   local runtime.

## Starter Template

Use [templates/public-skills/github-copilot/sourceharbor-watchlist-briefing.md](../../templates/public-skills/github-copilot/sourceharbor-watchlist-briefing.md)
when you want GitHub Copilot to operate over SourceHarbor watchlists, Ask, and
evidence surfaces without reading any private repo memory first.

## Plugin-Grade Bundle

If you want a stronger, source-installable bundle instead of a docs-only
starter, use:

- [starter-packs/github-copilot/sourceharbor-github-copilot-plugin/README.md](../../starter-packs/github-copilot/sourceharbor-github-copilot-plugin/README.md)
- [starter-packs/github-copilot/sourceharbor-github-copilot-plugin/plugin.json](../../starter-packs/github-copilot/sourceharbor-github-copilot-plugin/plugin.json)
- [starter-packs/github-copilot/sourceharbor-github-copilot-plugin/.mcp.json](../../starter-packs/github-copilot/sourceharbor-github-copilot-plugin/.mcp.json)
- [starter-packs/github-copilot/sourceharbor-github-copilot-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md](../../starter-packs/github-copilot/sourceharbor-github-copilot-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md)

This is the repo's strongest current artifact for GitHub Copilot source install
or repo marketplace distribution.

## Honest Boundary

- GitHub Copilot is a **ship-now fit** through MCP + HTTP API + the public starter layer.
- SourceHarbor now ships a GitHub Copilot plugin bundle, but that does **not**
  mean SourceHarbor is live-listed in an official marketplace.
- This is still a source-first integration story, not a hosted Copilot product.
