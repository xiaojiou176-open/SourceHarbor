# Public Distribution Status

This page is the shortest truthful answer to:

- which public distribution artifacts already exist
- which official-surface submissions are still only template-ready or bundle-ready
- which final steps still require human action or platform review
- what counts as proof after a submission is made

Use it like a shipping ledger, not like a launch post.

## Reading Rule

Keep these layers separate:

- repo-side packaging truth
- current remote `main` truth
- live release truth
- official-surface submission truth
- human-only or policy-gated submission steps

Do not collapse "bundle exists" into "officially listed."

## Current Public Distribution Matrix

| Surface | Strongest repo-side artifact today | Current public truth | What still needs to happen | Read-back proof to capture |
| --- | --- | --- | --- | --- |
| **Codex** | `starter-packs/codex/sourceharbor-codex-plugin/` | Codex-compatible plugin bundle exists; official self-serve listing still is not open | use the strongest public distribution surface that Codex currently allows; if an official directory submission path opens, submit there | listing URL, marketplace entry URL, or official directory receipt |
| **Claude Code** | `starter-packs/claude-code/sourceharbor-claude-plugin/` | submission-ready plugin bundle exists; live listing still depends on Anthropic review | submit the bundle to the official marketplace path when account policy and review flow allow it | submission receipt, pending review URL, live listing URL, or review identifier |
| **OpenClaw / ClawHub** | `starter-packs/openclaw/clawhub.package.template.json` plus `starter-packs/openclaw/` | first-cut local starter pack exists; ClawHub package metadata is publish-ready; no live publish receipt exists yet | publish or submit the OpenClaw package to the strongest official surface ClawHub/OpenClaw currently supports | publish receipt, package URL, pending review URL, or registry confirmation |
| **Official MCP Registry** | `starter-packs/mcp-registry/sourceharbor-server.template.json` | metadata template exists; registry publication is not proven yet | submit against the official MCP Registry path after verifying namespace ownership and install-artifact requirements | submission receipt, registry listing URL, or namespace verification result |
| **Public skills / starter surface** | `docs/public-skills.md`, `starter-packs/**`, `templates/public-skills/**`, `examples/**` | public starter surface is real and linked from the repo today | keep the surface honest, reproducible, and aligned with the actual bundles/templates above | docs links, sample command paths, and versioned starter assets |
| **GitHub social preview** | `docs/assets/sourceharbor-social-preview.png` and tracked config entry in `config/public/github-profile.json` | tracked asset exists, but live GitHub upload still remains a manual platform step | upload the image in the GitHub repo social preview settings | live GitHub social preview image shown on the repo |

## Current Release Truth

Release-current truth is still not the same thing as current remote `main`.

Current live reading:

- current remote `main` is active and green
- release-side truth is still separate
- if no live GitHub release exists yet, that absence is part of the current truth and must be stated honestly

Use [project-status.md](./project-status.md) and [proof.md](./proof.md) together before repeating any "release-ready" or "release-aligned" claim.

## What The Agent Can Finish Before You Touch Anything

These are still repo-side or documentation-side:

- tighten builder/front-door copy and navigation
- align README / builders / public-skills / proof/status wording
- keep bundles, templates, and starter packs internally consistent
- prepare submission metadata, listing copy, proof-loop language, and install paths
- produce a surface-by-surface submission ledger
- prepare the exact read-back checklist for each official surface

## What Usually Stays Human-Only

These are the steps most likely to require you:

- logging into the target platform
- solving CAPTCHA or human verification
- accepting marketplace or registry terms
- completing irreversible profile, payment, or legal fields
- clicking the final "Submit" button when the platform blocks automation
- uploading the GitHub social preview image

If a platform supports true self-serve submission without those gates, the agent can handle more.

## Exact Read-Back Checklist

After any submission, capture the strongest proof available:

1. submission receipt or success toast
2. pending review URL or review identifier
3. live listing URL if already published
4. exact package / bundle version or artifact reference
5. any policy-gated blocker that stopped the flow

If the platform only accepts the package and moves into review, that still counts as repo-side completion with an external blocker, not as failure.

## Related Surfaces

- [README.md](../README.md)
- [docs/builders.md](./builders.md)
- [docs/media-kit.md](./media-kit.md)
- [docs/public-skills.md](./public-skills.md)
- [docs/project-status.md](./project-status.md)
- [docs/proof.md](./proof.md)
