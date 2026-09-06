---
name: sre
description: Site Reliability Engineering practices — SLOs/error budgets, toil reduction, and blameless postmortems, as a discipline distinct from any specific tool. Use for reliability-process questions; see the observability skills (prometheus/grafana/etc.) for the tooling that implements them.
---

# SRE (Site Reliability Engineering)

The discipline of treating operations as an engineering problem with measurable targets, not a tool.
See `prometheus`/`grafana`/`datadog` for the instrumentation layer, and the `principal-sre` and
`production-incident-commander` agents for applied review/response.

## SLIs, SLOs, and Error Budgets

- **SLI** (Service Level Indicator): a measured value of user-facing behavior — availability, latency,
  correctness. Measure what the user experiences, not an internal proxy for it.
- **SLO** (Service Level Objective): a target for the SLI over a window (e.g. 99.9% availability over 30
  days) — should be looser than what's technically achievable, tight enough to matter to users; setting
  it is a product/business decision as much as an engineering one, don't pick a number unilaterally.
- **Error budget**: `1 - SLO` over the window — the amount of "badness" allowed before it's a problem.
  The budget only means something if crossing it has a defined consequence (freeze risky
  deploys/prioritize reliability work) — an SLO with no enforced consequence is a dashboard number, not
  a working error budget policy.

## Toil

- Toil is manual, repetitive, automatable, tactical work with no enduring value — distinct from necessary
  operational work that isn't automatable yet. Track it; if a team's toil percentage is trending up, that's
  a signal to invest in automation, not just "work harder."

## Reliability Practices

- **Blameless postmortems**: focus on system/process gaps (missing alert, unclear runbook, insufficient
  testing) rather than individual blame — people acting reasonably with the information they had is the
  default assumption; the goal is fixing the system, not finding who to blame.
- **Runbooks**: every page-worthy alert needs one reachable at 3am with reduced context — a link, not a
  requirement to remember institutional knowledge.
- **Change management**: most outages correlate with a recent change (deploy, config, infra) — correlate
  incident timing against change history as a first investigative step, every time.
- **Capacity planning**: reactive scaling (autoscaling) handles normal variance; capacity planning
  (forecasting growth against known limits — quotas, database connection limits, third-party API rate
  limits) catches what autoscaling can't fix in time.

## Common Pitfalls

- SLOs defined once and never revisited as the service's actual usage/criticality changes.
- Error budget policy that exists on paper but isn't actually enforced when the budget is burned.
- Postmortems that assign blame to a person instead of identifying the process/system gap that let the
  incident happen or last as long as it did.
- Toil treated as unavoidable "just how ops work is," rather than tracked and reduced over time.
