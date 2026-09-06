# Claude Code Setup

This `.claude/` directory is a **fully self-contained, reusable, domain-agnostic Claude Code
configuration**. It is not scoped to this repository's current EC2/nginx content — it is built to be
copied as one folder into any client repo, on any tech stack, and work correctly on day one. Nothing in
here hardcodes a cloud provider, Kubernetes distro, or tech stack; scope is detected at runtime per
[CLAUDE.md](CLAUDE.md) Section 1 and Section 2.

**New to this setup, or starting a new assignment?** Read [GETTING_STARTED.md](GETTING_STARTED.md) first —
it covers copying this to a new client, day-one workflow, and a command cheat sheet. This file (README.md)
is the architecture reference; GETTING_STARTED.md is the practical how-to-use-it guide.

## Why `CLAUDE.md` lives in here, and a stub sits at the project root

Claude Code only auto-loads `CLAUDE.md` from the project root (plus a user-global copy and nested
per-directory copies) — it does not look inside `.claude/` for one. So the *real* file is
[CLAUDE.md](CLAUDE.md) right here, and the project root carries only a one-line stub that
`@`-imports it. That keeps everything substantive in this one folder — copy `.claude/` into a new repo,
drop the same three-line stub at that repo's root, and the whole system works.

## How the pieces fit together

```text
.claude/CLAUDE.md      → always loaded (via the root stub). Core behavior + onboarding workflow +
                          pointers into this system.
.claude/rules/*.md      → always loaded (imported from CLAUDE.md via @rules/*.md).
                          Non-negotiable, tool-agnostic policy: secrets, safety, environment handling, git.
.claude/skills/*/        → loaded ON DEMAND, matched by description against the current task.
                          One skill = one tool/domain's how-to (Terraform, EKS, Trivy, SRE, MLflow, ...).
                          Keeps context lean: 67 skills exist, only the relevant 1-3 ever load per task.
.claude/agents/*.md      → specialized reviewer/operator personas, invoked explicitly or auto-matched
                          by description. Each is read-only/advisory by default (no Write/Edit) —
                          agents diagnose and recommend, the main session makes the actual changes.
.claude/commands/*.md    → slash commands (/onboard, /iac-review, /db-review, /cost-review, ...) that
                          kick off a specific agent + skill combination for a common workflow.
.claude/hooks/*.sh        → hook scripts, invoked from settings.json: a content-aware secret-read guard,
                          a mutating-command audit log, a Terraform auto-formatter, and a session-start
                          environment banner.
.claude/settings.json     → permissions (allow/ask/deny) wiring the hooks above in, plus the read-only /
                          ask / never-without-confirmation command lists.
```

## Why skills instead of one giant CLAUDE.md

An earlier version of this setup put every tool's guidance (Terraform, Ansible, Kubernetes distros,
observability stack, scanners...) directly into `CLAUDE.md`. That loads on every single message
regardless of relevance, which wastes context and dilutes the signal. Skills are the fix: each is a
self-contained `SKILL.md` with a `description` used for on-demand matching, so a Terraform-only task
never pulls in Datadog or OpenShift guidance.

## What's covered

- **IaC / config management**: terraform (+state/security/best-practices), ansible, kustomize, helm
- **Containers**: docker (+security/multi-stage)
- **Kubernetes**: kubernetes (core) + eks/aks/gke/kubeadm/openshift, argocd, gitops
- **CI/CD**: github-actions, jenkins, git, github, cicd-pipeline-design
- **Clouds**: aws, azure, gcp
- **Host/network/scripting**: linux, networking, bash-scripting, python-automation, yaml-config,
  cron-scheduling
- **Observability**: prometheus, grafana, loki, mimir, datadog, opentelemetry, node-exporter, promtail,
  dynatrace
- **Security scanning**: trivy, sonarqube, checkov, snyk, vault
- **Artifacts**: nexus, ghcr
- **MLOps platform**: kubeflow, kserve, mlflow, airflow
- **Databases**: mysql, postgresql, mongodb, oracle-database, database-operations
- **Disciplines**: sre, devsecops, mlops, aiops, platform-engineering, code-review, testing,
  architecture-review, production-debugging, repository-discovery

## Memory MCP (cross-session recall)

`.mcp.json` at the repo root registers the official `@modelcontextprotocol/server-memory` server. It
requires a fresh session to connect (project-scoped MCP servers load at session start, not mid-session).
See the `mcp-memory` skill for usage — the short version: always use `search_nodes()`, never `read_graph()`
by default, it dumps the entire graph and burns context for no reason.

## Recommended MCP servers to connect for this setup

None of the above requires an MCP server — every skill has a CLI/API fallback. But if the client
environment has these connected, the matching agent should prefer them over shelling out (structured
data, no local credentials/binaries needed):

- **GitHub** — PR/issue/Actions-run inspection for `github-actions-reviewer`, `terraform-reviewer`
  (change history), `security-auditor` (code search).
- **Grafana / Prometheus / Loki** (often bundled behind one gateway server) — live metric/log/dashboard
  queries for `observability-engineer` and `production-incident-commander`, instead of shelling out to
  `promtool`/`logcli`.
- **Datadog** — same role as above when Datadog is the observability platform of record.
- **PagerDuty / Opsgenie** — on-call schedule and incident lookups for `production-incident-commander`.
- **Slack** — posting the structured incident/postmortem output `production-incident-commander` produces
  directly into an incident channel.

This list is deliberately not wired into any agent's `tools:` frontmatter — a specific MCP server's name
is an artifact of one environment's connector setup, not something portable across every client. Instead,
the relevant agents note in their own body to check for and prefer connected MCP tools when present. Add a
server with `claude mcp add` (or the client's connector UI) per project; nothing here needs to change to
pick it up.

## Maintenance tooling

- `.claude/spec/authoring-guide.md` — the convention every skill follows; read before adding one.
- `.claude/spec/skill-template.md` — copy-paste starting point for a new skill (kept outside
  `.claude/skills/` on purpose, so a template with a placeholder name/description is never itself scanned
  as a real, activatable skill).
- `.claude/scripts/validate-skills.sh` — run after adding/editing a skill; checks frontmatter validity,
  naming consistency, unclosed code fences, duplicate names, leftover template placeholders, and obvious
  hardcoded-secret patterns. No dependencies (pure bash), unlike a PyYAML-based validator.
- `.claude/scripts/generate-skills-index.py` — regenerates `.claude/docs/SKILLS_INDEX.md` (every skill,
  alphabetical, with its actual description) from the real frontmatter, so the index can't go stale from
  manual editing.
- `.github/workflows/validate.yml` — runs the validator in CI if this is pushed to GitHub.

## Adding to this for a new client

- New cloud/tool the client uses but isn't covered → add `skills/<tool>/SKILL.md` following the existing
  skill format (frontmatter `name` + `description`, then Core Principles + a concrete checklist).
- New reviewer persona needed → add `agents/<role>.md` following the existing agent format.
- A policy that must always apply for this client (e.g. a stricter change-freeze window) → add or edit a
  file under `rules/` and reference it from `CLAUDE.md`.
- Delete whatever doesn't apply to the client's stack. Nothing here is load-bearing for anything else —
  skills and agents are independent files.
