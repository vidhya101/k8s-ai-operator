---
name: kubernetes-access-control
description: Kubernetes API access control pipeline — authentication, RBAC authorization, and admission control (OPA/Gatekeeper, Kyverno, Pod Security Admission). Use when debugging an access-denied error, designing RBAC, or reviewing what an admission policy actually enforces.
---

# Kubernetes Access Control (AuthN → AuthZ → Admission)

Every request to the Kubernetes API server passes through three stages in order — a request rejected at
any stage never reaches the next, which matters for diagnosing *why* something was denied.

```text
1. Authentication  — who is making this request?
2. Authorization   — is this identity allowed to do this action, on this resource?
3. Admission       — even if allowed, does this specific request satisfy policy (mutate/validate)?
```

## 1. Authentication

- **ServiceAccount tokens**: how pods authenticate to the API server — short-lived, auto-mounted, bound
  tokens by default in modern Kubernetes (projected, audience-bound, and expiring, replacing the old
  long-lived static ServiceAccount secret tokens).
- **Client certificates / OIDC**: how humans/CI typically authenticate — an OIDC integration (e.g. tied
  to the org's identity provider) is the common pattern for human `kubectl` access at any real scale,
  rather than distributing long-lived client certs.
- **Cloud-managed auth**: EKS/AKS/GKE each layer their own IAM/Entra ID/Google identity integration on top
  of this (see the `eks`/`aks`/`gke` skills) — `aws eks get-token`/`az aks get-credentials`/`gcloud
  container clusters get-credentials` are what actually populate a working kubeconfig's auth section.

```bash
kubectl auth whoami                # (newer kubectl) — confirm what identity you're actually authenticated as
```

## 2. Authorization (RBAC)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role                          # namespace-scoped; use ClusterRole for cluster-scoped resources
metadata: { name: pod-reader, namespace: my-ns }
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]  # least privilege: only what's actually needed
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: { name: read-pods, namespace: my-ns }
subjects:
  - kind: ServiceAccount
    name: my-app
    namespace: my-ns
roleRef: { kind: Role, name: pod-reader, apiGroup: rbac.authorization.k8s.io }
```

```bash
kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<ns>:<sa> -n <ns>   # test before granting
kubectl get rolebindings,clusterrolebindings -A -o wide | grep <subject>             # find what a subject can do
```

- `Role`/`RoleBinding` (namespace-scoped) vs. `ClusterRole`/`ClusterRoleBinding` (cluster-scoped, or
  reusable across namespaces via a RoleBinding referencing a ClusterRole) — a `ClusterRoleBinding` grants
  cluster-wide, not just the binding's apparent scope; a common accidental-over-grant source.
- Least privilege: no `cluster-admin` binding for a workload ServiceAccount; scope to the specific
  verbs/resources/namespace actually needed (see `kubernetes` skill's core RBAC principle).

## 3. Admission Control

- **Validating**: rejects a request outright if it violates policy (e.g. "no privileged containers," "must
  have resource limits") — implemented via `ValidatingAdmissionPolicy` (built-in, CEL-based, newer) or a
  `ValidatingWebhookConfiguration` pointing at an external policy engine (OPA/Gatekeeper, Kyverno).
- **Mutating**: modifies a request before it's persisted (e.g. injecting a sidecar, setting a default
  resource limit) — via `MutatingWebhookConfiguration`. Order matters: mutating admission runs before
  validating admission, so a mutation can bring a request into compliance before validation checks it.
- **Pod Security Admission** (built-in, replaces the deprecated PodSecurityPolicy): enforces the
  `privileged`/`baseline`/`restricted` Pod Security Standards at the namespace level via labels
  (`pod-security.kubernetes.io/enforce: restricted`) — the simplest built-in guardrail against obviously
  insecure pod specs (root, host namespaces, privileged containers) without needing a separate policy engine.
- OPA/Gatekeeper and Kyverno both implement policy-as-code admission control with more expressive custom
  policies than Pod Security Admission alone — check which (if either) a cluster runs before assuming
  Pod Security Admission is the only enforcement layer.

```bash
kubectl get validatingadmissionpolicies,validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get ns <name> -o jsonpath='{.metadata.labels}'   # check Pod Security Admission level
```

## OPA/Gatekeeper vs. Kyverno in Practice

- **OPA/Gatekeeper**: policies written in Rego (a dedicated policy language) — powerful and general
  (OPA is also used outside Kubernetes, e.g. for API authorization decisions), but Rego has a real
  learning curve distinct from YAML/Kubernetes-native syntax.

```rego
# Gatekeeper ConstraintTemplate rule (simplified) — deny containers with no resource limits
violation[{"msg": msg}] {
  container := input.review.object.spec.containers[_]
  not container.resources.limits
  msg := sprintf("Container %v has no resource limits", [container.name])
}
```

- **Kyverno**: policies written as plain Kubernetes YAML — no new language to learn, faster to onboard a
  team already fluent in Kubernetes manifests, and supports mutation (auto-fixing a resource, not just
  rejecting it) more naturally than Gatekeeper's validation-first model.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: require-resource-limits }
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-limits
      match: { resources: { kinds: [Pod] } }
      validate:
        message: "Resource limits are required"
        pattern:
          spec: { containers: [{ resources: { limits: { memory: "?*", cpu: "?*" } } }] }
```

- Choice is largely about team fit: Kyverno if the team wants to stay in pure YAML and values mutation
  support; OPA/Gatekeeper if policies need to be shared with non-Kubernetes enforcement points (OPA is
  also embeddable directly in application authorization logic) or the team is comfortable with Rego.
- Either way: start policies in **audit/dry-run mode** (`validationFailureAction: Audit` in Kyverno,
  Gatekeeper's own dry-run) against real existing workloads before switching to enforcing/blocking mode —
  same "confirm before enforcing" caution as any other new gate in this stack; a policy that would have
  blocked half of an existing production namespace's workloads needs to be known *before* it's enforced.

## Diagnosing a Denial

```text
"Unauthorized" / 401                → authentication failure — check the token/cert/kubeconfig is valid
"Forbidden" / 403                   → authorization (RBAC) — run `kubectl auth can-i` as that identity
Admission webhook denial (specific
  message from the policy engine)    → admission control — read the webhook's actual rejection message,
                                        it usually names the specific violated policy
```

## Common Pitfalls

- A `ClusterRoleBinding` used when a namespace-scoped `RoleBinding` (referencing a `ClusterRole` for
  reusability) was intended — grants far more than the apparent scope.
- Debugging a 403 by loosening RBAC broadly ("just grant more") instead of running `kubectl auth can-i`
  to find the exact missing verb/resource — over-grants tend to become permanent.
- A mutating webhook silently changing a resource in a way that only becomes visible when reading the
  object back (e.g. a sidecar injected, a default added) — check `kubectl get -o yaml` after apply, not
  just the manifest that was submitted.
- Pod Security Admission set to `restricted` on a namespace whose workloads weren't audited for
  compliance first — legitimate pods start failing to schedule with a policy violation error that looks
  like an unrelated bug.
