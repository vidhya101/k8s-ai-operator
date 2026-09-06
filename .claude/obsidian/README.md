# Obsidian memory graph — DevOpsHive

Auto-synced, always-on knowledge graph for the DevOps hive. Agents (and you)
read it to skip re-derivation — real token savings on every task that
overlaps with prior work.

## The path

**Vault location:** `~/DevOpsHive/`

Not `~/Documents/Obsidian Vault/DevOpsHive/`. macOS Sonoma+ blocks background
processes (launchd agents) from writing under `~/Documents/` without Full Disk
Access to the exact binary. Rather than fight TCC, the vault sits at a
non-protected path. You open it in Obsidian as a second vault (below).

## Open in Obsidian (one-time, 15 seconds)

1. Open Obsidian
2. Click the vault picker (bottom-left) → **Open another vault**
3. Click **Open folder as vault**
4. Pick `/Users/vidhyashankergoel/DevOpsHive/`
5. Trust the vault when prompted

Toggle graph view: `⌘⌥G` (⌘ + option + G). You'll see:
- All 51 team roles as nodes (Team/)
- 13 live hive agents as nodes (HiveMemory/) linked to their static roles
- The [[wikilink]] edges Munder's hive protocol writes when an agent references another

## What auto-syncs and when

`.claude/scripts/obsidian-sync.py` runs at login and every 5 minutes via
launchd. It's idempotent — files it hasn't changed are skipped, so the sync is
cheap even when nothing happened.

| Source | → Vault destination | Purpose |
|---|---|---|
| `~/claude-imp/hive/agents/*/memory.md` | `DevOpsHive/HiveMemory/<agent>.md` | Each live agent's accumulated working memory |
| `~/claude-imp/hive/agents/*/inbox/` (counts) | (front-matter of hive-memory notes) | How many messages the agent still owes work on |
| `~/claude-imp/claude/.claude/agents/*.md` | `DevOpsHive/Team/<agent>.md` | Static role definitions — the org chart |
| `~/.claude/projects/*/memory/*.md` | `DevOpsHive/CrossSession/*.md` | Long-lived cross-session facts |
| (auto-generated) | `DevOpsHive/README.md` | Index — the note Obsidian opens first |

## How agents use this to save tokens

Before an agent (say `terraform-manager`) re-derives context on a new task,
its FIRST tool call is:

```
Read /Users/vidhyashankergoel/DevOpsHive/HiveMemory/terraform-manager-<id>.md
```

That returns:
- Everything the agent recorded across previous tasks
- [[wikilinks]] to every peer it collaborated with
- Its current inbox/outbox counts

The cost is one file read (~2-8KB of tokens) vs. potentially minutes of
re-derivation from scratch. This is what "protecting tokens" means in practice.

## LaunchAgents installed

Two launchd jobs run automatically on login:

| Label | What it does | Restart? |
|---|---|---|
| `com.devopshive.memory-sync` | `obsidian-sync.py` every 5 min | on interval |
| `com.devopshive.gallery` | Hire gallery HTTP on `127.0.0.1:9977` | on crash (KeepAlive) |

**Not auto-started**: Munder itself. Electron + Vite + 5 processes is too heavy
for the login path. If you want Munder to open on login, add it via System
Settings → General → Login Items.

Manage the agents:

```bash
# Trigger a sync now (don't wait 5 min)
launchctl start com.devopshive.memory-sync

# Check status
launchctl list | grep devopshive

# Watch sync log live
tail -f ~/.local/state/devops-hive-sync.log

# Full reinstall (safe, idempotent)
.claude/scripts/install-launch-agents.sh

# Uninstall (removes plists + unloads)
.claude/scripts/install-launch-agents.sh uninstall
```

## Alternate: keep vault under ~/Documents

If you insist on `~/Documents/Obsidian Vault/DevOpsHive/`:

1. Grant `/usr/bin/python3` Full Disk Access:
   System Settings → Privacy & Security → Full Disk Access → **+** → navigate to `/usr/bin/python3` → toggle on
2. Change `VAULT_ROOT` in `.claude/scripts/obsidian-sync.py` back to `HOME / "Documents" / "Obsidian Vault"`
3. Set `DEVOPS_HIVE = VAULT_ROOT / "DevOpsHive"`
4. Reinstall the launch agents: `.claude/scripts/install-launch-agents.sh`

Note: macOS updates can reset Full Disk Access grants — you may have to re-authorize after
each major OS release. The default (`~/DevOpsHive`) doesn't have this problem.

## What lives in the vault

```
~/DevOpsHive/
├── README.md              ← auto-generated index (Obsidian opens this first)
├── HiveMemory/            ← 13 live-agent memory notes (rewritten every 5 min)
├── Team/                  ← 51 static role notes (rewritten when an agent .md changes)
├── CrossSession/          ← .claude/projects/*/memory/*.md carried across
└── Tasks/                 ← per-task notes (populated by the task-scaffolding hook — Phase 2)
```

Every note has YAML front matter Obsidian's Dataview plugin can query
(if installed): `type`, `agent`, `character`, `tags`, `inbox_pending`,
`outbox_pending`, `last_synced`.

## Common Pitfalls

- **Vault appears empty** — the sync hasn't run yet. `launchctl start com.devopshive.memory-sync` triggers immediately, or just wait for the next 5-minute tick.
- **Old data at `~/Documents/Obsidian Vault/DevOpsHive/`** — that was the pre-fix path; safe to delete (`rm -rf`). Current data is at `~/DevOpsHive/`.
- **Symlinks confuse Obsidian's graph** — this vault uses real files (no symlinks), so graph view is accurate.
- **Live agent notes revert when you edit them in Obsidian** — that's expected. `HiveMemory/*.md` and `Team/*.md` are RE-generated on every sync. Edit the SOURCE (`~/claude-imp/hive/agents/<id>/memory.md` or `~/claude-imp/claude/.claude/agents/<name>.md`) instead — your edit persists across syncs.
- **`~/.local/state/devops-hive-sync.log` grows without bound** — currently unbounded. If it exceeds ~10MB, truncate with `: > ~/.local/state/devops-hive-sync.log`.
