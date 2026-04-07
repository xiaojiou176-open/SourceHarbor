# Release Artifacts

This directory stores release-side evidence that is intentionally separate from local runtime proof.

- historical examples may live here as reference material
- tracked examples in this directory are not release verdict proof for the current head
- Only the **current run** bundle should be treated as fresh release-side evidence
- current release claims still need fresh remote evidence
- internal evidence bundles exported from jobs are a different surface: reusable for collaboration, but not the same thing as release-side proof
- current maintainer-local supervisor proof does not upgrade this directory into remote release proof on its own
- latest tagged release can still lag current `main`, so a successful current-main workflow run does not automatically make the latest release current
