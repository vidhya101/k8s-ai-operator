---
name: gitops
description: GitOps as a deployment methodology — repo structure, promotion between environments, and the CI/CD boundary. Use when designing how deployments should flow through Git rather than direct cluster mutation; see the argocd skill for ArgoCD-specific mechanics.
---

# GitOps

The methodology: Git is the single source of truth for desired state, and an operator (ArgoCD, Flux)
continuously reconciles the live system to match it. See `argocd` for the ArgoCD-specific implementation.

## Repo Structure Options

- **App repo + separate GitOps repo**: application source code lives in one repo, deployment manifests
  (Helm values, Kustomize overlays) in another that the operator watches — clean separation of "what the
  app is" from "what's deployed where," but requires CI to open a cross-repo commit/PR to promote a change.
- **Monorepo with a `deploy/` or `gitops/` directory**: simpler cross-referencing, one PR can change app
  code and its deployment config together — works well for a single team/service, gets unwieldy across
  many independent services with different release cadences.

Neither is universally correct — match it to how many teams/services are involved and how independently
they release; don't impose a structure the existing repo layout contradicts.

## Environment Promotion

- Typical pattern: a change lands in a lower environment's manifest (auto, on every merge to main) and
  promotion to higher environments (stage → prod) is a separate, often manual/gated, commit/PR bumping
  the image tag or Kustomize overlay in that environment's path.
- Promotion should be a Git operation (a PR, a tag, a branch merge) — not a manual `kubectl`/`helm`
  command against the target cluster, which is exactly the drift GitOps exists to prevent.

## The CI/CD Boundary

```text
CI:     build → test → scan → push image → update GitOps repo (image tag / values)
GitOps: operator detects the Git change → reconciles cluster state → (self-heals drift)
```

CI's responsibility ends at the Git commit to the GitOps repo. It should never run a mutating command
directly against a GitOps-managed cluster — that creates a second, competing source of truth.

## ArgoCD vs. Flux

Two operators implement this methodology — see `argocd` for ArgoCD specifics and `flux-cd` for Flux's
Kubernetes-native CRD approach (`GitRepository`/`Kustomization`/`HelmRelease`). The GitOps principles on
this page apply identically regardless of which operator a project uses; don't assume ArgoCD-specific
resource names (`Application`) if a repo's actual operator is Flux, or vice versa — check
`kubectl get applications` vs. `kubectl get gitrepositories,kustomizations` to confirm which is running
before referencing operator-specific commands.

## Common Pitfalls

- CI configured to both update the GitOps repo *and* run `kubectl apply`/`helm upgrade` directly "to
  speed things up" — creates drift and confusing double-deploys.
- Secrets committed in plaintext to the GitOps repo because "it's private" — use Sealed Secrets, External
  Secrets Operator, or SOPS regardless of repo visibility (see `.claude/rules/secrets.md`).
- No clear promotion path documented, so environment drift creeps in as manual "just this once" changes
  accumulate in prod's manifests but never get backported to lower environments' definitions.
