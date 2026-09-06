---
description: Generate a Markdown Standard Operating Procedure — install, recovery, and manual-override steps.
argument-hint: "<system/process to document, e.g. 'database failover' or 'onboarding a new service'>"
---

Write an SOP for: $ARGUMENTS

Structure:

```markdown
# SOP: <title>

## When to use this
<the specific trigger/situation this SOP applies to>

## Prerequisites
<access, tools, credentials needed before starting>

## Procedure
1. Step — expected result / how to verify it worked
2. Step — expected result / how to verify it worked
...

## Manual override / rollback
<what to do if the procedure fails partway, or needs to be reversed>

## Escalation
<who/what to contact if this SOP doesn't resolve the situation>
```

- Every step should have a way to verify it worked before moving to the next — an SOP followed under
  pressure (an incident, an on-call page) needs to be unambiguous about "did this step actually succeed."
- Write for someone with less context than you have right now — no unexplained jargon, no assumed
  familiarity with why a step exists if it isn't obvious.
- Base it on the actual current setup (read the relevant Terraform/K8s/CI config first) — don't write a
  generic SOP that doesn't match what's actually deployed.
