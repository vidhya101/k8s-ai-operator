---
description: End-of-session writeback — structure findings into memory MCP so the next session recalls them. Run before /clear or session end.
argument-hint: "[optional: session focus, e.g. 'terraform state migration failed and here's why']"
---

Write structured session findings back to memory MCP so the next session (yours or a colleague's
running the same setup) doesn't re-derive them: $ARGUMENTS

## What to do

1. **Identify what's worth persisting** from this session. Ruthlessly filter:
   - **YES** — a solution to a non-obvious problem, a decision made (with reasoning), a gotcha
     discovered, a pattern that worked well, a client-specific constraint that will re-apply next time
   - **NO** — routine command outputs, conversational chatter, trivial fixes, session-local scratch,
     anything future-you would have to re-derive faster than reading it back

2. **Structure each finding** as a memory entity using the naming convention from `mcp-memory` skill:
   - `Session-YYYY-MM-DD-<project>-<feature>` — a self-contained summary of THIS session's work,
     what was accomplished, what remains, key decisions
   - `Solution-<problem>-<technology>` — reusable "when you see X do Y" pattern
   - `Pattern-<architecture>-<context>` — architectural or organizational pattern discovered
   - `Decision-<what-was-decided>-<project>` — a decision made with the reasoning behind it,
     alternatives rejected, when it might need revisiting

3. **Write to memory** via `mcp__memory__create_entities` (new entities) or
   `mcp__memory__add_observations` (extend an existing entity, e.g. append to today's
   Session-YYYY-MM-DD entry as work continues within the day):

   ```
   mcp__memory__create_entities([
     {
       name: "Session-2026-08-17-fleet-impl-agent-team-buildout",
       entityType: "session",
       observations: [
         "Built 51-agent team structure: 1 orchestrator + 12 managers + 22 shared sub-agents + 16 existing specialists",
         "Discovered code-writer-* agents were missing Write/Edit in tools frontmatter — fixed",
         "Added .claude/config/tokens.env.template pattern for the 'one file for all tokens' ask",
         "Team dashboard generator at .claude/scripts/generate-team-dashboard.py — regenerate on agent changes"
       ]
     },
     {
       name: "Solution-agent-cannot-write-files-missing-tools-frontmatter",
       entityType: "solution",
       observations: [
         "If a Claude Code sub-agent's frontmatter tools: line omits Write/Edit, the agent literally cannot write files, even though its role is to write code",
         "Symptom: agent 'produces' code in prose but no file appears",
         "Fix: add Write, Edit to tools: — see .claude/agents/code-writer-*.md as the canonical example"
       ]
     }
   ])
   ```

4. **Link related entities** where useful via `mcp__memory__create_relations` — e.g. this
   session's Session-* entity "produced" a Solution-* entity, or a Decision-* "supersedes" a
   prior one. Sparingly — over-linking creates noise.

5. **Never write a real secret into memory.** Same rule as everywhere else — memory persists
   indefinitely, is trivially queryable, and a token/password in memory is worse than one in a
   log. See `.claude/rules/secrets.md`.

6. **Report what was written** — one line per entity, so the user sees the session's
   contribution to future sessions is real, not silent.

## Output format

```
## Session recap — memory writes

Wrote 3 entities:
- Session-2026-08-17-<project>-<feature>: <one-line summary>
- Solution-<problem>: <one-line insight>
- Decision-<what>: <one-line reasoning>

Relations created:
- Session-... PRODUCED Solution-...

Skipped (not worth persisting):
- <one-line per thing you considered but rejected>

Next-session pointer: run `/recall-context <project>` to pull this back.
```

## When to invoke

- Manually at end of a session doing non-trivial work (`/session-recap`)
- Automatically-ish via the Stop hook — the hook prints a reminder to invoke this if the session
  had meaningful activity (edits, mutating commands) and no `session-recap` was written yet
- Whenever finishing a discrete deliverable within a longer session (don't wait for session end
  if a chunk is done and worth persisting)

## Cross-reference

- `.claude/rules/memory-usage.md` — the always-loaded rule
- `mcp-memory` skill — the how-to
- `/recall-context` — the read counterpart
