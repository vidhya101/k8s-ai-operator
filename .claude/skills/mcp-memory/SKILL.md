---
name: mcp-memory
description: Using the memory MCP server (knowledge graph) for cross-session context — targeted search patterns and entity naming, to avoid token-expensive full-graph dumps. Use when this project has the memory MCP server connected and you want to save or recall context across sessions.
---

# Memory MCP (Cross-Session Knowledge Graph)

Configured for this project via `.mcp.json` at the repo root (`@modelcontextprotocol/server-memory`, the
official Anthropic reference implementation). Requires a new session to pick up — a `.mcp.json` added
mid-session doesn't retroactively connect for the current one.

## Core Rule: Never Dump the Whole Graph

- `read_graph()` returns everything stored — can be 10k+ tokens for a graph with real history, blowing
  out context for no benefit most of the time.
- Always use targeted queries instead:

```text
search_nodes("terraform state backend migration")     # a few hundred tokens, precisely relevant
open_nodes(["Session-2026-07-27-terraform-devops-onboarding"])   # fetch a specific known entity
```

Reach for `read_graph()` only when you genuinely need a full inventory (e.g. auditing what's stored at
all) — never as the default way to "check memory" for a specific question.

## Entity Naming (keep it queryable)

```text
Session-YYYY-MM-DD-<project>-<feature>     e.g. Session-2026-07-27-terraform-devops-ec2-nginx
Solution-<problem>-<technology>              e.g. Solution-terraform-state-lock-recovery
Pattern-<architecture>-<context>             e.g. Pattern-gitops-argocd-multi-env
```

Consistent naming is what makes `search_nodes` actually find things later — an entity named generically
("Notes", "Update") is effectively unsearchable in six months.

## What Belongs in Memory vs. What Belongs in `.claude/`

- **`.claude/skills`, `.claude/agents`, `.claude/rules`** — durable, curated, hand-authored reference
  material meant to apply to *any* project on this stack. Not where session-specific findings belong.
- **Memory MCP** — session-specific, project-specific facts and solutions: "here's the root cause we
  found for the terraform state lock issue on 2026-07-27," "here's the exact fix for the EC2 nginx
  install script's port conflict." Things worth recalling later, that aren't general enough to be a skill.
- If something learned in a session turns out to be broadly true for *any* project on this stack (not just
  this one), it belongs in a skill file, not memory — memory is per-project/session recall, skills are the
  reusable, portable layer this whole `.claude/` setup is built around.

## Hybrid Reliability

Memory MCP is a nice-to-have, not a dependency — if it's not connected in a given session (not every
client/environment will have it configured), fall back to normal repo exploration
(`repository-discovery` skill, `/repo-map` command) rather than blocking on it.

## Common Pitfalls

- Calling `read_graph()` reflexively "just to see what's there" instead of a targeted search — the
  single biggest token-waste mistake with this server.
- Vague entity names that can't be found by a later `search_nodes` query.
- Storing something in memory that's actually a reusable, stack-wide pattern — it should be a skill
  instead, so it's available to any project this `.claude/` folder gets copied into, not just this one.
