---
description: Run the full DevSecOps scan sweep (Trivy, Checkov, secret scan, dependency audit) and triage findings.
argument-hint: "[optional: path or image to scan]"
---

Run a security sweep against: $ARGUMENTS (default: whole repo + any Dockerfile/image it builds).

1. Use the `trivy`, `checkov`, `sonarqube`, and `snyk` skills for whichever tools are actually available
   in this environment or already configured in the repo's CI — do not assume all four are installed;
   check first (`command -v trivy`, etc.) and report which ran vs. which were skipped.
2. Run, where available: `trivy fs .` (dependency/misconfig scan), `trivy config .` (IaC misconfig),
   `trivy image <image>` if an image was built, `checkov -d .` (IaC policy), a secret scan
   (gitleaks/trufflehog if present).
3. Delegate triage to the `security-auditor` agent: classify each finding by real exploitability in this
   codebase, not just raw severity — a CRITICAL CVE in an unused code path is lower priority than a MEDIUM
   in an internet-facing entry point.
4. Never auto-remediate a finding by silently adding an ignore/suppress comment — flag it for the user's
   decision, with a suggested fix.

End with a findings table: severity, tool, location, one-line description, suggested fix.
