---
name: production-debugging
description: General method for debugging a live production issue — reproduce, isolate, correlate signals, and verify a fix, across any stack. Use when something is broken in production and the cause isn't yet known; pair with kubernetes/linux/networking skills for the specific layer once narrowed down.
---

# Production Debugging

Stack-agnostic method for diagnosing a live issue. Narrow down which layer is actually broken before
reaching for a layer-specific skill (`kubernetes`, `linux`, `networking`, `prometheus`/`loki`, etc.).

## Method

```text
1. Establish what "broken" actually means — get the exact symptom (error message, status code, latency
   number), not a vague description. Ask for it if it wasn't given.
2. Establish scope — all users or some? All requests or a specific path/feature? Since when, exactly?
   A narrow, well-defined scope is often most of the diagnosis.
3. Check what changed recently — deploy, config change, infra change (Terraform apply), dependency
   version bump, DNS/certificate expiry, a traffic pattern change (marketing push, bot traffic). Timing
   correlation against symptom onset is usually the fastest path to a hypothesis.
4. Correlate the observability signals in order: the alert/symptom → the metric confirming it →
   logs in that exact time window (shared labels: service, env) → a representative trace if tracing
   exists. State explicitly which of these aren't available rather than skipping silently.
5. Form a hypothesis and state what evidence would confirm or refute it before proposing a fix — don't
   jump straight to a fix based on a guess.
6. Propose the smallest safe mitigation first (rollback, scale, feature flag, traffic shift away from a
   bad instance/AZ) to stop user impact, separately from the full root-cause fix — see
   `production-incident-commander` agent for the incident-response structure this feeds into.
```

## Layer Triage (where to look next based on the symptom)

```text
Slow responses, high latency        → prometheus/datadog (RED metrics) → application logs →
                                       opentelemetry trace for a slow request → linux (resource pressure
                                       on the host/node) if infra-level
Errors/5xx                          → application logs first, then check if it's a downstream dependency
                                       (DB, third-party API) via traces/logs from that dependency
Can't connect / times out            → networking skill checklist (DNS, firewall, TLS, routing)
Pod/container crash-looping          → kubernetes skill / kubernetes-debugger agent
Host-level (disk, memory, CPU)       → linux skill
Deploy-correlated                    → check the diff of what was actually deployed (image tag, config,
                                       Terraform plan/apply history, ArgoCD sync history)
```

## Common Pitfalls

- Jumping to a fix based on the most recent change without confirming the timing actually correlates with
  symptom onset — coincidental timing leads to fixing the wrong thing.
- Debugging against an assumed environment/cluster without confirming context first (see
  `.claude/rules/environment-awareness.md`).
- Treating a single data point as confirmation instead of checking whether the pattern holds across the
  claimed scope (all instances, all regions, the specific time window).
