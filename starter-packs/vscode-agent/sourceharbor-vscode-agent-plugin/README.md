# SourceHarbor VS Code Agent Plugin Bundle

This bundle is the strongest repo-tracked VS Code agent plugin artifact
SourceHarbor can ship today without overclaiming a VS Code Marketplace listing.

Use it when you want:

- a VS Code agent plugin directory you can install from source
- a SourceHarbor MCP template with the repo-root placeholder already wired
- a public watchlist-briefing skill that does not depend on internal `.agents`

What is inside:

- `plugin.json`
- `.mcp.json`
- `skills/sourceharbor-watchlist-briefing/SKILL.md`

How to use it:

1. Copy this whole directory into the VS Code agent plugin source location you
   already manage, or point the source-install flow at this directory.
2. Replace `__REPLACE_WITH_SOURCEHARBOR_REPO_ROOT__` in `.mcp.json` with the
   absolute path to your SourceHarbor checkout.
3. Point VS Code at `plugin.json`, then start from the included skill.

Honest boundary:

- this is a plugin-grade VS Code agent bundle for source install
- it is not proof that SourceHarbor is live-listed in the VS Code Marketplace
- the strongest current promise is still source-first MCP and HTTP API reuse
