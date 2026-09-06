---
name: aiops
description: AIOps discipline — using telemetry-driven anomaly detection and correlation to reduce alert noise and speed diagnosis, with safe boundaries on auto-remediation. Use for alert-noise/automation design questions; see the aiops-reviewer agent for a structured review.
---

# AIOps

Applying automated analysis to operational telemetry to reduce noise and speed diagnosis — not a
replacement for good SRE fundamentals (see `sre` skill), but a layer on top once the fundamentals
(symptom-based alerting, RED/USE metrics) are already in place. See the `aiops-reviewer` agent for a
structured review of an existing system.

## Where AIOps Adds Value

- **Correlation**: grouping many related low-level signals (a spike in error rate, elevated latency, a
  specific pod's restarts) into one incident instead of N separate pages for one root cause.
- **Anomaly detection**: flagging deviation from a learned baseline for metrics that don't have an obvious
  static threshold (e.g. traffic patterns with strong daily/weekly seasonality) — useful where a fixed
  threshold would either miss real anomalies or false-positive constantly.
- **Noise reduction**: deduplication, suppression of known-flapping signals, and grouping — the actual
  measurable goal is fewer, higher-signal pages, not more sophisticated-looking dashboards.

## Auto-Remediation Boundaries

Automated action in response to a detected anomaly needs explicit safety boundaries:

- **Blast radius ceiling**: e.g. restart one unhealthy pod, not the whole deployment; scale out by a
  bounded increment, not "as much as needed."
- **Circuit breaker**: if an automated action fires repeatedly without resolving the underlying signal,
  it should stop and escalate to a human rather than looping — a restart loop "fixing" a crash-looping
  pod every 30 seconds is masking, not fixing, the actual problem.
- **Auditability**: every automated action logged with what triggered it, so it can be reviewed after the
  fact — a black-box automated fix with no trace of why it fired is a debugging liability during the next
  related incident.
- Automated actions with a high blast radius (anything touching production data, scaling down, deleting
  resources) should not be fully autonomous without a human-in-the-loop approval step — this is a
  significant risk-tolerance decision, confirm it with the user rather than assuming full autonomy is wanted.

## Common Pitfalls

- Anomaly-detection thresholds tuned on too little historical data, producing a high false-positive rate
  that trains the team to ignore the system entirely (worse than not having it).
- Auto-remediation with no circuit breaker, repeatedly "fixing" a symptom while the actual root cause goes
  uninvestigated because the pain that would normally prompt investigation is being auto-suppressed.
- Correlation grouping signals too aggressively, merging genuinely unrelated incidents into one and
  obscuring that there were actually two separate problems.
