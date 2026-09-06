---
description: Run the kubernetes-troubleshooter in continuous mode — consume the alert/event stream, auto-fix Tier-1 issues, PR Tier-2, page Tier-3.
argument-hint: "[--source alertmanager|events|loki] [--dry-run] [namespace or cluster context]"
---

Run Kubernetes autopilot: $ARGUMENTS

Delegate to the `kubernetes-troubleshooter` agent in **autonomous / continuous mode** (see that
agent's section 4b and `k8s/platform/remediation/README.md`).

1. Confirm `kubectl config current-context`, distro, and whether this is production. In production,
   start with `--dry-run` (diagnose + propose, apply nothing) until the user explicitly enables
   live remediation for this cluster.
2. Ingest the alert/event stream (default: `kubectl get events --sort-by=.lastTimestamp -A` since
   last tick; `--source alertmanager` for the webhook payload; `--source loki` for `type=Warning`).
   Do **not** poll object-by-object — one alert/event = one work item.
3. For each item: look it up in `k8s/platform/remediation/remediation-map.yaml`, run the diagnosis
   loop to a single confident root cause, then act **by tier**:
   - Tier 1 + on the allowlist + all circuit breakers green → apply → verify → log (Event + audit + note).
     Verify fails → roll back the action, escalate to Tier 3.
   - Tier 2 → open a GitOps PR (never apply a spec change directly).
   - Tier 3 → page with full diagnosis, evidence, proposed fix, blast radius.
4. Respect every circuit breaker: per-target 3/h, cluster-wide 10/10m (→ global pause + page),
   control-plane alerts firing (→ all autonomy paused), `remediation.io/policy: manual` label,
   `platform.io/freeze` silence, and "already auto-remediated and recurred" (→ escalate, it's not
   transient).
5. Tick every 60–120s (or react to webhooks). Between ticks, do nothing.

Each tick, report a one-line-per-item summary: `<alert> · <ns/obj> · <tier> · <action taken|PR #|paged> · <verified?>`.
End the run with a tally and anything a human still needs to look at.
