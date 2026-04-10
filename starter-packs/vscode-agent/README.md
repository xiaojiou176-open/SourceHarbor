# SourceHarbor VS Code Agent Pack

This is the first public VS Code agent plugin-grade starter pack for
SourceHarbor.

Use it when you want:

- the shortest VS Code agent plugin path that still points at the same MCP and HTTP API truth
- a tracked source-installable plugin directory for VS Code agent workflows
- a public watchlist-briefing skill without relying on repo-private `.agents/skills`

Start here:

- `docs/compat/vscode-agent.md`
- `starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/README.md`
- `starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/plugin.json`
- `starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/.mcp.json`
- `starter-packs/vscode-agent/sourceharbor-vscode-agent-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md`

## Three-step quickstart

1. Copy or clone the plugin bundle directory into the VS Code agent plugin
   location you already use, or point the source-install flow at this directory.
2. Replace `__REPLACE_WITH_SOURCEHARBOR_REPO_ROOT__` in `.mcp.json` with the
   absolute path to your SourceHarbor checkout.
3. Point VS Code at `plugin.json`, then start with
   `skills/sourceharbor-watchlist-briefing/SKILL.md`.

If your local SourceHarbor stack is not using `http://127.0.0.1:9000`, replace
the placeholder with the real `SOURCE_HARBOR_API_BASE_URL` before you hand the
bundle to VS Code.

Honest boundary:

- this is a plugin-grade VS Code agent bundle
- it is installable from source and repo-tracked today
- it is not proof of a live VS Code Marketplace extension listing
