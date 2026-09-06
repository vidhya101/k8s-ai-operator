# Skill Template

Copy this into `.claude/skills/<your-skill-name>/SKILL.md` and fill it in. Kept here (not inside
`.claude/skills/` itself) specifically so it's never scanned as a real, activatable skill — a template
with a placeholder name/description sitting inside `.claude/skills/` would otherwise show up as a
(useless, confusing) real skill.

See `.claude/spec/authoring-guide.md` for the full convention this follows.

```markdown
---
name: skill-name-in-kebab-case
description: One to three sentences — what this covers AND the concrete situations where it should
  activate. Be specific about triggers, not just a restatement of the title.
---

# Title In Title Case

One or two sentences of scope. Point to the closest related existing skill if the boundary isn't obvious.

## Core Principles

- The non-obvious, opinionated guidance an experienced engineer would want — not a tutorial.
- ...

## <A Concrete Section Specific To This Topic>

Real command examples / config snippets here — concrete and copy-adjustable, not abstract description.

\`\`\`bash
# a real, runnable example
\`\`\`

## Common Pitfalls

- **Specific failure mode** — what causes it, what it looks like, how to actually avoid/fix it. Not a
  vague "be careful with X."
- ...
```

After filling it in: move it to `.claude/skills/<name>/SKILL.md`, then run
`.claude/scripts/validate-skills.sh` and fix anything it flags.
