---
name: git
description: Core Git mechanics — rebase, bisect, reflog recovery, worktrees, and submodules. Use for git operations beyond basic add/commit/push; see git-conventions rule for branching/commit style and the github skill for GitHub-platform specifics.
---

# Git

Version control mechanics, independent of hosting platform. See `.claude/rules/git-conventions.md` for
branching/commit-message policy (detect and follow the repo's existing convention, don't impose one), and
the `github` skill for platform-specific features (PRs, branch protection, Actions).

## Recovery Operations (know these before you need them)

```bash
git reflog                                  # every HEAD movement, including "lost" commits after a
                                             # reset/rebase — the actual undo mechanism for most mistakes
git reset --soft HEAD~1                     # undo last commit, keep changes staged
git checkout <commit> -- <path>             # restore a specific file from any point in history
git stash / git stash pop                   # shelve uncommitted work temporarily
git cherry-pick <commit>                    # apply a specific commit onto the current branch
git revert <commit>                         # undo a commit via a new inverse commit (safe on shared
                                             # history, unlike reset/rebase which rewrite it)
```

## Bisecting a Regression

```bash
git bisect start
git bisect bad                     # current commit is broken
git bisect good <known-good-sha>   # this earlier commit was fine
# git checks out a midpoint; test it, then:
git bisect good   # or: git bisect bad
# repeat until git identifies the exact commit that introduced the regression
git bisect reset
```

## Worktrees (parallel checkouts without cloning)

```bash
git worktree add ../hotfix-branch hotfix-branch   # separate working directory, same repo/.git
git worktree list
git worktree remove ../hotfix-branch
```

Useful for working on an urgent fix without disturbing an in-progress branch's working directory state.

## Submodules

```bash
git submodule update --init --recursive     # after cloning a repo that has submodules
git submodule status                         # what commit each submodule is pinned to
```

- A submodule pins to a specific commit, not a branch — "the submodule is out of date" usually means the
  parent repo's recorded pointer wasn't updated after the submodule itself moved forward.

## History-Rewriting Caution

- `rebase`, `reset --hard`, `filter-branch`/`filter-repo`, and `push --force` all rewrite history — safe
  on a private/unshared branch, dangerous on anything already pushed and pulled by others (see
  `.claude/rules/safety.md` and the global git safety policy — these require explicit user authorization,
  never used as a default shortcut).
- `git revert` is the safe alternative to `reset`/rebase for undoing something already on a shared branch.

## Common Pitfalls

- Using `reset --hard` to "clean up" without checking `git status`/`git stash` first — silently discards
  uncommitted work.
- Force-pushing after a rebase on a branch others have already pulled, causing their local history to
  diverge painfully — confirm no one else is on the branch first.
- Detached HEAD state (from checking out a commit/tag directly) mistaken for being on a branch — commits
  made here are easy to lose; `git branch` from there before committing further work.
