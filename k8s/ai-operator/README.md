# `k8s/ai-operator/` — the in-cluster AI operator (local Ollama, no cloud LLM)

A set of cooperating agents that **live inside the cluster**, think with **your local Ollama**
(no data leaves your network), and run 24/7:

- **scan** every YAML — in your Git repo *and* live in the cluster — for security leaks,
  misconfigurations, missing best practices, and efficiency wins
- **fix** what they find — patch a manifest, open a port (Service/Ingress/Gateway/NetworkPolicy),
  install a chart, raise a limit — always **backup-first**, always validated, never destructive
- **learn** — every finding, fix, and outcome goes into an agentic memory (SQLite + embeddings via
  Ollama) so the same class of problem is recognised faster next time
- **talk to each other** through Kubernetes CRDs (`Finding`, `Remediation`) — which also means you
  see everything with `kubectl get findings` and can approve/veto anything

Portable: push this repo to GitHub, `git pull` on any box with cluster access, run **one script**
(`install.sh`) — it installs the prereqs (kubectl/helm/kustomize/istioctl), verifies/installs
Ollama, pulls the models the agents need, builds and deploys the operator, and wires memory.

---

## The one hard rule: it can create/update/alter, it CANNOT destroy

You said "can create, update, alter, but [not] destroy — take backup of existing and create new."
That is enforced three ways, not promised:

1. **RBAC** ([`deploy/rbac.yaml`](deploy/rbac.yaml)) — the operator's ServiceAccount has
   `get/list/watch/create/update/patch` on the resources Helm/Istio/Kustomize/kubectl need, but
   **no `delete` / `deletecollection`** on Deployments, StatefulSets, DaemonSets, Services,
   Ingresses, PVCs, PVs, Namespaces, Nodes, CRDs, Secrets, RBAC, or Istio config. The API server
   rejects any such call. It *can* delete Pods (a controller recreates them — reversible).
2. **Kyverno backstop** — an `Enforce` policy blocks the SA from `DELETE` verbs and from writing to
   `kube-system` / control-plane namespaces, even if the ClusterRole were later widened by mistake.
3. **Code** ([`src/kube_safe.py`](src/kube_safe.py)) — every change goes through `safe_apply()`:
   parse → **snapshot the current object to a backup** (Git commit + a `*-backup` ConfigMap) →
   `kubectl apply --dry-run=server` → Kyverno/OPA policy check → diff must be non-destructive
   (no field/subresource removal that loses data) → apply → verify → record outcome. Any failure
   rolls forward to `AwaitingHuman`, never a half-applied change.

"Alter an Istio VirtualService" = update-in-place or **backup + create the new one alongside** and
flip traffic — never delete-then-create.

---

## Architecture

```
                         your box / VM                          the cluster
              ┌───────────────────────────┐        ┌──────────────────────────────────────┐
              │  Ollama  (llama3, mistral, │◀──────▶│  ai-operator  (one Deployment)       │
              │  mixtral, deepseek-coder,  │  HTTP  │  ┌────────────────────────────────┐  │
              │  nomic-embed-text)         │  LAN   │  │ coordinator  — routes, dedupes, │  │
              └───────────────────────────┘        │  │   prioritises, writes learnings │  │
                                                   │  ├────────────────────────────────┤  │
   Git repo ──clone/pull──▶ /workspace  ──────────▶│  │ scanner   (deepseek-coder 6.7b) │  │
   (this repo + your manifests)                    │  │ security  (mixtral / llama3)    │  │
                                                   │  │ remediator(codellama 13b)      │  │
   PR / branch ◀──gitops agent──────────────────── │  │ gitops    (llama3 8b)           │  │
                                                   │  └───────────────┬────────────────┘  │
                                                   │        writes    │  watches          │
                                                   │   ┌──────────────▼───────────────┐   │
                                                   │   │ Finding / Remediation  CRDs  │   │  ◀── you: kubectl get findings
                                                   │   └──────────────────────────────┘   │      kubectl annotate finding X approve=true
                                                   │   PVC: /memory/agent.db (SQLite +    │
                                                   │        float32 embeddings) + backups │
                                                   └──────────────────────────────────────┘
```

**Agents** (config in [`config/agents.yaml`](config/agents.yaml), prompts in `config/prompts/`):

| Agent | Model (default) | Job |
|---|---|---|
| `coordinator` | `llama3:8b` | dedup findings, assign severity/priority, pick the remediation strategy, decide auto vs human, distil learnings into memory, keep the digest ConfigMap |
| `scanner` | `deepseek-coder:6.7b` | walk every `*.yaml`/`*.yml` in the repo + `kubectl get` live objects; flag misconfig, missing probes/limits/PDB/NetworkPolicy, `:latest`, privilege, anti-patterns, efficiency |
| `security` | `mixtral:latest` (fallback `llama3:latest`) | secret/token/key leakage in manifests + configmaps + env, over-broad RBAC, host mounts, exposed ports, missing `NetworkPolicy`, image provenance |
| `remediator` | `codellama:13b` | given a Finding, produce the exact minimal patch / Helm values / Gateway to fix it; must pass `safe_apply` validation |
| `gitops` | `llama3:8b` | commit the fix to a branch, open a PR with the Finding + evidence + diff, or (if a GitOps repo is configured) push for Argo/Flux to sync |

They cooperate by **passing `Finding` objects through the coordinator** — a scanner/security agent
creates a `Finding`; the coordinator triages it and creates a `Remediation`; the remediator fills
in the fix; `safe_apply` validates + applies (or the gitops agent PRs it); the outcome is written
back to the `Finding` and into memory.

---

## Agentic memory — how they "learn"

`src/memory.py`, backed by SQLite on a PVC:

- **`store(kind, scope, text, outcome, confidence)`** — every finding, remediation, and result.
  `text` is embedded with Ollama `nomic-embed-text`; the vector is stored as bytes.
- **`recall(text, k)`** — cosine similarity over past entries. Before an agent analyses something,
  the coordinator injects the top-k similar past cases into the prompt: *"last 3 times you saw
  something like this: … the fix that worked was … the fix that failed was …"*.
- **`patterns()`** — entries seen ≥ N times with a consistent successful fix get promoted to a
  **pattern**: the coordinator can then apply the known-good remediation with high confidence and
  skip re-asking the LLM (faster, cheaper, deterministic).
- **`digest`** — hourly, the coordinator writes `agent-memory-digest` ConfigMap: top patterns,
  recent wins, recurring problems. `kubectl -n ai-operator get cm agent-memory-digest -o yaml`.

Memory survives pod restarts (PVC). Back it up with Velero or a `CronJob` that copies `agent.db`
off-cluster (a sample is in `deploy/`).

---

## Use it

### First time, anywhere

```bash
git clone <your fork of this repo> && cd <repo>/k8s/ai-operator
cp .env.example .env && $EDITOR .env      # set OLLAMA_HOST, GIT_REPO_URL, GIT_TOKEN (as a k8s Secret)
./install.sh                              # detects distro, installs prereqs, Ollama + models, deploys
```

`install.sh` is idempotent — re-run it any time to upgrade the operator or re-pull models.

### Day to day

```bash
kubectl -n ai-operator get findings                     # what the agents have found
kubectl -n ai-operator get remediations                 # what they're doing about it
kubectl -n ai-operator describe finding <name>          # evidence + the proposed fix
kubectl -n ai-operator logs deploy/ai-operator -f       # live agent reasoning (structured JSON)
kubectl -n ai-operator get cm agent-memory-digest -o yaml   # what they've learned

# approve something the coordinator flagged for a human:
kubectl -n ai-operator annotate finding <name> ai-operator.io/decision=approve --overwrite
# veto / stop touching something:
kubectl -n ai-operator annotate finding <name> ai-operator.io/decision=dismiss --overwrite

# global controls (ConfigMap ai-operator-config):
kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"mode":"observe"}}'   # scan+report only, apply nothing
kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"mode":"assist"}}'    # auto-apply low-risk, PR the rest  (default)
kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"mode":"auto"}}'      # auto-apply everything on the allowlist
kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"paused":"true"}}'    # full stop
```

Run in `mode: observe` for the first few days, read the Findings, then move to `assist`.

---

## What runs automatically vs. what waits for you

| Auto (in `assist`/`auto`, backup-first, validated) | Always waits for a human (PR or `AwaitingHuman`) |
|---|---|
| add missing probes / resource limits / PDB / NetworkPolicy | deleting anything |
| pin `:latest` → digest; fix an obviously wrong value | scaling to zero |
| add a `ResourceQuota` / `LimitRange` to a namespace | RBAC changes that grant new powers |
| open a port the workload clearly needs (Service/Ingress/Gateway) that is in-policy | anything touching `kube-system` / control plane / etcd |
| move a leaked literal secret into a `Secret` + reference it *(and flag the value for rotation — rotation is yours)* | Namespace / CRD / PV / PVC changes |
| `helm upgrade` to a newer patch of an already-installed chart | new chart install that isn't on the `allowedCharts` list |
| bump CPU/RAM within the configured cap | cluster version upgrades (use `kubernetes-upgrader`) |

Circuit breakers (in `ai-operator-config`): max changes per target per hour, max cluster-wide per
10 min (→ auto-pause + Event), never act while the control plane is unhealthy, per-namespace
opt-out label `ai-operator.io/policy: manual`.

---

## Security posture (industry standard)

- Local inference only — Ollama on your LAN; a `NetworkPolicy` restricts the operator's egress to
  {API server, `OLLAMA_HOST`, your Git host} and nothing else.
- Operator pod: non-root, `readOnlyRootFilesystem`, all caps dropped, `RuntimeDefault` seccomp,
  Pod Security Admission `restricted`.
- Git credentials + any registry creds are Kubernetes `Secret`s, never in an image or ConfigMap.
- Every LLM-proposed change is schema-checked (`--dry-run=server`), policy-checked (Kyverno), and
  diff-checked (no data-losing removals) **before** apply. LLM output is never applied raw.
- Full audit: every action is a `Finding`/`Remediation` status transition + a JSON log line +
  a Kubernetes `Event` + a memory row. Nothing happens silently.
- Backups: Git commit of the pre-change manifest + a `<name>-backup-<ts>` ConfigMap for live-only
  objects, retained per `backupRetention`.

---

## Files

```
install.sh              one-command bootstrap (prereqs + Ollama + models + deploy)
uninstall.sh            removes the operator; keeps memory unless --purge
Dockerfile              the agent image (python:3.12-slim + kubectl/helm/kustomize/istioctl)
requirements.txt
.env.example
config/
  agents.yaml           agent → model → cadence → scope
  prompts/*.md          system prompt per agent
crds/
  finding.yaml          Finding CRD  (what an agent noticed)
  remediation.yaml      Remediation CRD  (what it's doing about it)
deploy/
  namespace.yaml rbac.yaml ollama.yaml networkpolicy.yaml pvc.yaml
  deployment.yaml config.yaml memory-backup-cronjob.yaml kustomization.yaml
src/
  operator.py           kopf handlers: scan timers + Finding→Remediation flow
  agents.py             agent registry + LLM orchestration + memory injection
  ollama_client.py      chat + embeddings, retry/backoff, model fallback
  memory.py             SQLite + embeddings: store / recall / patterns / digest
  kube_safe.py          safe_apply: backup → dry-run → policy → non-destructive diff → apply → verify
  scanner.py            git + live-cluster YAML enumeration
scripts/
  detect-distro.sh      kind/minikube/kubeadm/k3s/EKS/AKS/GKE/OpenShift
  pull-models.sh        pulls only the models config/agents.yaml references
```
