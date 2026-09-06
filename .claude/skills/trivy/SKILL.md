---
name: trivy
description: Vulnerability and misconfiguration scanning with Trivy — container images, filesystems/dependencies, and IaC. Use when running or interpreting a Trivy scan, or wiring one into a pipeline.
---

# Trivy

All-in-one scanner: container image CVEs, filesystem/dependency vulnerabilities, IaC misconfiguration,
and secret detection, in one tool.

## Scan Types

```bash
trivy image <name>:<tag>                          # OS packages + app dependencies in a built image
trivy image --severity HIGH,CRITICAL <name>:<tag>  # filter to what should block a pipeline
trivy fs .                                          # dependency vulnerabilities in the source tree
trivy fs --scanners vuln,secret .                   # also scan for committed secrets
trivy config .                                      # IaC misconfiguration (Terraform, K8s, Dockerfile)
trivy repo <git-url>                                # scan a remote repo without cloning manually
```

## Pipeline Integration

- Place an image scan (`trivy image`) right after build, before push — catch it before it reaches a
  registry, not after.
- Place a filesystem scan (`trivy fs`) at PR time — catches a newly added vulnerable dependency before
  merge, cheaper to fix than after it's built into an image.
- Exit code matters for gating: `--exit-code 1` on findings at/above the agreed severity makes the scan
  actually block the pipeline; without it, Trivy reports but doesn't fail the build.
- `--ignore-unfixed` to suppress findings with no available fix yet — reduces noise, but confirm this
  policy with the user since it means some real (if currently unfixable) risk goes unflagged in the gate.

## Interpreting Results

- A finding needs: the vulnerable package/resource, severity, whether a fix is available, and (for
  images) which layer introduced it.
- Cross-reference reachability before treating severity alone as priority — a CRITICAL in a dependency
  never invoked on any reachable code path is lower real risk than it looks (see the `security-auditor`
  agent for this triage).
- For IaC findings (`trivy config`), each maps to a specific misconfiguration class (public bucket,
  missing encryption, overly permissive IAM) — treat the same way as `checkov` findings.

## Common Pitfalls

- Running `trivy image` against `:latest` in CI instead of the actual immutable tag being shipped —
  scans the wrong artifact if `latest` has since moved.
- No `--exit-code` set, so the scan runs, reports, and the pipeline proceeds regardless of findings —
  looks like a working gate but isn't one.
- Suppressing a finding with `.trivyignore` with no comment explaining why — treat as its own finding
  (see `.claude/rules/secrets.md` and the general suppression-discipline principle).
- Scanning only the final image and never the base image directly — makes it unclear whether a CVE came
  from the base or from something added on top.
