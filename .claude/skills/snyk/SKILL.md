---
name: snyk
description: Dependency and container vulnerability scanning with Snyk — SCA, license compliance, and fix-PR workflows. Use when Snyk is the SCA tool in use, or when comparing it against Trivy for a given repo.
---

# Snyk

Commercial SCA (software composition analysis) platform — dependency vulnerabilities, container image
scanning, IaC scanning, and license compliance, with an emphasis on actionable fix suggestions/PRs.

## Scan Types

```bash
snyk test                              # dependency vulnerabilities in the current project
snyk test --severity-threshold=high    # gate at a specific severity
snyk container test <image>:<tag>       # container image scan
snyk iac test                           # IaC misconfiguration scan (Terraform, K8s, CloudFormation)
snyk monitor                            # snapshot current deps to Snyk's dashboard for ongoing tracking
```

## Pipeline Integration

- `snyk test` (or `snyk container test`) at PR time and build time respectively, same placement logic as
  `trivy`/`checkov` in `CLAUDE.md` Section 9 — gate with `--severity-threshold` and check the exit code.
- `snyk monitor` (distinct from `test`) doesn't fail the build — it registers the current dependency
  snapshot so Snyk can alert later if a *new* CVE is published against an already-shipped dependency.
  Both are useful and serve different purposes: `test` gates the current change, `monitor` watches what's
  already deployed.
- Fix PRs: Snyk can open PRs bumping a vulnerable dependency to a fixed version automatically — review
  these like any other dependency bump (check for breaking changes), don't merge blindly.

## License Compliance

- Snyk can flag dependencies under licenses the org disallows (e.g. GPL in a proprietary codebase) —
  this is a legal/policy decision, not a security one; confirm the disallowed-license list with the user
  rather than assuming a default policy.

## Common Pitfalls

- Running both Snyk and Trivy for the same purpose in the same pipeline with no clear reason — redundant
  gates that can disagree on severity scoring and confuse triage; pick one as primary unless there's a
  specific coverage gap being filled.
- `snyk monitor` mistaken for a blocking gate — it doesn't fail CI, it only sets up ongoing monitoring;
  relying on it alone means new code with a known-bad dependency isn't actually blocked at merge time.
- Auto-merging Snyk's dependency-bump PRs without running the test suite against them.
