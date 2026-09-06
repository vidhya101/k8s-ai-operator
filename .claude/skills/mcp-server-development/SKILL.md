---
name: mcp-server-development
description: Building an MCP (Model Context Protocol) server — tool/resource design, schema authoring, and safe permission boundaries. Use when building a custom MCP server to expose internal systems/APIs to Claude, distinct from mcp-memory's usage-pattern focus for the existing memory server.
---

# MCP Server Development

Building a Model Context Protocol server — the same mechanism this session's `memory` server, and any
Grafana/GitHub/PagerDuty integration, uses to expose tools to Claude. This skill covers *building* one;
see `mcp-memory` for *using* the memory server specifically.

## Core Concepts

- **Tools**: functions the model can call, each with a name, description, and JSON Schema input — the
  description is what the model uses to decide *when* to call a tool, so it needs to be specific and
  behavior-focused (what does this actually do, when should it be used), not just a name restatement —
  the same principle this entire `.claude/skills/` system's `description` frontmatter follows for
  matching tasks to skills.
- **Resources**: read-only data the model (or the host application) can access by URI — for exposing
  reference data (documentation, config, logs) distinct from actions.
- **Prompts**: reusable prompt templates the server can expose — less commonly used than tools/resources,
  useful for standardizing a common interaction pattern across every client that connects to the server.

## Design Principles

- **Narrow, well-described tools beat one giant do-everything tool** — a tool named `query_database` with
  a `sql` string parameter is powerful but dangerous and hard for the model to use well; several specific
  tools (`get_user_by_id`, `list_recent_orders`) are safer, more predictable, and easier for the model to
  pick correctly — the same "least-privilege, scoped access" principle from `.claude/rules/safety.md`
  applied to tool design itself.
- **Idempotency and side-effect clarity**: a tool's description should make clear whether calling it is
  safe to retry (read-only, idempotent) or has side effects (creates/mutates something) — this is what
  lets a host application (like this one) decide whether a tool call needs user confirmation before
  running, mirroring this repo's own `settings.json` allow/ask/deny model.
- **Error messages the model can act on**: a failed tool call should return a clear, specific error (not
  a raw stack trace) so the model can adjust its next call intelligently, rather than retrying blindly or
  giving up.

## Authentication & Scope

- MCP servers commonly need to authenticate to whatever backend they wrap (a database, an internal API) —
  scope those credentials to exactly what the server's tools need, the same least-privilege principle as
  any other service credential (`.claude/rules/secrets.md`).
- Never design a tool that returns raw secret values into the model's context if avoidable — if a tool
  must interact with something secret-bearing (e.g. checking whether a credential is valid), design it to
  return a boolean/status rather than the secret itself, mirroring this repo's own Vault-read caution in
  the `vault` skill.

## Common Pitfalls

- Tool descriptions that are too generic ("interacts with the database") — the model can't reliably
  decide when to use the tool, or picks it for the wrong situations; be as specific in a tool's
  description as this repository's own skill descriptions are.
- A single overly-broad tool (raw SQL execution, arbitrary shell access) instead of several narrow,
  purpose-built ones — maximizes both misuse risk and the chance the model uses it incorrectly.
- No distinction between read-only and mutating tools in how they're described/scoped, making it
  impossible for a host application to apply different confirmation policies the way this repo's
  `settings.json` does for Bash commands.
- Large, unbounded tool responses (dumping an entire dataset) instead of paginated/filtered results — the
  same token-economy concern the `mcp-memory` skill raises about `read_graph()` applies to any MCP
  server's tool design: return what's needed, not everything available.
