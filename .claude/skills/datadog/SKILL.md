---
name: datadog
description: Datadog as an integrated metrics/logs/traces/errors platform — agent setup, monitors, and cross-signal correlation. Use when the observability stack is Datadog rather than the Prometheus/Grafana/Loki OSS stack.
---

# Datadog

Integrated observability platform (metrics, logs, APM traces, RUM, error tracking) — the commercial
alternative to assembling Prometheus + Grafana + Loki + Tempo separately. Don't run both stacks for the
same data without a specific migration or coverage reason; check which one a repo actually uses first.

## Agent & Instrumentation

- Datadog Agent runs as a daemonset (Kubernetes) or host process, collecting infra metrics and forwarding
  APM traces/logs.
- APM auto-instrumentation available for most major languages (`ddtrace`) — reduces manual span
  instrumentation but still needs explicit spans/tags for custom business logic.
- `dd_trace_id`/`dd_span_id` correlate logs to traces automatically when using Datadog's logging
  integrations — verify this is actually wired up (log injection enabled in the tracer config) rather
  than assuming it's automatic.

## Monitors (Datadog's alerting)

```text
avg(last_5m):sum:trace.http.request.errors{service:api}.as_count() /
sum:trace.http.request.hits{service:api}.as_count() > 0.05
```

- Same discipline as Prometheus alerting: symptom-based (error rate/latency/SLO burn), tuned evaluation
  window to avoid noise, runbook link in the monitor message, routed to the real on-call tool
  (`@pagerduty-<service>` notification target or equivalent).
- Datadog SLOs (with error budget tracking) are a first-class feature — prefer them over ad hoc threshold
  monitors when the goal is genuinely SLO-based alerting.

## Key Concepts / Checks

```bash
datadog-agent status                       # agent health, which checks are running
datadog-agent check <check-name>            # run a specific check once, see raw output
# Via API/UI: Monitors > search by tag; APM > Service Catalog for a service's dependency map
```

## Common Pitfalls

- Custom metrics with unbounded tag cardinality (same failure mode as Prometheus labels) driving up
  Datadog's custom-metrics billing unexpectedly.
- APM auto-instrumentation enabled but log-trace correlation not configured, so logs and traces exist
  independently with no easy pivot between them during an incident.
- Monitors created ad hoc in the UI with no ownership/tagging, becoming untraceable noise over time —
  prefer Monitors-as-code (Terraform `datadog` provider) for anything meant to be maintained long-term.
- Running both Datadog APM and an OpenTelemetry pipeline in parallel without deciding which is the source
  of truth, doubling instrumentation maintenance cost.
