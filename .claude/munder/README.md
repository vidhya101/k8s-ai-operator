# Munder-Difflin integration

How to run **your** DevOps team inside [Munder-Difflin](https://github.com/chaitanyagiri/munder-difflin) —
the Electron office-floor harness. Munder handles the visualization, cross-agent
messaging (file-based hive), cost telemetry, and kanban; your `.claude/` folder
supplies the roster, skills, rules, sub-agents, and MCP wiring.

## What you get

- **The floor**: Michael (orchestrator) + 12 managers as characters at their desks
- **Live activity**: watch envelopes fly between agents when work is handed off
- **Terminal per agent**: click a character to open its `claude` session
- **Kanban + memory + cost tabs**: all free from Munder's built-in panels
- **Your discipline preserved**: each agent runs `claude` with your `.claude/`
  loaded — 51 sub-agents, 5 feedback loops, sandbox-verifier, memory MCP,
  everything you built. Munder is the shell; `.claude/` is the substance.

## Prereqs (one-time)

1. Munder-Difflin installed and launched at least once (see
   [its README](https://github.com/chaitanyagiri/munder-difflin)):
   ```bash
   git clone https://github.com/chaitanyagiri/munder-difflin.git
   cd munder-difflin
   npm install
   npm run dev
   ```
2. `python3` on your PATH (macOS system Python is fine; no pip installs needed —
   this uses only the standard library).
3. `claude` CLI on your PATH — the same Claude Code binary Munder wraps.

## Onboard your team (per Munder install)

From the root of `.claude/`'s parent repo:

```bash
# 1) Regenerate the 12 hire manifests (idempotent; safe to re-run any time)
python3 .claude/scripts/generate-munder-hires.py

# 2) Serve them as a local gallery — leave this running while you import
python3 .claude/scripts/serve-munder-hires.py
```

Open `http://127.0.0.1:9977/` in your browser — you'll see a table of your
12 managers with "import →" links. Each link opens the `munderdifflin://` deep
link, which pre-fills Munder's Add-Agent modal for that manager. Review the
pre-filled fields, then click **Spawn**.

**Cost-conscious order of operations (recommended):**

1. Michael (orchestrator) — already there, auto-provisioned by Munder
2. **cloud-manager** — you'll route the most work through this one first
3. **terraform-manager** + **kubernetes-manager** — the two workhorses
4. Everything else on demand — spawn only when Michael actually delegates to that domain

Each idle `claude` session burns tokens continuously. Only-Michael + 2-3 managers
is a comfortable steady state for the Anthropic subscription tier.

## Where each spawned agent's `.claude/` comes from

Munder's Add-Agent modal has a `cwd` field. Set it to the repo where your
`.claude/` lives (the same repo containing this file). Every `claude` process
spawned by Munder starts in that dir, so it reads:

- `.claude/agents/*.md` — all 51 sub-agents visible to the manager
- `.claude/skills/*/SKILL.md` — on-demand domain skills
- `.claude/rules/*.md` — always-loaded policy
- `.claude/commands/*.md` — slash commands (`/recall-context`, `/session-recap`, etc.)
- `.claude/settings.json` — permission gates and hook wiring
- `.mcp.json` — memory + code-review MCP servers

Nothing in `.claude/` needs to be duplicated per agent. All 12 point at the
same repo dir.

## Character assignment

Munder ships The Office cast (`OfficeCharacterName` — see
`src/renderer/src/scene/office/cast.ts`). The hire manifests we generate assign:

| Manager | Character | Rationale |
| ------- | --------- | --------- |
| orchestrator (auto) | michael | Munder's default GOD assignment |
| cloud-manager | jim | Big-picture generalist |
| observability-manager | pam | Watches everything, notices patterns |
| sre-manager | dwight | Rules, discipline, paranoia about failures |
| cicd-manager | oscar | Sequential accountant → pipeline gatekeeper |
| terraform-manager | angela | Strict, no exceptions → IaC state |
| linux-manager | stanley | Steady, no drama → systemd |
| docker-manager | kevin | Loves boxes; containers = boxes |
| github-manager | andy | Loud reviewer, always announcing merges |
| ansible-manager | phyllis | Playbooks matriarch |
| aiops-manager | kelly | Chatty pattern-noticer |
| mlops-manager | ryan | The temp → experimental iteration |
| kubernetes-manager | creed | Chaos, unpredictable → k8s ops |

(toby, meredith unassigned — free slots for future additions.)

## Fallback tier (Claude → Codex → Ollama)

Alongside the 12 claude-primary hires, `generate-fallback-hires.py` produces
**12 codex-fallback hires** (`<manager>-codex.json`). When Claude is throttled
or the task is a code-writing chore that doesn't need the top tier, Michael can
spawn a codex-backed peer for that domain and route work there instead.

**How the chain works:** see `.claude/rules/provider-routing.md` — the
always-loaded rule that tells every agent when to swap tiers.

**Setup readiness check:**

```bash
.claude/scripts/fallback-setup.sh
```

Reports whether each tier is available:
- Tier 1: `claude` CLI on PATH (required)
- Tier 2: `codex` CLI on PATH + `OPENAI_API_KEY` set
- Tier 3: Ollama service reachable at `localhost:11434`

Missing tiers are silently skipped — the chain uses whatever remains.

**Ollama** is intentionally NOT a hire manifest. Munder's hire spec allows only
`claude | antigravity | codex` providers; the `custom` provider (needed for
Ollama) also can't be a full hive citizen (hookless — mailbox routing bounces).
Spawn Ollama peers manually via **Add Agent → provider: custom** with the
`ollama` binary command. Or use the Ollama MCP (see below) so Claude/Codex
agents can *call* Ollama for cheap subtasks without spawning a dedicated peer.

**Ollama-MCP** (optional, high leverage): install with
```bash
claude mcp add ollama 'npx -y @rawveg/ollama-mcp' \
  -e OLLAMA_HOST=http://localhost:11434
```
Then any Claude/Codex agent can delegate cheap work (log summaries, doc drafts,
obvious-answer questions) to a local model without spending cloud tokens.

## Regenerating after `.claude/agents/` changes

The generator reads each manager's frontmatter `description:` field and rebuilds
the manifest. Re-run whenever you rename, add, or reword a manager:

```bash
python3 .claude/scripts/generate-munder-hires.py
```

`validate-skills.sh` (via its auto-regeneration hook) runs this alongside the
team-dashboard generator, so if you're already validating on agent changes,
the hires stay in sync automatically.

## Risks & mitigations (read this once before spawning)

| Risk | Mitigation |
| ---- | ---------- |
| 13 concurrent `claude` sessions burn tokens fast | Only-Michael steady state; spawn managers on-demand. Every manifest has `tokenCap: 500_000` as a runaway cap. |
| 6-10 GB RAM for 13 processes | Fine on 16GB+ Mac. On 8GB, keep to 3-4 spawned. |
| Multiple `claude` in the same repo dir may conflict on session state | Flip `isolate: true` per manifest before import → Munder puts each in its own git worktree. |
| Munder is v0.4.x prototype — schema changes possible | Manifests validate at import; re-generate if a future release rejects them. |
| Hires can't declare skills/MCPs (security posture) | Not a problem — everything loads from the cwd's `.claude/`. |

## Files in this folder

| File | What it is |
| ---- | ---------- |
| `README.md` (this file) | Onboarding + risks |
| `hires/<manager>.json` | 12 hire manifests (regenerated by the script) |
| `hires/gallery-index.json` | Index served by the local gallery |

## Why not fork Munder?

The Munder author (Chaitanya Giri) publishes a blog post in-repo,
`blog/src/posts/claude-code-subagents-vs-multi-agent-harness.md`, that answers
this exact question directly:

> A harness-managed agent can absolutely use subagents for its own work. The
> harness operates one level up, at the team scale; subagents operate one level
> down, at the task scale.

Our 12 managers are Munder-level. Our 39 sub-agents (designer, critic,
code-writers, reviewers, tester, sandbox-verifier, specialists) are sub-agent
level, invoked internally by each manager via the Task tool. This composition
is exactly what both projects were designed for — no fork required.
