---
description: Pull relevant prior-session context from memory MCP for the current project/task — run at start of any session that continues prior work.
argument-hint: "[optional: specific topic to search, e.g. 'terraform state migration']"
---

Query memory MCP for prior findings relevant to the current session's work: $ARGUMENTS

## What to do

1. **Detect the current project** — cwd basename, git remote if present, closest CLAUDE.md's
   project name. Use this as the primary search term.

2. **Run targeted `mcp__memory__search_nodes`** — never `read_graph` (see `mcp-memory` skill's
   token-cost warning). Search patterns to try, in order:
   - `search_nodes("<project-name>")` — pulls Session-*-<project>-*, Solution-*-<project>-*,
     Decision-*-<project> entries
   - `search_nodes("<technology-in-scope>")` — e.g. "terraform", "kubernetes", "argocd" — if the
     current task obviously involves one
   - `search_nodes("<user-provided-topic>")` — if `$ARGUMENTS` was passed
   - Skip if the first two return nothing relevant

3. **Structure the recall output** as:

   ```
   ## Memory recall for <project>

   ### Recent sessions on this project
   <list Session-* entries with dates, most recent first, one-line each>

   ### Relevant solutions / decisions
   <list Solution-* / Decision-* entries, one-line each, with the specific insight not just the title>

   ### Patterns worth reusing
   <list Pattern-* entries the current task might reuse>

   ### Nothing found?
   <if search returned no relevant results, say "memory recall: no prior context found for this
   project — this appears to be a fresh engagement" — do NOT invent context>
   ```

4. **Do NOT paste the raw memory nodes** — the point is to surface actionable prior context,
   not to burn tokens re-reading everything. Extract the specific insight ("last session found
   that X approach failed because Y — try Z instead"), cite the entity name, move on.

5. If the current session is clearly starting a NEW piece of work with no prior relevance, say so
   plainly ("memory recall: none relevant — proceeding fresh") and continue. Don't force-fit stale
   context onto new work.

## When to invoke

- Manually at start of a session that continues prior work (`/recall-context`)
- Automatically via the SessionStart hook — the hook prints a reminder to invoke this if the
  session's cwd matches a project that has prior Session-* entries
- Whenever `orchestrator` starts a multi-step task and prior sessions might inform the plan

## Cross-reference

- `.claude/rules/memory-usage.md` — the always-loaded rule requiring memory reads at start of
  non-trivial work
- `mcp-memory` skill — search_nodes patterns, entity naming conventions, read_graph anti-pattern
- `/session-recap` — the writeback counterpart, run at end of session
