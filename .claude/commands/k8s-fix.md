---
description: Resolve a Kubernetes problem end-to-end — root-cause, fix (with confirmation), verify, add a self-healing guardrail.
argument-hint: "<namespace/resource or symptom, e.g. 'prod/deploy/api CrashLoopBackOff' or 'nodes NotReady on kubeadm'>"
---

Fix this Kubernetes issue: $ARGUMENTS

Delegate to the `kubernetes-troubleshooter` agent, loading the `kubernetes` skill plus the
distro-specific skill once the cluster is fingerprinted (`eks` / `aks` / `gke` / `openshift` /
`kubeadm` / `kind`), and `kubernetes-autoscaling` / `keda` / `external-secrets` if the fix or
guardrail touches those.

1. Confirm `kubectl config current-context`, the distro, the namespace, and whether this is production
   before running anything mutating (`.claude/rules/environment-awareness.md`).
2. Run the full loop: locate → gather evidence read-only → single root cause (with the evidence that
   would disprove it) → propose the fix as a command or `kubectl diff` with blast radius stated.
3. Apply the fix **only after explicit confirmation** — `delete` / `rollout` / `scale` / `drain` /
   `apply` / `patch` / anything in `kube-system` or touching a node, PV, Secret, or CRD is in the
   settings.json "ask" list for a reason (`.claude/rules/safety.md`).
4. Verify recovery (object reaches its healthy terminal state, events stop).
5. Add a guardrail so the same failure is caught automatically next time — the right probe split, a
   PDB, ResourceQuota/LimitRange, HPA/VPA, NetworkPolicy, PriorityClass, an admission policy, or an
   alert. Prefer wiring the relevant `k8s/app/components/` (hardening / vpa / priority-scheduling /
   self-healing) into the workload's overlay over a bespoke manifest.

End with the agent's CONTEXT / SYMPTOM / EVIDENCE / ROOT CAUSE / FIX / RECOVERY / GUARDRAIL / FOLLOW-UP
block.
