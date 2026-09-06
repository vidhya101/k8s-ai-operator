# TEAM ROSTER

The org chart. How the 53 agents in this `.claude/agents/` folder work together as a team for
the user (senior DevOps engineer, 8+ years, running solo as a one-person consultancy augmented
by this AI team). Referenced by the `orchestrator` and every `*-manager` during delegation.

## Roster at a glance

**Total: 1 top-level router + 12 domain managers + 22 shared sub-agents + 18 existing specialists = 53 agents.**

### Top-level (1)

- `orchestrator` — routes cross-domain asks to the right managers, chains their outputs

### Domain managers (12) — own their domain end-to-end

- `linux-manager`
- `github-manager`
- `docker-manager`
- `cicd-manager`
- `ansible-manager`
- `terraform-manager`
- `cloud-manager` (AWS + Azure + GCP)
- `kubernetes-manager` (EKS + AKS + GKE + OpenShift + kubeadm + k3s + kind + minikube)
- `aiops-manager`
- `mlops-manager`
- `sre-manager`
- `observability-manager`

### Shared sub-agent pool (22) — invoked by managers, not by user directly

**Design layer** (5):
- `designer` — approach + steps + rejected alternatives + risks
- `critic` — structured objections (type + severity + failure_mode + condition); 2 rounds max
- `system-designer` — whole-system architecture spanning many services
- `backend-engineer` — single-service backend architecture (API, data, async)
- `frontend-engineer` — single-service frontend architecture (components, state, a11y)

**Implementation layer** (5 language coders):
- `code-writer-python`
- `code-writer-go`
- `code-writer-java`
- `code-writer-javascript`
- `code-writer-typescript` (preferred over -javascript when TS is available)

**Review layer** (5) — invoked in parallel (MANDATORY: one message, N Agent calls — see Loop 2 below);
multiple reviewers each pass over the same work independently:
- `code-reviewer` — language-agnostic quality/correctness review
- `bug-hunter` — adversarial, tries to BREAK the code with hostile inputs / races / exhaustion
- `code-simplifier` — same behavior, less code
- `yaml-config-reviewer` — YAML-layer gotchas (coercion, duplicate keys, anchor abuse)
- `port-security-auditor` — exposed-ports audit across Docker/K8s/cloud SG/host

**Verification layer** (2):
- `tester` — write/run tests, reproduce-then-fix for bugs
- `sandbox-verifier` — deploy to scratch env, prove desired = actual (never approximate)

**Specialists** (5):
- `network-engineer` — cross-cutting L3/L4/L7 depth
- `ai-engineer` — LLM/RAG/prompt/guardrails/eval
- `data-scientist` — model math, features, evaluation, stats
- `technical-writer` — runbooks, ADRs, README, onboarding
- `oracle-expert` — Oracle DB + OCI (only cloud not covered by cloud-manager)

### Existing specialists (18) — invoked by the appropriate manager as sub-experts

- `aiops-reviewer` (← aiops-manager)
- `data-engineering-reviewer` (← mlops-manager)
- `database-reliability-engineer` (cross-cutting DB review — any manager with a DB)
- `docker-reviewer` (← docker-manager)
- `github-actions-reviewer` (← github-manager / cicd-manager)
- `kubernetes-debugger` (← kubernetes-manager during troubleshooting — read-only diagnosis)
- `kubernetes-troubleshooter` (← kubernetes-manager — carries a fix through to verified recovery + adds a self-healing guardrail; cross-distro incl. OpenShift/ROSA/minikube)
- `kubernetes-upgrader` (← kubernetes-manager — full cluster version upgrades, control plane + workers, one minor at a time, pre-flight + etcd backup + phased execution with rollback; kubeadm/EKS/AKS/GKE/OpenShift/ROSA/k3s/RKE2)
- `mlops-reviewer` (← mlops-manager)
- `observability-engineer` (← observability-manager)
- `principal-cloud-architect` (← cloud-manager for structured architecture review)
- `principal-devsecops` (cross-cutting security — any manager, security-cross-cutting)
- `principal-finops-engineer` (← cloud-manager for cost)
- `principal-platform-engineer` (← kubernetes-manager / cloud-manager for IDP concerns)
- `principal-sre` (← sre-manager)
- `production-incident-commander` (← sre-manager during active incidents)
- `security-auditor` (cross-cutting; often runs in parallel with bug-hunter + code-reviewer)
- `terraform-reviewer` (← terraform-manager)

---

## How work flows

The user asks ONE thing. The `orchestrator` (or, for a clearly-single-domain ask, the relevant
manager directly) decomposes into a sequence of specialist invocations. Each step's output feeds
the next. Every code-producing step is peer-reviewed by multiple reviewers in parallel. Every
environment-touching step is sandbox-verified.

### Standard delegation chain within any manager

For a "propose + implement + verify" task:

```
manager
   ├─→ designer          (propose approach with rejected_alternatives, risks, verification)
   ├─→ critic            (object once, revise once, then accept or escalate — round 2 max)
   ├─→ code-writer-<lang> (implement per the design)
   │
   ├─→ code-reviewer   ┐
   ├─→ bug-hunter      ├─ IN PARALLEL — each finds different things; all findings routed
   ├─→ code-simplifier ┤  back to code-writer for one revision round; then re-review
   ├─→ security-auditor┤  round 2. Round-2 unresolved → ESCALATE.
   └─→ port-security-auditor (when the code exposes ports)
       (+ yaml-config-reviewer when the artifact contains YAML)
   │
   ├─→ tester            (write tests, run existing suite — must be green)
   ├─→ sandbox-verifier  (apply to scratch env; CLEAN / DIVERGENT / INDETERMINATE)
   │      └─→ DIVERGENT → back to designer (design missed something)
   │      └─→ INDETERMINATE → escalate (verification didn't complete)
   │      └─→ CLEAN → manager synthesizes and returns to orchestrator/user
   └─→ (async during and after) memory writes for future recall
```

### Cross-manager chaining (the "RAG-like loop")

When step N is one manager's output and step N+1 is a different manager's input:

```
Example: "Provision infra + deploy service + wire observability + define SLOs"

orchestrator
   ├─→ terraform-manager  → EKS cluster + node group
   │      output: cluster identifier + kubeconfig
   ├─→ kubernetes-manager (given terraform-manager's cluster) → Deployment + Service
   │      output: workload manifest + endpoint URL
   ├─→ observability-manager (given k8s-manager's workload) → Prometheus scrape + Grafana dashboard
   │      output: metric names + dashboard URLs
   └─→ sre-manager (given observability-manager's metrics) → SLI definitions + SLO + error budget
          output: SLO document + alert rules
```

Each manager's synthesized output — NOT its raw internal specialist calls — is what the next
manager sees.

---

## The five explicit feedback loops (the "cross-question, fight for good work" pattern)

The user asked for "collaboration, comment each other, check each other work, do critics, review,
feedback, resolve error, loop feedback." Here are the loops:

### Loop 1: Design critique (designer ⇄ critic) — bounded 2 rounds

- Round 1: designer proposes. critic objects with structured `failure_mode + condition` or accepts.
- Round 2 (if rejected): designer revises with objections; critic re-reviews.
- Round 3 does not exist. Unresolved → ESCALATE to user.

### Loop 2: Parallel independent review (the "fight for good work" pattern)

For any code artifact, multiple reviewers run **in parallel** and independently, each looking for
different things:

- `code-reviewer` → structured quality/correctness pass
- `bug-hunter` → adversarial ("what if input is malformed / race / timeout / attacker")
- `code-simplifier` → "same behavior in less code"
- `security-auditor` → credentials / injection / auth surface
- `port-security-auditor` → exposed-ports if the artifact exposes any
- `yaml-config-reviewer` → YAML mechanics if the artifact is YAML

Each returns findings. They can DISAGREE — e.g. code-simplifier proposes removing an abstraction
that bug-hunter says exists for a specific edge case. The manager arbitrates the disagreement,
does NOT silently pick one side, and if the disagreement is load-bearing, escalates to user.

All findings route back to `code-writer-<lang>` for ONE revision round. Then reviewers re-review
in parallel again. Unresolved after round 2 → ESCALATE to manager, then user.

**MANDATORY batching — no exceptions.** Managers invoking these reviewers MUST dispatch
ALL applicable reviewers in a SINGLE assistant message (concurrent Agent tool calls),
not one after the other. If four reviewers apply to an artifact, that is one turn with
four Agent tool calls, not four sequential turns. Sequential invocation of independent
reviewers wastes wall clock AND tokens (each round-trip re-loads context). The same rule
applies to the re-review after revision: batch. The only reason to serialize is when
reviewer N's findings are literally the input to reviewer N+1 — which, for
same-artifact independent reviewers, is never.

### Loop 3: Verification loop (sandbox-verifier → designer on DIVERGENT)

sandbox-verifier applies the artifact to a scratch env and compares desired vs actual state.

- CLEAN → forward, manager returns to user
- DIVERGENT (actual ≠ desired) → back to `designer` via manager (the DESIGN missed something,
  not just the code) → new design pass, code, review, verify. This is a FULL loop back, not
  just a code fix.
- INDETERMINATE (verification couldn't complete reliably) → ESCALATE. **INDETERMINATE is a
  FAILURE, not a pass.** Never report success on partial verification.

### Loop 4: Cross-manager handoff bugs

If manager A delegates to manager B, and B identifies that A's output contains a bug / vuln /
design flaw, B surfaces it in their response. The orchestrator routes back to A (usually with
`network-engineer` or `security-auditor` involved) to fix. Then B re-tries.

Example: cloud-manager designs a topology; terraform-manager implementing it finds a subnet
overlap; terraform-manager surfaces the finding; orchestrator routes back to cloud-manager +
network-engineer for a fix.

### Loop 5: Incident feedback (sre-manager → domain manager)

After an incident, the responsible domain manager receives specific findings from sre-manager
(via `production-incident-commander`'s postmortem). These become work items — design changes,
code fixes, runbook updates — owned by the domain manager.

Postmortem action items are always **owned** and **tracked**; sre-manager loops back later to
verify they're done.

---

## Self-learning (per `.claude/rules/memory-usage.md`)

Every agent reads memory at the start of significant work and writes findings back at the end.
This is how the team accumulates knowledge across sessions instead of re-deriving decisions
every conversation.

Naming (from `mcp-memory` skill):

- `Session-YYYY-MM-DD-<project>-<feature>`
- `Solution-<problem>-<technology>`
- `Pattern-<architecture>-<context>`
- `Decision-<what>-<project>`

Never write secret values to memory (see `.claude/rules/secrets.md`) — memory persists.

## Self-healing (bounded auto-remediation)

Any auto-remediation MUST have:

- **Bounded blast radius** (kill 1 pod, not the whole Deployment; scale by N not "as needed")
- **Circuit breaker** (if action fires N times without resolving, stop and escalate)
- **Full auditability**
- **Human confirmation for anything touching real data / credentials / scale-down**

Designed by `aiops-manager` with `sre-manager` sign-off. See `.claude/skills/aiops`. NEVER wire
up unattended auto-remediation without going through this design pass — `.claude/rules/safety.md`
applies doubly to automated action.

## Code quality standards (per `.claude/rules/code-quality.md`)

Every `code-writer-*` produces code meeting the code-quality rule (explicit error handling,
exception discipline, WHY-not-WHAT comments, secrets never in code, security defaults).
`code-reviewer` enforces this at review time — failures are blocking findings, not nits.

Formatting (indentation, spacing) is a TOOL responsibility (Black / gofmt / prettier / ruff
format) invoked by the coder as part of writing — no dedicated formatting agent.

---

## Routing decision — who owns what task class

Skip the orchestrator when the ask maps to one manager. Managers listed alphabetically:

| Task type                                       | Owner                                                   |
|-------------------------------------------------|---------------------------------------------------------|
| Adversarial bug hunting on critical-path code   | `bug-hunter` (invoked by the owning manager alongside code-reviewer) |
| Alert noise / correlation / anomaly detection   | `aiops-manager`                                         |
| Ansible playbook / role / inventory             | `ansible-manager`                                       |
| API design / backend architecture (per service) | `backend-engineer` (invoked by the owning manager)      |
| CI/CD pipeline SHAPE (stages, gates, promotion) | `cicd-manager`                                          |
| Cloud architecture (AWS/Azure/GCP)              | `cloud-manager`                                         |
| Code review (language-agnostic)                 | `code-reviewer` (invoked by any manager after coder)    |
| Code simplification                             | `code-simplifier` (invoked alongside code-reviewer)     |
| Docker image build/review/scan                  | `docker-manager`                                        |
| Exposed ports audit                             | `port-security-auditor` (parallel with security-auditor)|
| Frontend architecture                           | `frontend-engineer`                                     |
| GitHub Actions YAML / repo config / GHCR        | `github-manager`                                        |
| Incident response (active)                      | `sre-manager` → `production-incident-commander`         |
| Kubernetes workload / cluster / GitOps          | `kubernetes-manager`                                    |
| Linux host / systemd / kernel / resource pressure | `linux-manager`                                       |
| ML/LLM lifecycle (training, serving, RAG, drift)| `mlops-manager`                                         |
| Metrics/logs/traces instrumentation             | `observability-manager`                                 |
| Multi-domain ask ("design + build + deploy + monitor") | `orchestrator`                                    |
| Onboarding / runbook / ADR / README             | `technical-writer` (direct)                             |
| Oracle DB / OCI                                 | `oracle-expert`                                         |
| Postmortem                                      | `sre-manager` → `production-incident-commander`         |
| RAG debugging                                   | `mlops-manager` → `ai-engineer`                         |
| Security review / audit / scan triage           | `security-auditor` (direct or via manager)              |
| SLO / on-call / capacity / chaos                | `sre-manager`                                           |
| System-wide architecture (spans many services)  | `system-designer` (via orchestrator)                    |
| Terraform module / state / import               | `terraform-manager`                                     |
| YAML mechanics review (K8s / GHA / Helm YAML)   | `yaml-config-reviewer` (parallel with tool-specific)    |

For anything not on this list, invoke `orchestrator` — it will figure out the routing.

## What NOT to route through this team

- Trivial one-line fixes (edit directly)
- Read-only questions ("what does this config do") — respond directly
- Truly novel domains not covered by any manager — flag to user, expand the team if warranted
- Anything requiring credentials the user hasn't provided — stop and ask

## Adding to this team

- **New manager**: only when a whole DOMAIN is unrepresented (not a sub-topic of an existing
  manager). Follow the manager template from any existing `*-manager.md` file.
- **New sub-agent**: only when a real CROSS-CUTTING gap exists that multiple managers need.
  Don't add per-manager duplicates (no `python-coder-for-kubernetes` and `python-coder-for-mlops`
  — one `code-writer-python` serves all).
- **New rule**: only for policy that must apply to EVERY agent invocation. Rules are
  always-loaded and cost context on every message; keep them tight.

After adding: run `.claude/scripts/validate-skills.sh` (also validates agents indirectly by
convention), and re-generate `.claude/docs/SKILLS_INDEX.md` if a new skill was added.
