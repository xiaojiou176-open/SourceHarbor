# Public Artifact Exposure

This page defines which artifact shapes are safe to expose in the public repository.

## Safe Public Artifact Types

- sanitized markdown examples
- public contract snapshots
- generated proof indexes that do not embed sensitive payloads
- performance samples that are explicitly marked as public and sanitized

## Unsafe Public Artifact Types

- raw operator logs
- customer content
- unsanitized email digests
- private job payloads
- environment files or runtime secrets

## Practical Rule

If an artifact contains real user data, credentials, or sensitive runtime context, it does not belong in the tracked public surface.

If an artifact is meant to explain repository behavior to a newcomer, it should be:

- sanitized
- intentionally named
- stable enough to cite from README or docs

Two special cases matter in the current repo:

- workflow-dispatch readiness receipts may be public-safe to track while still waiting on protected-environment approval
- browser/login proof receipts can explain local operator state without turning third-party account surfaces into public product claims

For public presentation files under `docs/assets/`, use the file-level ledger in [public-assets-provenance.md](./public-assets-provenance.md).
