# Getting Started — Beginner's Guide

**You just inherited this `.claude/` folder. What do you do?**

This is the day-one guide. Written so you can actually use the setup within 15 minutes of
reading it, without having read anything else in `.claude/`. If you're stuck, section **10** is
troubleshooting.

---

## 1. What you have (in one paragraph)

`.claude/` is a folder that turns Claude Code into a team of **51 named AI specialists** for
DevOps / SRE / Platform / Cloud work — Kubernetes, Terraform, Ansible, cloud (AWS/Azure/GCP/OCI),
CI/CD, observability, security, MLOps. You ask Claude one thing in plain English; Claude
automatically routes to the right specialist(s) using the rules baked into this folder, gets
answers, and comes back. No slash commands required for most work — just talk normally.

---

## 2. First-time setup (5 minutes, once per machine)

### Step 1: Get your tokens set up (once)

```bash
.claude/scripts/setup-tokens.sh
```

This copies a template into `~/.config/devops-tokens.env` and adds a `source` line to your shell
profile. Then edit that file and paste in your real tokens:

```bash
${EDITOR:-nano} ~/.config/devops-tokens.env
```

You need at minimum: `ANTHROPIC_API_KEY`. Everything else (GitHub, Docker, AWS, cloud tokens)
is optional — fill in only what you use. Reload your shell after editing:

```bash
source ~/.config/devops-tokens.env
```

### Step 2: See the team you just inherited (30 seconds)

```bash
open .claude/dashboard/team-dashboard.html
```

(Linux: `xdg-open`. Windows: `start`.) One HTML page shows all 51 agents grouped by role. Click
any agent to see what they do and who they collaborate with. This is your reference — bookmark
it or keep it open in a tab.

### Step 3 (optional but recommended): Build the sandbox testing image

**Prerequisite: Docker must be running.** On macOS that means Docker Desktop, OrbStack, or
Colima is started. Check first:

```bash
docker info | grep -i "server version"    # prints a version if daemon is up; errors if not
```

If it errors, start your Docker runtime:

```bash
open -a Docker                             # Docker Desktop
# OR
colima start                                # if using Colima
# OR
open -a OrbStack                            # if using OrbStack
```

Wait ~30 seconds for the whale/orbstack icon to stop animating in your menu bar, then:

```bash
docker build -t devops-sandbox:latest -f .claude/sandbox/Dockerfile .claude/sandbox/
```

~10 minutes on first build. Gives agents a container preloaded with Terraform, kubectl, Helm,
Ansible, Docker CLI, Trivy, Checkov, Java/Python/Node/Go — so when they say "let me verify this
in a sandbox," they actually have somewhere to run it.

### Step 4: Confirm it's healthy

```bash
.claude/scripts/validate-skills.sh
```

Should end with `All checks passed (131 skills).` and auto-regenerate the dashboard.

**That's the whole setup.** Every future session starts with `claude` in a project directory
that has `CLAUDE.md` at its root — everything else loads automatically.

---

## 3. Your first day: **just ask normally**

The single most important thing: **you don't need to know any of the 51 agents' names.** Claude
reads their descriptions and picks the right one automatically. Talk like you'd talk to a senior
teammate.

**Examples that "just work":**

- *"Review this Dockerfile before I push"* → auto-invokes `docker-manager` → `docker-reviewer`
- *"Our EKS pod is CrashLoopBackOff, help me debug"* → `kubernetes-manager` → `kubernetes-debugger`
- *"Design a Terraform module for a new VPC in us-east-1"* → `terraform-manager` → `designer` → `critic` → back to you
- *"Our AWS bill spiked 40% this quarter"* → `cloud-manager` → `principal-finops-engineer`
- *"Write a runbook for database failover"* → `technical-writer`

You'll see Claude say "I'll delegate to X" or the specialist's response format. That's the team
working.

**When to skip a manager and call an agent by name** (rare, but useful): if you already know
exactly which specialist you want, mention them. *"Have `security-auditor` triage these Trivy
findings by real exploitability"* — Claude jumps straight there.

---

## 4. The three commands worth memorizing

Type `/` in Claude Code to see the full menu (17 commands total). These three are the ones a
beginner uses most:

| Command | When | What it does |
|---|---|---|
| `/onboard` | First time in a new project | Detects the stack, installs deps, reads the codebase, summarizes what it found. Run this before asking Claude to change anything in a repo it's never seen. |
| `/recall-context` | Start of a session that continues prior work | Queries memory MCP for prior sessions on this project — surfaces what you learned last time so you don't re-derive it. |
| `/session-recap` | End of a session with meaningful work | Writes structured findings back to memory MCP. The Stop hook nudges you to run this if you had mutating activity. |

Ignore the other 14 commands until you need them. When you need them, `/` shows the list with
descriptions.

---

## 5. Choose who to talk to — the routing decision

If you're not sure whether to invoke by name or just describe the task:

- **Single-domain task** → describe it plainly, Claude auto-picks the right manager. No name needed.
- **Multi-domain task** (spans 2+ domains — "design + provision + deploy + monitor") → describe it plainly, Claude engages the `orchestrator` which routes across managers.
- **You know EXACTLY which specialist you want** → name them (`"have terraform-reviewer look at this plan"`).
- **Not sure who owns this?** → open the dashboard, search for a keyword. It'll show you.

**The one anti-pattern to avoid**: don't try to invoke a sub-agent (`designer`, `critic`,
`code-writer-python`, etc.) directly. They're meant to be invoked BY a manager as part of a
delegation chain. If you say "have `designer` write me a K8s manifest," you skip the domain
expertise `kubernetes-manager` would have brought.

---

## 6. Walked example: "Build me a new microservice"

You say:
> "I need a rate-limiter microservice — designed, containerized, deployed on our EKS cluster, with metrics wired up."

What happens under the hood (no action required from you):

1. **`orchestrator`** decomposes into 4 steps
2. **`system-designer`** proposes the service topology (API shape, data flow, dependencies) → **`critic`** objects on one point → designer revises → accept
3. **`code-writer-go`** (or -python, based on your existing code) writes the service → 3 reviewers run in parallel (`code-reviewer` + `bug-hunter` + `code-simplifier` + `security-auditor`) → any findings routed back for one revision round
4. **`docker-manager`** produces the multi-stage Dockerfile → **`docker-reviewer`** signs off
5. **`terraform-manager`** writes the IaC for anything new needed → **`terraform-reviewer`** + **`security-auditor`** review
6. **`kubernetes-manager`** produces Deployment / Service / Ingress / HPA manifests → **`kubernetes-debugger`** verifies against `kubectl apply --dry-run=server`
7. **`observability-manager`** writes the Prometheus scrape config + Grafana dashboard JSON
8. **`sre-manager`** proposes SLIs / SLOs / alert rules for the new service
9. **`sandbox-verifier`** applies everything to a scratch namespace, confirms desired = actual
10. Final synthesis back to you

You see one coherent output: what to deploy, in what order, with the exact commands.

---

## 7. Walked example: "This is failing" (simple, single-domain)

You say:
> "kubectl get pods shows my api-server pod in CrashLoopBackOff with OOMKilled"

What happens:

1. Claude sees "kubernetes" + "crash" → `kubernetes-manager` auto-invoked
2. `kubernetes-manager` delegates to `kubernetes-debugger` for structured triage
3. `kubernetes-debugger` walks you through: check `describe` for events, `logs --previous` for the crash reason, memory limits vs. actual usage
4. Suggests a fix (raise memory limits, or find the leak)
5. Comes back with concrete next steps

You do NOT need to say "invoke kubernetes-manager and kubernetes-debugger." Just describe what
you see.

---

## 8. Walked example: "Review this PR before I merge"

You paste a PR link or say:
> "Review the changes in this branch before I merge"

What happens:

1. `code-reviewer` runs the language-agnostic quality pass
2. `bug-hunter` looks for edge cases and hostile inputs the code doesn't handle
3. `code-simplifier` finds anywhere the same behavior could be less code
4. `security-auditor` scans for creds, injection, auth gaps
5. If YAML/K8s manifests changed → `yaml-config-reviewer` runs too
6. If code exposes ports → `port-security-auditor` runs too
7. Findings arrive as a ranked list, blocking vs. optional distinguished, each with a specific fix

You get one consolidated review. Reviewers can disagree — the manager arbitrates and surfaces
the disagreement if it's load-bearing.

---

## 9. Health check — is my setup working?

Run these three anytime you're unsure something's wired right:

```bash
.claude/scripts/validate-skills.sh    # 131 skills valid, dashboard regenerates
```

Then in a Claude session, type:
```
what skills do you have available for terraform work?
```

Claude should list `terraform`, `terraform-state`, `terraform-security`, `terraform-best-practices`,
`terragrunt`, and offer to invoke `terraform-manager` or `terraform-reviewer`. If it says "I don't
have any skills" or ignores the domain — the folder didn't load. Check that `CLAUDE.md` at the
repo root has `@.claude/CLAUDE.md` in it.

---

## 10. Common gotchas for beginners

- **"How do I invoke agent X?"** — most of the time, don't. Describe the task; Claude picks the
  right agent from the description in each agent's frontmatter. Only name agents explicitly when
  you want to override the auto-routing.
- **"I copied `.claude/` to a new project but Claude isn't loading it"** — you also need a root
  `CLAUDE.md` file in that project. It's a 3-line stub that does `@.claude/CLAUDE.md`. Copy the
  one from this project too.
- **"Memory doesn't recall anything"** — memory MCP is **per-machine**, not per-repo. If you set
  it up on your laptop, findings persist across every project on that laptop, but a colleague on
  a different laptop won't see them. Also: memory needs a fresh session to load — restart Claude
  after adding the MCP server.
- **"Agents are trying to write files but nothing appears"** — this happens if a `code-writer-*`
  agent is missing `Write, Edit` in its tools frontmatter. All 5 code-writers here have it,
  fixed already, but if you add a new coder agent from scratch, include those tools.
- **"Where do I put my API tokens?"** — `~/.config/devops-tokens.env`, NOT in `.claude/`. The
  setup script bootstraps this. `.claude/` is designed to be copyable across client projects; if
  tokens were in there, one bad copy leaks everything.
- **"`docker build` fails with `Cannot connect to the Docker daemon` / `docker.sock: no such file or directory`"** — Docker isn't running. On macOS: `open -a Docker` (Docker Desktop) or `colima start` (Colima) or `open -a OrbStack`. Wait for it to be fully up, then retry the build. Check with `docker info` first.
- **"Do I need Ollama for this to work?"** — no. Everything runs on Claude by default. Ollama
  reference exists for future workflows where you want a local model for a specific specialist
  (see `.claude/config/environment.md`), but that's optional.
- **"There's a `fleet-impl` spec at `~/claude-imp/*.md` — is that part of this?"** — no, that's
  a separate 24/7-daemon-fleet spec (a different project you're implementing). The `.claude/`
  folder at `~/claude-imp/claude/.claude/` is what we use in Claude Code sessions. Two different
  things that happen to be co-located.

---

## 11. When the team gets things wrong

- **A finding you disagree with**: tell Claude "I disagree with that finding because X." The
  manager arbitrates — designer/critic have a bounded 2-round dispute; if unresolved, it escalates
  back to you. You always have final say.
- **An agent goes on too long**: interrupt (Escape). Ask for a shorter answer or a specific
  focus. Agents inherit brevity from how you frame the ask.
- **The wrong agent got picked**: name the right one explicitly. If the auto-routing is consistently
  wrong for a class of task, edit the target agent's `description:` frontmatter to trigger better
  on that pattern.

---

## 12. As you get comfortable, read these deeper docs

- **[`.claude/agents/TEAM_ROSTER.md`](agents/TEAM_ROSTER.md)** — the full org chart with delegation chains and the 5 explicit feedback loops
- **[`.claude/config/environment.md`](config/environment.md)** — where all credentials/tokens/endpoints are documented (references, never values)
- **[`.claude/README.md`](README.md)** — architecture overview: why skills vs. rules vs. agents vs. commands vs. hooks
- **[`.claude/spec/authoring-guide.md`](spec/authoring-guide.md)** — how to write a new skill, agent, or command that fits the existing conventions
- **[`.claude/sandbox/README.md`](sandbox/README.md)** — the regression-testing container image
- **[`.claude/dashboard/README.md`](dashboard/README.md)** — the team visualization

---

## 13. The one-line summary

**Type `claude` in a project. Describe what you need in plain English. The team routes itself.
Restart with `/recall-context` if continuing prior work; end with `/session-recap` before quitting.**

Everything else is optional depth for when you need it.
