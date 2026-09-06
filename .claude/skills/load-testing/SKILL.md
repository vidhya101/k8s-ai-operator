---
name: load-testing
description: Load and performance testing with k6 — scripting realistic load, interpreting results against SLOs, and where this fits versus chaos engineering. Use when writing a load test, validating a capacity assumption, or gating a pipeline on performance regressions.
---

# Load Testing (k6)

Verifies performance/capacity claims under realistic traffic, as distinct from `chaos-engineering`
(verifies resilience under *failure*, not load) and `testing` (verifies correctness, not performance).

## Scripting

```javascript
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "2m", target: 100 },   // ramp up to 100 VUs (virtual users)
    { duration: "5m", target: 100 },   // sustain
    { duration: "2m", target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],   // fail the test if p95 latency exceeds 500ms
    http_req_failed: ["rate<0.01"],     // fail if error rate exceeds 1%
  },
};

export default function () {
  const res = http.get("https://staging.example.com/api/resource");
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(1);
}
```

- **Thresholds** turn a load test into a pass/fail pipeline gate (same principle as any other scan gate
  in `devsecops`) — a load test that only produces a report nobody reads isn't actually gating anything.
- Ramp patterns matter: a sudden spike to target load tests a different failure mode (can the system
  absorb a burst) than a gradual ramp (what's the actual capacity ceiling) — pick the pattern that
  matches what's actually being validated (a real traffic pattern, a marketing-launch spike scenario, etc.).

## Interpreting Results Against SLOs

- Compare results against the service's actual SLO (see `sre` skill), not an arbitrary "seems fast
  enough" — a load test's pass/fail threshold should be derived from the same latency/error-rate targets
  the service is held to in production.
- p95/p99 latency matters more than average for user-facing SLOs — same principle as the `prometheus`
  skill's histogram-over-average guidance; a load test reporting only average latency hides tail latency
  problems that disproportionately affect real users.
- Watch resource utilization (CPU/memory on the system under test, via `prometheus`/`grafana`) alongside
  the load test's own client-side metrics — client-side latency degrading while server CPU is still low
  often points at a different bottleneck (connection pool exhaustion, a downstream dependency) than
  compute capacity.

## Where This Fits Alongside Other Testing

```text
testing (unit/integration/e2e)  — is the code correct?
load-testing (k6)                — does it perform acceptably under expected/peak load?
chaos-engineering                 — does it survive actual failures (not just load)?
```

All three are needed for a genuinely production-ready service; load testing alone doesn't verify
correctness, and passing under normal load doesn't verify resilience to failure.

## Common Pitfalls

- Load testing against a staging environment sized/configured differently from production (fewer
  replicas, smaller instance types, no CDN) — results don't transfer to production capacity planning
  unless the environments are comparable, or the difference is explicitly accounted for.
- No thresholds configured, so the test runs and produces a report but never actually fails the pipeline
  regardless of how bad the results are.
- Testing only the happy path (one endpoint, ideal payloads) instead of a realistic mix of the actual
  traffic patterns production sees.
- Running a full-scale load test against a shared staging environment other teams are actively using,
  without warning — coordinate before generating significant synthetic load anywhere shared.
