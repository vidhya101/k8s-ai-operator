---
description: Debug a misbehaving Kubernetes workload — gather evidence, form hypotheses, verify.
argument-hint: "<namespace/resource, e.g. 'prod/deploy/api' or a symptom description>"
---

Debug this Kubernetes issue: $ARGUMENTS

Delegate to the `kubernetes-debugger` agent using the `kubernetes` skill (and the platform-specific skill
— `eks`/`aks`/`gke`/`kubeadm`/`openshift` — once the cluster's distro is known from
`kubectl config current-context` / node labels).

1. Confirm the current `kubectl` context and namespace before running anything — never debug against an
   assumed cluster (see `.claude/rules/environment-awareness.md`).
2. Gather evidence read-only first: `kubectl get`, `describe`, `logs` (including `--previous` for crash
   loops), `kubectl get events --sort-by=.lastTimestamp`, resource requests/limits vs actual usage.
3. Form a hypothesis before proposing a fix; state what evidence supports it and what would disprove it.
4. Any remediation command (`kubectl delete pod`, `rollout restart`, `scale`, `drain`) is proposed, not
   run automatically — these are in the settings.json "ask" list for a reason.

End with: root cause (or leading hypotheses if unconfirmed), evidence, and the proposed fix.
