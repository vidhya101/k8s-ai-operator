# Skill Authoring Guide

The convention every skill in this repo follows, so new additions (by you or a future Claude session)
stay consistent without having to reverse-engineer the pattern from existing files. Run
`.claude/scripts/validate-skills.sh` after adding or editing a skill — it checks most of this
automatically.

This is our own convention — deliberately simpler than the stricter 8-required-section format some
public skill marketplaces use (which also require `license`/`compatibility`/`metadata.domain`
frontmatter). That format is built for a repo with external contributors across many agent platforms;
this one is a personal/team template maintained by one person for Claude Code specifically, so it stays
lighter-weight on purpose. Don't retrofit existing skills to a stricter format without a real reason —
see `CLAUDE.md` Section 1.2.

## Folder layout

```
.claude/skills/<skill-name>/SKILL.md
```

One file per skill. No `scripts/`/`references/` subfolders in this repo's convention — keep a skill
self-contained in its one `SKILL.md`; if something needs a runnable script, that belongs in
`.claude/hooks/` (if it's session automation) or `.claude/scripts/` (if it's a maintenance tool), not
inside an individual skill's folder.

## Required frontmatter

```yaml
---
name: skill-name-in-kebab-case
description: One to three sentences — what this skill covers AND the concrete situations where it
  should activate. This is the single field Claude uses to decide relevance with no other context, so
  be specific about triggers, not just a restatement of the title.
---
```

- `name`: kebab-case, must exactly match the parent folder name (`validate-skills.sh` checks this).
- `description`: single field, no line-break block scalars needed — keep it to 1-3 sentences dense with
  the actual trigger conditions ("Use when reviewing X" / "Use for Y-specific troubleshooting").
- No `license`, `compatibility`, or `metadata.domain` fields — this repo isn't distributed as a
  cross-platform marketplace package (see the `.claude-plugin` discussion this file's sibling
  conversation covered), so those fields would document nothing that's actually true here.

## Body shape

Not rigidly enforced section-by-section, but every skill in this repo follows this shape:

```markdown
# Title

One or two sentences of scope — what this covers, and a pointer to the closest related skill(s) if the
boundary between them isn't obvious (e.g. "see the X skill for Y instead").

## Core Principles  (or Core Concepts / Core Model — whichever fits the topic)

Bulleted, opinionated guidance — not a tutorial, a checklist an experienced engineer would actually want.

## <Concrete sections specific to the tool/topic>

Real command examples, real config snippets — concrete, copy-adjustable, not abstract description.

## Common Pitfalls

Always the closing section. Each pitfall is a specific failure mode, not a vague warning — "X causes Y
symptom" is the bar, not "be careful with X."
```

## Cross-referencing other skills

Reference other skills by backtick-quoted name in prose — `` `terraform-state` skill ``, not a markdown
link — since skills aren't meant to be read as a linked document tree, they're independently loaded by
description match. Every cross-referenced name should be a real skill in `.claude/skills/` — the audit
in `GETTING_STARTED.md`'s history checked this; keep it true going forward.

## Where a new skill belongs

- **A genuinely new, named technology/practice not covered anywhere** → new `SKILL.md`.
- **A sub-topic of something that already has a skill** (e.g. a new AWS service closely related to an
  existing AWS skill) → amend the existing skill with a new `##` section instead of fragmenting into a
  thin new file. This repo has bundled tightly-related concepts deliberately (`kubernetes-autoscaling`
  covers metrics-server + HPA + VPA + Cluster Autoscaler together, not four separate files) — match that
  judgment rather than defaulting to "always make a new file."

## After adding or editing a skill

```bash
.claude/scripts/validate-skills.sh
```

Fix anything it flags before considering the change done — it catches the same class of mistakes (a
stray character in the `name:` field, an unclosed code fence, a duplicate name) that were caught by hand,
one at a time, while this repo was being built.
