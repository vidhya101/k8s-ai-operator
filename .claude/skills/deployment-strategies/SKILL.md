---
name: deployment-strategies
description: Progressive delivery patterns — blue-green, canary, and rolling deployments — the mechanics and tradeoffs of each, and how they're implemented across Kubernetes, ArgoCD/Argo Rollouts, and cloud-native deploy tooling. Use when choosing or reviewing a deployment strategy for a specific service.
---

# Deployment Strategies (Blue-Green, Canary, Rolling)

The mechanics behind progressive delivery, referenced but not detailed in `cicd-pipeline-design`,
`kserve` (model rollout), and `aws-native-cicd` (CodeDeploy traffic shifting) — this skill is the shared
reference for the pattern itself, independent of which specific tool implements it.

## Rolling Deployment (Kubernetes Deployment's default)

- Replaces old pods with new ones incrementally (`maxSurge`/`maxUnavailable` control the pace) — no
  separate environment needed, simplest to operate, but a bad rollout is *mixed in* with good pods during
  the transition (some requests hit old code, some hit new, simultaneously) rather than being cleanly
  isolated.
- Rollback is `kubectl rollout undo` — fast, but only reverts the Deployment's pod spec, not any other
  side effects (a schema migration that already ran, external state already changed) — see
  `database-operations`'s rolling-deploy-compatible-migration principle for why this matters.

## Blue-Green

- Two full, independent environments ("blue" = current, "green" = new); traffic cuts over all at once
  (or is switched back) at the load balancer/DNS/Service-selector level — the new version is fully
  validated in isolation *before* receiving any real traffic, and rollback is an instant traffic
  switch-back rather than a redeploy.
- Costs double the running infrastructure during the transition (both environments fully up
  simultaneously) — a real tradeoff against rolling deployment's incremental resource usage; worth it for
  services where "all traffic hits untested new code simultaneously with no controlled ramp" is
  unacceptable risk.

## Canary

- A small percentage of traffic routed to the new version first, with the percentage increased gradually
  as confidence builds (automated, based on real metrics, or manual gate-by-gate) — the middle ground
  between rolling's "mixed in gradually with no explicit validation gate" and blue-green's
  "all-at-once cutover."
- **Automated canary analysis** (Argo Rollouts, Flagger) compares the canary's real metrics (error rate,
  latency — the same RED metrics `prometheus`/`observability-engineer` skills describe) against the
  baseline and automatically promotes or rolls back based on whether the canary is actually healthier or
  worse — turns "does this look okay" from a manual judgment call into an objective, metric-driven gate.

```yaml
# Argo Rollouts canary step example
strategy:
  canary:
    steps:
      - setWeight: 10
      - pause: { duration: 5m }
      - analysis: { templates: [{ templateName: success-rate }] }   # automated go/no-go on real metrics
      - setWeight: 50
      - pause: { duration: 10m }
```

## Choosing

```text
Rolling    — default choice for most stateless services; simplest, no extra infra cost
Blue-green  — when a clean, instant, fully-tested cutover matters more than resource efficiency
              (e.g. a major version bump, a risky migration alongside the deploy)
Canary       — when there's real traffic/user variance worth validating against gradually, and metrics
              exist to make the promote/rollback decision objectively
```

## Common Pitfalls

- Canary analysis with no automated rollback — a canary step that just waits a fixed duration and
  promotes regardless of metrics isn't actually validating anything, just adding latency to the rollout.
- Blue-green assumed to be "free" rollback safety when a database migration ran as part of the deploy —
  the code can roll back instantly, but a destructive/incompatible schema change can't be undone by a
  traffic switch alone; see `database-operations`'s migration-compatibility discipline.
- Rolling deployment's `maxUnavailable` set high enough that capacity drops meaningfully during a
  rollout, causing a self-inflicted capacity incident during what should be a routine deploy.
- A deployment strategy chosen once and never revisited as a service's risk profile changes — a service
  that started with simple rolling deploys may warrant canary once it's handling enough traffic/revenue
  that a bad rollout's blast radius has grown significantly.
