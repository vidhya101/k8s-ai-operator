---
name: dora-metrics
description: DORA metrics — deployment frequency, lead time for changes, change failure rate, and MTTR — the standard framework for measuring software delivery performance. Use when asked to assess or improve a team's delivery/DevOps performance, or when designing what to actually measure.
---

# DORA Metrics

The four metrics from Google's DevOps Research and Assessment program, empirically correlated with
organizational performance — the standard, defensible way to answer "are we good at shipping software"
with data instead of opinion. See `sre` for the closely related SLI/SLO/error-budget discipline these
complement (DORA measures delivery performance; SLOs measure operational reliability — related but distinct).

## The Four Metrics

```text
Deployment Frequency     — how often code successfully deploys to production
Lead Time for Changes     — time from code committed to running in production
Change Failure Rate        — percentage of deployments causing a production failure requiring remediation
Time to Restore Service     — (MTTR) how long to recover from a production failure
```

- **Elite/High/Medium/Low** performance bands exist per the DORA research (e.g. Elite: multiple deploys
  per day, lead time under an hour, <15% change failure rate, restore in under an hour) — useful as a
  reference point, but the actual goal is a team's own trend over time, not chasing a label.

## Why These Four Specifically

- They pair **throughput** (deployment frequency, lead time) with **stability** (change failure rate,
  MTTR) — the DORA research's core finding was that these aren't in tension: elite performers are
  simultaneously fast *and* stable, contradicting the common assumption that speed necessarily trades off
  against reliability. A team improving deployment frequency while change failure rate also improves is
  the actual target pattern, not a coincidence to celebrate cautiously.

## Where the Data Actually Comes From

- **Deployment frequency / lead time**: derivable from CI/CD pipeline data (`github-actions`/`jenkins`/
  `azure-devops` skills) — deploy timestamps and commit-to-deploy time are usually already logged, just
  not aggregated into a metric.
- **Change failure rate**: requires linking a deployment to whether it caused an incident — needs
  deployments and incidents (`production-incident-commander`'s timeline data) to share a common
  correlation key (a deploy ID, a git SHA) to compute automatically rather than being manually tallied.
- **MTTR**: comes directly from incident timeline data — the same timestamps the
  `production-incident-commander` agent's postmortem structure already captures (detection → mitigation).

## Common Pitfalls

- Measuring these once as a point-in-time snapshot instead of tracking trend over time — a single
  measurement says little; the value is in whether the trend is improving or degrading.
- Change failure rate gamed by narrowing the definition of "failure" until almost nothing counts — define
  it before measuring, tied to an objective signal (an incident was opened, a rollback happened), not a
  post-hoc judgment call.
- Optimizing deployment frequency in isolation without also watching change failure rate — deploying more
  often while quietly breaking more often isn't the DORA-defined improvement; both need to move together.
- Using these as an individual performance metric instead of a team/system-level one — DORA metrics
  measure the delivery *system* (pipeline, process, architecture), not individual engineer output; using
  them to rank individuals is a misuse of what the framework was designed to measure.
