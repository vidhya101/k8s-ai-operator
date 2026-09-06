---
name: loki
description: Grafana Loki log aggregation — label design, LogQL queries, and correlating logs with metrics/traces. Use when querying or designing log collection with Loki.
---

# Loki

Log aggregation designed to index only labels (like Prometheus), not full-text — keeps it cheap at scale,
but means label design matters as much as query design.

## Core Principles

- Index low-cardinality labels only (service, namespace, environment, level) — never index something
  high-cardinality (user ID, request ID, raw message content) as a label; put that in the log line body
  and query it with LogQL's line filters instead.
- Every log line should carry a trace ID (when tracing is in place) so you can pivot from a log line to
  the full distributed trace — this is the single highest-value correlation to get right.
- Structured logs (JSON) let LogQL parse and filter on fields within the line without needing them as
  indexed labels.

## LogQL Essentials

```logql
{service="api", env="prod"}                                    # base label selector
{service="api"} |= "error"                                     # line contains "error"
{service="api"} | json | status >= 500                          # parse JSON, filter parsed field
{service="api"} | json | line_format "{{.trace_id}} {{.msg}}"   # reshape output
sum(rate({service="api"} |= "error" [5m])) by (env)             # log-based rate, usable in alerting
{service="api"} | json | trace_id="<id-from-a-trace>"           # pivot from a trace to its logs
```

## Key Commands

```bash
logcli query '{service="api"}' --limit=100 --since=1h
logcli labels                          # list available label names
logcli labels service                  # list values for a label
```

## Common Pitfalls

- A high-cardinality field (user ID, session ID) added as a label "for easier filtering" — explodes the
  number of streams Loki has to manage and tanks performance; use a line filter/JSON field filter instead.
- Unstructured (plain text, inconsistent format) logs making LogQL field extraction brittle — push for
  structured logging at the application level rather than parsing with regex at query time.
- No trace ID in log lines, so during an incident there's no way to jump from "this log line looks bad"
  to "here's the full request trace that produced it."
- Retention configured shorter than what compliance/debugging actually needs, discovered only when
  someone needs a log from before the retention window.
