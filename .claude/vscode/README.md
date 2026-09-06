# VS Code integration

You're already fully wired for VS Code — this doc explains the three tiers of
integration and how the team uses each.

## Current state on your machine (verified)

- ✅ `/Applications/Visual Studio Code.app` present
- ✅ `code` CLI on PATH (v1.130)
- ✅ Claude Code VS Code extension installed (`anthropic.claude-code`)
  - Multiple version dirs under `~/.vscode/extensions/` — VS Code loads the
    newest automatically; the older ones are stale and can be pruned
    (`find ~/.vscode/extensions -maxdepth 1 -name "anthropic.claude-code-2.1.22[01]-*"` to see them)

## Three integration tiers, biggest→smallest lift

### Tier 1 — Full IDE session: the Claude Code VS Code extension

You open VS Code → Claude Code sidebar → chat with Claude directly in the IDE
with access to your open files, selection, and git state. This is Anthropic's
first-class integration; nothing our `.claude/` folder needs to add — the
extension reads `.claude/agents/*.md` and `.claude/skills/*` from your workspace
root automatically.

**Use it when**: you want a full agentic session focused on ONE task, alongside
the code you're editing. Multi-file changes, refactors, feature work.

### Tier 2 — Any agent can open a file for you: the `code` CLI

Any agent's Bash tool can invoke `code <path>` to open a file/folder in your
running VS Code window. This is how a manager that produces a Terraform
module or a k8s manifest lands the file in front of you at the end.

**Pattern for a manager to use it** (already available — every manager has Bash):

```bash
code /path/to/produced-file.tf              # open a single file
code /path/to/module-dir                    # open a folder as a workspace
code --diff /a.tf /b.tf                     # diff two versions
code --wait -r /path/to/file.tf             # open + wait until closed
                                            # (use `--wait` when you want the
                                            # agent to block on your review)
```

**Use it when**: an agent needs to hand off a produced artifact to you for
manual review inside the IDE.

### Tier 3 — Live status shared with agents via `.claude/state/`

If you want an agent (running from your Claude Code terminal) to know what
file is currently open in VS Code, that requires the VS Code extension +
Claude Code's own IPC — already handled by the extension when you use tier 1.
Nothing more to build. If you want a headless agent (Munder-spawned worker) to
have the same knowledge, that would need a small VS Code extension of our own
that writes the current file path to `~/DevOpsHive/state/vscode-context.md`.
Not built — flag this as Phase D if you decide it's worth it.

## What our `.claude/` team already gives you inside VS Code

Because Claude Code auto-loads the workspace `.claude/` folder, EVERY VS Code
sidebar session you open in `~/claude-imp/claude/` (or any dir where our
`.claude/` is present via the symlink) has:

- All 52 agents visible via `/agent <name>` or the sub-agent picker
- All 6 rules always-loaded on every prompt
- 131 skills searchable via `/skill` (loaded on-demand by description match)
- 17 slash commands including `/task-start`, `/task-end`, `/task-log`,
  `/recall-context`, `/session-recap`
- Both MCP servers (`memory` + `code-review-graph`) reachable via tool calls

## Recommended VS Code workflow with our stack

1. **Open the repo in VS Code** — cd to the project + `code .`
2. **Open the Claude Code sidebar** — `⌘⇧C` (or the extension icon)
3. **Start with `/task-start <slug>`** — creates the task folder + audit trail
   before the agentic work starts
4. **Chat naturally** — Claude has the workspace context automatically
5. **On completion, `/task-end`** — closes the audit trail; the task folder
   remains in `~/DevOpsHive/Tasks/` as a permanent record
6. **Optional: open Obsidian** — see the task node appear in the graph

## Cleanup: prune stale extension versions

VS Code sometimes leaves older versions of an extension side-by-side with the
current one. Harmless but wastes disk. To see + prune:

```bash
ls ~/.vscode/extensions | grep anthropic.claude-code
# Keep the newest one; the older versions can go:
# (don't rm blindly — verify each dir first)
```

## Common pitfalls

- **VS Code sidebar shows "no workspace" when you launch Claude Code** — you
  ran `code` without a directory. Open a folder first (`⌘O`), then reopen the
  sidebar.
- **Slash commands not showing up** — the workspace has no `.claude/` folder
  present. Verify with `ls .claude/` in the integrated terminal.
- **The Munder agents don't see what's open in VS Code** — correct. Tier 3
  isn't built (would need our own tiny extension). Use tier 2 (`code <path>`
  to hand files back) instead.
