# `remediation/` — how alerts become actions

Two execution paths, same decision table (`remediation-map.yaml`):

## Path A — off-the-shelf controllers (preferred; no custom code)
Already covered by installing the components in `k8s/platform/README.md` Layer 4:
Deployment controller, NodeHealthCheck + NPD + Self Node Remediation (`node-auto-recovery.yaml`),
Descheduler, Cluster Autoscaler/Karpenter, cert-manager, KEDA, Argo Rollouts auto-rollback,
Reloader. **~80% of real incidents are handled here with zero bespoke logic.** Reach for Path B
only for the long tail.

## Path B — the agent (or an Argo Events sensor) for the long tail
```
Alertmanager ──webhook──▶  receiver  ──▶  kubernetes-troubleshooter (autonomous mode)
                                          │  1. look up alert in remediation-map.yaml
                                          │  2. run diagnosis loop (evidence → single root cause)
                                          │  3. check circuit breakers (green?)
                                          │  4. tier 1 + allowlisted + confident → apply → verify → log
                                          │     tier 2 → open GitOps PR
                                          │     tier 3 → page with full diagnosis + proposed fix
                                          └─ every action → Event + audit log + Slack/PD note
```
Wire it with `/k8s-autopilot` (see `.claude/commands/k8s-autopilot.md`), or as an Argo Events
`Sensor` with an HTTP `EventSource` on the Alertmanager webhook if you want it running in-cluster.

Alertmanager route for Path B:
```yaml
route:
  routes:
    - matchers: ['tier=~"1|2"']
      receiver: auto-remediation      # webhook_configs: url to the agent/sensor
      group_wait: 30s
      continue: true                  # also send to humans so they see what the bot is doing
    - matchers: ['tier="3"']
      receiver: pagerduty
```

## Verify every layer actually fires — the drill

Run these on a non-prod cluster after install. Each should self-recover within the stated time
with **no human action**.

| Inject | Command | Expect | Within |
|---|---|---|---|
| Pod crash | `kubectl delete pod <one>` | replaced, endpoints never drop below PDB floor | 10 s |
| Bad rollout | deploy an image with a broken readiness path | Argo Rollouts aborts + rolls back, or `DeploymentRolloutStuck` → agent `rollout undo` | 15 m |
| Config break | edit a ConfigMap to an invalid value | Reloader rolls; new pods fail readiness; rollout holds at old ReplicaSet (no outage) | 2 m |
| Node fault | `kubectl taint node <n> e2e=chaos:NoExecute` then cordon | descheduler + scheduler move pods; PDB respected | 5 m |
| Node down | stop kubelet on a worker (in a VM lab) | NPD condition → NodeHealthCheck → drain → autoscaler replaces | 20 m |
| Cert expiry | issue a Certificate with `duration: 1h, renewBefore: 59m` | cert-manager reissues before expiry | < 1 h |
| Bad YAML | `kubectl apply` a Pod with `:latest` and no limits | **rejected at admission** by Kyverno (once in Enforce) | immediate |
| New namespace | `kubectl create ns drill` | default-deny NetworkPolicy + starter quota auto-generated | immediate |
| DiskPressure | fill a node's disk to 90% (lab) | image GC Job frees space, else cordon+drain+replace | 15 m |

For a rigorous version of this (steady-state hypothesis, blast radius, automated abort), use the
`chaos-engineering` skill with Chaos Mesh / LitmusChaos on a schedule — a resilience claim you
haven't tested is a resilience guess.

## Audit

Every autonomous action lands in three places: a Kubernetes `Event` on the target, a structured
JSON line in the platform audit log (ship to Loki with `action=auto-remediation`), and a
Slack/PagerDuty note. Weekly, review: what fired, did it help, any that masked a real bug that
should have been fixed forward. Auto-remediation that keeps papering over the same defect is a
process smell — the recurring item becomes a backlog ticket.
