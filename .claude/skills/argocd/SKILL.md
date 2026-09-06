---
name: argocd
description: GitOps deployment with ArgoCD — Application/ApplicationSet design, sync policies, self-heal, and drift resolution. Use when setting up or debugging a GitOps deployment pipeline, or when a cluster's state doesn't match Git.
---

# ArgoCD (GitOps)

ArgoCD reconciles a Git repo's declared state onto a cluster. Once a resource is ArgoCD-managed, `kubectl
apply`/`edit` against it directly is a mistake, not a shortcut — see `.claude/rules/safety.md`.

## Core Model

- CI's job ends at updating the GitOps repo (an image tag, a Helm values file, a Kustomize overlay) —
  it does not run `kubectl apply` or `helm upgrade` against the cluster itself.
- ArgoCD's `Application` resource points at a Git path + a destination cluster/namespace and continuously
  reconciles; drift (cluster ≠ Git) is either self-healed automatically or flagged as `OutOfSync`,
  depending on the sync policy.

## Application Configuration

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-service-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: <gitops-repo>
    targetRevision: main
    path: apps/my-service/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: my-service
  syncPolicy:
    automated:
      prune: true       # remove resources deleted from Git
      selfHeal: true     # revert manual cluster drift back to Git state
    syncOptions:
      - CreateNamespace=true
```

- `automated` sync (with `selfHeal`) for environments the team trusts to deploy on every merge; manual
  sync for anything requiring a human gate (commonly production) — confirm this policy with the user,
  don't assume which environments get automation (see `CLAUDE.md` Section 1.1).
- `ApplicationSet` (with a generator: list, cluster, git-directory) for fleets of similar Applications
  across many services/clusters/environments instead of hand-maintaining duplicate `Application` YAML.
- App-of-apps pattern (one root `Application` that manages other `Application` resources) for bootstrapping
  a whole environment from one entry point.

## Sync Hooks (PreSync / Sync / PostSync / SyncFail)

Run one-off Jobs at specific points in a sync, distinct from `sync-wave` (which orders regular resources
relative to each other):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync              # runs, and must succeed, before the sync proceeds
    argocd.argoproj.io/hook-delete-policy: HookSucceeded   # clean up the Job once it succeeds
spec:
  template:
    spec:
      containers: [{ name: migrate, image: my-app-migrator:latest }]
      restartPolicy: Never
```

- **PreSync**: runs before the sync applies the rest of the manifests — the standard place for a database
  migration that must complete before the new application version starts (matches `database-operations`
  skill's schema-migration-before-deploy discipline, expressed as an ArgoCD-native mechanism).
- **Sync**: runs alongside the main sync, after PreSync resources are healthy.
- **PostSync**: runs after the sync succeeds and resources are healthy — common for cache invalidation,
  smoke tests, or a notification.
- **SyncFail**: runs if the sync fails — useful for cleanup or alerting on a failed rollout.
- A `PreSync` hook that fails blocks the rest of the sync — correct for "don't deploy the new app version
  if its migration didn't succeed," but means a flaky migration Job can block deploys entirely; give it
  real retry/failure handling rather than treating it as fire-and-forget.

## Key Commands

```bash
argocd app list
argocd app get <app>
argocd app diff <app>                 # what's different between Git and the live cluster
argocd app sync <app>                 # manual sync
argocd app history <app>
argocd app rollback <app> <revision>
```

## Drift & Common Pitfalls

- Any manual `kubectl edit`/`apply` against an ArgoCD-managed resource is treated as an incident: with
  `selfHeal` on, ArgoCD will revert it (and the person who made the manual change may not know why);
  without `selfHeal`, the app sits `OutOfSync` until someone notices.
- `prune: true` without understanding what's currently in the cluster but not in Git — a first sync with
  pruning enabled on a cluster that has pre-existing manually-created resources will delete them.
- Secrets in the GitOps repo in plaintext — use Sealed Secrets, External Secrets Operator, or SOPS, never
  a raw `Secret` manifest with real values committed.
- Sync waves/hooks (`argocd.argoproj.io/sync-wave`) needed for ordering dependencies (e.g. a CRD before
  the resource using it) but omitted, causing a sync to fail non-deterministically depending on apply order.
