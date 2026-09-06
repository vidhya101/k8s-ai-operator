---
name: promtail
description: Promtail — the log-shipping agent for Grafana Loki (label discovery, pipeline stages). Use when configuring log collection into Loki; note Grafana now recommends Alloy for new deployments — see the migration note below.
---

# Promtail

Loki's log-shipping agent: discovers log sources (files, systemd journal, Kubernetes pod logs), attaches
labels, and pushes to Loki. See the `loki` skill for querying what it ships.

## Migration Note (current as of this writing)

Grafana has put Promtail into maintenance mode and recommends **Grafana Alloy** for new log-shipping
deployments — Alloy is a unified collector for logs, metrics, and traces. Existing Promtail deployments
still work and are supported, but a new setup should default to Alloy unless there's a specific reason
(existing team familiarity, an unmigrated config) to still choose Promtail — confirm which the project
actually wants rather than assuming.

## Configuration Shape

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml    # tracks read offset per file so restarts don't re-ship everything

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    pipeline_stages:
      - docker: {}                  # parse Docker's JSON log wrapper
      - labels:
          namespace:
          pod:
          container:
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
```

## Core Principles

- Label discipline mirrors Loki's own: only attach low-cardinality labels (namespace, pod, container,
  app, level) via `relabel_configs`/`pipeline_stages` — the same over-labeling mistake that hurts Loki
  hurts here at the source.
- `pipeline_stages` can parse structured logs (JSON, regex) and extract fields for labeling or metrics
  (`metrics` stage) without needing application-side changes — useful for legacy services that can't be
  easily re-instrumented.
- `positions.yaml` (or the equivalent state file) must be on persistent storage in Kubernetes (not an
  ephemeral `emptyDir` that resets on pod restart) to avoid re-shipping or gap-losing logs across restarts.

## Kubernetes Deployment

- Runs as a `DaemonSet` (one per node) with a hostPath mount to the node's container log directory
  (commonly `/var/log/pods` or `/var/lib/docker/containers`) — without this mount it has nothing to read.

## Common Pitfalls

- High-cardinality label extracted from a pipeline stage (e.g. a request ID promoted to a label instead
  of staying in the log line body) — causes the same Loki stream-count explosion the `loki` skill warns
  about, just introduced at the shipping layer instead of query layer.
- `positions.yaml` on ephemeral storage, causing full re-ship of all logs on every pod restart (log
  duplication) or silent gaps if the file resets to a later position than intended.
- DaemonSet missing the correct hostPath for the container runtime actually in use (Docker vs. containerd
  log paths differ) — results in Promtail running but shipping nothing, with no obvious error.
