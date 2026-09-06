# DevOps Hive · VS Code Context Publisher

A tiny local VS Code extension that publishes your current IDE state to a file
any agent can Read.

## What it publishes

Every ~500ms (debounced) when you switch files, change selection, open/close a
tab, or add/remove a workspace folder, this extension rewrites
`~/DevOpsHive/state/vscode-context.md` with:

- **`active_file`** — path of the file in the active editor
- **`active_language`** + **`active_dirty`** — languageId + unsaved-changes flag
- **`open_files_count`** and a list of the first 40 open tabs
- **`workspace_folders`** — root paths of the workspace
- **`selection`** — start/end line/col + a truncated preview of selected text
  (capped at 2 KB; disable via `devopsHive.includeSelection: false` if you're
  editing sensitive code you don't want agents to see)
- **`updated_at`** — ISO timestamp

Full YAML frontmatter + a markdown body — Obsidian dataview + our
`obsidian-sync.py` both understand it, and Claude/Munder agents can Read it
like any other note.

## Install (30 seconds)

```bash
.claude/vscode/extension/install.sh
```

Then in VS Code: `⌘⇧P` → **Developer: Reload Window**.

Verify it loaded:

```bash
code --list-extensions | grep devops-hive-vscode-context
```

Trigger a manual publish once + inspect the file:

```
⌘⇧P → "DevOps Hive: Publish Context Now"
cat ~/DevOpsHive/state/vscode-context.md | head -30
```

## How agents use it

Any agent (Claude Code session, Munder-spawned peer, Obsidian graph reader):

```
Read /Users/<you>/DevOpsHive/state/vscode-context.md
```

Cost: one file read (~1-3 KB). Return: what you're looking at, right now.

A manager who's about to propose a change can start with:

> Before I plan anything, let me check what file you're actually editing —

then Read the context file, and the resulting plan is grounded in the file
that's in front of you, not the file you mentioned three messages ago.

## Settings (VS Code → Preferences → Settings → search "DevOps Hive")

| Setting | Default | What it does |
|---|---|---|
| `devopsHive.contextPath` | `~/DevOpsHive/state/vscode-context.md` | Where to write |
| `devopsHive.debounceMs` | `500` | Coalesce rapid changes |
| `devopsHive.includeSelection` | `true` | Include selection text (turn off for sensitive editing) |

## Zero external deps

The extension imports only `vscode` (built-in) and Node built-ins (`fs`,
`path`, `os`). No `npm install` step; no `node_modules/`; no security surface
beyond what VS Code itself already grants any extension.

## Uninstall

```bash
.claude/vscode/extension/install.sh uninstall
# then in VS Code: ⌘⇧P → "Developer: Reload Window"
```

The extension folder is removed from `~/.vscode/extensions/`; the context file
itself stays (harmless if nothing writes to it).

## Failure modes (all fail-silent)

- **Context dir can't be created** — extension logs to VS Code's Output panel
  ("DevOps Hive") but doesn't crash the IDE
- **File write errors** — same: logged, not thrown; next successful write
  overwrites cleanly (writes are atomic via tmp + rename)
- **VS Code closed** — the file becomes stale (`updated_at` frozen); agents
  reading it should treat `updated_at` older than a few minutes as "no live
  context available"

## Common Pitfalls

- **File never appears** — extension didn't load. Check
  `code --list-extensions | grep devops-hive` and reload the window.
- **File updates but agents don't seem to read it** — Claude Code sessions
  need to explicitly `Read` the path; it's not auto-injected. Add a line to
  your prompt: "Read `~/DevOpsHive/state/vscode-context.md` first."
- **Selection text has secrets you didn't want shared** — toggle
  `devopsHive.includeSelection: false` when editing sensitive code, or
  scope-uninstall the extension for that workspace.
