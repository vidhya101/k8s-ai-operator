---
name: chatops
description: ChatOps — running operational commands and workflows from Slack/Teams instead of a terminal, with runbook automation and audit trail. Use when designing or reviewing a ChatOps integration, particularly for incident response and routine operational tasks.
---

# ChatOps

Runs operational actions (deploy, rollback, scale, query status) as chat commands in Slack/Teams instead
of requiring a terminal session — the value is less about convenience and more about **visibility and
audit trail**: everyone in the channel sees what action was taken, by whom, and what the result was,
without needing to ask.

## Where It Fits Best

- **Incident response**: the `production-incident-commander` agent's structured incident-channel updates
  are exactly what ChatOps automation formalizes — a bot posting deploy/rollback actions and their
  results directly into the incident channel as they happen, instead of someone manually relaying status.
- **Routine, well-understood operations**: a scoped, safe set of commands (check deployment status,
  restart a specific known-safe service, query a metric) — not a replacement for direct access when doing
  something novel/investigative that a fixed command set can't anticipate.
- **Runbook automation**: converting a written SOP (`sop` command's output) into an actual executable
  chat command closes the gap between "documented procedure" and "procedure someone actually runs
  correctly under pressure" — the same manual-step-by-step SOP execution, but with less room for a
  typo/mistake during a stressful incident.

## Design Principles

- **Scoped commands, not a shell**: a ChatOps bot should expose a specific, reviewed set of operations
  (not "run arbitrary kubectl/terraform commands via chat") — the same least-privilege principle applied
  to what the bot itself is allowed to do, since a compromised or misused bot account is now a path to
  production actions.
- **Confirmation for anything destructive**: a chat command that scales down, deletes, or rolls back
  should require an explicit confirmation step (a reaction, a follow-up "yes"), not fire on the first
  message — the chat equivalent of `.claude/rules/safety.md`'s "ask before mutating" principle.
- **Full audit trail**: every ChatOps action should be logged with who ran it and what happened — the
  channel itself is a natural audit log, but don't rely on chat history alone if compliance/retention
  requirements need something more durable.

## Common Pitfalls

- Overly broad bot permissions — a ChatOps bot with unscoped access to run any command is a single
  compromised bot token away from full production access, a much larger blast radius than the convenience
  usually justifies.
- No confirmation step on destructive commands, making a typo (or an accidental paste into the wrong
  channel) capable of triggering a real production action.
- ChatOps commands that don't actually match what a runbook says, drifting apart over time as the
  runbook is updated but the bot's implementation isn't (or vice versa) — keep them as one source of
  truth, not two independently maintained ones.
- Treating ChatOps as the only interface for critical operations with no fallback if the chat platform
  itself is unavailable during an incident — don't create a single point of failure in the incident
  response tooling itself.
