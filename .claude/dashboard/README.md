# Team Dashboard

Self-contained HTML rendering of every agent in `.claude/agents/` — one browser tab, whole team
visible. Built from Munder-Difflin's "office floor" idea, minus the Electron / Pixi.js overhead;
plain HTML that opens anywhere.

## Open

```bash
open .claude/dashboard/team-dashboard.html
```

(macOS. On Linux: `xdg-open`. On Windows: `start`.)

## What it shows

- **51 agents** grouped by category (orchestrator, managers, design/impl/review/verify layers,
  cross-cutting specialists, existing specialists)
- **Color-coded** per category so the org structure is visible at a glance
- **Click any card** for full description + who invokes them + who they invoke
- **Search box** filters live by name or description — type "kubernetes" and only k8s-relevant
  agents highlight

## Regenerate

The HTML is generated from live agent frontmatter. Regenerate whenever agents are added,
removed, or renamed:

```bash
python3 .claude/scripts/generate-team-dashboard.py
```

The `.claude/scripts/validate-skills.sh` auto-runs the generator on every successful validation,
so if you're already running that on agent changes, the dashboard stays in sync automatically.

## Adapting

- Edit `.claude/scripts/generate-team-dashboard.py` to change layout, colors, or add sections
- Categories are classified in the `classify()` function — adjust when adding a new agent type
- Manager → specialist delegation edges are declared in `MANAGER_SPECIALISTS` dict
- Colors are in the `CATEGORIES` list

## Why HTML instead of Pixi.js

Munder-Difflin's Electron+Pixi.js floor is a live app with real-time animation of agent
messaging. Claude Code isn't Electron; it can't run a persistent visualization process. This
static HTML captures the *legibility* value (see the team at a glance, discover who does what)
without needing the runtime. If you eventually want the live-animation version, that would be a
separate desktop app project, not a `.claude/` addition.
