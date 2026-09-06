---
name: provider-handoff
description: Cross-provider handoff protocol — how a claude-primary manager hands work to its codex-fallback (or ollama) peer via Munder's file-based hive. Load when a manager needs to route work to a different tier of the provider chain because the current tier is throttled, cost-constrained, or a poor fit for the task.
---

# Provider Handoff Protocol

**When to use this skill.** You're a manager working through Munder's file-based
hive. You've decided (per `.claude/rules/provider-routing.md`) that the current
task belongs at a different tier of the provider chain — you're throttled, the
circuit breaker fired, or the task is cheap enough that a fallback peer should
handle it. This skill tells you the exact message shape to write into your
`outbox/` so Munder's router delivers it correctly and the fallback peer knows
what to do.

## Preconditions

- Your fallback peer exists on the floor. Check the roster — you need
  `<your-name>-codex` (or an equivalent) already spawned. If it isn't, don't
  handoff — instead address a message to `god` requesting the swap ("please
  spawn my codex peer; I'm throttled on X").
- The receiving peer has the same `.claude/` inventory available (same cwd),
  so it can pick up your work without re-onboarding.

## Message shape

Write exactly one JSON file into your outbox:

```
<AGENT_DIR>/outbox/handoff-<yyyy-mm-ddThh-mm-ss>-<random>.json
```

Contents (all fields required unless marked optional):

```json
{
  "kind": "request",
  "from": "<your-agent-id>",
  "to":   "<fallback-agent-id>",
  "subject": "Handoff: <one-line task summary>",
  "body": {
    "reason": "<why-you-are-handing-off>",
    "task": "<what-you-need-them-to-do>",
    "context": [
      "<file-path-or-artifact-relevant-to-the-task>",
      "<memory-note-they-should-read-first, e.g. /path/to/memory.md>"
    ],
    "success_criteria": ["<measurable-outcome-1>", "<measurable-outcome-2>"],
    "constraints": {
      "token_budget": 100000,
      "deadline": "<ISO-8601 or 'best-effort'>"
    },
    "return_via": "outbox → your-inbox",
    "attribution": "attribute the result to '<your-name> via <fallback>' in synthesis"
  },
  "reply_needed": true,
  "hops": 0,
  "ts": "<iso-8601>"
}
```

## Reason codes

Use one of these exact strings in `body.reason` so the receiving peer + `god`
know the class of handoff:

| Reason | When to use |
|---|---|
| `throttled-primary` | Anthropic API rate-limited your calls; work must continue somewhere |
| `constrained-by-breaker` | Munder's circuit breaker sent you "constrain" — you MUST STOP repeating this class of work; delegate down |
| `cost-optimization` | Task is genuinely cheap (log summary, doc draft, obvious refactor) — no reason to burn primary-tier tokens |
| `task-class-fit` | Task class matches lower tier by nature (mechanical code emit vs. judgment call) |

## What NOT to hand off

- **Design decisions**, **security audits**, **incident triage**, **postmortems**
  — these need the primary tier. If Claude is unavailable for these, escalate to
  the user ("stop and tell the user"), don't downgrade silently.
- **Any task where the two tiers might reasonably disagree in a load-bearing
  way** — a codex peer's answer to "should we use Aurora Serverless?" may
  differ from Claude's; if the answer matters, don't outsource it silently.

## What the fallback peer does when it receives your message

1. Reads the message file from its inbox
2. Reads every path in `body.context`
3. Executes the task in `body.task`
4. On success: writes a reply message with `kind: "inform"`, subject
   `Handoff result: <original>`, and body containing what it produced +
   pointers to any artifact files created
5. Moves the original into `<its-agent-dir>/inbox/.done/` per hive protocol
6. Records the handoff in its own `memory.md`

## What YOU do after handing off

1. Note the handoff in your `who-did-what.md` (via `/task-log <you>
   "handed off X to <peer> — reason: throttled-primary"`)
2. Note it in your `memory.md` too so future-you finds it
3. Wait for the reply in your inbox — DON'T also do the work in parallel
   (double-spend on tokens)
4. When the reply lands, verify the result meets `success_criteria`. If not,
   iterate (max 2 rounds), else escalate to `god` for re-routing.

## Handoff to Ollama specifically

Ollama peers spawned via Munder's `custom` provider **cannot receive hive
mailbox messages** (hookless — mail bounces). For Ollama work:

- **Preferred**: call Ollama through the Ollama MCP as a tool — no handoff
  message needed. Example: from your `claude` session, invoke
  `mcp__ollama__generate` (or the equivalent tool the MCP exposes) with the
  cheap subtask.
- **Not recommended for hive routing**: don't try to send outbox messages
  to an ollama-worker agent — they won't drain. Use the MCP path instead.

## Example: throttled cloud-manager hands off Terraform module boilerplate

```json
{
  "kind": "request",
  "from": "cloud-manager-mt42mxfe",
  "to": "cloud-manager-codex-xyz789",
  "subject": "Handoff: generate VPC + subnets Terraform boilerplate",
  "body": {
    "reason": "throttled-primary",
    "task": "Write terraform for a production VPC in us-east-1 with 3 AZs (public + private subnets each), NAT gateway per AZ, VPC endpoints for S3 + DynamoDB. Follow the module conventions in /Users/vidhyashankergoel/claude-imp/claude/.claude/skills/terraform/. Return one Terraform module in /tmp/handoff-vpc/.",
    "context": [
      "/Users/vidhyashankergoel/claude-imp/claude/.claude/skills/terraform/SKILL.md",
      "/Users/vidhyashankergoel/claude-imp/hive/agents/cloud-manager-mt42mxfe/memory.md"
    ],
    "success_criteria": [
      "terraform validate passes",
      "checkov -d /tmp/handoff-vpc returns 0 high/critical",
      "module structure follows examples in .claude/skills/terraform"
    ],
    "constraints": { "token_budget": 100000, "deadline": "best-effort" },
    "return_via": "outbox → your-inbox",
    "attribution": "attribute to 'cloud-manager via cloud-manager-codex' in the final synthesis"
  },
  "reply_needed": true,
  "hops": 0,
  "ts": "2026-08-23T14:00:00Z"
}
```

## Common Pitfalls

- **Handing off a design decision** because Claude is slow — that's not a
  handoff-worthy reason. Slow ≠ throttled. Wait or ask the user.
- **Skipping the `context:` array** — the fallback peer has NO memory of your
  session; they need explicit file paths to read.
- **Not writing a `return_via`** — the peer won't know how you want the reply
  formatted or where to put it.
- **Missing `success_criteria`** — the peer will produce something, but you
  won't know if it's the right shape until you re-read it end-to-end.
- **Trying to handoff to an Ollama agent via outbox** — it bounces (hookless).
  Use the MCP tool call instead.
- **Silently downgrading a task that materially needed the primary tier** —
  escalate to the user; don't hide the tier swap in a synthesis.
