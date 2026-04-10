# VS Code Agent Compatibility

This is the shortest honest VS Code agent adoption path for SourceHarbor.

## Pick Your Door

| If you want to... | Use this | Why |
| --- | --- | --- |
| give VS Code agent workflows governed access to jobs, retrieval, and artifacts | MCP | same control-tower truth the operator surfaces use |
| call SourceHarbor from scripts or tools | `@sourceharbor/sdk` | typed HTTP client for the public contract |
| do quick terminal inspection | `@sourceharbor/cli` | thin CLI over the current API |
| boot and manage the whole repo locally | `./bin/sourceharbor` | repo-local runtime management stays in the clone |

## Fastest Path

1. Start with [docs/builders.md](../builders.md).
2. Choose MCP if you want agent reuse, or CLI/SDK if you want builder reuse.
3. Follow [docs/start-here.md](../start-here.md) only when you need the full
   local runtime.

## Starter Template

Use [templates/public-skills/vscode-agent/sourceharbor-watchlist-briefing.md](../../templates/public-skills/vscode-agent/sourceharbor-watchlist-briefing.md)
when you want VS Code agent workflows to operate over SourceHarbor watchlists,
Ask, and evidence surfaces without reading any private repo memory first.

## Plugin-Grade Bundle

If you want a stronger, source-installable bundle instead of a docs-only
starter, use:

- [starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/README.md](../../starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/README.md)
- [starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/plugin.json](../../starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/plugin.json)
- [starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/.mcp.json](../../starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/.mcp.json)
- [starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md](../../starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md)

This is the repo's strongest current artifact for VS Code agent source install
or local plugin-location loading.

## Honest Boundary

- VS Code agent workflows are a **ship-now fit** through MCP + HTTP API + the public starter layer.
- SourceHarbor now ships a VS Code agent plugin bundle, but that does **not**
  mean SourceHarbor is live-listed in the VS Code Marketplace.
- This is still a source-first integration story, not a hosted VS Code product.
