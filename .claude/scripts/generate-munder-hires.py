#!/usr/bin/env python3
"""
Generate Munder-Difflin hire manifests for our 12 domain managers.

WHY THIS EXISTS. Munder's "hire manifest" (spec: `munder-difflin/hire@1`) is
its portable, sharable format for pre-configured agent roles. Instead of the
user manually filling out the Add-Agent modal 12 times, we generate one
manifest per manager here and the user imports each with a single click.

Michael (the GOD orchestrator) is auto-provisioned by Munder on first launch,
so we do NOT emit a manifest for our own `orchestrator` — the two would
collide. Michael's `claude` process, spawned in this repo's dir, will still
see our `.claude/agents/orchestrator.md` as a sub-agent he can consult; keeping
that file lets any manager that needs orchestration discipline invoke it.

OUTPUTS:
  .claude/munder/hires/<manager>.json     — one hire manifest per manager
  .claude/munder/hires/gallery-index.json — index served by the local gallery

SAFE FIELDS ONLY. Per Munder's security model (see src/shared/hire.ts:HireManifest),
the manifest CANNOT declare skills, MCPs, or arbitrary commands the way our
.claude/ setup uses them. That's fine: Claude Code auto-loads .claude/skills,
.claude/rules, .claude/agents, and .mcp.json from the cwd we point each agent
at, so all our tooling comes in transparently.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Character sheet — see src/renderer/src/scene/office/cast.ts.
# Michael reserved for the auto-provisioned GOD; toby/meredith unassigned.
MANAGER_CHARACTERS: dict[str, str] = {
    "cloud-manager":         "jim",
    "observability-manager": "pam",
    "sre-manager":           "dwight",
    "cicd-manager":          "oscar",
    "terraform-manager":     "angela",
    "linux-manager":         "stanley",
    "docker-manager":        "kevin",
    "github-manager":        "andy",
    "ansible-manager":       "phyllis",
    "aiops-manager":         "kelly",
    "mlops-manager":         "ryan",
    "kubernetes-manager":    "creed",
}

# Accent color per manager — the selection-glow color around the character on
# the floor. Values from src/renderer/src/design/tokens.ts:AccentColorName.
# Chosen so at-a-glance the color hints at the domain (green=infra, blue=cloud,
# coral=fire-fighting/incident, lemon=observability/watch, peach=ml/soft, lilac=meta).
MANAGER_ACCENTS: dict[str, str] = {
    "cloud-manager":         "sky",    # blue = cloud
    "observability-manager": "lemon",  # yellow-glow = watching
    "sre-manager":           "coral",  # red-orange = on-fire discipline
    "cicd-manager":          "mint",   # green = pipelines flowing
    "terraform-manager":     "lilac",  # purple = declarative infra
    "linux-manager":         "peach",  # warm neutral = the base OS
    "docker-manager":        "sky",    # blue-adjacent = shipping containers
    "github-manager":        "mint",   # green = merge success
    "ansible-manager":       "lilac",  # purple = configuration state
    "aiops-manager":         "lemon",  # yellow = alerts + patterns
    "mlops-manager":         "peach",  # warm = model iteration
    "kubernetes-manager":    "coral",  # red = orchestrator chaos
}

# Routing hints per manager — Munder's GOD uses `capabilities` to decide who
# to delegate to. Keep short + domain-flavored; these become the tags Michael
# matches when parsing a user request. Sourced from each manager's frontmatter
# description in .claude/agents/.
CAPABILITIES: dict[str, list[str]] = {
    "cloud-manager":         ["aws", "azure", "gcp", "cloud", "landing-zone", "iam", "networking", "cost"],
    "observability-manager": ["metrics", "logs", "traces", "prometheus", "grafana", "loki", "datadog", "otel"],
    "sre-manager":           ["sli", "slo", "error-budget", "oncall", "incident", "postmortem", "chaos"],
    "cicd-manager":          ["ci", "cd", "pipeline", "release", "artifact", "sast", "sca", "gates"],
    "terraform-manager":     ["terraform", "iac", "state", "modules", "checkov", "tfsec", "plan"],
    "linux-manager":         ["linux", "systemd", "sysctl", "kernel", "package", "service", "cpu-mem-disk"],
    "docker-manager":        ["docker", "container", "image", "dockerfile", "distroless", "cve", "sbom"],
    "github-manager":        ["github", "repo", "branch-protection", "codeowners", "actions", "dependabot"],
    "ansible-manager":       ["ansible", "playbook", "role", "vault", "idempotency", "inventory"],
    "aiops-manager":         ["aiops", "anomaly", "correlation", "alert-noise", "auto-remediation"],
    "mlops-manager":         ["mlops", "training", "experiment", "model-registry", "serving", "drift"],
    "kubernetes-manager":    ["kubernetes", "eks", "aks", "gke", "openshift", "helm", "argo", "kubeadm"],
}

# Per-manager one-line displayed description — hand-written so it fits Munder's
# 200-char cap without mid-word truncation. Falls back to the agent file's
# frontmatter description if a manager is missing from this map.
DESCRIPTIONS: dict[str, str] = {
    "cloud-manager":         "AWS/Azure/GCP architecture — landing zones, IAM, networking, cost. Free-tier-first; $50 CAD/month hard ceiling.",
    "observability-manager": "Metrics/logs/traces/errors stack — Prometheus, Grafana, Loki, Datadog, Dynatrace, OpenTelemetry. Instrument before ship.",
    "sre-manager":           "SRE — SLIs/SLOs/error budgets, on-call rotation, incident response, chaos, load testing. Blameless postmortems.",
    "cicd-manager":          "CI/CD pipeline design — gate placement (SAST/SCA/image/IaC scan), promotion, immutable artifacts, deployment strategies.",
    "terraform-manager":     "Terraform IaC — modules, backend/lock state, plan review, Checkov/tfsec, brownfield reverse-engineering. Never auto-apply.",
    "linux-manager":         "Linux host work — systemd units, resource-pressure debugging (CPU/mem/disk/IO/inodes), sysctl/kernel tuning, packages.",
    "docker-manager":        "Container images — multi-stage builds, hardening (non-root, cap drop), Trivy/Grype scans, SBOM, cosign. Distroless-first.",
    "github-manager":        "GitHub platform — repos, branch protection, CODEOWNERS, PR workflow, Actions, Dependabot, secret & code scanning.",
    "ansible-manager":       "Ansible config management — playbooks, roles, idempotency, static + dynamic inventory, Ansible Vault, molecule tests.",
    "aiops-manager":         "AIOps — anomaly detection over telemetry, alert-noise reduction (grouping/dedup/inhibit), safe auto-remediation.",
    "mlops-manager":         "MLOps — reproducible training, experiment tracking, model registry + promotion, serving (KServe/vLLM), drift detection.",
    "kubernetes-manager":    "Kubernetes across all distros (EKS/AKS/GKE/OpenShift/kubeadm/k3s/kind) — workloads, RBAC, network policy, admission control.",
}

# Per-manager one-line "standing goal" — pre-fills Munder's goal field. Kept
# imperative + narrow so Michael's routing has something concrete to target.
GOALS: dict[str, str] = {
    "cloud-manager":         "Own AWS/Azure/GCP architecture and cost — landing zones, IAM boundaries, budgets. Free-tier-first; hard $50 CAD/month ceiling.",
    "observability-manager": "Own the metrics/logs/traces/errors stack — Prometheus, Grafana, Loki, OTel. Instrument every service before it ships.",
    "sre-manager":           "Own SLIs/SLOs/error budgets, on-call, incident response, chaos testing. Every service ships with an SLO and a runbook.",
    "cicd-manager":          "Own CI/CD pipeline design — gate placement (SAST/SCA/image/IaC scan), promotion, immutable artifacts. No manual deploys.",
    "terraform-manager":     "Own Terraform IaC — modules, state (backend + locking), plan review, Checkov/tfsec gate. Never apply without explicit sign-off.",
    "linux-manager":         "Own Linux host work — systemd units, resource-pressure debugging, sysctl tuning, package/service management. Reproduce-then-fix.",
    "docker-manager":        "Own container images — multi-stage builds, hardening (non-root, capability drop), Trivy/Grype scans, SBOM. Distroless-first.",
    "github-manager":        "Own GitHub — repos, branch protection, CODEOWNERS, Actions workflows, Dependabot/secret scanning. Left-shift security in the repo.",
    "ansible-manager":       "Own Ansible — playbooks, roles, idempotency, Vault, inventory (static + dynamic). Every play converges cleanly on re-run.",
    "aiops-manager":         "Own AIOps — anomaly detection over telemetry, alert noise reduction (grouping/dedup/inhibit), safe auto-remediation. No silent silencing.",
    "mlops-manager":         "Own MLOps — reproducible training, experiment tracking, model registry + promotion, serving, drift detection. Model lineage always intact.",
    "kubernetes-manager":    "Own Kubernetes across all distros (EKS/AKS/GKE/OpenShift/kubeadm/k3s/kind). Workload design, RBAC, network policy, admission control.",
}


def parse_frontmatter_description(agent_file: Path) -> str:
    """Extract the `description:` value from a Claude Code agent's frontmatter.
    Handles values that continue onto the next line up to the next YAML key or
    the closing `---`. Returns empty string on any failure.
    """
    if not agent_file.exists():
        return ""
    text = agent_file.read_text(encoding="utf-8", errors="replace")
    # Frontmatter is between the first two `---` lines.
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    # `description:` may span multiple lines until the next `key:` or end.
    dm = re.search(
        r"^description:\s*(.*?)(?=^\S+:|\Z)",
        fm,
        re.MULTILINE | re.DOTALL,
    )
    if not dm:
        return ""
    # Flatten whitespace and strip trailing pipes/newlines.
    return re.sub(r"\s+", " ", dm.group(1)).strip()


def build_manifest(agent: str, fallback_description: str) -> dict[str, Any]:
    """Build a hire-manifest dict for one manager. Field caps mirror
    src/shared/hire.ts (name ≤40, description ≤200, goal ≤400, capabilities ≤12 items ≤40 each).
    Prefers the hand-written DESCRIPTIONS entry (fits under 200 cleanly);
    falls back to the parsed frontmatter description if a manager is missing
    from that map.
    """
    description = DESCRIPTIONS.get(agent) or fallback_description or f"Domain manager: {agent}"
    return {
        "spec": "munder-difflin/hire@1",
        "name": agent[:40],
        "description": description[:200],
        # Pre-fill character + accent so the user doesn't have to pick them in
        # the modal — one fewer click per hire. Fall back to a safe default so
        # an unmapped manager still validates.
        "character": MANAGER_CHARACTERS.get(agent, "jim"),
        "accent": MANAGER_ACCENTS.get(agent, "sky"),
        "provider": "claude",
        # Leave model unset so each agent picks up the user's default model in
        # Munder's Settings. If they want to pin, they edit the JSON.
        "goal": GOALS.get(agent, f"Own the {agent.replace('-manager','')} domain end-to-end.")[:400],
        "capabilities": CAPABILITIES.get(agent, []),
        # Shared cwd for now — all 12 managers point at this repo. If the user
        # runs into git/session contention, flip this to true per agent to get
        # per-agent worktrees.
        "isolate": False,
        # Per-agent token ceiling — Munder applies this as a runaway guard AFTER
        # spawn. 500K is generous enough for real work but hard-capped so a
        # runaway loop can't drain the subscription.
        "tokenCap": 500_000,
        "author": "vidhya · .claude/scripts/generate-munder-hires.py",
        "homepage": "https://github.com/vidhya101",
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    agents_dir = repo_root / ".claude" / "agents"
    out_dir = repo_root / ".claude" / "munder" / "hires"
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[dict[str, str]] = []
    for agent, character in MANAGER_CHARACTERS.items():
        desc = parse_frontmatter_description(agents_dir / f"{agent}.md")
        manifest = build_manifest(agent, desc)
        (out_dir / f"{agent}.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        written.append({
            "name": agent,
            "character": character,
            "file": f"hires/{agent}.json",
            "goal": manifest["goal"],
        })

    # Gallery index — served by serve-munder-hires.py as the local gallery
    # landing page (a small JSON list Munder's import UI can iterate).
    index = {
        "spec": "munder-difflin/hire-gallery@1",
        "author": "vidhya · .claude/ DevOps team",
        "description": "12 domain-manager hires for a DevOps/SRE/Platform Engineering hive.",
        "agents": written,
    }
    (out_dir / "gallery-index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Generated {len(written)} hire manifests in {out_dir.relative_to(repo_root)}/")
    for w in written:
        print(f"  {w['name']:24s} → character '{w['character']}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
