---
name: platform-engineering
description: Platform Engineering discipline — internal developer platforms, golden paths, and self-service infrastructure with guardrails. Use for developer-experience/platform design questions; see the principal-platform-engineer agent for a structured review.
---

# Platform Engineering

Building an internal developer platform (IDP) that makes the safe, supported way to do something also
the easiest way — see the `principal-platform-engineer` agent for a structured review of a specific
proposal.

## Golden Paths

- A golden path is a documented, supported, opinionated way to accomplish a common task (provision a
  database, deploy a new service, add a CI pipeline) — it should be the path of least resistance, not the
  only path enforced by a hard block, unless there's a compliance reason to disallow alternatives entirely.
- A golden path earns adoption by being genuinely easier than the alternative, not by mandate alone — if
  teams are routing around it, that's a signal the path itself needs improvement, not (only) more
  enforcement.

## Self-Service with Guardrails

- Teams should be able to provision what they need (a new service scaffold, a database, a namespace)
  without a manual ticket/approval for the common case, with policy-as-code (see `devsecops` skill)
  enforcing the guardrails automatically instead of a human reviewer gating every request.
- Guardrails belong in the platform (a Terraform module that only exposes safe configuration options, an
  admission policy that rejects an insecure manifest) rather than in a wiki page nobody reads before
  making the mistake.

## Interface Design

- The platform's interface (a CLI, a template repo, a Backstage-style catalog, a Terraform module) should
  hide genuinely unnecessary complexity — but not so much that a team hits a wall the moment their need
  doesn't fit the golden path exactly. An escape hatch (a documented way to go off-path with appropriate
  extra scrutiny) beats a hard wall that just pushes teams to route around the platform entirely.

## Common Pitfalls

- Building a platform abstraction before more than one team has actually asked for it — premature
  platform investment is still premature abstraction (see `CLAUDE.md` Section 1.2).
- A "self-service" system that still requires a ticket and 3-day wait for the platform team to actually
  provision — self-service in name only.
- No feedback loop from the teams using the platform back to the platform team, so friction accumulates
  invisibly until adoption quietly drops.
- Platform team's own on-call/maintenance burden growing unsustainably because every team's edge case was
  accommodated inside the "golden path" instead of via a documented escape hatch.
