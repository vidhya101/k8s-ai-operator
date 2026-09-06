# `k8s/platform/` — the self-healing platform layer

This is the "manage any cluster, detect and fix issues automatically" layer that sits **above**
individual workloads (`k8s/app/`). It is a composition of battle-tested open-source components,
not a bespoke engine — that is the industry-standard approach and the one you can actually operate.

---

## Read this first: two expectations to reset

**1. You do not poll. Nothing "checks 1,000,000 pods every second".**
The Kubernetes API server + etcd would fall over under that load — it is a self-inflicted DoS and
the #1 way people take down their own control plane. The professional pattern is **event-driven**:

| Signal | Mechanism | Latency | Cost |
|---|---|---|---|
| Object state changes (pod dies, deploy edited) | **watch / informer** (long-lived stream, server pushes deltas) | milliseconds | ~zero API load |
| Metrics (CPU, memory, restart count, queue depth) | **Prometheus scrape** of kube-state-metrics / node-exporter / cAdvisor | 15–30 s | one HTTP GET per target per interval |
| Events (`FailedScheduling`, `BackOff`, `Unhealthy`) | **Events API watch** → kubernetes-event-exporter | seconds | ~zero |
| Logs | **Promtail/Alloy → Loki** (push, indexed by label) | seconds | streaming |
| Traces | **OpenTelemetry SDK → OTel Collector → Tempo** | seconds | streaming |
| Runtime syscall anomalies | **Falco** (eBPF, in-kernel) | milliseconds | in-kernel, no API load |

A controller watching 1M pods holds **one watch connection** and a work queue with rate-limiting —
it reacts in milliseconds without ever "scanning" anything. Detection latency for the fast path
(crash, OOM, node down) is **1–5 seconds**, not one second and not by brute force.

**2. "Fix automatically" has a hard boundary — and every serious shop draws it in the same place.**
Autonomous remediation is real, but only for a small allowlist of **reversible, well-understood,
low-blast-radius** actions with circuit breakers. Anything that mutates intent (a Deployment spec,
RBAC, a NetworkPolicy, a namespace, etcd) goes through a **human approval gate** or a **GitOps PR**.
This is not timidity — it is because an auto-remediator acting on a wrong diagnosis during an
incident turns one outage into three. See the tier table below.

---

## What you need — the full stack

Install order matters (each layer depends on the one above). Everything is Helm-installable and
rolled to every cluster by one ArgoCD `ApplicationSet` (see `fleet/`).

### Layer 0 — Cluster baseline (must exist before anything else)
| Component | Purpose | Chart |
|---|---|---|
| `metrics-server` | `kubectl top`, HPA/VPA input | `metrics-server/metrics-server` |
| CNI + `NetworkPolicy` engine (Calico/Cilium) | pod networking + default-deny enforcement | distro-dependent |
| `cert-manager` | issue + **auto-renew** TLS (removes "cert expired" as a failure class) | `jetstack/cert-manager` |
| CoreDNS autoscaler + PDB | DNS is a SPOF; scale it with the cluster | built-in / `cluster-proportional-autoscaler` |

### Layer 1 — Observability (you cannot fix what you cannot see)
| Component | Signal | Chart |
|---|---|---|
| **kube-prometheus-stack** (Prometheus + Alertmanager + Grafana + node-exporter + kube-state-metrics + the standard alert rules) | metrics + alerting | `prometheus-community/kube-prometheus-stack` |
| **Loki** + **Alloy/Promtail** | logs (label-indexed, cheap) | `grafana/loki`, `grafana/alloy` |
| **Tempo** + **OpenTelemetry Collector** | traces | `grafana/tempo`, `open-telemetry/opentelemetry-collector` |
| **kubernetes-event-exporter** | ships Events to Loki/Alertmanager so they're queryable and alertable | `bitnami/kubernetes-event-exporter` or upstream |
| **Thanos** or **Mimir** | **only for fleet** — global query + long retention across N clusters | `bitnami/thanos`, `grafana/mimir` |

Details + the values that actually matter: [`observability/README.md`](observability/README.md).

### Layer 2 — Detection (turn signals into typed, actionable alerts)
| Component | Catches | This repo |
|---|---|---|
| **PrometheusRules** — the alert catalog | CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending/unschedulable, rollout stuck, replica shortfall, node NotReady / pressure, PVC pending, cert expiry, quota exhaustion, HPA maxed, API-server / etcd health, certs, DNS error rate | [`detection/prometheus-rules.yaml`](detection/prometheus-rules.yaml) |
| **Falco** | runtime threats — shell in container, unexpected egress, write to `/etc`, privilege escalation | `falco` skill + `falcosecurity/falco` |
| **Polaris** / **kube-score** | config smells in what's *already running* (missing probes, no limits, running as root) | `fairwinds/polaris` |
| **Trivy Operator** | CVEs in running images, exposed secrets, RBAC risks, misconfig — continuously | `aquasecurity/trivy-operator` |

### Layer 3 — Prevention (stop the bad YAML / config / image *before* it is admitted)
This is where "fix any YAML issue / config issue / image issue / namespace issue" is *actually*
solved — at the admission webhook, before it becomes a running problem.

| Component | Blocks / fixes at admission | This repo |
|---|---|---|
| **Kyverno** (validate + **mutate** + generate) | rejects `:latest`, unpinned digests, disallowed registries, missing probes / limits / PDB / PriorityClass, privileged pods, `hostPath`, missing `NetworkPolicy`; **auto-injects** defaults it can safely add; **auto-generates** a namespace's default-deny NetworkPolicy + ResourceQuota + LimitRange | [`detection/kyverno-enforce.yaml`](detection/kyverno-enforce.yaml) |
| **Pod Security Admission** `restricted` | the pod-security baseline, built in, no webhook | `k8s/app/components/hardening` |
| **Validating Admission Policy** (CEL, built-in ≥ 1.30) | cheap structural rules with no external webhook on the hot path | `detection/kyverno-enforce.yaml` header note |
| GitOps (**ArgoCD**/**Flux**) with `kubectl diff` in CI + schema validation (`kubeconform`) + `kustomize build` gate | a malformed manifest never reaches the cluster — it fails the PR | `.github/workflows` + `fleet/` |

### Layer 4 — Remediation (act on the alerts)
| Component | Auto-remediates | Gate |
|---|---|---|
| Deployment/ReplicaSet/StatefulSet controllers | lost pods, crashed containers (restart) | none — core Kubernetes |
| **Node Problem Detector** + **Draino** / **Medik8s (NHC + self-node-remediation)** | node with a permanent problem → cordon → drain (PDB-aware) → let the autoscaler replace it | auto (reversible; PDB-protected) — [`remediation/node-auto-recovery.yaml`](remediation/node-auto-recovery.yaml) |
| **Descheduler** (CronJob) | pods on over-used / tainted / wrong-affinity nodes → evict → reschedule | auto (PDB-aware, `nodeFit`) — `k8s/app/components/self-healing` |
| **Cluster Autoscaler** / **Karpenter** | Pending pods from capacity shortage → add nodes; empty nodes → remove | auto (bounded by min/max) |
| **cert-manager** | expiring certs → reissue | auto |
| **KEDA** | load spikes / queue backlog → scale (incl. scale-to-zero) | auto (bounded) |
| **Argo Rollouts** | bad deploy (analysis metric regression) → **automatic rollback** | auto (rollback is reversible by definition) |
| **Stakater Reloader** | stale/broken config after a ConfigMap/Secret change → rolling restart | auto |
| **Argo Events + Argo Workflows** sensor (or the `kubernetes-troubleshooter` agent in autonomous mode) | the long tail: stuck `Terminating` namespace finalizer, orphaned PVC, image GC on DiskPressure, `rollout restart` on a known-transient failure signature | **allowlist only** + circuit breaker — [`remediation/remediation-map.yaml`](remediation/remediation-map.yaml) |
| **A human** (paged via Alertmanager → PagerDuty/Opsgenie) | anything not on the allowlist: spec changes, RBAC, NetworkPolicy, data-loss risk, etcd, repeated remediation failure | approval gate |

---

## Hands-off autonomous mode — `autopilot/`

If you want the no-prompt, no-human-in-the-loop version: [`autopilot/`](autopilot/README.md) is an
**in-cluster** stack (a scoped `cluster-autopilot` ServiceAccount + VPA Auto + a CronJob) that runs
Tier-0/Tier-1 forever with zero per-action approval — because its RBAC physically cannot delete a
Deployment, PVC, namespace, node, or Secret. It right-sizes CPU/RAM automatically (VPA, capped),
restarts transient crash-loops, force-deletes stuck-Terminating pods, and emits a Warning Event
for everything it's deliberately not allowed to fix alone. Kill switch: one ConfigMap field.
Deploy it once and it's authorized; the AI agent then only handles escalations.

## The remediation tier model (memorize this)

```
TIER 0  Kubernetes already does it        restart pod, reschedule, reconcile ReplicaSet
        └─ always on, no config

TIER 1  Autonomous, reversible, bounded    cordon+drain bad node, evict mis-scheduled pod,
        └─ allowlist + circuit breaker     add/remove nodes, renew cert, scale within HPA bounds,
                                           auto-rollback a bad deploy, restart on transient signature

TIER 2  GitOps auto-PR (human merges)      bump a resource limit VPA recommends, add a missing probe,
        └─ bot opens PR, human approves    pin an image digest, add a NetworkPolicy

TIER 3  Human-in-the-loop (paged)          namespace deletion, RBAC change, spec change of unknown
        └─ Alertmanager → on-call          intent, etcd restore, anything after N failed auto-attempts,
                                           anything in a namespace labelled remediation.io/policy=manual
```

**Circuit breakers on Tier 1** (non-negotiable):
- Max N auto-remediations per target per hour (default 3) → then escalate to Tier 3.
- Max M auto-remediations cluster-wide per 10 min (default 10) → global pause + page (a storm means
  the diagnosis is wrong or there's a systemic cause).
- Every auto-action writes an Event + a structured audit log line + a Slack/PagerDuty note.
- A namespace/Deployment label `remediation.io/policy: manual` opts fully out.
- Auto-remediation is **disabled during an active change freeze** (Alertmanager silence or a
  `platform.io/freeze` ConfigMap).

---

## How the `kubernetes-troubleshooter` agent fits

The agent is the **Tier 1 long-tail executor and the Tier 2/3 diagnostician**. In autonomous mode
(`/k8s-autopilot`) it:
1. Consumes the alert stream (Alertmanager webhook / `kubectl get events` / a Loki query).
2. For each alert, runs its diagnosis loop (evidence → single root cause).
3. If the fix is on the **Tier 1 allowlist** and circuit breakers are green → applies it, verifies
   recovery, logs it.
4. Otherwise → opens a GitOps PR (Tier 2) or pages with a full diagnosis + proposed fix (Tier 3).

It never invents a new kind of action, never acts on low-confidence diagnosis, and always respects
`.claude/rules/safety.md`. The allowlist and loop are defined in the agent
([`.claude/agents/kubernetes-troubleshooter.md`](../../.claude/agents/kubernetes-troubleshooter.md),
"Autonomous / continuous mode").

---

## Scale: one cluster vs. a fleet of 1,000,000 pods

| | Single cluster (≤ ~5k nodes / ~150k pods — the Kubernetes supported ceiling) | Fleet (many clusters, 1M+ pods total) |
|---|---|---|
| Metrics | one Prometheus (+ remote-write to keep local retention short) | per-cluster Prometheus/Agent → **Thanos/Mimir** for global query |
| Detection | PrometheusRules run in-cluster | rules run per-cluster; global rollup rules in Mimir |
| Remediation | controllers + one agent instance | **sharded** — agent/controller per cluster or per shard; ArgoCD ApplicationSet rolls identical config to all |
| Config delivery | `kubectl apply` / one Argo app | **ArgoCD ApplicationSet** (one definition → N clusters), cluster inventory in Git |
| Control-plane load | a single watch + rate-limited work queue scales fine | never centralize watches across clusters — one agent per cluster, results aggregated |

You do **not** build a thing that reaches into 1M pods from one place. You run the same small,
proven stack in every cluster and aggregate the *signals*, not the *control*. See
[`fleet/README.md`](fleet/README.md).

---

## Install

```bash
# 1. Layer 0–1 via Helm (see observability/README.md for the values that matter)
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f observability/values-kube-prometheus-stack.yaml
helm upgrade --install loki grafana/loki -n monitoring -f observability/values-loki.yaml
# ... tempo, alloy, otel-collector, event-exporter, cert-manager

# 2. Layer 2–4 from this directory
kubectl apply -k k8s/platform            # PrometheusRules + Kyverno policies + NPD + descheduler wiring

# 3. Fleet: point one ApplicationSet at your cluster inventory (fleet/)
```

Verify: `remediation/README.md` has the chaos drills (kill a pod, taint a node, apply a bad
manifest, expire a cert) that prove each layer actually fires.
