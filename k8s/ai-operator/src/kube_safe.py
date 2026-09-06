"""safe_apply: the only path by which the operator changes the cluster.

    snapshot current  ->  dry-run (server)  ->  policy check (admission)  ->
    non-destructive diff  ->  apply (server-side)  ->  verify  ->  outcome

Any failure stops before apply (or rolls the Remediation to Failed/AwaitingHuman). LLM output is
never applied raw."""
from __future__ import annotations

import base64
import datetime as dt
import json
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any

import yaml

log = logging.getLogger("ai-operator.kube_safe")

# subresources/fields kubectl or controllers add and that we don't count as "removed by us"
_IGNORE_PREFIXES = (
    "metadata.managedFields", "metadata.resourceVersion", "metadata.uid",
    "metadata.generation", "metadata.creationTimestamp", "metadata.annotations.kubectl.kubernetes.io/last-applied-configuration",
    "status",
)

PROTECTED_KINDS = {
    "Namespace", "PersistentVolumeClaim", "PersistentVolume", "CustomResourceDefinition",
    "Node", "Secret", "Role", "ClusterRole", "RoleBinding", "ClusterRoleBinding",
    "ValidatingWebhookConfiguration", "MutatingWebhookConfiguration",
}


class SafeApplyError(RuntimeError):
    pass


@dataclass
class ApplyResult:
    ok: bool
    phase: str                       # Validated | AwaitingHuman | Applied | Verified | Failed
    backup_ref: str = ""
    messages: list[str] = field(default_factory=list)
    dry_run_ok: bool = False
    policy_ok: bool = False
    non_destructive: bool = False


def _kubectl(args: list[str], stdin: str | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["kubectl", *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=120,
        check=check,
    )


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def _ignored(path: str) -> bool:
    return any(path == p or path.startswith(p + ".") or path.startswith(p + "[") for p in _IGNORE_PREFIXES)


def get_live(api_version: str, kind: str, name: str, namespace: str | None) -> dict[str, Any] | None:
    args = ["get", f"{kind}.{api_version.split('/')[0]}" if "/" in api_version else kind, name, "-o", "json"]
    if namespace:
        args += ["-n", namespace]
    r = _kubectl(args)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def snapshot(target: dict[str, Any], namespace_ops: str) -> str:
    """Store the current object (if it exists) as a ConfigMap `<kind>-<name>-backup-<ts>` in the
    operator namespace. Returns the backup ref, or 'none:new-object' if it doesn't exist yet."""
    live = get_live(target["apiVersion"], target["kind"], target["name"], target.get("namespace"))
    if live is None:
        return "none:new-object"
    live.get("metadata", {}).pop("managedFields", None)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cm_name = f"bak-{target['kind'].lower()}-{target['name']}-{ts}"[:253]
    body = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": cm_name,
            "namespace": namespace_ops,
            "labels": {"app.kubernetes.io/name": "ai-operator", "ai-operator.io/backup": "true"},
            "annotations": {
                "ai-operator.io/of": f"{target['kind']}/{target.get('namespace','')}/{target['name']}",
            },
        },
        "data": {"object.yaml": yaml.safe_dump(live, sort_keys=False)},
    }
    r = _kubectl(["apply", "--server-side", "-f", "-"], stdin=yaml.safe_dump(body))
    if r.returncode != 0:
        raise SafeApplyError(f"could not write backup: {r.stderr.strip()}")
    return f"configmap/{namespace_ops}/{cm_name}"


def dry_run(manifest_yaml: str) -> tuple[bool, list[str]]:
    r = _kubectl(["apply", "--server-side", "--dry-run=server", "-f", "-"], stdin=manifest_yaml)
    ok = r.returncode == 0
    msgs = [line for line in (r.stdout + r.stderr).splitlines() if line.strip()]
    return ok, msgs


def policy_check(manifest_yaml: str) -> tuple[bool, list[str]]:
    """Kyverno/Gatekeeper run as admission webhooks, so a server dry-run already exercises them.
    This is a second explicit pass with `kubectl apply --dry-run=server --warnings-as-errors` so a
    policy *warning* also blocks auto-apply (a human can still choose to proceed via a PR)."""
    r = _kubectl(
        ["apply", "--server-side", "--dry-run=server", "--warnings-as-errors", "-f", "-"],
        stdin=manifest_yaml,
    )
    ok = r.returncode == 0
    msgs = [ln for ln in (r.stdout + r.stderr).splitlines() if "Warning" in ln or "error" in ln.lower()]
    return ok, msgs


def non_destructive(current: dict[str, Any] | None, proposed: dict[str, Any]) -> tuple[bool, list[str]]:
    """True iff `proposed` does not REMOVE any data-bearing field that exists in `current`.
    Additions and value changes are fine. New objects are trivially non-destructive."""
    if current is None:
        return True, []
    cur_flat = _flatten(current)
    new_flat = _flatten(proposed)
    removed = [
        p for p in cur_flat
        if p not in new_flat and not _ignored(p)
        and (p.startswith("spec") or p.startswith("data") or p.startswith("rules")
             or p.startswith("webhooks") or p.startswith("stringData"))
    ]
    return (len(removed) == 0), removed


def apply(manifest_yaml: str) -> tuple[bool, list[str]]:
    r = _kubectl(["apply", "--server-side", "--field-manager=ai-operator", "-f", "-"], stdin=manifest_yaml)
    return r.returncode == 0, [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]


def verify(target: dict[str, Any]) -> tuple[bool, str]:
    """Light verification: the object exists and, for workloads, isn't worse than before."""
    live = get_live(target["apiVersion"], target["kind"], target["name"], target.get("namespace"))
    if live is None:
        return False, "object not found after apply"
    conds = {c.get("type"): c.get("status") for c in live.get("status", {}).get("conditions", [])}
    if target["kind"] in ("Deployment", "StatefulSet"):
        if conds.get("Available") == "False":
            return False, f"{target['kind']} Available=False after apply"
    return True, "ok"


def safe_apply(
    proposed_manifest_yaml: str,
    *,
    namespace_ops: str,
    allow_protected: bool = False,
) -> ApplyResult:
    try:
        proposed = yaml.safe_load(proposed_manifest_yaml)
    except yaml.YAMLError as exc:
        return ApplyResult(False, "Failed", messages=[f"proposed manifest is not valid YAML: {exc}"])

    kind = proposed.get("kind", "")
    md = proposed.get("metadata", {})
    target = {
        "apiVersion": proposed.get("apiVersion", ""),
        "kind": kind,
        "name": md.get("name", ""),
        "namespace": md.get("namespace"),
    }

    if kind in PROTECTED_KINDS and not allow_protected:
        return ApplyResult(False, "AwaitingHuman",
                           messages=[f"{kind} is protected — routed to a human (GitOps PR)"])

    res = ApplyResult(False, "Failed")

    # 1. dry-run
    res.dry_run_ok, dr_msgs = dry_run(proposed_manifest_yaml)
    res.messages += dr_msgs
    if not res.dry_run_ok:
        res.phase = "Failed"
        return res

    # 2. policy (warnings-as-errors)
    res.policy_ok, pol_msgs = policy_check(proposed_manifest_yaml)
    res.messages += pol_msgs
    if not res.policy_ok:
        res.phase = "AwaitingHuman"      # a policy said no / warned — let a human decide via PR
        return res

    # 3. non-destructive diff vs live
    current = get_live(target["apiVersion"], target["kind"], target["name"], target.get("namespace"))
    res.non_destructive, removed = non_destructive(current, proposed)
    if not res.non_destructive:
        res.messages.append("would remove existing field(s): " + ", ".join(removed[:20]))
        res.phase = "AwaitingHuman"
        return res

    # 4. backup
    try:
        res.backup_ref = snapshot(target, namespace_ops)
    except SafeApplyError as exc:
        res.messages.append(str(exc))
        res.phase = "Failed"
        return res

    # 5. apply
    applied, ap_msgs = apply(proposed_manifest_yaml)
    res.messages += ap_msgs
    if not applied:
        res.phase = "Failed"
        return res
    res.phase = "Applied"

    # 6. verify
    ok, why = verify(target)
    res.messages.append(f"verify: {why}")
    res.ok = ok
    res.phase = "Verified" if ok else "Failed"
    return res


def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()
