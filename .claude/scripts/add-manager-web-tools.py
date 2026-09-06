#!/usr/bin/env python3
"""
Add `WebFetch` and `WebSearch` tools to the managers that legitimately need
to look things up on the internet — cloud-manager, kubernetes-manager,
observability-manager, sre-manager, aiops-manager, mlops-manager,
cicd-manager, github-manager. Skips managers whose work stays local to
installed skills (linux-manager, docker-manager for image hardening,
ansible-manager, terraform-manager for state, orchestrator itself).

Also skips sub-agents — they operate within a manager's context and inherit
whatever tools the manager has already loaded.

Idempotent: if the manager already has both tools listed, we leave it alone.
If it has one but not the other, we add the missing one.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Managers that BENEFIT from web access — external doc lookup for correctness.
# The list is deliberately narrow: web access = attack surface, so only where
# the value clearly outweighs the risk.
WEB_ENABLED_MANAGERS = {
    "cloud-manager":         "AWS/Azure/GCP docs + pricing pages + service quotas",
    "kubernetes-manager":    "k8s upstream docs, KEPs, distro-specific quirks (EKS/AKS/GKE release notes)",
    "observability-manager": "vendor docs (Datadog/Dynatrace/Grafana), Prometheus RFCs, exporter READMEs",
    "sre-manager":           "SLO calculators, Google SRE book references, incident-response frameworks",
    "aiops-manager":         "vendor anomaly-detection docs, algorithm references",
    "mlops-manager":         "model registry docs, framework compatibility matrices (KServe/vLLM/BentoML)",
    "cicd-manager":          "GHA marketplace, action deprecation notes, semver of runners/actions",
    "github-manager":        "GitHub API docs, action inputs/outputs, branch-protection schema updates",
}

# Managers NOT getting web access — work stays local.
WEB_SKIPPED_MANAGERS = {
    "orchestrator":       "routes only; individual managers do their own research",
    "linux-manager":      "man pages + local docs are canonical; web would be noise",
    "docker-manager":     "Dockerfile reference is stable; scans use local databases",
    "ansible-manager":    "playbooks reference local modules; ansible-galaxy on the CLI already",
    "terraform-manager":  "registry.terraform.io needed but 'terraform providers' + local cache cover most cases",
}


TOOLS_LINE_RE = re.compile(r"^tools:\s*(.*)$", re.MULTILINE)


def has_tool(tools_value: str, tool: str) -> bool:
    """Case-sensitive membership check in a comma-separated `tools:` list."""
    parts = [p.strip() for p in tools_value.split(",")]
    return tool in parts


def add_tools(path: Path, add: list[str]) -> str:
    """Append missing tools to the manager's `tools:` line.
    Returns one of: 'updated', 'unchanged', 'no-tools-line', 'no-frontmatter'.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return "no-frontmatter"

    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return "no-frontmatter"
    fm = m.group(1)
    body_start = m.end()

    tm = TOOLS_LINE_RE.search(fm)
    if not tm:
        return "no-tools-line"

    current = tm.group(1).strip()
    missing = [t for t in add if not has_tool(current, t)]
    if not missing:
        return "unchanged"

    new_tools_value = current.rstrip(",")
    for t in missing:
        new_tools_value = new_tools_value + ", " + t

    new_fm = TOOLS_LINE_RE.sub(f"tools: {new_tools_value}", fm, count=1)
    new_text = "---\n" + new_fm + "\n---\n" + text[body_start:]
    path.write_text(new_text, encoding="utf-8")
    return "updated"


def main() -> int:
    agents_dir = Path(__file__).resolve().parents[2] / ".claude" / "agents"

    counts = {"updated": 0, "unchanged": 0, "no-tools-line": 0, "no-frontmatter": 0, "missing": 0}

    print("Enabling web tools on managers that need them:")
    for name, why in WEB_ENABLED_MANAGERS.items():
        path = agents_dir / f"{name}.md"
        if not path.exists():
            print(f"  missing:      {name}.md")
            counts["missing"] += 1
            continue
        result = add_tools(path, ["WebFetch", "WebSearch"])
        marker = {"updated": "✓ added ",
                  "unchanged": "· already ",
                  "no-tools-line": "! no-line",
                  "no-frontmatter": "! no-fm  "}[result]
        print(f"  {marker} {name:24s}  ({why})")
        counts[result] += 1

    print()
    print("Skipped (deliberately no web access):")
    for name, why in WEB_SKIPPED_MANAGERS.items():
        print(f"  · {name:24s}  {why}")

    print()
    total_ok = counts["updated"] + counts["unchanged"]
    print(f"Result: {counts['updated']} newly enabled · {counts['unchanged']} already had it · "
          f"{total_ok}/{len(WEB_ENABLED_MANAGERS)} target managers configured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
