"""Enumerate Kubernetes manifests to review — from the cloned Git repo and from live cluster
objects — and yield them one document at a time with just enough context for an agent."""
from __future__ import annotations

import logging
import os
import pathlib
import subprocess
from dataclasses import dataclass, field
from typing import Iterator

import yaml

log = logging.getLogger("ai-operator.scanner")

_K8S_KINDS = {
    "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob", "Pod",
    "Service", "Ingress", "ConfigMap", "Secret", "ServiceAccount",
    "Role", "ClusterRole", "RoleBinding", "ClusterRoleBinding",
    "HorizontalPodAutoscaler", "PodDisruptionBudget", "NetworkPolicy",
    "ResourceQuota", "LimitRange", "Gateway", "VirtualService", "PeerAuthentication",
}


@dataclass
class ManifestUnit:
    source: str                       # "git" | "cluster"
    doc: dict                          # the parsed manifest
    file_path: str = ""               # repo-relative (source == git)
    context: dict = field(default_factory=dict)   # usage metrics, memory hits, etc.

    @property
    def kind(self) -> str:
        return self.doc.get("kind", "")

    @property
    def name(self) -> str:
        return self.doc.get("metadata", {}).get("name", "")

    @property
    def namespace(self) -> str | None:
        return self.doc.get("metadata", {}).get("namespace")

    def target_ref(self) -> dict:
        return {
            "apiVersion": self.doc.get("apiVersion", ""),
            "kind": self.kind,
            "name": self.name,
            "namespace": self.namespace,
        }

    def as_yaml(self) -> str:
        return yaml.safe_dump(self.doc, sort_keys=False)


def clone_or_pull(repo_url: str, token: str | None, workspace: str, branch: str = "main") -> str:
    """Clone (or fast-forward) the repo into `workspace`. Returns the checkout path."""
    dest = pathlib.Path(workspace) / "repo"
    url = repo_url
    if token and repo_url.startswith("https://"):
        url = repo_url.replace("https://", f"https://x-access-token:{token}@", 1)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if dest.exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", branch],
                       check=True, env=env, capture_output=True, text=True, timeout=120)
        subprocess.run(["git", "-C", str(dest), "reset", "--hard", f"origin/{branch}"],
                       check=True, env=env, capture_output=True, text=True, timeout=60)
    else:
        subprocess.run(["git", "clone", "--depth", "1", "--branch", branch, url, str(dest)],
                       check=True, env=env, capture_output=True, text=True, timeout=180)
    return str(dest)


def iter_git_manifests(repo_path: str) -> Iterator[ManifestUnit]:
    root = pathlib.Path(repo_path)
    for path in sorted(root.rglob("*.y*ml")):
        if any(part in {".git", "node_modules", "vendor", "charts"} for part in path.parts):
            continue
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            log.debug("skip %s: %s", rel, exc)
            continue
        # skip obvious Helm templates (unrendered {{ }} ) — we review rendered output from the cluster
        if "{{" in text and "}}" in text:
            continue
        try:
            docs = list(yaml.safe_load_all(text))
        except yaml.YAMLError as exc:
            yield ManifestUnit(source="git", doc={"kind": "ParseError", "metadata": {"name": rel}},
                               file_path=rel, context={"error": str(exc)})
            continue
        for d in docs:
            if isinstance(d, dict) and d.get("kind") in _K8S_KINDS:
                yield ManifestUnit(source="git", doc=d, file_path=rel)


def iter_cluster_manifests(kinds: list[str], exclude_ns: set[str]) -> Iterator[ManifestUnit]:
    for kind in kinds:
        r = subprocess.run(
            ["kubectl", "get", kind, "-A", "-o", "yaml"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            log.debug("kubectl get %s failed: %s", kind, r.stderr.strip())
            continue
        try:
            listing = yaml.safe_load(r.stdout) or {}
        except yaml.YAMLError:
            continue
        for item in listing.get("items", []):
            ns = item.get("metadata", {}).get("namespace")
            if ns in exclude_ns:
                continue
            # strip server-side noise before handing to the model
            item.get("metadata", {}).pop("managedFields", None)
            item.pop("status", None)
            yield ManifestUnit(source="cluster", doc=item)


def pod_usage(namespace: str, selector: str) -> dict:
    """Best-effort recent CPU/mem for efficiency findings (needs metrics-server)."""
    r = subprocess.run(
        ["kubectl", "top", "pod", "-n", namespace, "-l", selector, "--no-headers"],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        return {}
    lines = [ln.split() for ln in r.stdout.splitlines() if ln.strip()]
    return {"samples": [{"pod": p[0], "cpu": p[1], "mem": p[2]} for p in lines if len(p) >= 3]}
