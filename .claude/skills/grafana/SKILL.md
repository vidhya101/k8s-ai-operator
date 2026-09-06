---
name: grafana
description: Grafana dashboard design and alerting across Prometheus/Mimir, Loki, and other data sources. Use when building or reviewing dashboards, or wiring Grafana-managed alerts.
---

# Grafana

Visualization and (optionally) alerting layer across Prometheus/Mimir, Loki, and other data sources —
the single pane correlating metrics, logs, and traces.

## Dashboard Design

- Lead with RED metrics (rate/errors/duration) for a service dashboard — the questions asked during an
  incident first, not every metric that exists.
- Use variables (`$service`, `$env`, `$namespace`) so one dashboard serves every service/environment
  instead of duplicating a dashboard per service.
- Link panels to logs: a metrics panel showing an error spike should have an explicit link/button to the
  Loki/Datadog logs query for that same service + time window — don't make the on-call engineer manually
  reconstruct the query.
- Annotations for deploys/config changes overlaid on time-series panels — makes "did the deploy cause
  this" a visual answer instead of a cross-reference exercise.

## Alerting (Grafana-managed, if not using Prometheus Alertmanager directly)

- Route through the team's actual on-call/paging tool (PagerDuty, Opsgenie, native Slack) — don't leave
  alerts firing only into a dashboard nobody's watching.
- Same discipline as Prometheus alerting rules: symptom-based, tuned `for:` duration, runbook link in the
  notification.

## Key Concepts / Commands

```bash
# Dashboard-as-code (preferred over hand-editing in the UI for anything production-critical)
# Provisioned via YAML pointing at JSON dashboard definitions, or Grafonnet/grafana-foundation-sdk

curl -H "Authorization: Bearer <token>" <grafana>/api/dashboards/uid/<uid>   # fetch current dashboard JSON
curl -H "Authorization: Bearer <token>" <grafana>/api/datasources           # list configured data sources
```

## Common Pitfalls

- Dashboards built and tuned only in the UI, never exported/versioned as code — changes are unreviewable
  and easily lost.
- A dashboard with 40 panels and no clear "start here" — during an incident, more panels isn't more
  useful if the RED-metric panel isn't the first thing visible.
- Data source queries with no time-range-aware downsampling on a long-range panel, causing slow/expensive
  dashboard loads.
- Alerts configured in Grafana AND in Prometheus Alertmanager for the same condition, causing duplicate
  pages — pick one alerting path per condition.
