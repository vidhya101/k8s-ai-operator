---
name: dast-security-testing
description: Dynamic Application Security Testing (DAST) with OWASP ZAP — scanning a running application for exploitable vulnerabilities, distinct from static (SAST) or dependency (SCA) scanning. Use when setting up or reviewing a DAST gate in the pipeline.
---

# DAST (OWASP ZAP)

Tests a **running** application from the outside (like an attacker would), catching what static analysis
can't: actual request/response behavior, auth flow weaknesses, misconfigured headers, and runtime-only
vulnerabilities. Complements, doesn't replace, `sonarqube` (SAST) and `trivy`/`snyk` (SCA/image) —
each catches a different class of issue at a different pipeline stage.

## Where DAST Fits

```text
SAST (sonarqube)      — source code, at PR time, no running app needed
SCA (trivy/snyk)        — dependencies, at PR/build time, no running app needed
Image scan (trivy)       — the built container, at build time, no running app needed
DAST (OWASP ZAP)          — the actual running application, needs a deployed target (staging, a
                             preview environment, or an ephemeral environment spun up for the scan)
```

DAST necessarily runs later in the pipeline than the other scan types, since it needs something actually
running to attack — place it against a staging/preview environment before production, not as a
production-only check.

## Running ZAP

```bash
# Baseline scan — passive only, fast, safe to run against anything including production
docker run -t zaproxy/zap-stable zap-baseline.py -t https://staging.example.com -r report.html

# Full scan — active attack simulation (SQLi, XSS attempts, etc.) — only against staging/test
# environments with data you can afford to have corrupted/exercised, never production
docker run -t zaproxy/zap-stable zap-full-scan.py -t https://staging.example.com -r report.html

# API scan — targets an OpenAPI/GraphQL spec directly instead of crawling
docker run -t zaproxy/zap-stable zap-api-scan.py -t https://staging.example.com/openapi.json -f openapi
```

- **Baseline scan**: passive, non-intrusive — safe against any environment including production for
  ongoing monitoring, catches missing security headers, cookie flags, obvious exposed info.
- **Full scan**: actively attempts exploitation (injection, XSS payloads) — only run against a
  non-production environment; this can genuinely corrupt data or trigger real side effects if pointed at
  a live production system.
- Authenticated scanning (providing ZAP with valid session credentials/a login script) finds far more than
  an unauthenticated crawl — most of an application's actual attack surface is behind auth; an
  unauthenticated-only DAST scan gives a false sense of coverage.

## Pipeline Integration

- Gate on ZAP's alert severity the same way as any other scanner (`devsecops` skill's severity-threshold
  principle) — confirm the blocking threshold with the user rather than assuming.
- A DAST finding on a staging environment still needs the same fix-and-verify cycle as a SAST/SCA
  finding — don't treat DAST as informational-only just because it runs later in the pipeline.

## Common Pitfalls

- Full/active scan pointed at a production URL "just this once" — this is a real attack against a real
  system and can cause genuine damage/data corruption; treat it with the same caution as any other
  irreversible production action.
- Unauthenticated-only scanning, missing the majority of the actual application (everything behind login).
- DAST run once at initial setup and never again — a new feature/endpoint added later has no DAST
  coverage until the scan is re-run; needs to be a recurring pipeline stage, not a one-time audit.
- ZAP findings triaged with no exploitability check (same principle as the `security-auditor` agent) —
  not every alert is equally urgent; a missing security header is not the same severity as a confirmed
  SQL injection point.
