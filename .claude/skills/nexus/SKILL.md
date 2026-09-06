---
name: nexus
description: Sonatype Nexus Repository as the artifact-of-record — hosted/proxy/group repositories for packages, retention policies, and vulnerability scanning integration. Use when managing build artifacts, package caching, or Nexus repository configuration.
---

# Nexus Repository

Generic and language-specific artifact management (npm, Maven, PyPI, Docker, raw files) — typically the
artifact-of-record for build outputs and a caching proxy for public registries.

## Repository Types

- **Hosted**: artifacts your own builds publish to (release and/or snapshot repos) — the source of truth
  for what your org built.
- **Proxy**: caches an upstream public registry (npm registry, Maven Central, PyPI, Docker Hub) — speeds
  up builds and provides resilience if the upstream is briefly unavailable, and is a natural point to
  apply org-wide vulnerability/license policy on what gets pulled in.
- **Group**: a single URL that aggregates hosted + proxy repos, so consumers (CI, developers) point at one
  endpoint instead of juggling multiple repo URLs.

## Common Configuration

```text
- Retention/cleanup policies on hosted snapshot repos — unbounded accumulation of snapshot builds is a
  common cause of Nexus disk exhaustion; keep releases indefinitely (or per compliance requirement),
  prune snapshots on a schedule.
- Blob store sizing and location (local disk vs. S3-backed) matched to expected artifact volume.
- Role-based access: publish rights scoped to CI service accounts/specific teams, not broadly writable.
```

## Key Operations

```bash
# Publish (example: npm, mirrors similarly for other formats via each tool's registry config)
npm publish --registry https://<nexus>/repository/npm-hosted/

# Consume via the group repo
npm config set registry https://<nexus>/repository/npm-group/

# REST API (component/search operations, used for cleanup scripting or CI checks)
curl -u <user>:<pass> "https://<nexus>/service/rest/v1/search?repository=<repo>"
```

## Common Pitfalls

- Publishing directly to a hosted repo from a developer machine instead of only from CI — breaks
  traceability of what produced a given artifact.
- No cleanup policy on a snapshot/dev repository, silently filling the blob store until writes start
  failing.
- Consumers pointed directly at a proxy repo instead of the group repo, bypassing any hosted-repo
  artifacts that should take precedence.
- Nexus not integrated with a vulnerability scanner (Nexus IQ, or an external scan on ingest) for the
  proxy layer, meaning a known-vulnerable package can be pulled in without any gate at the point it enters
  the org's artifact stream.
