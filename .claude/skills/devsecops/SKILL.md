---
name: devsecops
description: DevSecOps as a discipline — shifting security left across the whole pipeline, policy-as-code, and least-privilege by default. Use for pipeline-wide security-posture questions; see trivy/checkov/sonarqube/snyk for specific tool mechanics.
---

# DevSecOps

Security as a property of the whole pipeline — every stage from commit to production — rather than a
single gate. See `CLAUDE.md` Section 9 for the concrete gate placement, and the `principal-devsecops` and
`security-auditor` agents for applied review.

## Shift-Left Principle

The earlier a class of risk can be caught, the cheaper it is to fix and the smaller its blast radius:

```text
Commit/PR time    → SAST, secret scanning, dependency (SCA) scan, IaC policy scan
Build time         → container image scan, license compliance
Pre-deploy         → rendered-manifest IaC scan, signed-image verification
Runtime            → runtime security monitoring, admission control (e.g. block unsigned images),
                      anomaly detection (see aiops skill)
```

A vulnerability caught at PR time costs a few minutes; the same class of vulnerability caught in
production is an incident. Design gates to catch things as early as the pipeline allows.

## Policy as Code

- Security/compliance rules expressed as code (Checkov, OPA/Gatekeeper, Sentinel) that runs automatically
  in the pipeline, rather than a manual review checklist that's easy to skip under deadline pressure.
- Policy-as-code should have a clear owner and change-review process itself — a security gate that
  anyone can quietly loosen is not much of a gate.

## Least Privilege by Default

- CI credentials, service accounts, and IAM roles scoped to exactly what each job/workload needs —
  OIDC federation over static long-lived credentials wherever the target supports it.
- Applies at every layer: cloud IAM, Kubernetes RBAC, container capabilities, registry push/pull scopes.

## Suppression Discipline

Every suppressed/ignored finding across every tool (Checkov skip, Trivy ignore, SonarQube NOSONAR, Snyk
ignore) needs a linked justification. An unexplained suppression is itself a finding — it means either a
real risk is being silenced, or the suppression's reasoning is lost the moment the person who added it
forgets why.

## Common Pitfalls

- Security treated as a single end-of-pipeline gate (e.g. only an image scan before push) instead of
  layered across commit, build, and deploy — misses classes of risk the single gate isn't designed for.
- Severity thresholds for blocking left undefined/inconsistent across tools and teams, so "the pipeline
  is secure" means different things in different repos.
- A security exception granted once under pressure that never gets revisited once the pressure is gone.
