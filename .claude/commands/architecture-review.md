---
description: Review a proposed or existing system/infra design for scalability, resilience, and unnecessary complexity.
argument-hint: "<what to review, e.g. 'the new EKS multi-region layout'>"
---

Review this design: $ARGUMENTS

Delegate to `principal-cloud-architect` and `principal-platform-engineer`, using the `architecture-review`
skill. Evaluate against:

- **Necessity** — does the complexity match a stated requirement (RTO/RPO, compliance, real scale need),
  or is it speculative? Flag over-engineering per `CLAUDE.md` Section 1.2 as hard as under-engineering.
- **Resilience** — multi-AZ where it matters, self-healing paths, single points of failure.
- **Blast radius** — what fails together; is there a shared-fate risk (single VPC/subscription/project,
  shared control plane, shared secret) that undermines an otherwise-redundant design?
- **Operability** — can the team on-call this? Does it need capabilities (multi-cloud tooling, a service
  mesh, a second K8s distro) the team doesn't have and didn't ask for?
- **Cost shape** — anything that scales cost non-linearly with usage without a corresponding safeguard.

Present findings as trade-offs with a recommendation, not a single "correct" answer — architecture
decisions here are the user's to make (see `CLAUDE.md` Section 1.1, "do not silently choose").
