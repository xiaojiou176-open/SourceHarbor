# SourceHarbor Watchlist Briefing Template for OpenClaw

Use this public template when you want OpenClaw to inspect one SourceHarbor watchlist and answer a question with the current story context.

## Goal

- start from one watchlist
- reuse the current briefing/story context
- answer one question with evidence
- hand back a concrete operator action

## Inputs To Fill In

- `WATCHLIST_ID`: the watchlist you want to inspect
- `QUESTION`: the question you want answered
- `API_BASE_URL`: the SourceHarbor API base URL
- `MCP_STATUS`: whether OpenClaw is already connected to the SourceHarbor MCP server

## Prompt Skeleton

```text
You are operating against SourceHarbor as a source-first, proof-first control tower.

Task:
- inspect watchlist `WATCHLIST_ID`
- reuse the current briefing/story context
- answer `QUESTION`
- cite the evidence you used

Use the strongest available path in this order:
1. SourceHarbor MCP, if connected
2. SourceHarbor HTTP API at `API_BASE_URL`
3. SourceHarbor web routes only as visible proof surfaces

Required workflow:
1. Load the watchlist.
2. Load the current watchlist briefing or briefing page payload.
3. Identify the selected story and what changed recently.
4. Answer the question from that story context.
5. Return:
   - Current story
   - What changed
   - Evidence
   - Recommended next action

Guardrails:
- Do not pretend SourceHarbor is a hosted SaaS.
- Do not turn sample/demo surfaces into live-proof claims.
- Do not answer without evidence.
- If MCP or API access is partial, keep the answer honest about that boundary.
```

## Related Public Surfaces

- `docs/compat/openclaw.md`
- `docs/mcp-quickstart.md`
- `docs/builders.md`
- `starter-packs/openclaw/README.md`
