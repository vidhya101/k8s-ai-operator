---
name: sonarqube
description: Static code analysis and quality gates with SonarQube/SonarCloud — code smells, bugs, vulnerabilities, and coverage-on-new-code. Use when reviewing SonarQube findings or configuring a quality gate.
---

# SonarQube / SonarCloud

Static analysis (SAST) plus code-quality metrics, applied as a pipeline gate — typically at PR time.

## Core Concepts

- **Quality Gate**: a pass/fail threshold on a set of conditions (new bugs = 0, new vulnerabilities = 0,
  coverage on new code ≥ X%, duplication on new code ≤ Y%) — evaluated on *new/changed* code by default
  ("clean as you code"), not the whole codebase's historical debt, which is usually the right scope for a
  PR gate.
- **Issue types**: Bug (likely runtime defect), Vulnerability (security), Code Smell (maintainability),
  Security Hotspot (needs human review to confirm exploitability — not auto-failed like a Vulnerability).
- Coverage data comes from the project's own test run (e.g. `coverage.xml`/`lcov.info`) fed into the
  Sonar scanner — SonarQube doesn't run tests itself, it ingests results.

## Pipeline Integration

```bash
sonar-scanner \
  -Dsonar.projectKey=<key> \
  -Dsonar.sources=. \
  -Dsonar.host.url=<server> \
  -Dsonar.login=<token> \
  -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info   # language-specific coverage path
```

- Run after tests (coverage report must exist first) and before merge — a PR-blocking quality gate check,
  same placement logic as the other scan gates in `CLAUDE.md` Section 9.
- Fail the pipeline on Quality Gate status != `OK`, not just report it — same "exit code must actually
  gate" principle as `trivy`.

## Security Hotspots

- These require a human decision (is this actually exploitable in context?), unlike Vulnerabilities which
  are auto-counted against the gate — don't treat an unreviewed Hotspot backlog as "handled" just because
  it isn't failing the build; it needs a person to triage it (see the `security-auditor` agent).

## Common Pitfalls

- Quality Gate scoped to the whole codebase instead of new code, so a legacy-heavy repo can never pass
  and the gate gets disabled/ignored rather than fixed.
- Coverage report path misconfigured, so Sonar reports 0% coverage on new code and fails the gate for a
  reason that isn't the actual code quality.
- `// NOSONAR` or equivalent suppression comments added with no linked justification — same suppression-
  discipline issue as any other scanner.
- Running the scan but never actually wiring its exit status to fail the CI job, so it's informational
  only despite looking like a gate.
