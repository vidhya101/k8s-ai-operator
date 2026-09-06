---
name: jfrog-artifactory
description: JFrog Artifactory — universal artifact repository manager, as an alternative to Nexus. Use when a project's artifact-of-record is Artifactory; see the nexus skill for the shared hosted/proxy/group repository concepts.
---

# JFrog Artifactory

Universal artifact repository — the same hosted/proxy/group repository model `nexus` describes, under
Artifactory's own terminology and with a few distinct capabilities worth knowing when a project uses it
instead of (or alongside) Nexus.

## Repository Model (same concepts, Artifactory naming)

- **Local repositories**: your own builds' artifacts — equivalent to Nexus's hosted repos.
- **Remote repositories**: proxy/cache an upstream public registry (npm, Maven Central, Docker Hub,
  PyPI) — equivalent to Nexus's proxy repos.
- **Virtual repositories**: aggregate local + remote under one URL for consumers — equivalent to Nexus's
  group repos.

## Distinct Capabilities Worth Knowing

- **Xray**: Artifactory's integrated security/license scanning (SCA) directly on artifacts as they're
  stored/promoted — overlaps with `trivy`/`snyk`'s role; check whether a project relies on Xray, an
  external scanner, or both before assuming scan coverage.
- **Build promotion / repository paths as pipeline stages**: a common Artifactory pattern promotes a
  build's artifacts through named repository paths (`libs-snapshot-local` → `libs-release-local`) as it
  passes pipeline gates — a repository-path-based way of expressing the same environment-promotion
  principle `cicd-pipeline-design` describes generically.
- **AQL (Artifactory Query Language)**: a query language for searching/scripting against artifact
  metadata at scale — useful for cleanup scripts (find and remove artifacts older than N days matching a
  pattern) beyond what a simple UI search supports.

```bash
# Publish (example: npm, same pattern as Nexus's registry config)
npm publish --registry https://<artifactory>/artifactory/api/npm/npm-local/

# Promote a build (CLI or REST API)
jf rt build-promote <build-name> <build-number> libs-release-local
```

## Common Pitfalls

- Same core pitfalls as `nexus`: publishing directly from a developer machine instead of only from CI,
  no cleanup/retention policy on snapshot repositories, consumers pointed at a local/remote repo directly
  instead of the virtual repo that should front them.
- Xray scan results not actually gating build promotion — same "scanner present but not wired into the
  gate" gap flagged for every other scanner in this stack.
- AQL cleanup scripts run without a dry-run/review pass first — a broad AQL query used for bulk deletion
  is as risky as any other bulk-destructive operation and deserves the same review-before-execute caution.
