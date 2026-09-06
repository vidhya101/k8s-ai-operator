#!/usr/bin/env python3
"""Regenerates .claude/dashboard/team-dashboard.html from the actual agent files.

Reads every .claude/agents/*.md (except TEAM_ROSTER.md), pulls name + description
from frontmatter, classifies into categories per TEAM_ROSTER's org structure,
and emits a self-contained HTML dashboard (no external deps, opens in any browser).

Regenerate whenever agents are added/removed/renamed:
    python3 .claude/scripts/generate-team-dashboard.py
"""
import glob
import json
import os
import re
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .claude/
AGENTS_DIR = os.path.join(ROOT, "agents")
OUT_PATH = os.path.join(ROOT, "dashboard", "team-dashboard.html")

# Category classification — matches TEAM_ROSTER.md structure exactly.
DESIGN_LAYER = {"designer", "critic", "system-designer", "backend-engineer", "frontend-engineer"}
IMPL_LAYER = {"code-writer-python", "code-writer-go", "code-writer-java",
              "code-writer-javascript", "code-writer-typescript"}
REVIEW_LAYER = {"code-reviewer", "bug-hunter", "code-simplifier",
                "yaml-config-reviewer", "port-security-auditor"}
VERIFY_LAYER = {"tester", "sandbox-verifier"}
NEW_SPECIALIST = {"network-engineer", "ai-engineer", "data-scientist",
                  "technical-writer", "oracle-expert"}


def classify(name: str) -> str:
    """Return the category slug for an agent name."""
    if name == "orchestrator":
        return "orchestrator"
    if name.endswith("-manager"):
        return "manager"
    if name in DESIGN_LAYER:
        return "design"
    if name in IMPL_LAYER:
        return "implementation"
    if name in REVIEW_LAYER:
        return "review"
    if name in VERIFY_LAYER:
        return "verification"
    if name in NEW_SPECIALIST:
        return "specialist"
    return "existing-specialist"


# Human labels + colors per category.
CATEGORIES = [
    ("orchestrator",         "Top-level router",               "#8b5cf6"),
    ("manager",              "Domain managers",                "#3b82f6"),
    ("design",               "Design layer",                   "#06b6d4"),
    ("implementation",       "Implementation layer (coders)",  "#10b981"),
    ("review",               "Review layer (parallel)",        "#f59e0b"),
    ("verification",         "Verification",                   "#eab308"),
    ("specialist",           "Cross-cutting specialists",      "#ec4899"),
    ("existing-specialist",  "Existing specialists",           "#64748b"),
]

# Delegation edges — matches TEAM_ROSTER.md's "standard delegation chain" + cross-manager patterns.
# format: (from_name, to_name, label) — label shown on hover.
EDGES = [
    # Orchestrator → managers
    ("orchestrator", "linux-manager",         "cross-domain routing"),
    ("orchestrator", "github-manager",        "cross-domain routing"),
    ("orchestrator", "docker-manager",        "cross-domain routing"),
    ("orchestrator", "cicd-manager",          "cross-domain routing"),
    ("orchestrator", "ansible-manager",       "cross-domain routing"),
    ("orchestrator", "terraform-manager",     "cross-domain routing"),
    ("orchestrator", "cloud-manager",         "cross-domain routing"),
    ("orchestrator", "kubernetes-manager",    "cross-domain routing"),
    ("orchestrator", "aiops-manager",         "cross-domain routing"),
    ("orchestrator", "mlops-manager",         "cross-domain routing"),
    ("orchestrator", "sre-manager",           "cross-domain routing"),
    ("orchestrator", "observability-manager", "cross-domain routing"),
    # Standard delegation chain — every manager can invoke these
    # (rendered as "delegation pool" edges rather than N x M explicit lines)
]

# Managers' domain-specific existing specialists they delegate to
MANAGER_SPECIALISTS = {
    "aiops-manager":         ["aiops-reviewer"],
    "mlops-manager":         ["mlops-reviewer", "data-engineering-reviewer"],
    "docker-manager":        ["docker-reviewer"],
    "github-manager":        ["github-actions-reviewer"],
    "cicd-manager":          ["github-actions-reviewer"],
    "kubernetes-manager":    ["kubernetes-debugger", "principal-platform-engineer"],
    "observability-manager": ["observability-engineer"],
    "cloud-manager":         ["principal-cloud-architect", "principal-finops-engineer",
                              "principal-platform-engineer"],
    "sre-manager":           ["principal-sre", "production-incident-commander"],
    "terraform-manager":     ["terraform-reviewer"],
}


def parse_frontmatter(path: str) -> tuple[str, str]:
    """Extract (name, description) from an agent .md file's YAML frontmatter."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    fm = m.group(1) if m else ""
    name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc_m = re.search(r"^description:\s*(.+?)(?=\n\S|\n\n|\Z)", fm, re.M | re.S)
    name = name_m.group(1).strip() if name_m else os.path.splitext(os.path.basename(path))[0]
    desc = desc_m.group(1).strip().replace("\n", " ") if desc_m else ""
    # description may run into <example> tags — cut at first < or after 300 chars
    desc = desc.split("<")[0].strip()
    if len(desc) > 400:
        desc = desc[:397] + "..."
    return name, desc


def load_agents() -> list[dict]:
    """Load every agent file, return list of {name, desc, category}."""
    agents = []
    for path in sorted(glob.glob(os.path.join(AGENTS_DIR, "*.md"))):
        if os.path.basename(path) == "TEAM_ROSTER.md":
            continue
        name, desc = parse_frontmatter(path)
        agents.append({
            "name": name,
            "desc": desc,
            "category": classify(name),
        })
    # Add manager→specialist edges based on MANAGER_SPECIALISTS
    for mgr, specs in MANAGER_SPECIALISTS.items():
        for s in specs:
            EDGES.append((mgr, s, "delegates domain review to"))
    return agents


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Team Roster — DevOps AI Team ({total} agents)</title>
<style>
  :root {{
    --bg: #0f172a;
    --panel: #1e293b;
    --panel-hi: #334155;
    --border: #334155;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #6366f1;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --panel-hi: #f1f5f9;
      --border: #cbd5e1;
      --text: #0f172a;
      --text-dim: #475569;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    background: var(--bg);
    color: var(--text);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  header {{
    padding: 20px 32px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 16px;
  }}
  header h1 {{
    margin: 0; font-size: 20px; font-weight: 600;
  }}
  header .meta {{
    color: var(--text-dim); font-size: 13px;
  }}
  header .controls {{
    display: flex; gap: 12px; align-items: center;
  }}
  #search {{
    padding: 8px 12px;
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    font: inherit;
    min-width: 240px;
  }}
  #search:focus {{
    outline: none;
    border-color: var(--accent);
  }}
  main {{
    padding: 24px 32px;
    max-width: 1400px;
    margin: 0 auto;
  }}
  .row {{
    margin-bottom: 32px;
  }}
  .row-header {{
    display: flex; align-items: baseline; gap: 12px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
  }}
  .row-title {{
    font-size: 15px; font-weight: 600; letter-spacing: 0.02em;
  }}
  .row-count {{
    color: var(--text-dim); font-size: 12px;
  }}
  .row-swatch {{
    width: 12px; height: 12px; border-radius: 3px; display: inline-block;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }}
  .agent-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-left-width: 4px;
    border-radius: 6px;
    padding: 12px 14px;
    cursor: pointer;
    transition: background 0.12s, transform 0.12s;
    display: flex; flex-direction: column; gap: 6px;
    min-height: 74px;
  }}
  .agent-card:hover {{
    background: var(--panel-hi);
    transform: translateY(-1px);
  }}
  .agent-name {{
    font-weight: 600; font-size: 13px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  .agent-desc {{
    color: var(--text-dim); font-size: 12px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .agent-card.dim {{
    opacity: 0.25;
  }}
  /* Modal */
  #modal-backdrop {{
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.6);
    display: none;
    align-items: center; justify-content: center;
    z-index: 100;
    padding: 24px;
  }}
  #modal-backdrop.open {{ display: flex; }}
  #modal {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    max-width: 720px; width: 100%;
    max-height: 82vh;
    overflow-y: auto;
    padding: 24px 28px;
  }}
  #modal h2 {{
    margin: 0 0 4px; font-family: ui-monospace, monospace;
    font-size: 20px;
  }}
  #modal .category-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.03em; text-transform: uppercase;
    color: white;
    margin-bottom: 16px;
  }}
  #modal .modal-desc {{
    color: var(--text); line-height: 1.65;
    margin-bottom: 20px;
  }}
  #modal h3 {{
    margin: 20px 0 8px; font-size: 13px; font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.04em;
  }}
  #modal .rel-list {{
    display: flex; flex-wrap: wrap; gap: 6px;
  }}
  #modal .rel-item {{
    padding: 4px 10px;
    background: var(--panel-hi);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: ui-monospace, monospace;
    font-size: 12px;
    cursor: pointer;
  }}
  #modal .rel-item:hover {{
    border-color: var(--accent);
    color: var(--accent);
  }}
  #modal .close {{
    position: sticky; top: 0; float: right;
    background: transparent; border: none;
    color: var(--text-dim); font-size: 24px; cursor: pointer;
    line-height: 1;
  }}
  #modal .close:hover {{ color: var(--text); }}
  footer {{
    padding: 24px 32px;
    color: var(--text-dim);
    font-size: 12px;
    border-top: 1px solid var(--border);
    text-align: center;
  }}
  footer code {{
    background: var(--panel-hi);
    padding: 2px 6px; border-radius: 3px;
  }}
</style>
</head>
<body>

<header>
  <div>
    <h1>DevOps AI Team</h1>
    <div class="meta">{total} agents · regenerate with <code>python3 .claude/scripts/generate-team-dashboard.py</code></div>
  </div>
  <div class="controls">
    <input id="search" type="search" placeholder="Filter by name or description…" autocomplete="off">
  </div>
</header>

<main id="floors">
  {rows}
</main>

<footer>
  Click any agent for full description + who invokes them + who they invoke.
  Data source: <code>.claude/agents/*.md</code> frontmatter. Categories: <code>.claude/agents/TEAM_ROSTER.md</code>.
</footer>

<div id="modal-backdrop">
  <div id="modal">
    <button class="close" onclick="closeModal()">×</button>
    <h2 id="modal-name"></h2>
    <div class="category-badge" id="modal-badge"></div>
    <div class="modal-desc" id="modal-desc"></div>
    <h3>Delegates to</h3>
    <div class="rel-list" id="modal-out"></div>
    <h3>Invoked by</h3>
    <div class="rel-list" id="modal-in"></div>
  </div>
</div>

<script>
const AGENTS = {agents_json};
const EDGES = {edges_json};
const CATS = {cats_json};
const catLookup = Object.fromEntries(CATS.map(c => [c[0], c]));

const byName = Object.fromEntries(AGENTS.map(a => [a.name, a]));
const outEdges = {{}}, inEdges = {{}};
for (const [from, to, label] of EDGES) {{
  (outEdges[from] ||= []).push([to, label]);
  (inEdges[to]  ||= []).push([from, label]);
}}

function openModal(name) {{
  const a = byName[name];
  if (!a) return;
  const [_, catLabel, catColor] = catLookup[a.category];
  document.getElementById("modal-name").textContent = name;
  const badge = document.getElementById("modal-badge");
  badge.textContent = catLabel;
  badge.style.background = catColor;
  document.getElementById("modal-desc").textContent = a.desc || "(no description)";
  document.getElementById("modal-out").innerHTML =
    (outEdges[name] || []).map(([n, l]) =>
      `<span class="rel-item" onclick="openModal('${{n}}')" title="${{l}}">${{n}}</span>`
    ).join("") || '<span style="color:var(--text-dim); font-size:12px;">— none defined —</span>';
  document.getElementById("modal-in").innerHTML =
    (inEdges[name] || []).map(([n, l]) =>
      `<span class="rel-item" onclick="openModal('${{n}}')" title="${{l}}">${{n}}</span>`
    ).join("") || '<span style="color:var(--text-dim); font-size:12px;">— any manager can invoke via the standard chain —</span>';
  document.getElementById("modal-backdrop").classList.add("open");
}}

function closeModal() {{
  document.getElementById("modal-backdrop").classList.remove("open");
}}

document.getElementById("modal-backdrop").addEventListener("click", (e) => {{
  if (e.target.id === "modal-backdrop") closeModal();
}});
document.addEventListener("keydown", (e) => {{
  if (e.key === "Escape") closeModal();
}});

const searchInput = document.getElementById("search");
searchInput.addEventListener("input", () => {{
  const q = searchInput.value.trim().toLowerCase();
  for (const card of document.querySelectorAll(".agent-card")) {{
    const match = !q || card.dataset.search.includes(q);
    card.classList.toggle("dim", !match);
  }}
}});
</script>
</body>
</html>
"""


def render_row(cat_slug: str, cat_label: str, cat_color: str, agents: list[dict]) -> str:
    """Render one category row."""
    if not agents:
        return ""
    cards = []
    for a in agents:
        search = (a["name"] + " " + a["desc"]).lower().replace('"', "&quot;")
        cards.append(
            f'<div class="agent-card" style="border-left-color:{cat_color}" '
            f'data-search="{escape(search, quote=True)}" '
            f'onclick="openModal(\'{a["name"]}\')">'
            f'<div class="agent-name">{escape(a["name"])}</div>'
            f'<div class="agent-desc">{escape(a["desc"])}</div>'
            f'</div>'
        )
    return f"""
  <section class="row">
    <div class="row-header">
      <span class="row-swatch" style="background:{cat_color}"></span>
      <span class="row-title">{escape(cat_label)}</span>
      <span class="row-count">{len(agents)}</span>
    </div>
    <div class="grid">{''.join(cards)}</div>
  </section>"""


def main():
    agents = load_agents()
    total = len(agents)
    by_cat = {slug: [] for slug, _, _ in CATEGORIES}
    for a in agents:
        by_cat[a["category"]].append(a)

    rows = "".join(
        render_row(slug, label, color, by_cat[slug])
        for slug, label, color in CATEGORIES
    )

    html = HTML_TEMPLATE.format(
        total=total,
        rows=rows,
        agents_json=json.dumps(agents),
        edges_json=json.dumps(EDGES),
        cats_json=json.dumps(CATEGORIES),
    )

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"wrote {total} agents to {OUT_PATH}")
    print(f"  file size: {os.path.getsize(OUT_PATH):,} bytes")
    print(f"open with: open {OUT_PATH}")


if __name__ == "__main__":
    main()
