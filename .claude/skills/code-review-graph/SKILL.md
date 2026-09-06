---
name: code-review-graph
description: code-review-graph (CRG) — a Tree-sitter-based structural code graph served via MCP, so Claude reads only the "blast radius" of a change instead of scanning the whole repo. Use when reviewing a change's impact, or when repo exploration is burning more tokens than it should; complements repository-discovery and mcp-server-development.
---

# code-review-graph (CRG)

An MCP server (plus CLI, VS Code extension, and GitHub Action) that parses a repository into an AST-based
graph — functions, classes, imports, call edges, inheritance, test coverage — via Tree-sitter, stored
locally in SQLite. At review time it answers "what does this change actually affect" with a precise,
graph-derived slice instead of Claude reading files broadly. Local-first: parsing and querying happen
entirely on-device/on-runner, nothing is sent externally. See `repository-discovery` for the
manual-exploration fallback when this isn't installed, and `mcp-server-development` for how a tool like
this is built.

## Why This Is a Different Risk Profile Than a Lossy-Compression Proxy

Unlike a tool that renders context as images for token savings (lossy, with a documented "silent
confabulation" failure mode on exact identifiers — see this session's evaluation of that category of
tool), CRG's token savings come from **precision, not compression**: it returns an exact, structurally-
derived subset of the real graph (real function names, real call edges, real file paths), not an
approximate visual re-read. The failure mode here is "the graph missed an edge" (recall gap), not "the
model misread a rendered character" — a meaningfully safer category for infra/DevOps work where exact
identifiers matter.

## Core Concepts

- **Blast radius**: given a changed file/function, the graph traces every caller, dependent, and test
  that could be affected — the concrete mechanism behind a fast, accurate "what do I need to review" answer.
- **Incremental updates**: file-save/commit hooks re-parse only files whose SHA-256 hash actually changed,
  and re-resolve their dependents through existing graph edges — a two-file change on a ~3,000-file repo
  reindexes in ~2.5s, not a full re-parse.
- **Risk-scored PR review** (via the GitHub Action): posts a sticky PR comment with risk-scored functions,
  affected execution flows, and test gaps — can be configured as a merge gate (`fail-on-risk`).

## Installation (not run automatically by any skill/agent in this repo — a deliberate, explicit step)

```bash
pip install code-review-graph                        # or: pipx install code-review-graph
code-review-graph install --platform claude-code       # scope to Claude Code specifically, not every
                                                        # detected tool on the machine
code-review-graph build                                 # parse the current repo
```

- `code-review-graph install` (no `--platform` flag) auto-detects and configures *every* supported tool
  on the machine (Cursor, Codex, Windsurf, etc.) — prefer the scoped `--platform claude-code` form unless
  cross-tool setup is actually wanted, since the unscoped form touches more configuration than a
  single-project setup needs.
- `code-review-graph uninstall --dry-run` previews exactly what a removal would touch before running it
  for real — use this to understand what `install` changed, even after the fact.

## Usage Once Installed

```text
"Build the code review graph for this project"     — initial build (~10s for a 500-file project)
"What's the blast radius of changing <function>?"    — impact analysis before touching it
"What tests cover this function?"                     — the same graph, queried for coverage
```

- Pairs naturally with `/onboard` and the `repository-discovery` skill: once a graph exists for a repo,
  subsequent sessions in that repo can query it instead of re-doing broad `find`/`grep` exploration.
- Pairs with `code-review` and `terraform-reviewer`/`kubernetes-debugger`-style review work: "what does
  this change affect" is exactly the question those skills/agents need answered before reviewing.

## Common Pitfalls

- Treating the graph as exhaustive ground truth for *runtime* behavior — it's a **static** structural
  graph (calls/imports/inheritance as written), not a dynamic trace; reflection, dynamic dispatch, or
  string-built import paths can create real dependencies the static graph can't see. Don't skip a manual
  sanity check on a change touching highly dynamic code just because the graph reported a small blast radius.
- Graph staleness if hooks/watch mode aren't enabled — a graph built once and never updated as the repo
  changes gives increasingly wrong answers with no obvious error, the same staleness risk any cached
  index carries.
- Installing unscoped (`code-review-graph install` with no `--platform`) when only Claude Code setup was
  actually wanted, touching other tools' configs unnecessarily.
- The GitHub Action's `fail-on-risk` used as a hard merge gate without first observing its risk-scoring
  behavior on real PRs — same "understand a new gate's real-world signal-to-noise before making it
  blocking" caution this repo's `devsecops` skill applies to any new pipeline gate.
