---
name: sourceharbor_watchlist_briefing
description: Inspect one SourceHarbor watchlist through MCP or HTTP API and answer with grounded evidence.
---

# SourceHarbor Watchlist Briefing

Use this workspace skill when you want OpenClaw to inspect one SourceHarbor
watchlist and answer a question with the current story and evidence context.

## Before You Use This Skill

- Prefer a configured SourceHarbor MCP server if your OpenClaw runtime already
  has one.
- Otherwise set `SOURCE_HARBOR_API_BASE_URL` and use the SourceHarbor HTTP API.
- Use SourceHarbor web routes only as visible proof surfaces, not as hidden
  sources of truth.

## Inputs To Fill In

- `WATCHLIST_ID`: the watchlist you want to inspect
- `QUESTION`: the question you want answered
- `SOURCE_HARBOR_API_BASE_URL`: the SourceHarbor API base URL when MCP is not wired
- `SOURCE_HARBOR_MCP_STATUS`: whether SourceHarbor MCP is already connected

## Workflow

1. Load the watchlist object.
2. Load the current watchlist briefing or briefing page payload.
3. Identify the selected story and the recent changes.
4. Answer `QUESTION` using that story context.
5. Return:
   - Current story
   - What changed
   - Evidence used
   - Suggested next operator action

## Guardrails

- Do not pretend SourceHarbor is a hosted SaaS.
- Do not turn sample/demo surfaces into live-proof claims.
- Do not answer without evidence.
- If MCP or HTTP access is partial, say so clearly instead of filling gaps.

## Related Public Surfaces

- `docs/compat/openclaw.md`
- `docs/builders.md`
- `docs/mcp-quickstart.md`
- `starter-packs/openclaw/README.md`
