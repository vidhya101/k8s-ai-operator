# Rule: Memory Usage (Cross-Session Recall)

Sessions are ephemeral. The `@modelcontextprotocol/server-memory` MCP server (wired in `.mcp.json`)
is how this team accumulates knowledge across sessions. Every agent — the orchestrator, every domain
manager, every sub-agent — MUST use it:

## Read at start

Before starting any non-trivial work, call `mcp__memory__search_nodes` with query terms specific
to the task (project name, technology, symptom, artifact type). Cheap operation, targeted result
— NOT `mcp__memory__read_graph` (which dumps everything and burns context, see the `mcp-memory`
skill's warning). If nothing relevant returns, say "memory recall: none" and proceed.

## Write at end

After completing significant work, call `mcp__memory__create_entities` for new entities (a project
setup, a solution to a specific problem, an important gotcha, a decision made) or
`mcp__memory__add_observations` to extend existing ones. Write only what a future session would
actually benefit from — not routine command outputs, not conversational chatter.

Entity naming convention (from the `mcp-memory` skill):
- `Session-YYYY-MM-DD-<project>-<feature>`
- `Solution-<problem>-<technology>`
- `Pattern-<architecture>-<context>`
- `Decision-<what-was-decided>-<project>`

## Applies to

Every agent invocation, including sub-agents invoked BY managers. A manager delegating to
`designer` inherits this rule — the designer also checks memory (design decisions the same
project made before) and writes back (the design it produced, if novel).

## When it does NOT apply

- Trivial one-shot answers (a typo fix, a "what does X mean" clarification)
- Actions the user explicitly wants isolated to this session
- Content that would violate `.claude/rules/secrets.md` (never write a secret value into memory,
  even one seen in tool output — memory persists indefinitely)

## Cross-reference

See the `mcp-memory` skill for query pattern examples, entity naming detail, and the
`read_graph` anti-pattern. This rule is the always-loaded enforcement; the skill is the
on-demand how-to.
