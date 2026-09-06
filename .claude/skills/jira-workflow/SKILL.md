---
name: jira-workflow
description: Jira ticket workflow — writing tickets that are actually actionable, status/workflow design, and linking work to code changes. Use when authoring/triaging Jira tickets or reviewing a team's Jira workflow configuration, common in enterprise/consulting engagements.
---

# Jira Workflow

Enterprise ticket tracking — ubiquitous in consulting/enterprise engagements (banking, insurance,
aviation-style clients) even when the actual engineering work happens elsewhere (GitHub, Azure DevOps).
See `github`/`azure-devops` skills for the code-side workflow this connects to.

## Writing an Actionable Ticket

- A good ticket states: the problem/goal in plain language, acceptance criteria (how do we know this is
  done), and any known constraints/dependencies — a ticket that's just a title with no acceptance
  criteria forces the assignee to guess at scope, the single biggest source of ticket-to-code mismatch.
- Bug tickets specifically need: exact reproduction steps, expected vs. actual behavior, and environment/
  version — the same "get the exact symptom, not a vague description" discipline the `fix` command and
  `production-debugging` skill apply to any debugging session.
- Story points / sizing should reflect actual complexity/uncertainty, not effort-as-a-proxy-for-worth —
  a ticket sized without the assignee's input is usually wrong in a predictable direction.

## Workflow & Status Design

- Keep the status workflow (To Do → In Progress → In Review → Done, or whatever variant) matched to what
  the team actually does — a workflow with statuses nobody uses correctly (tickets sitting in "In Review"
  that were actually merged weeks ago) makes Jira data unreliable for anything built on top of it
  (`dora-metrics`' lead-time calculations, sprint reporting).
- Required fields on ticket creation/transition (a resolution reason, a fix version) should be genuinely
  needed downstream, not process theater — every required field is friction that a team either respects
  or routes around (garbage data entered just to satisfy the requirement).

## Linking Work to Code

- Commit message / PR linking (via ticket ID in the branch name or commit message, e.g. `PROJ-123`) is
  what makes "which code changed for this ticket" answerable later — without this convention, that
  question requires manual archaeology.
- Automation (a PR merge auto-transitioning the linked ticket to "Done") reduces the toil of manually
  keeping ticket status in sync with actual code state — worth setting up once, saves repeated manual
  updates indefinitely.

## Common Pitfalls

- Tickets with no acceptance criteria, discovered to be ambiguous only after work is already underway or
  "done" and reviewed as not matching what was actually wanted.
- A workflow with too many required transitions/fields for the team's actual size/process maturity,
  training people to fill them in with junk just to move a ticket forward.
- Sprint/velocity metrics trusted as precise data when the underlying ticket statuses are known to be
  unreliable — garbage in, garbage out applies to any DORA/velocity reporting built on top of Jira data.
- Using Jira as the source of truth for technical decisions/design (better suited to a `decision-record`-
  style doc or Confluence page, see `confluence-authoring`) instead of just work tracking.
