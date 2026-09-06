#!/usr/bin/env python3
"""
Generate codex-provider fallback hire manifests — one per manager, so Michael
can route work to `<manager>-codex` when the primary claude tier is throttled
or the task is a code-writing chore that doesn't need the top tier.

Uses the same character assignments as the primary hires but:
  - provider: codex (OpenAI Codex CLI)
  - name suffix: `-codex`
  - accent nudged one shade to visually distinguish the fallback on the floor
  - tokenCap halved (fallback tier is for cheaper work by design)

Runs alongside generate-munder-hires.py — both write into
.claude/munder/hires/. The gallery lists the full 24 (12 primary + 12 fallback);
you spawn only the ones you need at any given time.

Manifests are only USABLE once the codex CLI is installed and OPENAI_API_KEY
is set. Run `.claude/scripts/fallback-setup.sh` to check readiness.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Import the primary generator's inventory so we stay in lock-step.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "primary_gen", Path(__file__).resolve().parent / "generate-munder-hires.py"
)
_primary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_primary)  # type: ignore[union-attr]

MANAGER_CHARACTERS = _primary.MANAGER_CHARACTERS
CAPABILITIES = _primary.CAPABILITIES
GOALS = _primary.GOALS
DESCRIPTIONS = _primary.DESCRIPTIONS
parse_frontmatter_description = _primary.parse_frontmatter_description


# One-shade shift so fallback avatars glow differently from their primaries.
# Same 6 accents from src/renderer/src/design/tokens.ts; shift by +1 mod 6.
ACCENT_CYCLE = ["coral", "mint", "sky", "lemon", "lilac", "peach"]

# Reuse the primary accent map from the sibling module.
_primary_accents = _primary.MANAGER_ACCENTS


def fallback_accent(primary: str) -> str:
    try:
        i = ACCENT_CYCLE.index(primary)
        return ACCENT_CYCLE[(i + 1) % len(ACCENT_CYCLE)]
    except ValueError:
        return "coral"


def build_fallback_manifest(agent: str, description: str) -> dict:
    primary_char = MANAGER_CHARACTERS[agent]
    primary_acc = _primary_accents.get(agent, "sky")
    desc = DESCRIPTIONS.get(agent) or description or f"Fallback domain manager: {agent}"
    return {
        "spec": "munder-difflin/hire@1",
        "name": f"{agent}-codex"[:40],
        "description": f"[codex fallback] {desc}"[:200],
        "character": primary_char,
        "accent": fallback_accent(primary_acc),
        "provider": "codex",
        "goal": (f"CODEX FALLBACK for {agent}. "
                 + GOALS.get(agent, f"Own the {agent.replace('-manager','')} domain end-to-end."))[:400],
        "capabilities": CAPABILITIES.get(agent, []) + ["fallback", "codex"],
        # Fallback tier defaults to shared cwd so it sees the same .claude/ setup.
        "isolate": False,
        # Half the primary tokenCap — this tier is meant for cheaper work.
        "tokenCap": 250_000,
        "author": "vidhya · .claude/scripts/generate-fallback-hires.py",
        "homepage": "https://github.com/vidhya101",
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    agents_dir = repo_root / ".claude" / "agents"
    out_dir = repo_root / ".claude" / "munder" / "hires"
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[dict] = []
    for agent in MANAGER_CHARACTERS.keys():
        fb_desc = parse_frontmatter_description(agents_dir / f"{agent}.md")
        manifest = build_fallback_manifest(agent, fb_desc)
        target = out_dir / f"{agent}-codex.json"
        target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        written.append({"name": manifest["name"], "character": manifest["character"],
                        "accent": manifest["accent"], "provider": "codex",
                        "file": f"hires/{agent}-codex.json"})

    print(f"Generated {len(written)} codex-fallback hire manifests")
    for w in written:
        print(f"  {w['name']:24s} char={w['character']:<10} accent={w['accent']}")
    print("\nInstall codex CLI + set OPENAI_API_KEY before importing these:")
    print("  .claude/scripts/fallback-setup.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
