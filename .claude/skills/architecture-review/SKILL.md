---
name: architecture-review
description: Evaluate a system/infrastructure design for necessity, resilience, blast radius, and operability. Use when reviewing a proposed architecture or auditing an existing one; pair with principal-cloud-architect/principal-platform-engineer agents for a structured review.
---

# Architecture Review

A structural lens for evaluating designs — infrastructure, service boundaries, or deployment topology.
See the `/architecture-review` command and `principal-cloud-architect`/`principal-platform-engineer`
agents for a delegated, structured pass.

## Evaluation Dimensions

- **Necessity**: is the complexity justified by a stated requirement (real scale, a compliance
  requirement, a specific RTO/RPO), or speculative? Over-engineering is a defect, not caution — flag it
  as directly as under-engineering (see `CLAUDE.md` Section 1.2).
- **Resilience**: what fails together (shared-fate analysis) — a single VPC/subscription/project, a
  shared control plane, a shared secret/credential, a single AZ — undermines redundancy elsewhere in the
  design if the "redundant" components all still share one of these.
- **Blast radius**: when this fails, what's the actual impact surface — one team, one service, one
  environment, or everything? Smaller blast radius by default (separate accounts/namespaces/state files)
  unless there's a reason to share.
- **Operability**: can the team actually run this — does it need skills/tooling (multi-cloud expertise, a
  service mesh, a second Kubernetes distro) the team doesn't currently have, and did anyone ask for that
  tradeoff explicitly?
- **Cost shape**: does cost scale linearly and predictably with usage, or is there a component that could
  scale non-linearly (e.g. unbounded metric cardinality, an uncapped autoscaling group) without a
  safeguard?

## Method

1. State the requirement driving each major design decision explicitly — if a decision (multi-region,
   multi-cloud, a particular consistency model) has no clear requirement behind it, that's a finding, not
   an assumption to fill in.
2. Trace failure scenarios: "if X fails, what else fails with it, and what stays up?" — for each critical
   dependency.
3. Compare against the simplest design that would meet the stated requirements — every increment of
   complexity beyond that needs its own justification.

## Output

Present findings as trade-offs with a recommendation, not a single mandated answer — architecture
decisions (region, provider, DR objective, deployment strategy) are explicitly the user's to make per
`CLAUDE.md` Section 1.1; this skill is for surfacing the trade-offs clearly, not deciding for them.
