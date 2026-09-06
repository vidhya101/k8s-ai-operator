---
name: node-exporter
description: Prometheus node_exporter — host-level metrics collection (CPU, memory, disk, network) and the textfile collector for custom metrics. Use when instrumenting or debugging host-level metrics feeding into Prometheus.
---

# node_exporter

The standard Prometheus exporter for host/OS-level metrics — runs as a daemon (or DaemonSet in
Kubernetes) exposing `/metrics` for Prometheus to scrape. See the `prometheus` skill for querying/alerting
on the metrics it produces, and `linux` for the underlying host troubleshooting these metrics point at.

## Deployment

- Bare metal/VM: runs as a systemd service, one per host, typically on port `9100`.
- Kubernetes: deployed as a `DaemonSet` (one pod per node) with `hostNetwork`/`hostPID` access to see the
  actual node, not just the pod's own cgroup — a node_exporter pod without host-level access reports
  meaningless (containerized) numbers instead of real node metrics.

## Key Metrics

```text
node_cpu_seconds_total{mode="idle|user|system|iowait"}   # use rate() and 1 - idle for utilization
node_memory_MemAvailable_bytes                            # more meaningful than MemFree (accounts for
                                                            # reclaimable cache/buffers)
node_filesystem_avail_bytes{mountpoint="..."}              # disk space, per mount
node_filesystem_files_free{mountpoint="..."}                # inode availability — a separate exhaustion
                                                              # mode from disk space (see linux skill)
node_network_receive_bytes_total / transmit_bytes_total     # use rate() for throughput
node_load1 / node_load5 / node_load15                       # load average
```

## Useful PromQL

```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)   # CPU utilization %
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100                 # memory available %
node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1                    # disk <10% free
```

## Textfile Collector (custom metrics without writing an exporter)

- node_exporter can read `.prom`-formatted files from a configured directory (commonly
  `/var/lib/node_exporter/textfile_collector/`) and expose them alongside its built-in metrics — the
  standard way to get a cron job's or custom script's output into Prometheus without building a full
  exporter.

```bash
# A cron job writing a custom metric:
echo "my_custom_metric 42" > /var/lib/node_exporter/textfile_collector/my_metric.prom.$$
mv /var/lib/node_exporter/textfile_collector/my_metric.prom.$$ /var/lib/node_exporter/textfile_collector/my_metric.prom
# (write-then-atomic-rename avoids node_exporter reading a partially-written file)
```

## Common Pitfalls

- DaemonSet deployed without `hostNetwork: true`/`hostPID: true` and the right hostPath volume mounts
  (`/proc`, `/sys`), silently reporting container-scoped rather than node-scoped metrics.
- Textfile collector files written without the atomic rename pattern, occasionally scraped mid-write and
  producing a parse error or truncated metric.
- Disabled default collectors that are actually needed (node_exporter ships many collectors enabled by
  default; some environments disable a subset for scrape-size reasons) — check `--collector.*` flags
  before assuming a metric "should" exist but doesn't.
- Scrape interval mismatched with `rate()` window sizes used in queries/alerts (e.g. a 5m rate window
  with a 5m scrape interval leaves very few samples, producing noisy results) — see the `prometheus` skill.
