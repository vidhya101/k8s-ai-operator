"""ai-operator — cooperating in-cluster agents on local Ollama.

kopf handlers:
  * timer on ai-operator-config  -> full scan sweep (scanner + security -> Finding CRs)
  * on.create findings           -> coordinator triage -> Remediation CR or AwaitingHuman
  * on.create/resume remediations-> remediator fills the change -> safe_apply OR gitops PR
  * timer (hourly)               -> write agent-memory-digest ConfigMap

Everything the operator writes to the cluster goes through kube_safe.safe_apply().
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time

import kopf
import yaml
from kubernetes import client, config as kconfig

import kube_safe
import scanner as scan
from agents import AgentRegistry, ConfigView
from memory import Memory
from ollama_client import OllamaClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ai-operator")

NS = os.environ.get("POD_NAMESPACE", "ai-operator")
GROUP, VERSION = "ai-operator.io", "v1alpha1"
CONFIG_MAP = os.environ.get("CONFIG_MAP", "ai-operator-config")
MEMORY_DB = os.environ.get("MEMORY_DB", "/memory/agent.db")
WORKSPACE = os.environ.get("WORKSPACE", "/workspace")

_state: dict = {}          # holds ollama, memory, registry, cfg — set in startup


# ==================================================================================================
# lifecycle
# ==================================================================================================
@kopf.on.startup()
async def startup(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.INFO
    settings.persistence.finalizer = "ai-operator.io/finalizer"
    try:
        kconfig.load_incluster_config()
    except kconfig.ConfigException:
        kconfig.load_kube_config()

    cfg = ConfigView()
    _refresh_config(cfg)

    ollama = OllamaClient(
        host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        timeout=cfg.int("ollamaTimeoutSeconds", 180),
        max_concurrent=cfg.int("ollamaMaxConcurrent", 2),
    )
    if not await ollama.health():
        log.warning(json.dumps({"lvl": "warn", "msg": "Ollama not reachable at startup",
                                "host": os.environ.get("OLLAMA_HOST")}))
    memory = Memory(MEMORY_DB)
    registry = AgentRegistry(ollama, memory, cfg)

    _state.update(ollama=ollama, memory=memory, registry=registry, cfg=cfg,
                  core=client.CoreV1Api(), custom=client.CustomObjectsApi(),
                  apps=client.AppsV1Api())
    log.info(json.dumps({"lvl": "info", "msg": "ai-operator started",
                         "agents": [a.name for a in registry.all()],
                         "mode": cfg.get("mode"), "ollama_models": await ollama.list_models()}))


@kopf.on.cleanup()
async def cleanup(**_):
    if _state.get("ollama"):
        await _state["ollama"].aclose()
    if _state.get("memory"):
        _state["memory"].close()


def _refresh_config(cfg: ConfigView) -> None:
    try:
        core = client.CoreV1Api()
        cm = core.read_namespaced_config_map(CONFIG_MAP, NS)
        cfg.update(cm.data or {})
    except client.ApiException as exc:
        log.warning(json.dumps({"lvl": "warn", "msg": "config read failed", "err": str(exc)}))


def _halted(cfg: ConfigView) -> str | None:
    if cfg.bool("paused"):
        return "paused"
    if cfg.bool("requireHealthyControlPlane", True):
        r = kube_safe._kubectl(["get", "--raw", "/readyz"])
        if r.returncode != 0:
            return "control-plane-unhealthy"
    return None


# ==================================================================================================
# 1. periodic scan sweep
# ==================================================================================================
@kopf.timer("v1", "configmaps", field="metadata.name", value=CONFIG_MAP,
            interval=float(os.environ.get("SCAN_INTERVAL", "900")), sharp=True)
async def scan_sweep(**_):
    cfg: ConfigView = _state["cfg"]
    _refresh_config(cfg)
    reason = _halted(cfg)
    if reason:
        log.info(json.dumps({"lvl": "info", "msg": "scan skipped", "reason": reason}))
        return

    registry: AgentRegistry = _state["registry"]
    exclude = set(cfg.csv("excludeNamespaces"))
    units: list[scan.ManifestUnit] = []

    if cfg.bool("scanGitEnabled", True) and os.environ.get("GIT_REPO_URL"):
        try:
            repo = scan.clone_or_pull(os.environ["GIT_REPO_URL"], os.environ.get("GIT_TOKEN"),
                                      WORKSPACE, cfg.get("gitBranchBase", "main"))
            units += list(scan.iter_git_manifests(repo))
        except Exception as exc:  # git problems must not stop the cluster scan
            log.warning(json.dumps({"lvl": "warn", "msg": "git scan failed", "err": str(exc)}))

    if cfg.bool("scanClusterEnabled", True):
        kinds = sorted({k for a in registry.all() for k in a.scan.get("kinds", [])})
        units += list(scan.iter_cluster_manifests(kinds, exclude))

    log.info(json.dumps({"lvl": "info", "msg": "scan sweep", "units": len(units)}))

    sem = asyncio.Semaphore(_state["cfg"].int("ollamaMaxConcurrent", 2))

    async def review(unit: scan.ManifestUnit):
        async with sem:
            await _review_unit(unit)

    await asyncio.gather(*(review(u) for u in units), return_exceptions=True)


async def _review_unit(unit: scan.ManifestUnit):
    registry: AgentRegistry = _state["registry"]
    if unit.kind in ("ParseError",) or not unit.name:
        return
    payload = json.dumps({
        "source": unit.source, "filePath": unit.file_path,
        "target": unit.target_ref(), "manifest": unit.as_yaml()[:12000],
    })
    recall_q = f"{unit.kind} {unit.name} {unit.file_path}"

    for agent_name in ("scanner", "security"):
        if unit.kind not in registry.get(agent_name).scan.get("kinds", []):
            continue
        try:
            issues = await registry.run(agent_name, payload, recall_query=recall_q)
        except Exception as exc:
            log.warning(json.dumps({"lvl": "warn", "agent": agent_name, "err": str(exc),
                                    "unit": unit.name}))
            continue
        if not isinstance(issues, list):
            continue
        for issue in issues:
            await _create_finding(agent_name, unit, issue)


async def _create_finding(agent_name: str, unit: scan.ManifestUnit, issue: dict):
    custom = _state["custom"]
    tgt = unit.target_ref()
    key = f"{tgt['kind']}|{tgt.get('namespace')}|{tgt['name']}|{issue.get('category')}|{issue.get('summary','')[:80]}"
    name = "f-" + hashlib.sha1(key.encode()).hexdigest()[:16]

    body = {
        "apiVersion": f"{GROUP}/{VERSION}", "kind": "Finding",
        "metadata": {"name": name, "namespace": NS,
                     "labels": {"ai-operator.io/category": issue.get("category", "improvement"),
                                "ai-operator.io/severity": issue.get("severity", "low"),
                                "ai-operator.io/by": agent_name}},
        "spec": {
            "source": unit.source, "filePath": unit.file_path or "",
            "target": {k: v for k, v in tgt.items() if v},
            "category": issue.get("category", "improvement"),
            "severity": issue.get("severity", "low"),
            "summary": str(issue.get("summary", ""))[:500],
            "detail": str(issue.get("detail", ""))[:8000],
            "evidence": [str(e)[:2000] for e in issue.get("evidence", [])][:10],
            "detectedBy": agent_name,
            "suggestedFix": str(issue.get("suggestedFix", ""))[:8000],
        },
    }
    try:
        custom.create_namespaced_custom_object(GROUP, VERSION, NS, "findings", body)
        log.info(json.dumps({"lvl": "info", "msg": "finding", "name": name,
                             "cat": body["spec"]["category"], "sev": body["spec"]["severity"],
                             "target": body["spec"]["target"]}))
    except client.ApiException as exc:
        if exc.status != 409:            # 409 = already exists = already known, fine
            log.warning(json.dumps({"lvl": "warn", "msg": "finding create failed", "err": str(exc)}))


# ==================================================================================================
# 2. triage a Finding
# ==================================================================================================
@kopf.on.create(GROUP, VERSION, "findings")
@kopf.on.resume(GROUP, VERSION, "findings")
async def triage_finding(body, patch, **_):
    cfg: ConfigView = _state["cfg"]
    _refresh_config(cfg)
    if body.get("status", {}).get("phase") not in (None, "New"):
        return

    decision = (body.get("metadata", {}).get("annotations", {}) or {}).get("ai-operator.io/decision")
    if decision == "dismiss":
        patch.status["phase"] = "Dismissed"
        return

    registry: AgentRegistry = _state["registry"]
    memory: Memory = _state["memory"]
    spec = body["spec"]

    open_findings = _list("findings")
    ctx = json.dumps({
        "finding": spec,
        "openFindings": [{"name": f["metadata"]["name"], "target": f["spec"]["target"],
                          "category": f["spec"]["category"], "summary": f["spec"]["summary"]}
                         for f in open_findings if f["metadata"]["name"] != body["metadata"]["name"]][:40],
        "knownPatterns": memory.patterns(),
    })
    try:
        d = await registry.run("coordinator", ctx,
                               recall_query=f"{spec['category']} {spec['summary']}")
    except Exception as exc:
        patch.status["phase"] = "Failed"
        patch.status["message"] = f"triage error: {exc}"
        return

    if d.get("action") == "deduplicate":
        patch.status["phase"] = "Dismissed"
        patch.status["deduplicatedInto"] = d.get("deduplicatedInto", "")
        return
    if d.get("action") == "dismiss":
        patch.status["phase"] = "Dismissed"
        patch.status["message"] = d.get("rationale", "")
        return

    patch.status["phase"] = "Triaged"
    patch.status["priority"] = int(d.get("priority", 5))
    patch.status["confidence"] = float(d.get("confidence", 0.0))
    patch.status["message"] = d.get("rationale", "")[:2000]

    if d.get("action") == "escalate" or decision != "approve" and d.get("route") != "auto":
        if decision == "approve":
            pass  # human said yes -> fall through to create a Remediation
        else:
            patch.status["phase"] = "AwaitingHuman"
            _event(body, "Warning", "AwaitingHuman", d.get("rationale", "needs a human decision"))
            return

    # create the Remediation
    rem_name = "r-" + body["metadata"]["name"][2:]
    rbody = {
        "apiVersion": f"{GROUP}/{VERSION}", "kind": "Remediation",
        "metadata": {"name": rem_name, "namespace": NS,
                     "ownerReferences": [{"apiVersion": f"{GROUP}/{VERSION}", "kind": "Finding",
                                          "name": body["metadata"]["name"],
                                          "uid": body["metadata"]["uid"]}]},
        "spec": {"findingRef": body["metadata"]["name"],
                 "strategy": d.get("remediationStrategy", "gitops-pr"),
                 "riskClass": d.get("riskClass", "high"),
                 "change": {}},
    }
    try:
        _state["custom"].create_namespaced_custom_object(GROUP, VERSION, NS, "remediations", rbody)
        patch.status["phase"] = "InProgress"
        patch.status["remediationRef"] = rem_name
    except client.ApiException as exc:
        if exc.status != 409:
            patch.status["phase"] = "Failed"
            patch.status["message"] = str(exc)


# ==================================================================================================
# 3. execute a Remediation
# ==================================================================================================
@kopf.on.create(GROUP, VERSION, "remediations")
@kopf.on.resume(GROUP, VERSION, "remediations")
async def execute_remediation(body, patch, **_):
    cfg: ConfigView = _state["cfg"]
    _refresh_config(cfg)
    if body.get("status", {}).get("phase") not in (None, "Planned"):
        return
    reason = _halted(cfg)
    if reason:
        patch.status["phase"] = "Planned"
        patch.status["result"] = f"held: {reason}"
        return
    if not _breakers_ok(body["spec"]):
        patch.status["phase"] = "AwaitingHuman"
        patch.status["result"] = "circuit breaker tripped — too many recent changes"
        return

    registry: AgentRegistry = _state["registry"]
    memory: Memory = _state["memory"]
    finding = _get("findings", body["spec"]["findingRef"])
    if not finding:
        patch.status["phase"] = "Failed"
        patch.status["result"] = "finding not found"
        return

    # -- fill in the actual change via the remediator ------------------------------------------
    tgt = finding["spec"]["target"]
    live = kube_safe.get_live(tgt.get("apiVersion", "v1"), tgt["kind"], tgt["name"], tgt.get("namespace"))
    manifest = yaml.safe_dump(live, sort_keys=False) if live else finding["spec"].get("suggestedFix", "")
    try:
        fix = await registry.run(
            "remediator",
            json.dumps({"finding": finding["spec"], "manifest": manifest[:12000]}),
            recall_query=f"{finding['spec']['category']} {finding['spec']['summary']}",
        )
    except Exception as exc:
        patch.status["phase"] = "Failed"
        patch.status["result"] = f"remediator error: {exc}"
        return

    strategy = fix.get("strategy", "gitops-pr")
    risk = fix.get("riskClass", "high")
    change = fix.get("change", {})
    patch.spec = {"strategy": strategy, "riskClass": risk, "change": change}

    mode = cfg.get("mode", "observe")
    auto_ok = (
        mode in ("assist", "auto")
        and risk in cfg.csv("autoApplyRiskClasses")
        and strategy in ("patch", "apply", "open-port", "helm-upgrade", "backup-and-recreate")
        and (finding["metadata"].get("annotations", {}) or {}).get("ai-operator.io/decision") != "dismiss"
    )
    if mode == "auto":
        auto_ok = auto_ok or (risk == "medium" and strategy != "gitops-pr")

    # -- observe mode / not auto-eligible -> PR or AwaitingHuman -------------------------------
    if mode == "observe" or not auto_ok or strategy == "gitops-pr":
        pr_url = await _open_pr(finding, fix) if os.environ.get("GIT_REPO_URL") else ""
        patch.status["phase"] = "AwaitingHuman" if not pr_url else "AwaitingHuman"
        patch.status["pullRequestURL"] = pr_url
        patch.status["result"] = "opened PR" if pr_url else f"proposed ({mode}); apply disabled or risk too high"
        _patch_status("findings", body["spec"]["findingRef"],
                      {"phase": "AwaitingHuman" if not pr_url else "InProgress"})
        _remember_outcome(memory, finding, fix, "proposed", 0.0)
        return

    # -- auto path: safe_apply --------------------------------------------------------------------
    proposed_yaml = change.get("manifest") or _apply_patch(live, change)
    if not proposed_yaml:
        patch.status["phase"] = "Failed"
        patch.status["result"] = "remediator produced no applyable manifest"
        return

    res = kube_safe.safe_apply(proposed_yaml, namespace_ops=NS)
    patch.status["backupRef"] = res.backup_ref
    patch.status["validation"] = {"dryRunOK": res.dry_run_ok, "policyOK": res.policy_ok,
                                  "nonDestructive": res.non_destructive, "messages": res.messages[:20]}
    patch.status["phase"] = res.phase
    patch.status["attempts"] = int(body.get("status", {}).get("attempts", 0)) + 1
    patch.status["appliedAt"] = _now() if res.phase in ("Applied", "Verified") else None
    patch.status["result"] = "; ".join(res.messages[-3:])[:2000]

    outcome = "success" if res.ok else ("partial" if res.phase == "Applied" else "failure")
    _patch_status("findings", body["spec"]["findingRef"],
                  {"phase": "Fixed" if res.ok else "Failed"})
    _event(finding, "Normal" if res.ok else "Warning", "Remediated" if res.ok else "RemediationFailed",
           patch.status["result"])
    _remember_outcome(memory, finding, fix, outcome, float(res.ok))


# ==================================================================================================
# 4. hourly learnings digest
# ==================================================================================================
@kopf.timer("v1", "configmaps", field="metadata.name", value=CONFIG_MAP, interval=3600.0)
async def write_digest(**_):
    memory: Memory = _state["memory"]
    dig = memory.digest()
    body = {
        "apiVersion": "v1", "kind": "ConfigMap",
        "metadata": {"name": "agent-memory-digest", "namespace": NS,
                     "labels": {"app.kubernetes.io/name": "ai-operator"}},
        "data": {"digest.yaml": yaml.safe_dump(dig, sort_keys=False)[:900000],
                 "updated": _now()},
    }
    try:
        _state["core"].replace_namespaced_config_map("agent-memory-digest", NS, body)
    except client.ApiException as exc:
        if exc.status == 404:
            _state["core"].create_namespaced_config_map(NS, body)
        else:
            log.warning(json.dumps({"lvl": "warn", "msg": "digest write failed", "err": str(exc)}))


# ==================================================================================================
# helpers
# ==================================================================================================
def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _list(plural: str) -> list[dict]:
    try:
        return _state["custom"].list_namespaced_custom_object(GROUP, VERSION, NS, plural).get("items", [])
    except client.ApiException:
        return []


def _get(plural: str, name: str) -> dict | None:
    try:
        return _state["custom"].get_namespaced_custom_object(GROUP, VERSION, NS, plural, name)
    except client.ApiException:
        return None


def _patch_status(plural: str, name: str, status: dict) -> None:
    try:
        _state["custom"].patch_namespaced_custom_object_status(
            GROUP, VERSION, NS, plural, name, {"status": status})
    except client.ApiException as exc:
        log.warning(json.dumps({"lvl": "warn", "msg": "status patch failed", "err": str(exc)}))


def _event(obj: dict, etype: str, reason: str, msg: str) -> None:
    try:
        _state["core"].create_namespaced_event(NS, client.CoreV1Event(
            metadata=client.V1ObjectMeta(generate_name="ai-operator-", namespace=NS),
            involved_object=client.V1ObjectReference(
                api_version=f"{GROUP}/{VERSION}", kind=obj["kind"],
                name=obj["metadata"]["name"], namespace=NS, uid=obj["metadata"].get("uid")),
            reason=reason, message=msg[:900], type=etype,
            source=client.V1EventSource(component="ai-operator"),
            first_timestamp=_now(), last_timestamp=_now(),
        ))
    except client.ApiException:
        pass


def _breakers_ok(spec: dict) -> bool:
    cfg: ConfigView = _state["cfg"]
    per_target = cfg.int("maxChangesPerTargetPerHour", 3)
    cluster_wide = cfg.int("maxChangesClusterWidePer10Min", 8)
    now = time.time()
    applied = [r for r in _list("remediations")
               if r.get("status", {}).get("appliedAt")]
    def age(r):
        try:
            return now - time.mktime(time.strptime(r["status"]["appliedAt"], "%Y-%m-%dT%H:%M:%SZ"))
        except (KeyError, ValueError):
            return 1e9
    if sum(1 for r in applied if age(r) < 600) >= cluster_wide:
        _state["core"].patch_namespaced_config_map(
            CONFIG_MAP, NS, {"data": {"paused": "true"}})
        log.warning(json.dumps({"lvl": "warn", "msg": "cluster-wide breaker -> paused=true"}))
        return False
    fref = spec.get("findingRef", "")
    same = sum(1 for r in applied if r["spec"].get("findingRef") == fref and age(r) < 3600)
    return same < per_target


def _apply_patch(live: dict | None, change: dict) -> str:
    """Turn a remediator patch into a full manifest for safe_apply (which does server-side apply)."""
    if not live:
        return ""
    body = change.get("patch", "")
    if not body:
        return ""
    try:
        patch_doc = yaml.safe_load(body)
    except yaml.YAMLError:
        return ""
    merged = _deep_merge(json.loads(json.dumps(live)), patch_doc)
    merged.get("metadata", {}).pop("managedFields", None)
    merged.pop("status", None)
    return yaml.safe_dump(merged, sort_keys=False)


def _deep_merge(base: dict, over: dict) -> dict:
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _remember_outcome(memory: Memory, finding: dict, fix: dict, outcome: str, confidence: float) -> None:
    spec = finding["spec"]
    text = (f"{spec['category']} on {spec['target'].get('kind')}/{spec['target'].get('name')}: "
            f"{spec['summary']} -> {fix.get('strategy')} ({fix.get('riskClass')}). "
            f"{fix.get('explanation','')[:300]} Result: {outcome}.")
    asyncio.create_task(_embed_and_store(memory, finding, text, outcome, confidence, fix))


async def _embed_and_store(memory, finding, text, outcome, confidence, fix):
    reg: AgentRegistry = _state["registry"]
    emb = await reg.embed(text)
    scope = f"{finding['spec']['target'].get('kind')}/{finding['spec']['target'].get('name')}"
    pattern = ""
    try:
        distil = await reg.run("coordinator",
                               json.dumps({"instruction": "WRITE A LEARNING", "finding": finding["spec"],
                                           "fix": fix, "outcome": outcome}))
        pattern = distil.get("pattern", "") if isinstance(distil, dict) else ""
        if isinstance(distil, dict) and distil.get("learning"):
            text = distil["learning"]
    except Exception:
        pass
    memory.store("outcome", scope, text, emb, pattern=pattern, outcome=outcome, confidence=confidence)


async def _open_pr(finding: dict, fix: dict) -> str:
    """Best-effort GitHub PR via the REST API. Returns the PR URL or '' if not configured/failed."""
    repo = os.environ.get("GIT_REPO_URL", "")
    token = os.environ.get("GIT_TOKEN", "")
    if not (repo and token and "github.com" in repo):
        return ""
    try:
        import httpx
        slug = repo.split("github.com/")[-1].removesuffix(".git")
        base = _state["cfg"].get("gitBranchBase", "main")
        branch = f"{_state['cfg'].get('gitBranchPrefix','ai-operator/')}{finding['metadata']['name']}"
        repo_path = scan.clone_or_pull(repo, token, WORKSPACE, base)
        import subprocess
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        subprocess.run(["git", "-C", repo_path, "checkout", "-B", branch], check=True, env=env,
                       capture_output=True, text=True)
        # write files from fix (gitops agent output) or a single manifest
        gp = fix.get("files") or []
        if not gp and fix.get("change", {}).get("manifest") and finding["spec"].get("filePath"):
            gp = [{"path": finding["spec"]["filePath"], "contents": fix["change"]["manifest"]}]
        for f in gp:
            p = os.path.join(repo_path, f["path"])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(f["contents"])
        subprocess.run(["git", "-C", repo_path, "add", "-A"], check=True, env=env, capture_output=True, text=True)
        subprocess.run(["git", "-C", repo_path, "-c", f"user.name=ai-operator",
                        "-c", "user.email=ai-operator@noreply", "commit",
                        "-m", fix.get("commitMessage", f"fix: {finding['spec']['summary']}")],
                       check=True, env=env, capture_output=True, text=True)
        push_url = repo.replace("https://", f"https://x-access-token:{token}@", 1)
        subprocess.run(["git", "-C", repo_path, "push", "-f", push_url, branch], check=True, env=env,
                       capture_output=True, text=True)
        async with httpx.AsyncClient(timeout=30) as h:
            r = await h.post(
                f"https://api.github.com/repos/{slug}/pulls",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                json={"title": fix.get("prTitle", f"fix: {finding['spec']['summary']}"[:72]),
                      "head": branch, "base": base,
                      "body": fix.get("prBody", finding["spec"].get("detail", ""))},
            )
        if r.status_code in (200, 201):
            return r.json().get("html_url", "")
        log.warning(json.dumps({"lvl": "warn", "msg": "PR create failed", "code": r.status_code,
                                "body": r.text[:300]}))
    except Exception as exc:
        log.warning(json.dumps({"lvl": "warn", "msg": "open_pr failed", "err": str(exc)}))
    return ""
