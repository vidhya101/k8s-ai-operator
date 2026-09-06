---
name: confluence-authoring
description: Confluence documentation authoring and governance — structuring runbooks/architecture docs so they stay findable and don't rot, distinct from in-repo docs-as-code (TechDocs/Backstage). Use when writing or reorganizing Confluence content, common in enterprise engagements.
---

# Confluence Authoring & Governance

Enterprise wiki documentation — common where `backstage`'s docs-as-code TechDocs model isn't (yet, or
ever) the standard, and where non-engineering stakeholders need direct access to the same documentation
engineers use. The failure mode is different from a codebase: Confluence content rots silently because
nothing forces it to stay in sync with reality the way a code review does for docs-as-code.

## Structure That Actually Stays Findable

- A flat "everyone writes wherever" space becomes unsearchable past a modest size — organize by a
  consistent hierarchy (space per team/product, consistent page-tree structure within it: Overview →
  Architecture → Runbooks → Decisions) rather than ad hoc.
- **Page ownership**: every page of consequence (a runbook, an architecture doc) should have a clear
  owner responsible for keeping it current — an unowned page is a page nobody will update as things change.
- Labels/tags used consistently (not per-author preference) are what make cross-team search actually
  work — agree on a small, consistent taxonomy rather than letting it grow organically into noise.

## Runbooks Specifically

- Same content discipline as the `sop` command's output: every step verifiable, written for someone with
  less context than the author, a clear escalation path — Confluence is just the delivery mechanism.
- Runbooks are the highest-decay-risk content type (the underlying system changes, the runbook doesn't) —
  worth an explicit review cadence (quarterly, or triggered by a related incident) rather than "write
  once, hope it stays accurate."

## Architecture / Decision Documentation

- Architecture Decision Records (a decision, its context, alternatives considered, and consequences —
  see the `architecture-review`/`engineering:architecture` pattern) belong in a stable, linkable location
  — Confluence's page history and permanent links make it a reasonable home if the team doesn't use
  in-repo ADRs instead; don't scatter the same category of content across both without a clear convention
  for which goes where.

## Common Pitfalls

- Documentation written once during a project's initial build and never revisited — the exact "text file
  trap" problem described in [the MCP memory context](../skills/mcp-memory/SKILL.md) at a larger,
  organizational scale: pages accumulate, nobody's sure which is current, search returns five
  contradictory versions of "how to deploy X."
- No page ownership, so an obviously stale runbook sits unflagged because updating it isn't clearly
  anyone's job.
- Critical operational knowledge (how to actually recover from a specific failure mode) living only in
  one senior engineer's head, with no Confluence page at all — the thing worth writing down before it's
  needed under incident pressure, not during the incident itself.
- Confluence used for content that should be docs-as-code instead (API references, anything that should
  version alongside the code it describes) — see `backstage`'s TechDocs for when that's the better fit.
