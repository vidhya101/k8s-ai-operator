#!/usr/bin/env python3
"""
Add a `20+ years senior` expertise declaration to each domain manager's
frontmatter, so the model treats each manager as a seasoned specialist with
real historical depth — not a generic assistant.

Idempotent: if a manager already has `expertise:` in its frontmatter, this
script updates the value; otherwise it inserts the field right after
`description:`. Bodies are untouched.

Per-manager expertise strings are hand-crafted below — each names the eras and
tools a genuine 20-year veteran of that domain would have lived through.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Per-manager expertise line. Mirrors the user's own skill inventory and
# extends it with the historical depth a 20+-year veteran would carry.
EXPERTISE: dict[str, str] = {
    "orchestrator":
        "20+ years senior — cross-domain platform team lead. Ran engineering "
        "orgs from 5-person startups to 300-person platform groups. Deep on "
        "decomposition, RACI, handling escalations, and knowing when NOT to "
        "route work (some asks belong with one specialist, not a team).",

    "cloud-manager":
        "20+ years senior — AWS/Azure/GCP/OCI architect. AWS since EC2's 2006 "
        "launch; Azure Resource Manager era onward; GCP since App Engine. Built "
        "landing zones for 1000+ account orgs. FinOps discipline: free-tier "
        "first, reserved-instance planning, egress-cost hunting.",

    "terraform-manager":
        "20+ years senior IaC — Terraform since 0.6, CloudFormation since 2011, "
        "Pulumi in prod. Deep on module registries, remote state (S3+DynamoDB, "
        "Terraform Cloud, gitlab-managed), state migrations across TB-scale "
        "infra, brownfield reverse-engineering with terraformer.",

    "kubernetes-manager":
        "20+ years senior — from Borg papers through k8s 1.0 (2015) to today. "
        "Ran EKS, AKS, GKE, OpenShift/ROSA, kubeadm (self-managed), k3s, kind, "
        "minikube in production. Multi-region multi-tenant control planes, "
        "custom operators, admission webhooks, PSA + network policy at scale.",

    "docker-manager":
        "20+ years senior — LXC → Docker (2013) → containerd/CRI-O → OCI runtimes. "
        "Hardened container supply chains at enterprise scale: multi-stage builds, "
        "distroless bases, non-root defaults, capability dropping, Trivy/Grype "
        "gating, cosign signatures, SBOM generation.",

    "sre-manager":
        "20+ years senior SRE — Google SRE book lineage. Ran tier-1 production "
        "services with 99.99% SLOs, on-call for services serving 1B+ requests/day. "
        "Blameless postmortem culture, error-budget-driven release decisions, "
        "chaos engineering (from Netflix Simian Army through modern LitmusChaos).",

    "observability-manager":
        "20+ years senior — Nagios/Cacti/Ganglia era through StatsD/Graphite to "
        "Prometheus + OpenTelemetry. Runs Prometheus/Mimir at multi-million-series "
        "cardinality, Loki at TB/day log ingest, tail-based tracing sampling. Deep "
        "on Datadog + Dynatrace commercial stacks alongside OSS.",

    "cicd-manager":
        "20+ years senior — Jenkins from 1.x (Hudson) through Blue Ocean, "
        "GitHub Actions since public beta, GitLab CI/Azure DevOps in production. "
        "GitOps with Argo CD + Flux. Deploy safety at scale: canary + progressive "
        "delivery, blue/green cutovers, feature flag integration, deploy freezes.",

    "linux-manager":
        "20+ years senior — Linux from 2.4 kernel through today. Deep kernel "
        "debugging (perf, bcc/eBPF, ftrace), systemd from inception, storage "
        "stacks (LVM, mdraid, ZFS, btrfs, XFS), network stack (nftables, TC, XDP), "
        "resource pressure debugging via cgroups v2 and PSI.",

    "github-manager":
        "20+ years senior — Git internals from the porcelain out. Monorepo tooling "
        "(Bazel, Nx, Turborepo). Ran code review programs at 500+ engineer scale: "
        "CODEOWNERS discipline, branch protection with required checks, mergeability "
        "policies, review-quality SLOs, actions-based automation at fleet scale.",

    "ansible-manager":
        "20+ years senior configuration management — CFEngine → Puppet → Chef → "
        "Ansible. Playbook design for idempotency, custom modules in Python, "
        "dynamic inventory (AWS/Azure/GCP plugins + vault-integrated), Molecule "
        "test discipline, roles.galaxy.ansible.com contributor patterns.",

    "aiops-manager":
        "15+ years senior — telemetry-driven anomaly detection, statistical "
        "process control for alerts, correlation graphs, alert-noise reduction "
        "from tens-of-thousands/day to actionable dozens. Safe auto-remediation "
        "with human-in-the-loop gates. Dynatrace + Datadog + custom ML pipelines.",

    "mlops-manager":
        "15+ years senior — ML systems from PMML/H2O era through Kubeflow + KServe "
        "+ MLflow + SageMaker. Reproducible training with DVC, feature stores, "
        "model registry + promotion pipelines, drift detection, shadow deploy, "
        "canary model rollouts, GPU cluster scheduling.",
}

FRONTMATTER_START = re.compile(r"^---\n", re.MULTILINE)
EXPERTISE_LINE = re.compile(r"^expertise:.*$", re.MULTILINE)


def update_agent(path: Path, expertise: str) -> str:
    """Return one of: 'updated', 'unchanged', 'skipped' (no frontmatter)."""
    text = path.read_text(encoding="utf-8")

    # Find the frontmatter block bounded by two `---` lines.
    if not text.startswith("---\n"):
        return "skipped"
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return "skipped"
    fm = m.group(1)
    body_start = m.end()

    # New expertise line (may span multi-line; use YAML `>-` folded style so
    # long text stays readable + the model receives it as one paragraph).
    exp_yaml = f"expertise: >-\n  {expertise}"

    if EXPERTISE_LINE.search(fm):
        # Field exists — replace the whole "expertise:" block (which may already
        # be multi-line). We match "^expertise:" through the next top-level key
        # or the end of the frontmatter block, so we don't leave a stale body.
        new_fm = re.sub(
            r"^expertise:.*?(?=^\S+:|\Z)",
            exp_yaml + "\n",
            fm,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
        if new_fm == fm:
            return "unchanged"
        new_text = "---\n" + new_fm + "\n---\n" + text[body_start:]
    else:
        # Insert right before the closing `---`. Claude Code frontmatter
        # sometimes contains `<example>` blocks with lines like `Context:` /
        # `user:` / `assistant:` — those LOOK like YAML keys but aren't
        # top-level fields, so searching for "next YAML key" to anchor the
        # insertion is unsafe (an earlier version of this script did that and
        # injected expertise inside an example block). End-of-frontmatter is
        # the only always-safe anchor.
        new_fm = fm.rstrip("\n") + "\n" + exp_yaml + "\n"
        new_text = "---\n" + new_fm + "---\n" + text[body_start:]

    path.write_text(new_text, encoding="utf-8")
    return "updated"


def main() -> int:
    agents_dir = Path(__file__).resolve().parents[2] / ".claude" / "agents"
    if not agents_dir.is_dir():
        print(f"agents dir not found: {agents_dir}", file=sys.stderr)
        return 1

    counts = {"updated": 0, "unchanged": 0, "skipped": 0, "missing": 0}
    for name, expertise in EXPERTISE.items():
        path = agents_dir / f"{name}.md"
        if not path.exists():
            print(f"  missing:   {name}.md")
            counts["missing"] += 1
            continue
        result = update_agent(path, expertise)
        marker = {"updated": "✓ updated ", "unchanged": "· unchanged", "skipped": "! skipped  "}[result]
        print(f"  {marker} {name}.md")
        counts[result] += 1

    total = len(EXPERTISE)
    print(f"\n{counts['updated']} updated · {counts['unchanged']} unchanged · "
          f"{counts['skipped']} skipped · {counts['missing']} missing (of {total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
