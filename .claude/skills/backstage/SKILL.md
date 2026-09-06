---
name: backstage
description: Backstage — the most widely-adopted open-source Internal Developer Platform (IDP) framework, for a software catalog, golden-path templates, and TechDocs. Use when a platform-engineering effort is standardizing on Backstage; see platform-engineering for the discipline this implements concretely.
---

# Backstage

An open-source framework (originated at Spotify) for building an Internal Developer Platform — the
concrete tool most commonly used to implement what the `platform-engineering` skill describes
conceptually (golden paths, self-service, a catalog of what exists). Not a SaaS product — it's a
framework you deploy and customize, which is both its main strength (fits your org) and its main cost
(needs real ongoing engineering investment, not just configuration).

## Core Concepts

- **Software Catalog**: a structured inventory of every service/component/API/resource an org owns,
  defined via `catalog-info.yaml` files living alongside the code they describe — the answer to "what do
  we actually have and who owns it," which most orgs past a certain size don't have a reliable source of
  truth for otherwise.

```yaml
# catalog-info.yaml, in a service's own repo
apiVersion: backstage.io/v1alpha1
kind: Component
metadata: { name: orders-service, description: "Handles order processing" }
spec:
  type: service
  owner: team-commerce
  lifecycle: production
  dependsOn: ["component:default/payments-service"]
```

- **Software Templates** (Scaffolder): the concrete implementation of a golden path — a developer fills
  in a form, Backstage generates a new repo/service scaffold following the org's standards (CI config,
  Dockerfile, base structure) instead of copy-pasting from an existing service and hoping they didn't
  copy something stale.
- **TechDocs**: docs-as-code (Markdown in the repo, rendered in the Backstage UI) — keeps documentation
  next to the code it describes instead of drifting in a separate wiki.
- **Plugins**: Backstage's extensibility model — a huge ecosystem of plugins integrating CI/CD status,
  cost data, security posture, on-call info, etc. directly into each catalog entity's page, making
  Backstage the single pane of glass the `platform-engineering` skill's IDP concept describes.

## Adoption Reality

- Backstage is a framework requiring real, ongoing engineering investment (a dedicated platform team, or
  at least dedicated time) — not a deploy-and-forget tool. Confirm the organization actually has the
  capacity to own it before recommending it; an under-resourced Backstage instance with a stale catalog
  is worse than no catalog (false confidence in data nobody kept current).
- Catalog data quality depends entirely on teams actually maintaining `catalog-info.yaml` — without an
  enforcement mechanism (a CI check requiring one, ownership metadata review), the catalog decays exactly
  the way undocumented systems always do.

## Common Pitfalls

- Deployed without a clear owner/maintenance plan, becoming another IDP tool nobody keeps updated —
  the specific "self-service in name only" failure mode `platform-engineering` warns about.
- Software Templates that don't actually stay in sync with the org's evolving standards, so
  scaffolded services are outdated relative to current best practice from day one.
- Catalog entities created once and never updated as ownership/architecture changes, becoming actively
  misleading rather than just incomplete.
- Treating the catalog as optional documentation instead of the source of truth other tooling (cost
  attribution, on-call routing, security posture) increasingly depends on as plugins get added.
