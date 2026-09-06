#!/usr/bin/env python3
"""Regenerates .claude/docs/SKILLS_INDEX.md from every skill's actual frontmatter.

Run after adding/removing/renaming a skill so the index never goes stale:
    python3 .claude/scripts/generate-skills-index.py
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .claude/
SKILLS_GLOB = os.path.join(ROOT, "skills", "*", "SKILL.md")
OUT_PATH = os.path.join(ROOT, "docs", "SKILLS_INDEX.md")


def load_skills():
    skills = []
    for f in sorted(glob.glob(SKILLS_GLOB)):
        text = open(f, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        fm = m.group(1) if m else ""
        name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
        desc_m = re.search(r"^description:\s*(.+)$", fm, re.M)
        name = name_m.group(1).strip() if name_m else os.path.basename(os.path.dirname(f))
        desc = desc_m.group(1).strip() if desc_m else ""
        skills.append((name, desc))
    skills.sort(key=lambda x: x[0])
    return skills


def render(skills):
    lines = [
        "# Skills Index",
        "",
        "Every skill in `.claude/skills/`, alphabetical. Regenerate after adding/removing/renaming a "
        "skill:",
        "",
        "```bash",
        "python3 .claude/scripts/generate-skills-index.py",
        "```",
        "",
        f"**Total: {len(skills)} skills.**",
        "",
    ]
    for name, desc in skills:
        lines.append(f"- **[`{name}`](../skills/{name}/SKILL.md)** — {desc}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    skills = load_skills()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(skills))
    print(f"wrote {len(skills)} skills to {OUT_PATH}")
