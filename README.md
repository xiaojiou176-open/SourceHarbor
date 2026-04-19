# SourceHarbor

<p align="center">
  <img
    src="./docs/assets/sourceharbor-studio-preview.svg"
    alt="SourceHarbor studio preview showing source intake, digest generation, and searchable artifacts"
    width="100%"
  />
</p>

<p align="center">
  <strong>Turn long-form sources into grounded search, reader-ready briefs, and inspectable agent workflows.</strong>
</p>

<p align="center">
  <a href="#see-it-in-30-seconds">See It In 30 Seconds</a>
  ·
  <a href="./docs/start-here.md">Run Locally</a>
  ·
  <a href="./docs/proof.md">Proof</a>
  ·
  <a href="./docs/builders.md">Builders</a>
  ·
  <a href="./docs/see-it-fast.md">No-Boot Tour</a>
  ·
  <a href="./docs/index.md">Docs Home</a>
</p>

<p align="center">
  <img alt="CI" src="https://github.com/xiaojiou176-open/SourceHarbor/actions/workflows/ci.yml/badge.svg" />
  <img alt="License" src="https://img.shields.io/github/license/xiaojiou176-open/SourceHarbor" />
  <img alt="GitHub Discussions" src="https://img.shields.io/github/discussions/xiaojiou176-open/SourceHarbor" />
  <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/xiaojiou176-open/SourceHarbor?style=social" />
</p>

SourceHarbor helps you turn long-form sources into grounded search results,
knowledge cards, traceable job runs, and MCP-ready operations. It stays
source-first and proof-first: you can inspect it, run it locally, and verify
each surface instead of trusting product copy on vibes alone.

## Start With One First Path

Choose only one first step:

| If you want to... | Open this first | Why this is the right first door |
| --- | --- | --- |
| **See whether the product is worth your time** | [docs/see-it-fast.md](./docs/see-it-fast.md), then [docs/proof.md](./docs/proof.md) | start with the shop window, then inspect the evidence ladder before you boot anything |
| **Run one real local flow** | [docs/start-here.md](./docs/start-here.md) | this is the shortest truthful path from clone to `/reader`, `/feed`, `/search`, `/ask`, and one real job |
| **Build on top of SourceHarbor** | [docs/builders.md](./docs/builders.md) and [docs/public-distribution.md](./docs/public-distribution.md) | these pages keep MCP, API, CLI, SDK, starter packs, and official submit/read-back truth out of the newcomer path |

If you only remember one sentence, remember this:

> SourceHarbor is a **reader-first, source-first, proof-first** product repo.

Current intake truth:

- **strong support:** YouTube channels and Bilibili creators
- **general substrate:** RSSHub routes and generic RSS/Atom feeds
- **not yet claimable:** route-by-route verification for the full RSSHub universe

## Product In One Glance

| Surface | Why open it first | Current truth |
| --- | --- | --- |
| **Reader** | See the finished surface instead of starting in a control panel | real local route after boot: `/reader` |
| **Subscriptions + Feed** | Follow a few sources, then watch the reading flow fill in | real local routes after boot: `/subscriptions` and `/feed` |
| **Search + Ask** | Search saved material or ask for the current story with evidence nearby | real local routes after boot: `/search` and `/ask` |
| **Jobs + Proof** | Inspect the pipeline, artifacts, and truth layers instead of trusting marketing copy | `/jobs`, [docs/proof.md](./docs/proof.md), and [docs/project-status.md](./docs/project-status.md) |

SourceHarbor is a **multi-surface product repo, not a single skill package**.
Public starter packs and plugin-grade bundles are adoption layers inside that
repo. They are not the whole product, and they are not raw exports of the
internal `.agents/skills` tree.

## Builder Off-Ramp

If you are here as a builder, use the builder path on purpose:

- **MCP / API / CLI / SDK map:** [docs/builders.md](./docs/builders.md)
- **Official submit/read-back truth:** [docs/public-distribution.md](./docs/public-distribution.md)
- **Public packages and starter packs:** [`packages/sourceharbor-cli`](./packages/sourceharbor-cli/README.md), [`packages/sourceharbor-sdk`](./packages/sourceharbor-sdk/README.md), [`starter-packs/README.md`](./starter-packs/README.md)
- **Registry ownership marker:** `mcp-name: io.github.xiaojiou176-open/sourceharbor-mcp`

Container truth also stays separate on purpose:

- the repo newcomer path is still [docs/start-here.md](./docs/start-here.md)
- the dedicated API image is a builder lane, not the default install story
- core-services compose, devcontainer, and strict-CI images are runtime or infrastructure surfaces, not the product front door

## What It Does Not Claim Today

Think of this as the label on the box, not fine print:

- SourceHarbor is **not** presented as a hosted SaaS or online signup product.
- Agent Autopilot is **not** a shipped capability; it remains a bounded spike direction.
- Hosted Team Workspace is **not** a current promise; it remains a deferred bet.
- SourceHarbor does **not** yet ship a public Python SDK.
- SourceHarbor does **not** claim that one public image is the whole product stack; the dedicated API image still expects external Postgres/Temporal once you move past health-only smoke.
- SourceHarbor does **not** collapse a repo-side PyPI/GHCR route into a live registry claim without read-back proof.
- SourceHarbor does **not** claim official marketplace or registry listing everywhere.
- SourceHarbor does **not** yet claim a registry-published OpenClaw plugin package or official Codex directory listing.
- SourceHarbor does **not** claim that every RSSHub route has already been individually validated.

If you need the explicit bet boundaries, read:

- [Ecosystem And Big-Bet Decisions](./docs/reference/ecosystem-and-big-bet-decisions.md)
- [Future-direction boundaries](./docs/reference/project-positioning.md)

## Public Readiness Notes

Keep these truth layers separate when you read or share the repo:

- current `main` truth can move ahead of the latest release tag
- tracked GitHub profile metadata can move ahead of the live GitHub repo settings
- workflow-dispatch lanes such as release evidence attestation and strict CI standard-image publish are manual proof lanes, not the public install ledger, even when required checks on `main` are already green
- local support-service containers plus devcontainer/strict-CI images do not turn Docker or GHCR into the current product front door
- local real-profile browser proof can confirm login persistence and page state without turning those same sites into source-ingestion product claims

That is why SourceHarbor keeps `proof.md`, `project-status.md`, and the public-reference docs as separate ledgers instead of one blanket “ready” claim.

## Compounder Layer

These are the surfaces that make SourceHarbor reusable instead of one-and-done:

| Compounder | What it does | Current truth |
| --- | --- | --- |
| **Watchlists** | Save a topic, claim kind, or source matcher as a durable tracking object | Real route: `/watchlists` |
| **Trends** | Compare recent matched runs for a watchlist and show what was added or removed | Real route: `/trends` |
| **Briefings** | Collapse one watchlist into a unified story surface that starts with the current summary, highlights recent deltas, and keeps evidence one click away | Real route: `/briefings`; now backed by a server-owned briefing page payload that shares one canonical selected-story object with Ask |
| **Evidence bundle** | Export one job as a reusable internal bundle with digest, trace summary, knowledge cards, and artifact manifest | Real route on demand: `/api/v1/jobs/<job-id>/bundle` |
| **Playground** | Explore clearly labeled sample corpus and demo outputs without pretending they are live operator state | Real route: `/playground` + [docs/samples/README.md](./docs/samples/README.md) |
| **Use-case pages** | Route newcomer traffic into truthful capability stories for YouTube, Bilibili, RSS, MCP, and research workflows | Real routes: `/use-cases/youtube`, `/use-cases/bilibili`, `/use-cases/rss`, `/use-cases/mcp-use-cases`, `/use-cases/research-pipeline` |

## Future Directions Under Evaluation

These are real directions, but they are **not** current product claims:

- **Agent Autopilot** is currently a spike topic, not a shipped capability. The most honest next slice is human-approved workflow orchestration, not silent autonomy. See [docs/reference/project-positioning.md](./docs/reference/project-positioning.md).
- **Hosted or managed SourceHarbor** is also a spike topic, not a current promise. Today the repository remains source-first and local-proof-first. See [docs/reference/project-positioning.md](./docs/reference/project-positioning.md).

## First Practical Win

Choose the shortest honest path for the result you want first:

| I want to... | Do this first | What I get |
| --- | --- | --- |
| discover the repo-local command surface first | `./bin/sourceharbor help` | a thin menu over the existing `bin/*` entrypoints without inventing a second CLI stack |
| evaluate without booting anything | [docs/see-it-fast.md](./docs/see-it-fast.md) | the fastest public tour of the command center, digest feed, and job trace |
| run a real local flow | [docs/start-here.md](./docs/start-here.md) | the shortest repo-documented path to a local stack and a queued or completed job |
| inspect the trust boundary first | [docs/proof.md](./docs/proof.md) | the current proof map, including what is locally provable and where the public boundary stops |

There are three honest first paths:

- **Evaluate fast:** inspect the product shape and evidence surfaces without booting anything.
- **Run locally:** install dependencies, boot the stack, and queue a real job on your own machine.
- **Inspect the trust boundary:** read the proof ladder first so you know exactly which claims are local proof and which still depend on live remote verification.

> Truth route, in plain English:
> `README.md` is the front door, [`docs/start-here.md`](./docs/start-here.md) is the first real run, [`docs/proof.md`](./docs/proof.md) is the proof ladder, and [`docs/project-status.md`](./docs/project-status.md) plus the public reference docs keep the stable shipped-vs-gated summary.

Current non-promises:

- SourceHarbor is **not** described here as a turnkey hosted team workspace.
- Agent autopilot remains a bounded spike direction, not a shipped product capability.
- Those future-direction boundaries live in [docs/reference/project-positioning.md](./docs/reference/project-positioning.md) and [docs/reference/ecosystem-and-big-bet-decisions.md](./docs/reference/ecosystem-and-big-bet-decisions.md). Volatile working contracts stay in the internal planning ledger and are not part of the public repo story.

If you want the shortest honest summary of what is already real, what is still gated, and what remains future direction, read [docs/project-status.md](./docs/project-status.md).

## See It In 30 Seconds

If you only have half a minute, do not start with setup. Start with the three surfaces that explain the product fastest:

1. **Command center:** one operator view for subscriptions, intake, job counts, and recent artifacts.
2. **Digest feed:** a reading flow where entries such as `AI Weekly` and `Digest One` become reusable summaries instead of lost links, and already-materialized items can jump straight into the current reader edition.
3. **Job trace:** a step-by-step timeline with statuses, retries, degradations, and artifact references.

```text
Source -> queued job -> digest feed -> searchable artifact -> MCP / API reuse
```

Representative result shape, based on the current digest template and UI surfaces:

```markdown
# AI Weekly

> Source: [Original video](https://www.youtube.com/watch?v=abc)
> Platform: youtube | Video ID: video-uid-123 | Generated at: 2026-02-10T00:00:00Z

## One-Minute Summary
- This episode focuses on agent workflows, operator visibility, and job trace.

## Key Takeaways
- Every job carries a step summary, artifacts index, and pipeline final status.
```

For the lightweight evaluation path, go to [docs/see-it-fast.md](./docs/see-it-fast.md).

## Why Star SourceHarbor Now

- **It solves the full loop, not a single step.** SourceHarbor handles subscription intake, ingestion, digest production, artifact indexing, retrieval, and notification-ready outbound lanes in one system.
- **It exposes proof, not vague claims.** Jobs, artifacts, step summaries, CI, and local verification paths are all first-class public surfaces.
- **It is ready for operators and agents at the same time.** Humans use the command center. Agents use API and MCP. Both point at the same pipeline.
- **It is already shaped like a real product.** The repository is source-first and inspectable, but the public surface is now optimized around outcomes rather than internal wiring.

## What You Get

| Surface | What you can do | Why it matters |
| :-- | :-- | :-- |
| **Subscriptions** | Start from strong YouTube/Bilibili templates or widen into RSSHub and generic RSS intake through the shared backend template catalog | Build a durable intake layer without pretending every source family is equally proven |
| **Digest feed** | Read generated summaries in one operator flow, then jump into the current reader edition when that digest already has a published doc bridge | Turn long-form content into an actionable daily reading stream without hiding the finished published-doc layer |
| **Search & Ask** | Search raw evidence and turn a watchlist or selected story briefing into an answer + change + citation flow on one page, with Briefings and Ask now sharing a server-owned story read-model instead of parallel browser-side selection glue | Make the knowledge layer visible without pretending every question already has a global answer engine |
| **Job trace** | Inspect pipeline status, retries, degradations, and artifacts | Debug with evidence instead of guessing what happened |
| **Notifications** | Configure and send digests outward when the notification lane is enabled | Push results outward instead of trapping them in a database |
| **Retrieval** | Search over generated artifacts | Reuse digests as a searchable knowledge layer |
| **MCP tools** | Expose subscriptions, ingestion, jobs, artifacts, search, and notifications to agents | Let assistants act on the same system without custom glue code |

## Evaluate Fast: No-Boot Tour

Think of this like walking past a storefront window before deciding whether to step inside.

This path is for evaluation, not a hosted trial. You are inspecting the product shape, evidence surfaces, and result format before deciding whether a local run is worth it.

1. Open [docs/see-it-fast.md](./docs/see-it-fast.md) to see the command center, digest feed, and job trace path in one page.
2. Open [docs/proof.md](./docs/proof.md) to see what is locally provable today and where the public-proof boundary stops. Treat it as the evidence map, not as a machine-generated live verdict page.
3. If the shape matches what you need, continue to [docs/start-here.md](./docs/start-here.md) for the local boot path.

## Run Locally: Result Path

This is the shortest truthful local setup path. It starts when you are ready to install dependencies and boot the stack yourself; it is not a hosted "try now" flow.

By the end of this path, you should have:

- a local stack running
- a first queued or completed processing job
- a digest feed you can inspect
- a job page with step-level evidence

### 1. Boot the stack

```bash
./bin/sourceharbor help
cp .env.example .env
set -a
source .env
set +a
UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$SOURCE_HARBOR_CACHE_ROOT/project-venv}" \
  uv sync --frozen --extra dev --extra e2e
bash scripts/ci/prepare_web_runtime.sh >/dev/null
./bin/bootstrap-full-stack
./bin/full-stack up
source .runtime-cache/run/full-stack/resolved.env
```

Read the resolved local routes:

- API: `${SOURCE_HARBOR_API_BASE_URL}`
- Web: `http://127.0.0.1:${WEB_PORT}`

The clean local path is container-first for Postgres. By default `.env.example`
uses `CORE_POSTGRES_PORT=15432` together with
`postgresql+psycopg://postgres:postgres@127.0.0.1:${CORE_POSTGRES_PORT}/sourceharbor`
so a host Postgres on `127.0.0.1:5432` does not silently become the active data
plane.

Two local runtime layers now stay explicitly separated:

- **core stack:** Postgres + Temporal + API/Web/Worker. `./bin/bootstrap-full-stack`
  still prefers Docker-backed core services first, but it can now fall back to
  repo-owned local Postgres/Temporal under `.runtime-cache/` when Docker is
  unavailable and local `postgres` / `initdb` / `pg_ctl` / `temporal` binaries
  exist.
  `./bin/full-stack up` can now self-heal this layer once too: when worker
  preflight finds Temporal down, it first attempts the repo-owned
  `core_services.sh up` path before failing the local start.
- **reader stack:** Miniflux + Nextflux. This stays a Docker-only optional lane
  and no longer blocks the base first-run path by default.

If you intentionally want the reader stack too, opt in:

```bash
./bin/bootstrap-full-stack --with-reader-stack 1 --reader-env-file env/profiles/reader.local.env
```

Open the operator UI at the resolved web URL:

- `http://127.0.0.1:${WEB_PORT}`

If you only need the repo-managed local proof, stop at the supervisor checks
first:

```bash
./bin/full-stack status
./bin/doctor
curl -sS "${SOURCE_HARBOR_API_BASE_URL}/healthz"
curl -I "http://127.0.0.1:${WEB_PORT}/ops"
```

`./bin/smoke-full-stack --offline-fallback 0` is the stricter long live-smoke
lane. It goes beyond local supervisor proof and can still stop on provider-side
YouTube preflight or Resend sender configuration even after the local stack is
healthy.

### 2. Set the local write token for direct API calls

```bash
export SOURCE_HARBOR_API_KEY="${SOURCE_HARBOR_API_KEY:-sourceharbor-local-dev-token}"
```

If you launch the API outside `./bin/full-stack up`, export both
`SOURCE_HARBOR_API_KEY` and `WEB_ACTION_SESSION_TOKEN` **before** starting the
API process so write routes and web actions share the same local token contract.

When you stay on the repo-managed `./bin/full-stack up` path, SourceHarbor now
writes the local web runtime's `.env.local` inside
`.runtime-cache/tmp/web-runtime/workspace/apps/web/` so the browser bundle and
server actions both inherit the same local write-session fallback. This keeps
`CI=false` style env noise from accidentally suppressing the maintainer-local
`sourceharbor-local-dev-token` fallback.

### 3. Queue a first processing run

Replace the sample URL with any public YouTube or Bilibili video:

```bash
curl -sS -X POST "${SOURCE_HARBOR_API_BASE_URL}/api/v1/videos/process" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SOURCE_HARBOR_API_KEY}" \
  -d '{
    "video": {
      "platform": "youtube",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    },
    "mode": "full"
  }'
```

### 4. Inspect the resulting job and feed

```bash
curl -sS "${SOURCE_HARBOR_API_BASE_URL}/api/v1/videos" | jq
curl -sS "${SOURCE_HARBOR_API_BASE_URL}/api/v1/feed/digests" | jq
curl -sS "${SOURCE_HARBOR_API_BASE_URL}/api/v1/jobs/<job-id>" | jq
```

Current maintainer-local truth for the real YouTube `mode=full` lane:

- a fresh local run can complete again
- the repo-side fixes that made this true were:
  - current Gemini fast-model naming (`gemini-3-flash-preview`)
  - file-upload waiting until Gemini Files becomes `ACTIVE`
  - a lightweight proxy-video path so giant raw `.webm` downloads do not stall
    the primary video lane forever

Open these front-door routes after the stack is up:

- `/search` for grounded search
- `/ask` for the story-aware, briefing-backed Ask front door, now sharing the same server-owned selected-story read-model that `/briefings` uses
- `/mcp` for the in-product MCP front door
- `/ops` for operator diagnostics and hardening gates

The truthful package story today is intentionally thin:

- `sourceharbor` from [`packages/sourceharbor-cli`](./packages/sourceharbor-cli/README.md) stays repo-aware and delegates to the repo-local command substrate instead of pretending to manage the whole local runtime itself
- `./bin/sourceharbor mcp` and `./bin/sourceharbor doctor` remain the repo-local operator entrypoints
- [`packages/sourceharbor-sdk`](./packages/sourceharbor-sdk/README.md) is the public TypeScript SDK surface and still stays contract-first instead of becoming a second business-logic stack
- Python SDK, Hosted, Autopilot, and plugin-market surfaces still stay later/no-go

### 5. Run the repo smoke path

```bash
./bin/smoke-full-stack --offline-fallback 0
```

When you want the operator-side log trail, start at `.runtime-cache/logs/components/full-stack`.

If you want the stricter repo-side closeout gate on a maintainer workstation,
`./bin/repo-side-strict-ci --mode pre-push` still prefers the standard-env
container path while Docker is healthy, but it now falls back to the
host-bootstrapped pre-push quality gate when the Docker daemon itself is the
only missing layer.

For a guided version with operator notes and public-proof boundaries, go to [docs/start-here.md](./docs/start-here.md).

## Why SourceHarbor Feels Different

Most repos in this space stop at one of these layers:

- a transcript extractor
- a summarizer script
- a search index
- an internal dashboard

SourceHarbor is built around the full knowledge flow:

1. **Capture** sources continuously
2. **Process** each item into job-backed artifacts
3. **Read** results in a digest feed
4. **Search** generated knowledge later
5. **Deliver** updates through configured notifications when the outbound lane is enabled
6. **Reuse** the same surface through MCP and API

See the full comparison in [docs/compare.md](./docs/compare.md).

## Public Proof, Not Hand-Waving

This repository does not ask you to trust product copy on its own.

- **Proof of behavior:** [docs/start-here.md](./docs/start-here.md)
- **Proof of runtime truth:** [docs/runtime-truth.md](./docs/runtime-truth.md)
- **Proof of architecture:** [docs/architecture.md](./docs/architecture.md)
- **Proof of verification:** [docs/testing.md](./docs/testing.md)
- **Proof of current public claims:** [docs/proof.md](./docs/proof.md)

GitHub profile intent is tracked in `config/public/github-profile.json`. Use
`python3 scripts/github/apply_public_profile.py --verify` to compare the live
description, homepage, and topics against the current tracked intent, and use
`python3 scripts/github/apply_public_profile.py` when you intentionally want to
sync those settings after current `main` truth is ready. Social preview upload
still requires a manual GitHub Settings check.

Operator-generated pointers and historical planning ledgers can help maintainers inspect deeper evidence, but they are not the public truth route.

> SourceHarbor is a public, source-first engineering repository.
>
> It is inspectable, and you can run it locally. It is not marketed as a turnkey hosted product, and external distribution claims are valid only when live remote workflows prove them for the current `main` commit.

For local verification, the repo-managed route snapshot under
`.runtime-cache/run/full-stack/resolved.env` is the runtime truth for API/Web
ports. Do not assume any process already listening on `9000`, `3000`, or
`5432` belongs to the clean-path stack.

## Documentation Map

Start where you are:

- **I want the fastest first impression:** [docs/index.md](./docs/index.md)
- **I want the no-boot product tour:** [docs/see-it-fast.md](./docs/see-it-fast.md)
- **I want to see a real local result:** [docs/start-here.md](./docs/start-here.md)
- **I want the system map:** [docs/architecture.md](./docs/architecture.md)
- **I want the MCP quickstart:** [docs/mcp-quickstart.md](./docs/mcp-quickstart.md)
- **I want the public builder packages:** [docs/builders.md](./docs/builders.md), [starter-packs/README.md](./starter-packs/README.md), [packages/sourceharbor-cli/README.md](./packages/sourceharbor-cli/README.md), [packages/sourceharbor-sdk/README.md](./packages/sourceharbor-sdk/README.md)
- **I want proof and verification commands:** [docs/proof.md](./docs/proof.md)
- **I want testing and CI details:** [docs/testing.md](./docs/testing.md)
- **I want positioning and trade-offs:** [docs/compare.md](./docs/compare.md)
- **I want contributor/community paths:** [CONTRIBUTING.md](./CONTRIBUTING.md), [SUPPORT.md](./SUPPORT.md), [SECURITY.md](./SECURITY.md)

## FAQ Snapshot

### Is this a hosted SaaS?

No. SourceHarbor is a source-first repository you can inspect, run locally, adapt, and extend.

### Is this only for video?

No. The public surface is strongest around long-form video today, but the feed and retrieval layers already model both `video` and `article` content types.

### Why star it if I am not deploying it this week?

Because it sits at the intersection of source ingestion, digest pipelines, retrieval, operator UI, and MCP reuse. Even if you are not adopting it immediately, it is a strong reference point for how to turn long-form inputs into reusable knowledge products.

More questions are answered in [docs/faq.md](./docs/faq.md).

## Repository Surfaces

- `apps/api`: FastAPI service for ingestion, jobs, artifacts, retrieval, notifications, and operator controls
- `apps/worker`: pipeline runner, Temporal workflows, and delivery automation
- `apps/mcp`: MCP tool surface for agents
- `apps/web`: browser command center for operators
- `contracts`: shared schemas and generated contract artifacts
- `docs`: layered public navigation, proof, and architecture

## Community

- **Questions and roadmap discussion:** [GitHub Discussions](https://github.com/xiaojiou176-open/SourceHarbor/discussions)
- **Bug reports and feature requests:** [GitHub Issues](https://github.com/xiaojiou176-open/SourceHarbor/issues)
- **Security reports:** [SECURITY.md](./SECURITY.md)
- **Project conduct and ownership:** [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md), [.github/CODEOWNERS](./.github/CODEOWNERS)
- **Rights and public artifact boundaries:** [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md), [docs/reference/public-artifact-exposure.md](./docs/reference/public-artifact-exposure.md)
- **Public asset provenance:** [docs/reference/public-assets-provenance.md](./docs/reference/public-assets-provenance.md)

## License

SourceHarbor is released under the MIT License. See [LICENSE](./LICENSE).
