# `autopilot/` — hands-off autonomous remediation

You asked for: **fix the cluster automatically, no permission prompts, no manual intervention,
add CPU/RAM when needed, read logs, debug, iterate — but never delete an app or a resource
without me.**

Here is exactly that, and here is the one design decision behind it.

## The autonomy lives in the cluster, not in an AI that skips confirmations

An AI agent (Claude / `kubernetes-troubleshooter`) running `kubectl` still goes through this repo's
permission gate — [`.claude/rules/safety.md`](../../../.claude/rules/safety.md) forbids bypassing
it, and for good reason: an agent acting on a wrong diagnosis at 3am with no gate turns one outage
into three. "Fix at any cost" is the exact failure mode that rule exists to stop.

So the no-prompt autonomy is delivered the way every serious platform does it — **in-cluster
controllers you authorize once**:

```
                    ┌─────────────────────────────────────────────────────┐
   you deploy this  │  cluster-autopilot ServiceAccount                    │
   ONCE, and that   │  + a ClusterRole that has NO destructive verbs       │
   IS the           │  + circuit breakers + a kill switch                  │
   permission       └───────────────────────┬─────────────────────────────┘
                                            │ runs forever, no prompts
        ┌───────────────────────────────────┼───────────────────────────────────┐
   operators (fast path, ~80%)        VPA Auto (right-size)         CronJob (long tail)
   NodeHealthCheck/NPD → node recovery  adds CPU/RAM from real       transient CrashLoop → rollout restart
   Descheduler → rebalance             usage, PDB-gated, capped      stuck Terminating pod → force-delete POD
   Cluster Autoscaler/Karpenter → nodes                             Pending / OOM-without-optin → Warning Event
   KEDA → event scaling                                             (escalate, don't guess)
   Argo Rollouts → auto-rollback bad deploys
   cert-manager → renew certs
   Reloader → roll on config change
```

The AI agent's role shrinks to **Tier-2/3 diagnostician**: when the autonomous stack escalates
(emits an `AutopilotEscalate` Warning Event), `/k8s-autopilot` picks it up, does the deep
diagnosis, and either opens a GitOps PR or pages you. It doesn't need to skip the gate because the
in-cluster stack already did the safe, immediate work.

## "Never delete my app" — enforced, not promised

[`rbac.yaml`](rbac.yaml) gives `cluster-autopilot` a ClusterRole that **does not contain**
`delete` / `deletecollection` on: Deployments, StatefulSets, DaemonSets, ReplicaSets, Jobs,
CronJobs, Services, Ingresses, PVCs, PVs, Namespaces, Nodes, CRDs, Secrets, ConfigMaps, RBAC.
The API server rejects any such call. A Kyverno policy additionally blocks the SA from writing to
system namespaces at all. The only thing it can delete is a **Pod** — which its controller
recreates in seconds, so it's additive in effect, not destructive.

To let it delete something specific one time, a human grants a narrow namespaced Role. The
ClusterRole is never widened.

## What it does autonomously (all additive · reversible · circuit-broken)

| Situation | Action | Guard |
|---|---|---|
| Pod CrashLoopBackOff, 3–25 restarts, not OOM, owner is a Deployment/StatefulSet | `rollout restart` the owner | 30-min cooldown per owner; ≤ 3 actions/target/hour |
| Pod stuck `Terminating` > 15 min, its node is Ready | force-delete **the pod** | node-Ready check; per-target breaker |
| Deployment labelled `autopilot.platform.io/rightsize=true` and getting OOMKilled | VPA (Auto, memory-only, capped at `maxAllowed`) resizes it | PDB-gated, `minReplicas: 2`, CPU left to the HPA |
| Node NotReady / kernel deadlock / runtime down | NodeHealthCheck → cordon → drain → autoscaler replaces | `minHealthy: 70%`; control-plane nodes excluded |
| Pods Pending on capacity | Cluster Autoscaler / Karpenter adds a node | bounded by your min/max |
| Load spike | HPA / KEDA scale replicas | bounded by maxReplicas |
| Bad rollout (metric regression) | Argo Rollouts auto-rollback | analysis-driven |
| Config change | Reloader rolls the workload | — |
| **Anything else** (Pending with no autoscaler, OOM without the opt-in label, restarts > 25, StatefulSet degraded, control-plane alerts) | **emit a Warning Event and stop** — the agent / a human takes it | never guesses |

## Circuit breakers (in [`autopilot-config`](remediation-runner.yaml))

- `maxActionsPerTargetPerHour: 3` → stop touching that object, emit `AutopilotEscalate`.
- `maxActionsClusterWidePer10Min: 8` → **auto-sets `paused: true`** + Warning Event (a storm means
  the cause is systemic; autonomy stands down).
- Control plane `/readyz` failing → the pass does nothing.
- Namespaces in `excludeNamespaces` and all system namespaces → never touched.

## Operate

```bash
# install (after k8s/platform and its prereqs)
kubectl apply -k k8s/platform/autopilot

# watch what it's doing
kubectl get events -A --field-selector source=cluster-autopilot --sort-by=.lastTimestamp
kubectl -n platform-system logs -l app.kubernetes.io/component=autopilot --tail=200

# kill switch  /  dry-run
kubectl -n platform-system patch cm autopilot-config --type merge -p '{"data":{"paused":"true"}}'
kubectl -n platform-system patch cm autopilot-config --type merge -p '{"data":{"dryRun":"true"}}'

# opt a workload into automatic right-sizing
kubectl -n <ns> label deploy <name> autopilot.platform.io/rightsize=true
```

Run it in `dryRun: "true"` for the first week and read the Events it *would* have created. Flip to
live once you trust the decisions.

## Why not "just let it do everything"

Additive + reversible + pod-level actions are safe to automate because the worst case is a brief
extra restart. Deleting a Deployment, scaling to zero, editing RBAC, draining a control-plane
node, or restoring etcd are **not reversible in seconds** — an automated system that gets the
diagnosis wrong there causes an incident instead of preventing one. Those stay with a human (or a
GitOps PR a human merges). That's not a limitation bolted on — it's the line that makes the
autonomous part safe to leave unattended.
