# SourceHarbor Watchlist Briefing

Use this public OpenClaw-shaped skill when you want one repeatable workflow for
watchlists, briefings, Ask, and evidence.

## Goal

- inspect one SourceHarbor watchlist
- reuse the current story context
- answer one question with evidence
- leave one concrete operator next step

## Inputs

- `WATCHLIST_ID`
- `QUESTION`
- `API_BASE_URL`
- `MCP_STATUS`

## Workflow

1. Use SourceHarbor MCP first when it is already connected.
2. Fall back to the SourceHarbor HTTP API when MCP is not connected.
3. Use web routes only as visible proof surfaces, not as hidden truth.
4. Load the watchlist.
5. Load the current watchlist briefing or briefing page payload.
6. Identify the selected story and recent changes.
7. Answer the question with citations and evidence.
8. Return:
   - current story
   - what changed
   - evidence used
   - recommended next action

## Guardrails

- Do not pretend SourceHarbor is a hosted SaaS.
- Do not answer without evidence.
- Do not treat sample/demo proof as live production proof.
- If MCP or API access is partial, say so clearly.

## Related Public Surfaces

- `docs/compat/openclaw.md`
- `starter-packs/openclaw/README.md`
- `templates/public-skills/openclaw/sourceharbor-watchlist-briefing.md`
