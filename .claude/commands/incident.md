---
description: Start structured incident triage — severity, timeline, correlation across metrics/logs/traces, and next actions.
argument-hint: "<what's happening / alert that fired>"
---

Incident: $ARGUMENTS

Delegate to the `production-incident-commander` agent (drawing on `sre`, `observability-engineer`'s
skills, and whichever of `prometheus`/`grafana`/`loki`/`mimir`/`datadog` the repo actually uses).

1. State severity and blast radius as best known right now (even if incomplete) — don't wait for full
   certainty before giving an initial assessment.
2. Correlate the four signals in order: what alert/symptom fired → what metric shows it → what do logs in
   that window say → is there a trace for a representative failing request. Note which of these aren't
   available in this environment rather than skipping silently.
3. Look for a recent change as the likely trigger: last deploy, last Terraform apply, last config change,
   last ArgoCD sync — correlate timing against when the symptom started.
4. Propose the smallest safe mitigation (rollback, scale, feature flag, traffic shift) before proposing a
   root-cause fix — stop the bleeding first, understand fully second.
5. Every mutating action proposed here still goes through the normal confirmation gate.

Close with a structure the user can paste into an incident channel: Severity / Impact / Current status /
Timeline / Next action / Owner-needed-for.
