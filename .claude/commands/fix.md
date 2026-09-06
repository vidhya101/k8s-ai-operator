---
description: Deep troubleshooting mode — reproduce, parse the actual error/stack trace, isolate root cause, verify the fix.
argument-hint: "<error message, stack trace, or symptom description>"
---

Debug: $ARGUMENTS

Follow the `production-debugging` skill's method (or `kubernetes-debugger`/`terraform-reviewer` if the
symptom is clearly scoped to one of those) rather than guessing at a fix from the symptom alone:

1. Get the exact error — full message/stack trace, not a paraphrase. Ask for it if not given.
2. Reproduce it if possible, or identify the exact conditions that trigger it.
3. Isolate: bisect between "this worked" and "this doesn't" — a recent change (deploy, config, dependency
   bump), a specific input, or an environment difference are the usual suspects; check what changed before
   assuming a novel bug.
4. State a root-cause hypothesis and what evidence supports it before writing a fix.
5. Fix per `testing` skill's reproduce-then-fix discipline: a failing test/repro case first if practical,
   then the change that makes it pass.
6. Verify the original symptom is actually gone, not just that the code compiles/deploys.

Don't propose a fix for symptoms you haven't traced to an actual cause — "try this and see if it helps" is
a hypothesis to state explicitly, not a fix to apply silently.
