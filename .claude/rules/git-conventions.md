# Rule: Git & Branching Conventions

Do not impose a branching/commit strategy — detect and follow the one already in use in the repo.

- Before creating a branch or commit, check for existing convention: `git log --oneline -20` for commit
  message style (Conventional Commits, ticket-prefixed, freeform), `git branch -a` for branch naming
  (`feature/`, `feat/`, ticket-ID-based, GitFlow's `develop`/`release/*`), and any `CONTRIBUTING.md` or
  PR template in the repo.
- If no convention is evident (new/empty repo), ask which style to use rather than picking one — this is
  a "do not silently choose a branching strategy" case per `CLAUDE.md` Section 1.1.
- Never commit directly to `main`/`master`/`production` branches if the repo shows any evidence of a
  PR-based workflow (protected branch rules, existing PR history, a `CODEOWNERS` file) — open a branch
  and let the user decide on the PR.
- Match existing commit message length/format/tense; don't switch a terse repo to verbose messages or
  vice versa.
- Only commit when the user explicitly asks (see global git safety policy) — this applies doubly to
  infrastructure repos, where a commit can trigger a CI/CD apply against real infrastructure.
