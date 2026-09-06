---
name: senior-engineering-practices
description: Senior/principal-level engineering practice — technical decision records, cross-team roadmap ownership, and structured technical review, distinct from the hands-on execution skills elsewhere in this repo. Use when the task is itself a senior-IC-level activity (a design review, a build-vs-buy call, coordinating a multi-team initiative) rather than implementation work.
---

# Senior / Principal Engineering Practices

The practices that distinguish senior/principal-level work from execution — applies across any tech
stack, complementing the hands-on skills elsewhere in this repo rather than duplicating them. Where the
`architecture-review` skill is a review *method*, this skill covers the broader set of senior-IC
responsibilities: making and recording decisions, owning technical direction across teams, and
structured review of someone else's design.

## Technical Decision Records

- A decision worth recording (a build-vs-buy call, a technology choice with real long-term consequences)
  needs: the context/problem, the options actually considered (not just the one chosen), the tradeoffs of
  each, and the decision with its reasoning — the same shape as `engineering:architecture`'s ADR format.
- **Record the decision at the time it's made**, not reconstructed later — the reasoning (especially why
  rejected alternatives were rejected) is far more accurate and far more useful to a future reader written
  in the moment than recalled months later once the context has faded.
- A decision record's value is realized when someone later asks "why did we do it this way" — write for
  that future reader specifically, the same "write for someone with less context than you have right now"
  principle the `sop` command applies to runbooks.

## Cross-Team Technical Roadmap Ownership

- Coordinating technical direction across teams that don't report to each other requires influence rather
  than authority — the actual work is making the tradeoffs and dependencies visible (what blocks what,
  what's genuinely shared infrastructure vs. team-specific) so teams can plan around reality rather than
  around an incomplete picture.
- Technical debt and platform investment compete with every team's own feature roadmap for the same
  engineering time — making that tradeoff explicit and visible (not assumed as "someone else's problem")
  is a core part of this responsibility, not a side conversation.

## Structured Technical Review

- A senior review of someone else's design should separate **blocking concerns** (a real correctness/
  scalability/security problem) from **preference** (how the reviewer would have done it differently) —
  the same blocking-vs-nit distinction the `code-review` skill applies to code, now applied to a design
  document or proposal.
- The most valuable senior review often isn't "here's what's wrong," it's naming the **assumption that
  hasn't been tested** or the **failure mode that hasn't been considered** — the thing a less experienced
  design is most likely to have missed entirely, not a stylistic disagreement.
- Give a design review a clear verdict (approved, approved-with-changes, needs-rework) rather than a list
  of comments with no overall signal — an author reading ambiguous feedback can't tell whether it's ready
  to proceed.

## Common Pitfalls

- Decisions made informally in a meeting/Slack thread with no lasting record, forcing the same debate to
  happen again from scratch when someone questions the choice later (or worse, when a new team member
  reverses a decision they never knew was already made deliberately).
- Roadmap ownership exercised as top-down mandate instead of making tradeoffs visible and letting teams
  plan around them — breeds resentment and workarounds rather than actual alignment.
- Technical review focused entirely on style/preference nits, missing the one actually load-bearing
  assumption or failure mode the design didn't account for.
- Review feedback with no clear verdict, leaving the author to guess whether they're actually clear to
  proceed.
