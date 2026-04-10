# SourceHarbor GitHub Copilot Pack

This is the first public GitHub Copilot plugin-grade starter pack for
SourceHarbor.

Use it when you want:

- the shortest GitHub Copilot plugin path that still reuses the same MCP and HTTP API truth
- a tracked bundle root you can install from source or keep in a repo marketplace
- a public watchlist-briefing skill without depending on repo-private `.agents/skills`

Start here:

- `docs/compat/github-copilot.md`
- `starter-packs/github-copilot/sourceharbor-github-copilot-plugin/README.md`
- `starter-packs/github-copilot/sourceharbor-github-copilot-plugin/plugin.json`
- `starter-packs/github-copilot/sourceharbor-github-copilot-plugin/.mcp.json`
- `starter-packs/github-copilot/sourceharbor-github-copilot-plugin/skills/sourceharbor-watchlist-briefing/SKILL.md`

## Three-step quickstart

1. Copy or clone the plugin bundle directory into the GitHub Copilot plugin or
   source-install location you already use.
2. Replace `__REPLACE_WITH_SOURCEHARBOR_REPO_ROOT__` in `.mcp.json` with the
   absolute path to your SourceHarbor checkout.
3. Point GitHub Copilot at `plugin.json`, then start with
   `skills/sourceharbor-watchlist-briefing/SKILL.md`.

If your local SourceHarbor stack is not using `http://127.0.0.1:9000`, replace
the placeholder with the real `SOURCE_HARBOR_API_BASE_URL` before you hand the
bundle to GitHub Copilot.

Honest boundary:

- this is a plugin-grade GitHub Copilot bundle
- it is installable from source and repo-tracked today
- it is not proof of a live official marketplace or directory listing
