#!/usr/bin/env python3
"""
Task folder scaffolding — creates the per-task audit trail the user asked for.

For every task you start, this creates:

    ~/DevOpsHive/Tasks/task-YYYY-MM-DD-<slug>/
        _index.md         Obsidian note with front matter — becomes a vault node
        readme.md         What the task is + success criteria
        flow.md           Ordered plan (managers write here as they execute)
        tasks.md          Kanban-style list (todo/doing/blocked/done)
        who-did-what.md   Per-agent audit log — appended by /task-log or hook
        tokens.md         Token accounting (start / end / delta)
        skills.md         Skills the team consulted
        git.md            Any git operations performed
        start-time.txt    ISO timestamp — set on /task-start
        end-time.txt      Set on /task-end
        logs/             Auto-populated by the PostToolUse hook
            bash.log      Every Bash invocation across the whole task
            writes.log    Every Write / Edit target
        data/             Empty dir — task-specific data files land here

A `~/DevOpsHive/Tasks/current` symlink always points at the active task, so
hooks and agents can find "the current task dir" without state anywhere else.

WHY IT LANDS IN THE OBSIDIAN VAULT. `~/DevOpsHive/` is already the vault, so
every task folder becomes browsable in Obsidian instantly. The `_index.md`
carries YAML front matter that Dataview (if installed) can query, and the
[[wikilinks]] in it connect the task node to the agents that worked on it in
the graph view.

USAGE (via slash commands):
    /task-start <slug> [description]
    /task-log <who> <what>
    /task-end [summary]

Or directly:
    python3 .claude/scripts/task-scaffold.py start <slug> [description...]
    python3 .claude/scripts/task-scaffold.py log <who> <what...>
    python3 .claude/scripts/task-scaffold.py end [summary...]
    python3 .claude/scripts/task-scaffold.py current
    python3 .claude/scripts/task-scaffold.py status
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
TASKS_ROOT = HOME / "DevOpsHive" / "Tasks"
CURRENT_LINK = TASKS_ROOT / "current"

SLUG_RE = re.compile(r"[^a-z0-9-]+")


def now_iso() -> str:
    """ISO-8601 UTC timestamp, seconds precision — sortable, unambiguous."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    """YYYY-MM-DD in UTC — matches ISO. Consistent with folder-name convention."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def kebab(text: str) -> str:
    """Make a filesystem-safe slug — lowercase, kebab-case, no runs of dashes."""
    s = SLUG_RE.sub("-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s) or "task"


def resolve_current() -> Path | None:
    """Follow the `current` symlink to the active task dir, or None."""
    if CURRENT_LINK.is_symlink():
        try:
            resolved = CURRENT_LINK.resolve()
            return resolved if resolved.is_dir() else None
        except OSError:
            return None
    return None


# --- subcommands ---------------------------------------------------------------


def cmd_start(args: argparse.Namespace) -> int:
    slug = kebab(args.slug)
    description = " ".join(args.description) if args.description else ""

    task_dir = TASKS_ROOT / f"task-{today()}-{slug}"

    if task_dir.exists():
        # Non-fatal: allow re-opening the same task later in the day. Just
        # re-point `current` and leave existing contents untouched — the audit
        # trail so far is preserved.
        print(f"task dir already exists: {task_dir}", file=sys.stderr)
        _repoint_current(task_dir)
        print(f"→ re-pointed current to {task_dir}")
        return 0

    # Layout
    for sub in ("logs", "data"):
        (task_dir / sub).mkdir(parents=True, exist_ok=True)

    started_at = now_iso()

    _write(task_dir / "start-time.txt", started_at + "\n")
    _write(task_dir / "end-time.txt", "")

    _write(task_dir / "readme.md", _tpl_readme(slug, description, started_at))
    _write(task_dir / "flow.md", _tpl_flow())
    _write(task_dir / "tasks.md", _tpl_tasks())
    _write(task_dir / "who-did-what.md", _tpl_who())
    _write(task_dir / "tokens.md", _tpl_tokens(started_at))
    _write(task_dir / "skills.md", _tpl_skills())
    _write(task_dir / "git.md", _tpl_git())
    _write(task_dir / "_index.md", _tpl_index(slug, description, started_at, task_dir))

    _repoint_current(task_dir)

    print(f"→ task started: {task_dir}")
    print(f"→ current symlink: {CURRENT_LINK} → {task_dir.name}")
    print(f"→ audit hook will append tool calls to {task_dir.name}/logs/")
    return 0


def cmd_end(args: argparse.Namespace) -> int:
    task_dir = resolve_current()
    if not task_dir:
        print("no current task (no `current` symlink) — nothing to end", file=sys.stderr)
        return 1

    ended = now_iso()
    _write(task_dir / "end-time.txt", ended + "\n")

    # Compute duration in a human-friendly way.
    start_txt = (task_dir / "start-time.txt").read_text().strip()
    try:
        started = datetime.fromisoformat(start_txt)
        duration = datetime.fromisoformat(ended) - started
        secs = int(duration.total_seconds())
        h, rem = divmod(secs, 3600); m, s = divmod(rem, 60)
        dur = f"{h}h{m}m{s}s"
    except Exception:
        dur = "?"

    summary = " ".join(args.summary) if args.summary else ""
    _append(task_dir / "who-did-what.md",
            f"\n### {ended} · task ended\n\n"
            f"- Duration: **{dur}**\n"
            + (f"- Summary: {summary}\n" if summary else "")
            + "\n")

    # Update the _index.md front matter to reflect completion.
    _touch_index(task_dir, ended=ended, duration=dur, summary=summary)

    # Retire the symlink — the next /task-start creates a fresh one. The task
    # dir itself remains at ~/DevOpsHive/Tasks/task-.../ forever.
    if CURRENT_LINK.is_symlink() or CURRENT_LINK.exists():
        CURRENT_LINK.unlink()

    print(f"→ task ended after {dur}: {task_dir.name}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    task_dir = resolve_current()
    if not task_dir:
        # Non-fatal — if the user hasn't run /task-start, we don't want random
        # tool calls to error out. Just no-op.
        return 0

    who = args.who
    what = " ".join(args.what) if args.what else ""
    if not what:
        return 0

    _append(task_dir / "who-did-what.md",
            f"- `{now_iso()}` · **{who}** · {what}\n")
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    task_dir = resolve_current()
    if not task_dir:
        print("(none)")
        return 1
    print(task_dir)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    task_dir = resolve_current()
    if not task_dir:
        print("no current task")
        return 1

    print(f"current: {task_dir}")
    print(f"started: {(task_dir / 'start-time.txt').read_text().strip()}")
    end_txt = (task_dir / "end-time.txt").read_text().strip()
    print(f"ended:   {end_txt or '(still running)'}")
    print()
    bash_log = task_dir / "logs" / "bash.log"
    write_log = task_dir / "logs" / "writes.log"
    print(f"bash invocations logged: {_count_lines(bash_log)}")
    print(f"write/edits logged:      {_count_lines(write_log)}")
    who = task_dir / "who-did-what.md"
    if who.is_file():
        n = sum(1 for line in who.read_text().splitlines() if line.startswith("- `"))
        print(f"who-did-what entries:    {n}")
    return 0


# --- helpers -------------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def _count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def _repoint_current(task_dir: Path) -> None:
    """Atomically re-point the `current` symlink to a new task."""
    if CURRENT_LINK.is_symlink() or CURRENT_LINK.exists():
        CURRENT_LINK.unlink()
    # Relative symlink so it survives moving the whole vault.
    os.symlink(task_dir.name, CURRENT_LINK)


def _touch_index(task_dir: Path, *, ended: str, duration: str, summary: str) -> None:
    """Rewrite _index.md front matter with completion info."""
    idx = task_dir / "_index.md"
    if not idx.is_file():
        return
    text = idx.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if m:
            fm = m.group(1)
            fm = re.sub(r"^ended:.*$", f"ended: {ended}", fm, flags=re.MULTILINE)
            fm = re.sub(r"^duration:.*$", f"duration: {duration}", fm, flags=re.MULTILINE)
            if summary:
                fm = re.sub(r"^status:.*$", f"status: complete", fm, flags=re.MULTILINE)
            new_text = "---\n" + fm + "\n---\n" + text[m.end():]
            if summary:
                new_text += f"\n## Summary (end of task)\n\n{summary}\n"
            idx.write_text(new_text, encoding="utf-8")


# --- templates ----------------------------------------------------------------
# Every template is a full markdown file the agents can edit as work proceeds.


def _tpl_readme(slug: str, desc: str, started: str) -> str:
    return (
        f"# {slug}\n\n"
        f"**Started:** {started}\n\n"
        f"## What we're doing\n\n"
        f"{desc or '_(fill in as the task is planned)_'}\n\n"
        f"## Why\n\n_(the reason this is worth doing — one paragraph)_\n\n"
        f"## Success criteria\n\n"
        f"- [ ] _(measurable outcome 1)_\n"
        f"- [ ] _(measurable outcome 2)_\n\n"
        f"## Non-goals\n\n_(what we're deliberately NOT doing)_\n"
    )


def _tpl_flow() -> str:
    return (
        "# Execution flow\n\n"
        "_The manager writes here as it decomposes and delegates. Each step should name\n"
        "the agent, the input, and the expected output. Update as work progresses._\n\n"
        "1. **orchestrator** → decompose the ask; state the plan\n"
        "2. **<manager>** → produce **<artifact>**\n"
        "3. **<manager>** → verify **<artifact>** meets **<criterion>**\n"
    )


def _tpl_tasks() -> str:
    return (
        "# Tasks (kanban)\n\n"
        "## Todo\n"
        "- [ ] \n\n"
        "## Doing\n"
        "- [ ] \n\n"
        "## Blocked\n"
        "- [ ] \n\n"
        "## Done\n"
        "- [x] task-start scaffolding created\n"
    )


def _tpl_who() -> str:
    return (
        "# Who did what (audit log)\n\n"
        "_Appended by `/task-log <who> <what>` and by the PostToolUse hook._\n\n"
    )


def _tpl_tokens(started: str) -> str:
    return (
        "# Token accounting\n\n"
        f"| snapshot | at | input tokens | output tokens | notes |\n"
        f"| -------- | -- | ------------ | ------------- | ----- |\n"
        f"| start | {started} | 0 | 0 | task started |\n"
    )


def _tpl_skills() -> str:
    return (
        "# Skills consulted\n\n"
        "_The manager records which SKILL.md files it loaded (from `.claude/skills/`)\n"
        "and any external documentation it consulted, so the next similar task can\n"
        "jump straight to what worked._\n\n"
        "- \n"
    )


def _tpl_git() -> str:
    return (
        "# Git operations\n\n"
        "_Any branch/commit/PR that came out of this task, with links._\n\n"
        "- \n"
    )


def _tpl_index(slug: str, desc: str, started: str, task_dir: Path) -> str:
    """The Obsidian-facing top note — YAML front matter Dataview can query,
    body has [[wikilinks]] the graph view can visualize."""
    return "\n".join([
        "---",
        f"type: task",
        f"slug: {slug}",
        f"started: {started}",
        f"ended: ",
        f"duration: ",
        f"status: active",
        "---",
        "",
        f"# task: {slug}",
        "",
        f"{desc or '_(no description at start — fill in as scope becomes clear)_'}",
        "",
        f"## Structure",
        "",
        f"- [readme.md]({task_dir.name}/readme.md) — what, why, success criteria",
        f"- [flow.md]({task_dir.name}/flow.md) — execution steps",
        f"- [tasks.md]({task_dir.name}/tasks.md) — kanban",
        f"- [who-did-what.md]({task_dir.name}/who-did-what.md) — audit log",
        f"- [tokens.md]({task_dir.name}/tokens.md) — token accounting",
        f"- [skills.md]({task_dir.name}/skills.md) — skills consulted",
        f"- [git.md]({task_dir.name}/git.md) — git operations",
        f"- `logs/` — bash + write/edit trace (populated by hook)",
        f"- `data/` — task-produced data files",
        "",
        "## Team on this task",
        "",
        "_(agents that touched this task will show up as [[wikilinks]] once the audit fires)_",
        "",
    ])


# --- entry point --------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("start", help="start a new task folder")
    ps.add_argument("slug", help="short kebab-safe slug — becomes part of the dir name")
    ps.add_argument("description", nargs="*", help="one-line description (optional)")
    ps.set_defaults(fn=cmd_start)

    pe = sub.add_parser("end", help="end the current task (writes end-time + summary)")
    pe.add_argument("summary", nargs="*", help="one-line summary (optional)")
    pe.set_defaults(fn=cmd_end)

    pl = sub.add_parser("log", help="append a line to who-did-what.md")
    pl.add_argument("who", help="agent name or role")
    pl.add_argument("what", nargs="*", help="what they did")
    pl.set_defaults(fn=cmd_log)

    pc = sub.add_parser("current", help="print the current task directory path")
    pc.set_defaults(fn=cmd_current)

    pt = sub.add_parser("status", help="print status of the current task")
    pt.set_defaults(fn=cmd_status)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
