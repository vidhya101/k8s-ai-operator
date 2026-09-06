---
name: prometheus
description: Prometheus metrics — instrumentation (RED/USE), PromQL, alerting rules, and scrape configuration. Use when writing/debugging PromQL queries, designing alerts, or instrumenting a service's metrics.
---

# Prometheus

Pull-based metrics collection and alerting. See `mimir` for horizontally-scalable, long-retention,
multi-tenant Prometheus-compatible storage, and `grafana` for visualization.

## Instrumentation

- RED for services: **R**ate (requests/sec), **E**rrors (error rate), **D**uration (latency, as a
  histogram for percentiles, not just an average).
- USE for resources: **U**tilization, **S**aturation, **E**rrors — for CPU, memory, disk, queues.
- Use histograms (`_bucket`, `_sum`, `_count`) for latency, not just a gauge of the last value — percentiles
  need the distribution, not a point sample.
- Keep label cardinality bounded — never label with something unbounded (raw user ID, full request path
  with IDs embedded, timestamp) — this is the most common cause of Prometheus/Mimir cost and performance
  blowups.

## PromQL Essentials

```promql
rate(http_requests_total[5m])                                    # requests/sec over 5m window
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)    # error rate by service
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))  # p99 latency
increase(errors_total[1h])                                       # total increase over an hour
avg_over_time(node_memory_available_bytes[10m])
<metric> offset 1h                                                # value from 1h ago, for comparison
```

## Scrape Configuration & Service Discovery

```yaml
scrape_configs:
  - job_name: "static-targets"
    static_configs:
      - targets: ["app1:9100", "app2:9100"]

  - job_name: "kubernetes-pods"
    kubernetes_sd_configs:
      - role: pod                              # discovers every pod automatically, cluster-wide
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: "true"                          # only scrape pods opted in via annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        target_label: __address__               # relabel to use the pod's declared metrics port
```

- `static_configs` for a small, fixed set of targets; `kubernetes_sd_configs` (or `ec2_sd_configs`,
  `azure_sd_configs`, etc.) for anything dynamic — a static list drifts the moment autoscaling adds/
  removes instances, same principle as Ansible's dynamic inventory.
- `relabel_configs` runs *before* scraping (filters which discovered targets actually get scraped, and
  can rewrite labels); `metric_relabel_configs` runs *after* scraping (can drop/rename specific metrics
  post-collection) — using the wrong one is a common source of "why is this label/target not what I
  expected."

## Alerting Rules

```yaml
groups:
  - name: service-slo
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5..",service="api"}[5m]))
          / sum(rate(http_requests_total{service="api"}[5m])) > 0.05
        for: 5m
        labels: { severity: page }
        annotations:
          summary: "API error rate above 5% for 5m"
          runbook: "<link>"
```

- Alert on the symptom (error rate, latency, SLO burn), with a `for:` duration to avoid paging on a
  transient blip — tune the duration against real incident/noise history, don't guess.
- Every paging alert needs a runbook link in its annotations — an alert with no documented response isn't
  ready to page a human.

## Alertmanager (routing, grouping, and delivery)

Prometheus evaluates alerting *rules* and fires alerts into Alertmanager, which is the separate component
responsible for grouping, deduplicating, silencing, and routing them to a receiver (Slack, PagerDuty,
Opsgenie, a generic webhook) — an alert with a correct expression but no matching Alertmanager route
never reaches anyone.

```yaml
route:
  receiver: default-slack
  group_by: ["alertname", "service"]    # bundles related alerts into one notification instead of N
  group_wait: 30s                        # wait briefly to catch related alerts before the first notify
  repeat_interval: 4h                    # how often to re-notify an still-firing, un-acked alert
  routes:
    - match: { severity: page }
      receiver: pagerduty-oncall         # route by label — different severities to different channels

receivers:
  - name: default-slack
    slack_configs: [{ channel: "#alerts", api_url: "<webhook-url>" }]
  - name: pagerduty-oncall
    pagerduty_configs: [{ service_key: "<key>" }]

inhibit_rules:
  - source_match: { severity: critical }
    target_match: { severity: warning }
    equal: ["alertname", "service"]      # suppress the warning if a critical for the same thing is firing
```

- `group_by` prevents alert storms from becoming N separate notifications for one underlying incident —
  the same correlation principle the `aiops` skill describes, implemented natively here.
- `inhibit_rules` suppress a lower-severity alert when a related higher-severity one is already firing —
  reduces noise without silencing anything that isn't already covered by a more urgent notification.
- Route by label (`severity`, `team`, `service`) to the correct receiver — a route with no `match`
  reaching every alert into one channel regardless of severity is a common source of alert fatigue.

## Key Commands

```bash
amtool check-config alertmanager.yml
amtool alert query                    # currently firing/suppressed alerts
promtool check config prometheus.yml
promtool check rules alerts.yml
promtool query instant <server> '<promql>'
curl <prometheus>/api/v1/targets     # scrape target health
```

## Common Pitfalls

- Unbounded label cardinality (user ID, session ID, raw path) silently exploding storage/query cost.
- Alerting on an instant threshold with no `for:` duration, paging on single-scrape noise.
- Using `avg` across instances for a latency SLO instead of an aggregated histogram quantile — averaging
  percentiles across instances is mathematically wrong.
- Recording rules not used for expensive repeated queries (e.g. dashboard panels re-computing the same
  heavy aggregation on every load).
