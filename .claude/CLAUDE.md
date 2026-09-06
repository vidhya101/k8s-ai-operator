# CLAUDE.md

Universal engineering instructions for DevOps, DevSecOps, SRE, Platform Engineering, Cloud Engineering,
MLOps, AIOps, Data Engineering, Infrastructure as Code, CI/CD, Kubernetes, observability, and production
operations — across any tech stack, any cloud, any client repository.

This file is intentionally short. It states core behavior and the onboarding workflow, which apply to
every task regardless of stack. Everything tool/domain-specific (Terraform, Kubernetes distros,
observability backends, scanners, etc.) lives in `skills/` and loads only when relevant — see Section 3.
These instructions apply to the entire repository unless a more specific nested `CLAUDE.md` overrides them.

@rules/safety.md
@rules/secrets.md
@rules/environment-awareness.md
@rules/git-conventions.md
@rules/memory-usage.md
@rules/code-quality.md
@config/environment.md

---

# 1. Core Engineering Behavior

## 1.1 Think Before Coding

Do not assume. Do not hide uncertainty. Surface tradeoffs.

Before making changes:

- Understand the request.
- Inspect the existing project.
- State important assumptions.
- Identify missing information.
- Present multiple valid interpretations when ambiguity exists.
- Prefer the simplest valid solution.
- Push back when a requested approach introduces unnecessary risk or complexity.
- Ask before proceeding when requirements are materially unclear.

Do not silently choose:

- a cloud provider
- a region
- an environment
- a Kubernetes distribution
- a deployment strategy
- a secret-management system
- a networking model
- a state backend
- an artifact registry
- a branching strategy
- a disaster-recovery objective

## 1.2 Simplicity First

Use the minimum code and infrastructure required to solve the stated problem.

Do not:

- add features that were not requested
- create abstractions for a single use
- introduce a module solely for appearance
- add unnecessary configuration flags
- create speculative future architecture
- over-engineer development environments
- introduce tools without a clear operational benefit
- rewrite working code for style preference

Ask:

> Would a senior engineer consider this unnecessarily complicated?

If yes, simplify.

## 1.3 Surgical Changes

Touch only what is necessary.

When modifying existing code:

- preserve the existing architecture unless change is required
- preserve naming conventions
- preserve formatting style
- preserve resource addresses where possible
- do not refactor unrelated code
- do not remove unrelated dead code
- do not update unrelated dependencies
- do not change adjacent comments unless necessary
- do not rename variables, files, modules, resources, workflows, or jobs without a clear reason

Every changed line must directly support the requested result.

When your changes make something unused:

- remove only imports, variables, functions, files, resources, or configuration made obsolete by your own
  changes
- mention pre-existing cleanup opportunities separately

## 1.4 Goal-Driven Execution

Convert the request into measurable success criteria.

For multi-step work, use:

```text
1. Action
   Verify: command or expected result

2. Action
   Verify: command or expected result

3. Action
   Verify: command or expected result
```

---

# 2. Repository Onboarding Workflow

Run this sequence at the start of any non-trivial task, in any repo, on any stack. Skip a step only if it
does not apply and say so. The `repository-discovery` skill and the `/onboard` command carry out this
workflow's mechanics in detail — invoke either when starting cold in an unfamiliar repo.

```text
1. Detect dependency manifests
   Verify: find requirements.txt, pyproject.toml, package.json, go.mod, pom.xml, build.gradle,
   Gemfile, Cargo.toml, *.tf, *.tfvars, ansible.cfg/requirements.yml, Dockerfile(s),
   docker-compose*.yml, Chart.yaml, kustomization.yaml, .github/workflows/*.yml

2. Install/sync dependencies for every manifest found
   Verify: install command exits 0 (pip install -r requirements.txt, npm ci, go mod download,
   terraform init, ansible-galaxy install -r ...)

3. Learn the project
   Verify: can state in one paragraph what the service does, its entry point, its runtime, its
   external dependencies (DB, queue, APIs), and its current deployment target (if any)

4. Identify existing infra/CI/CD state
   Verify: know whether Terraform state exists (local or remote backend), whether a CI pipeline
   already exists, whether a K8s manifest/Helm chart/Argo Application already exists — do not
   create parallel/duplicate pipelines

5. Build and validate the container image, if one exists (see the docker-multi-stage,
   docker-security skills)
   Verify: image builds clean, runs, health check passes

6. Enumerate ports, network exposure, and secrets (see the docker-security, networking,
   terraform-security skills)
   Verify: documented list of exposed ports, their purpose, and whether each should be public,
   cluster-internal, or loopback-only

7. Only after 1-6: propose or build the CI/CD pipeline
   Verify: pipeline plan reviewed against Section 1.1 (no silent choices)
```

Do not jump to writing pipeline YAML or Terraform before steps 1-4 are done. Infrastructure written
against an unread codebase is a guess, not an implementation.

---

# 3. How This Claude Code Setup Is Organized

Everything lives under `.claude/` — this file included — so the whole setup is one self-contained,
copyable folder. See [README.md](README.md) (i.e. `.claude/README.md`) for the full explanation. In short:

- **`rules/*.md`** — always-loaded, non-negotiable policy (imported above): change safety, secret
  handling, environment awareness, git conventions.
- **`skills/*/SKILL.md`** — on-demand domain/tool reference (Terraform, every major Kubernetes distro,
  every cloud, the observability stack, the scanning tools, GitOps, MLOps platforms, databases, scripting
  languages, and the SRE/DevSecOps/MLOps/AIOps/Platform-Engineering/FinOps disciplines). Loaded only when
  the current task matches, keeping context lean.
- **`agents/*.md`** — specialized reviewer/operator personas (principal-level architects, tool reviewers,
  a Kubernetes debugger, a database reliability engineer, an incident commander, a FinOps engineer).
  Advisory by default — they diagnose and recommend; the main session makes the actual changes.
- **`commands/*.md`** — slash commands (`/onboard`, `/iac-review`, `/security-scan`, `/k8s-debug`,
  `/incident`, `/pipeline-audit`, `/docker-review`, `/architecture-review`, `/db-review`, `/cost-review`)
  that kick off a specific agent + skill combination for a common workflow. `/k8s-fix` runs the
  `kubernetes-troubleshooter` agent — root-cause → fix (with confirmation) → verify → self-healing
  guardrail — across EKS/AKS/GKE/OpenShift/ROSA/kubeadm/k3s/kind/minikube; `/k8s-autopilot` runs it
  in continuous mode against an alert/event stream (Tier-1 auto-fix, Tier-2 GitOps PR, Tier-3 page).
  `/k8s-upgrade` runs the `kubernetes-upgrader` agent — full cluster version upgrade (control plane
  + workers), one minor at a time, read-only pre-flight (`k8s/platform/upgrade/preflight.sh`) →
  etcd backup → phased execution with confirmation at every boundary → rollback plan.
  The platform layer it operates — observability + detection (PrometheusRules) + prevention (Kyverno
  admission) + remediation (NPD/Medik8s, descheduler, autoscalers) + the tier model + fleet rollout —
  lives in `k8s/platform/` (see its `README.md`). `k8s/platform/autopilot/` is the hands-off
  in-cluster variant: a scoped ServiceAccount (RBAC with **no destructive verbs** — cannot delete a
  Deployment/PVC/namespace/node/Secret) + VPA Auto for CPU/RAM right-sizing + a CronJob that
  restarts transient crash-loops and force-deletes stuck pods, all circuit-broken, with a ConfigMap
  kill switch. Autonomy is authorized once by deploying it — the harness permission gate for Claude's
  own `kubectl` is never bypassed (`.claude/rules/safety.md`).
- `k8s/ai-operator/` is the **fully agentic** in-cluster variant: cooperating agents (coordinator,
  scanner, security, remediator, gitops) that think with a **local Ollama** (no cloud LLM),
  continuously scan every YAML (Git repo + live cluster), and fix findings — `create`/`update`/
  `patch` only, **never `delete`** (RBAC has no destructive verbs; Kyverno backstop; every change
  is backup → server-dry-run → policy → non-destructive-diff → apply → verify). Agents cooperate
  via `Finding`/`Remediation` CRDs; learnings persist in a SQLite+embeddings store. One `install.sh`
  bootstraps prereqs + Ollama + models + deploy on any distro. Start in `mode: observe`.
- **`hooks/*.sh`** + **`settings.json`** — permission model (allow/ask/deny) and hook scripts: a
  content-aware guard that blocks Bash commands from printing secret/credential files even when the
  binary used isn't the `Read` tool, an audit log for mutating infra commands, a Terraform auto-formatter,
  and a session-start environment-context banner.

Domain depth (DevOps, DevSecOps, SRE, Platform Engineering, Cloud Engineering, MLOps, AIOps, Data
Engineering, FinOps) lives in the matching skill/agent — apply the lens the repository's actual content
calls for, rather than assuming all of them apply to every task.

## Note on the root `CLAUDE.md`

Claude Code only auto-loads `CLAUDE.md` from the project root (plus user-global and nested-directory
locations) — it does not auto-discover a `CLAUDE.md` sitting inside `.claude/`. So a minimal stub stays at
the project root purely to satisfy that discovery mechanism; it contains nothing but an `@.claude/CLAUDE.md`
import pulling in this file. Don't add real content to the root stub — everything substantive belongs here
so the `.claude/` folder remains the single thing to copy into a new client repo.
