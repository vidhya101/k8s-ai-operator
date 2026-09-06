---
name: opentelemetry
description: OpenTelemetry instrumentation — traces, spans, context propagation, and the Collector. Use when adding distributed tracing to a service or debugging a broken trace/span chain, regardless of which backend (Tempo, Datadog, Jaeger) receives the data.
---

# OpenTelemetry

Vendor-neutral instrumentation standard for traces (and increasingly metrics/logs) — the SDK/API is the
same regardless of backend; only the exporter configuration changes.

## Core Concepts

- A **trace** is the full path of one request across services; a **span** is one unit of work within it
  (an HTTP call, a DB query, a function); spans nest to form the trace tree.
- **Context propagation**: the trace/span ID must be passed across every service boundary (HTTP headers —
  `traceparent` per the W3C Trace Context standard, or a queue message's metadata) — a broken propagation
  link at any hop makes that hop's downstream work show up as a disconnected, separate trace.
- Auto-instrumentation libraries exist for most frameworks (HTTP servers/clients, common DB drivers) and
  should cover the request-path skeleton; add manual spans for business-logic-significant operations the
  auto-instrumentation can't see into.

## Setting Up

```text
1. Add the OTel SDK for the language + auto-instrumentation for the framework/libraries in use.
2. Configure an exporter pointing at the OTel Collector (preferred) or directly at the backend
   (Tempo, Datadog, Jaeger, etc.).
3. Ensure context propagation headers survive every hop: synchronous HTTP calls, message queue publishes,
   and any manual thread/async boundary in the code (propagation can silently break across these).
4. Add resource attributes (service.name, service.version, deployment.environment) so traces are
   filterable/groupable in the backend.
```

## The Collector

- Runs as a sidecar, daemonset, or standalone service; receives telemetry from instrumented apps,
  processes it (batching, filtering, sampling, PII redaction), and exports to one or more backends.
- Centralizing export logic in the Collector (rather than each service exporting directly) makes changing
  or adding a backend a Collector config change, not a redeploy of every instrumented service.
- Sampling decisions (head-based at the SDK, or tail-based at the Collector) matter for cost at scale —
  tail-based sampling (keep all traces containing an error, sample the rest) preserves the traces that
  matter most for debugging.

## Common Pitfalls

- Context not propagated across an async boundary (a goroutine, a queue consumer, a background job),
  silently breaking the parent/child link and making the downstream work appear trace-less.
- Every span given the same generic name (e.g. every DB call span named `"db-query"`), making the trace
  waterfall useless for identifying which specific query was slow.
- No correlation ID shared between traces and logs (see `loki`/`datadog` skills) — the trace exists, the
  logs exist, but nothing connects them for a given request.
- 100% head-based sampling left on in production at high traffic, generating cost and Collector load with
  no corresponding debugging value over a well-designed tail-sampling policy.
