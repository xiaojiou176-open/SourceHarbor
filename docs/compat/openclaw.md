# OpenClaw Compatibility

This is the shortest honest OpenClaw adoption path for SourceHarbor.

OpenClaw is no longer limited here to a vague "generic MCP / HTTP only" story.
SourceHarbor now ships a first-cut local OpenClaw starter pack on top of the
same MCP and HTTP API surfaces already documented for Codex and Claude Code.

## Pick Your Door

| If you want to... | Use this | Why |
| --- | --- | --- |
| install a local OpenClaw-ready pack | `starter-packs/openclaw/` | first-cut local pack with plugin manifest, MCP template, and starter skill |
| reuse the same operator truth from OpenClaw | MCP | strongest fit when you want jobs, retrieval, artifacts, and watchlists through the shared agent doorway |
| call SourceHarbor from OpenClaw-managed tools or scripts | `@sourceharbor/sdk` | typed HTTP client over the same public contract |
| do quick command-line inspection | `@sourceharbor/cli` | thin shell doorway into search, Ask, jobs, and templates |
| manage the full runtime in a local clone | `./bin/sourceharbor` | repo-local operator/runtime commands stay in the checkout |

## Fastest Path

1. Read [docs/mcp-quickstart.md](../mcp-quickstart.md) so you start from the
   shared MCP / HTTP boundary instead of guessing.
2. Copy or symlink `starter-packs/openclaw/` into the local plugin or
   workspace-skill directory you already use for OpenClaw.
3. Open `starter-packs/openclaw/sourceharbor-mcp-template.json` and replace
   `__REPLACE_WITH_SOURCEHARBOR_REPO_ROOT__` with the absolute path to your
   SourceHarbor checkout.
4. Point OpenClaw at that MCP template plus
   `starter-packs/openclaw/openclaw.plugin.json`.
5. If you need a full SourceHarbor stack first, follow
   [docs/start-here.md](../start-here.md).

## Five-Minute Local Setup

Think of this like wiring one adapter, not building a second product.

### 1. Start from the pack directory

Use the whole `starter-packs/openclaw/` folder as your local handoff surface.
The important files are:

- `openclaw.plugin.json` for the local plugin manifest
- `sourceharbor-mcp-template.json` for the MCP command template
- `skills/sourceharbor-watchlist-briefing/SKILL.md` for the first workflow

### 2. Replace the repo-root placeholder once

The MCP template is intentionally explicit:

```json
{
  "command": "bash",
  "args": [
    "-lc",
    "cd \"__REPLACE_WITH_SOURCEHARBOR_REPO_ROOT__\" && ./bin/dev-mcp"
  ],
  "env": {
    "SOURCE_HARBOR_API_BASE_URL": "http://127.0.0.1:9000"
  }
}
```

Replace `__REPLACE_WITH_SOURCEHARBOR_REPO_ROOT__` with the absolute path to
your checkout, for example:

```json
"cd \"/workspace/SourceHarbor\" && ./bin/dev-mcp"
```

If your repo-managed stack resolved to a different API port, source
`.runtime-cache/run/full-stack/resolved.env` first and mirror the real
`SOURCE_HARBOR_API_BASE_URL` instead of assuming `9000`.

### 3. Use the first workflow immediately

After OpenClaw can see the local plugin manifest and the MCP template:

- load `skills/sourceharbor-watchlist-briefing/SKILL.md` as your first starter
  workflow
- use MCP when you want jobs, retrieval, artifacts, and watchlists through the
  shared agent doorway
- use `@sourceharbor/sdk` only when you explicitly want typed code integration

That is the honest first hop today: a local starter-pack fit over the same MCP
and HTTP contract, not a registry plugin or marketplace install.

## Public Starter Assets

- [starter-packs/openclaw/README.md](../../starter-packs/openclaw/README.md)
- [starter-packs/openclaw/openclaw.plugin.json](../../starter-packs/openclaw/openclaw.plugin.json)
- [starter-packs/openclaw/clawhub.package.template.json](../../starter-packs/openclaw/clawhub.package.template.json)
- [starter-packs/openclaw/skills/sourceharbor-watchlist-briefing/SKILL.md](../../starter-packs/openclaw/skills/sourceharbor-watchlist-briefing/SKILL.md)
- [starter-packs/openclaw/sourceharbor-mcp-template.json](../../starter-packs/openclaw/sourceharbor-mcp-template.json)
- [templates/public-skills/openclaw/sourceharbor-watchlist-briefing.md](../../templates/public-skills/openclaw/sourceharbor-watchlist-briefing.md)

## Honest Boundary

- OpenClaw is now a **first-cut local starter-pack fit** through MCP + HTTP API
  plus the new public starter layer.
- SourceHarbor now also ships a ClawHub-oriented package metadata template, so
  the repo has a publish-ready artifact even before a live ClawHub publish receipt exists.
- This does **not** mean SourceHarbor ships a registry-published OpenClaw
  plugin today.
- This does **not** mean SourceHarbor ships an OpenClaw plugin marketplace.
- This still does **not** turn internal `.agents/skills` into a public support
  promise.
