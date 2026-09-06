# `observability/` — the signal layer

Install with the upstream Helm charts (don't vendor their multi-thousand-line values). Below is
**only the config that matters for auto-remediation** — the rest keep at chart defaults.

## Metrics — `prometheus-community/kube-prometheus-stack`

```yaml
# values-kube-prometheus-stack.yaml (the parts that matter)
prometheus:
  prometheusSpec:
    retention: 24h                      # keep local short; long-term goes to Thanos/Mimir
    retentionSize: "ROUGHLY 80% of the PV"
    scrapeInterval: 30s                  # 15s only if you truly need it — doubles cardinality cost
    resources: { requests: { cpu: "1", memory: 4Gi }, limits: { memory: 8Gi } }
    # discover PrometheusRule / ServiceMonitor across ALL namespaces, not just the release namespace:
    ruleSelectorNilUsesHelmValues: false
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    # fleet: forward everything to a central store
    remoteWrite:
      - url: http://mimir.observability.svc:9009/api/v1/push   # or Thanos receive
    # survive a node loss
    replicas: 2
    podAntiAffinity: hard
kube-state-metrics:
  # the source of truth for kube_pod_*, kube_deployment_*, kube_node_* used by every alert here
  metricLabelsAllowlist:
    - pods=[app.kubernetes.io/name,app.kubernetes.io/part-of]
    - deployments=[app.kubernetes.io/name]
alertmanager:
  alertmanagerSpec:
    replicas: 3                          # HA — a lost Alertmanager must not lose alerts
  config:
    route: { see remediation/README.md for the tier-based routing }
grafana:
  defaultDashboardsEnabled: true
  # add the Kyverno, Loki, and Node Problem Detector dashboards
```

Scale note: one Prometheus handles ~1–2M active series comfortably on the resources above. Past
that, **shard** by namespace/team (Prometheus Operator `shards:`) or move to a Prometheus Agent +
Mimir/Thanos model — do not scale one Prometheus vertically forever.

## Logs — `grafana/loki` + `grafana/alloy`

```yaml
# Loki: label-index, not full-text — keep labels LOW cardinality (namespace, app, level, cluster).
# Never put pod name / trace id / request id in a label; those go in the log line, queried with |=.
loki:
  limits_config:
    retention_period: 168h              # 7d hot; archive to object storage for longer
    max_label_names_per_series: 15
  storage: { type: s3 }                 # gcs/azure equivalent — object storage, not a PV
```
Alloy (or Promtail) as a DaemonSet tails `/var/log/pods`. The agent queries Loki for the fast
"what did it log right before it died" during diagnosis:
`{namespace="x",pod=~"api.*"} |= "panic" | logfmt` .

## Traces — `grafana/tempo` + `open-telemetry/opentelemetry-collector`

OTel Collector as a `deployment` (gateway) + optional `daemonset` (agent). Apps send OTLP to the
collector; collector exports to Tempo. Tempo's `metrics-generator` turns spans into RED metrics
(rate/errors/duration) Prometheus scrapes — that's how a latency regression becomes an alert that
Argo Rollouts can auto-rollback on.

```yaml
# collector config essentials
processors:
  k8sattributes: {}                     # attach namespace/pod/deployment to every span
  tail_sampling:                        # keep all errors + slow traces, sample the rest
    policies:
      - { name: errors, type: status_code, status_code: { status_codes: [ERROR] } }
      - { name: slow, type: latency, latency: { threshold_ms: 500 } }
      - { name: sample, type: probabilistic, probabilistic: { sampling_percentage: 5 } }
```

## Events — `kubernetes-event-exporter`

Kubernetes Events are GC'd after 1h and aren't in any of the above by default. The event-exporter
ships them to Loki (queryable history) and can route `Warning` events straight to Alertmanager.

```yaml
config:
  route:
    routes:
      - match: [{ type: "Warning" }]
        exports: [loki, alertmanager]
      - match: [{ type: "Normal" }]
        exports: [loki]
```

## Fleet rollup — `grafana/mimir` (or Thanos)

Only when you have >1 cluster. Every cluster's Prometheus `remoteWrite`s to a central Mimir;
Grafana + global alert rules query Mimir. Retention/compaction/downsampling live there, so each
cluster's local Prometheus stays small and disposable. See `../fleet/README.md`.
