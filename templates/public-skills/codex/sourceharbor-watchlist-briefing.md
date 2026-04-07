# SourceHarbor Watchlist Briefing Template for Codex

Use this public template when you want Codex to turn one SourceHarbor watchlist
into a repeatable briefing workflow without relying on private repo memory.

## Goal

- read one watchlist and its current story surface
- inspect what changed recently
- answer one question with evidence
- leave the operator with concrete next steps

## Inputs To Fill In

- `WATCHLIST_ID`: the watchlist you want to inspect
- `QUESTION`: the question you want answered
- `API_BASE_URL`: the SourceHarbor API base URL
- `MCP_STATUS`: whether you plan to use MCP, HTTP API, or both

## Prompt Skeleton

```text
You are helping an operator inspect one SourceHarbor watchlist.

Goal:
- summarize the current story for watchlist `WATCHLIST_ID`
- explain what changed recently
- answer `QUESTION`
- cite the evidence you used

Use the strongest available path in this order:
1. SourceHarbor MCP, if it is already connected
2. SourceHarbor HTTP API at `API_BASE_URL`
3. SourceHarbor web routes only as proof surfaces, not as hidden sources of truth

Required workflow:
1. Fetch the watchlist object.
2. Fetch the current watchlist briefing or briefing page payload.
3. Identify the selected story, recent changes, and supporting evidence.
4. Answer the question using the same story/evidence context instead of starting from scratch.
5. Return:
   - Current story
   - Recent changes
   - Evidence used
   - Suggested next operator action

Guardrails:
- Do not invent a hosted SourceHarbor surface.
- Do not treat sample/demo proof as live production proof.
- Do not drop citations.
- If the best available state is partial, say so clearly.
```

## Related Public Surfaces

- `docs/compat/codex.md`
- `docs/mcp-quickstart.md`
- `docs/builders.md`
- `starter-packs/codex/AGENTS.md`
