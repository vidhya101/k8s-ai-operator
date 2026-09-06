# ai-operator — an in-cluster AI agent that reviews and fixes your Kubernetes YAML

Cooperating agents run **inside your cluster**, think with a **local Ollama** (no cloud LLM, no
data leaves the cluster), continuously scan every manifest (live objects + optionally a Git repo),
and remediate what they find — **create / update / patch only, never delete** (enforced by RBAC,
not a promise). Findings and fixes are Kubernetes objects you can see and approve with `kubectl`.

---

## Quick start — installs into your **existing** cluster

**Prerequisite:** you can already reach your cluster. Verify:

```bash
kubectl get nodes        # must list your nodes
```

- **From your laptop:** that means `~/.kube/config` is set up for the cluster.
- **From the control-plane node:** if `kubectl` isn't configured for your user, the installer
  falls back to `/etc/kubernetes/admin.conf` automatically (or run `sudo ./install.sh`).

Then:

```bash
git clone https://github.com/vidhya101/k8s-ai-operator.git
cd k8s-ai-operator/k8s/ai-operator
./install.sh
```

It does **not** create or modify a cluster — it deploys the operator into one you already have. It:
1. **lists the kube contexts in your kubeconfig and asks which cluster** (or `--context NAME` /
   `KUBE_CONTEXT` in `.env` to skip the prompt),
2. shows that cluster's health (nodes Ready, API server, failing pods) — informative, not a gate;
   a cluster in bad shape is exactly what this is for — then asks to confirm,
4. preflights the real blockers: your user can create Deployments + ClusterRoles, and a **default
   StorageClass exists** (the operator's PVCs need one) — fails early with the fix if not,
5. applies the CRDs + operator with server-side apply (idempotent — safe to re-run); a partial
   failure is reported, not fatal,
6. starts Ollama in the cluster and pulls the small (≤8B) models the agents use,
7. optionally installs Kyverno as an extra backstop (skippable — the operator is safe without it),
8. waits for it to come up (~2 min first time).

**No cluster yet, just trying it out?** `./install.sh --kind` spins up a throwaway local cluster
(needs Docker running; reuses any models already in `~/.ollama`). This is the *only* mode that
creates anything.

### Optional config — `.env`

Everything works with defaults. Copy `env.template` to `.env` only to change something:

```bash
MODE=observe                                   # observe | assist | auto
OLLAMA_EXTERNAL_URL=http://192.168.1.50:11434   # use a faster GPU Ollama instead of in-cluster
GIT_REPO_URL=https://github.com/you/manifests.git   # also scan a repo's files + open PRs
GIT_TOKEN=<PAT>
```

---

## Watch it work

```bash
kubectl -n ai-operator get pods
kubectl -n ai-operator logs deploy/ai-operator -f          # live agent reasoning (JSON)
kubectl -n ai-operator get findings                        # what it found
kubectl -n ai-operator describe finding <name>             # evidence + proposed fix
kubectl -n ai-operator get remediations                    # what it did about it
kubectl -n ai-operator get cm agent-memory-digest -o yaml  # what it has learned
```

Steer it:
```bash
kubectl -n ai-operator annotate finding <name> ai-operator.io/decision=approve --overwrite
kubectl -n ai-operator annotate finding <name> ai-operator.io/decision=dismiss --overwrite

kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"mode":"assist"}}'
kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"paused":"true"}}'   # stop
```

Start in `observe` for a few days, read the findings, then `assist`.

---

## The agents

| Agent | Model (default, in-cluster) | Job |
|---|---|---|
| coordinator | `llama3:8b` | triage findings, dedupe, decide auto-vs-human, write learnings to memory |
| scanner | `deepseek-coder:6.7b` | misconfig, missing probes/limits/PDB/quota/NetworkPolicy, `:latest`, waste |
| security | `llama3:8b` | leaked secrets/tokens, over-broad RBAC, host mounts, exposed ports |
| remediator | `codellama:7b` | produce the minimal patch / Helm values / open-port bundle |
| gitops | `llama3:8b` | commit an approved fix to a branch, open a PR |

They cooperate through the `Finding` and `Remediation` CRDs. For better quality, point
`OLLAMA_EXTERNAL_URL` at a GPU Ollama and raise the `model.*` values in `deploy/config.yaml` to
`mixtral` / `codellama:13b`.

**Memory:** SQLite + `nomic-embed-text` embeddings on a PVC. Similar past cases are injected into
each prompt; repeated successful fixes become "patterns" applied without an LLM call.

---

## "It cannot delete my app" — enforced 3 ways

1. **RBAC** (`deploy/rbac.yaml`): the operator's ClusterRole has `get/list/watch/create/update/patch`
   (so Helm, Istio, Kustomize, kubectl all work) but **no `delete`/`deletecollection`** on
   Deployments, StatefulSets, Services, Ingresses, PVCs, PVs, Namespaces, Nodes, CRDs, Secrets,
   RBAC. The API server rejects it. It can delete Pods (a controller recreates them — reversible).
2. **`src/kube_safe.py`**: every change goes snapshot → `kubectl apply --dry-run=server` → policy
   check → a diff that **rejects removal of any `spec`/`data`/`rules` field** → apply → verify.
   LLM output is never applied raw.
3. **Kyverno** (`deploy/kyverno-guardrails.yaml`, optional): blocks the SA from any `DELETE`, from
   writing system namespaces, from non-Helm Secrets, from binding `cluster-admin`.

Deleting an app, PVC, namespace, or node always needs a human (or a GitOps PR the operator opens).

---

## What runs automatically vs. waits for you

| Auto in `assist`/`auto` (backup-first, validated, circuit-broken) | Always a human / PR |
|---|---|
| add probes / limits / PDB / NetworkPolicy / quota | any delete |
| pin `:latest` → digest; fix a clearly-wrong value | RBAC changes granting new powers |
| open a port the workload needs (Service/Ingress/Gateway) | anything in `kube-system` / control plane |
| move a leaked literal secret into a Secret + reference it (flags the value for rotation) | Namespace / CRD / PV / PVC changes |
| `helm upgrade` an already-installed chart to a newer patch | new chart installs not on the allow-list |
| raise CPU/RAM within the cap | cluster version upgrades |

Circuit breakers (`ai-operator-config`): max changes per target/hour, max cluster-wide/10min (→
auto-pause), never act while the control plane is unhealthy, `ai-operator.io/policy: manual`
namespace opt-out.

---

## Uninstall

```bash
./install.sh --uninstall            # removes the operator, keeps the memory + models PVCs
./install.sh --uninstall --purge    # also deletes the namespace/PVCs (and the kind cluster)
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| operator pod stuck `Init` | `kubectl -n ai-operator logs deploy/ai-operator -c code` (clone) / `-c deps` (pip). Needs egress to github.com + pypi.org — the NetworkPolicy allows 443. |
| `ollama` pod `CrashLoopBackOff` / OOM | a model is too big for the memory limit — lower the `model.*` values or raise `deploy/ollama.yaml` limits. |
| findings never appear | `kubectl -n ai-operator logs deploy/ollama` — is it serving? `kubectl -n ai-operator exec deploy/ollama -- ollama list` — are models pulled? |
| using `OLLAMA_EXTERNAL_URL` and nothing happens | install.sh printed whether a cluster pod could reach it. Ollama must bind `0.0.0.0`, the IP must be routable from pods, host firewall must allow `:11434`. |
| cluster too small | `./install.sh --kind` for a clean one, or free up capacity. The operator itself is tiny (~150m/384Mi); Ollama wants ~3–12Gi. |
