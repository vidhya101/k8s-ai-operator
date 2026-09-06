---
name: dynatrace
description: Dynatrace — OneAgent auto-instrumentation, Davis AI root-cause analysis, and Smartscape topology mapping. Use when the observability/APM platform is Dynatrace rather than the Prometheus/Grafana or Datadog stacks.
---

# Dynatrace

Commercial full-stack observability platform emphasizing automatic instrumentation and AI-assisted root
cause analysis (Davis AI) over manually-built dashboards/alerts. Don't run this alongside Prometheus/
Datadog for the same signal without a specific reason — check which platform a repo actually uses first.

## OneAgent

- A single agent installed per host/container that auto-instruments processes it detects (no per-service
  SDK integration required for most supported languages/frameworks) — the main practical difference from
  OpenTelemetry/Datadog APM's more manual/explicit instrumentation model.
- Kubernetes: deployed via the Dynatrace Operator as a DaemonSet (or via CSI driver for injection into
  application pods) — verify which injection mode is in use, as it affects what needs to be present in
  the pod spec for auto-instrumentation to actually attach.

## Davis AI

- Automatically correlates anomalies across the full stack (infra, process, service, user experience) and
  proposes a root cause, rather than requiring a human to manually correlate metrics/logs/traces — the
  `observability-engineer`/`aiops-reviewer` agents' correlation principles apply here, just largely
  automated by the platform instead of hand-built.
- A Davis-identified "problem" should still be verified against the actual evidence (Smartscape topology,
  the specific failing component) before acting — treat it as a strong hypothesis, not an infallible verdict.

## Smartscape

- Automatically discovered topology map (hosts → processes → services → applications) — useful for
  understanding blast radius/dependency chains during an incident without manually maintaining a
  service-dependency diagram.

## Key Operations

```bash
# Via the Dynatrace API (token-authenticated) rather than a primary CLI:
curl -H "Authorization: Api-Token $DT_TOKEN" "$DT_ENV_URL/api/v2/problems"          # active problems
curl -H "Authorization: Api-Token $DT_TOKEN" "$DT_ENV_URL/api/v2/metrics/query?metricSelector=..."
curl -H "Authorization: Api-Token $DT_TOKEN" "$DT_ENV_URL/api/v2/entities?entitySelector=type(SERVICE)"
```

## Common Pitfalls

- OneAgent installed but a specific process/technology isn't in the supported-auto-instrumentation list —
  assumed to be monitored when it isn't; check the actual coverage rather than assuming OneAgent presence
  means full visibility.
- Davis AI's proposed root cause accepted without checking the underlying evidence — especially for a
  novel failure mode the model hasn't seen enough of, correlation can point at a contributing factor
  rather than the true root cause.
- API tokens scoped too broadly (Dynatrace tokens are permission-scoped per API area) — request only the
  specific scopes a given integration needs.
- Cost/data-volume surprises from full-fidelity auto-instrumentation at high traffic — Dynatrace's
  automatic depth is powerful but not free; sampling/data-volume settings are worth reviewing at scale.
