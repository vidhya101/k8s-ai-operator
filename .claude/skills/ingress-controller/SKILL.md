---
name: ingress-controller
description: Kubernetes Ingress and Ingress controllers — routing rules, TLS termination, and controller choice (nginx, cloud-native ALB/AGIC/GCE, Istio Gateway). Use when configuring or debugging external HTTP(S) access into a cluster.
---

# Ingress & Ingress Controllers

`Ingress` is a Kubernetes API object describing HTTP(S) routing rules; an Ingress **controller** is the
actual component that reads those objects and configures a real load balancer/proxy. An `Ingress` resource
does nothing without a controller watching it — confirm one is installed before debugging "why doesn't my
Ingress work" as if the resource alone should do something.

## Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  annotations:
    # Annotations are controller-specific — nginx, ALB, and GCE controllers each have their own set;
    # copying an annotation from the wrong controller's docs silently does nothing.
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx        # explicitly picks which controller handles this Ingress when >1 exists
  tls:
    - hosts: ["app.example.com"]
      secretName: app-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: my-app-svc, port: { number: 80 } }
```

## Controller Choice

- **ingress-nginx**: the most common cloud-agnostic choice, runs as pods in-cluster; annotations control
  most nginx-specific behavior (rewrites, rate limiting, auth).
- **Cloud-native controllers**: AWS Load Balancer Controller (provisions an ALB/NLB from Ingress/Service,
  see `eks` skill), AGIC (Azure Application Gateway, see `aks` skill), GKE Ingress (provisions a GCE load
  balancer, see `gke` skill) — these provision a real cloud load balancer resource per Ingress, with cost
  and provisioning-time implications ingress-nginx (self-hosted) doesn't have.
- **Istio Gateway/VirtualService**: if a service mesh (see `service-mesh` skill) is in use, ingress traffic
  is often handled by Istio's own `Gateway` resource instead of/alongside plain `Ingress` — check which
  model a mesh-enabled cluster actually uses before assuming plain Ingress is the entry point.
- **Gateway API** (`Gateway`/`HTTPRoute`): the newer, more expressive successor to `Ingress`, increasingly
  supported across controllers — check whether a cluster has standardized on this instead of classic
  `Ingress` before assuming the older API is what's in use.

## TLS Termination

- TLS commonly terminates at the ingress controller/cloud load balancer, with plaintext HTTP from there to
  the backend Service inside the cluster (fine within a trusted cluster network; verify that assumption
  holds if the mesh/network model requires end-to-end encryption — see `service-mesh` skill's mTLS).
- Certificates: `cert-manager` is the standard way to automate issuance/renewal (Let's Encrypt or an
  internal CA) into the `Secret` an Ingress's `tls.secretName` references — a manually-managed cert that
  expires with no renewal automation is a recurring, avoidable outage cause.

## Common Pitfalls

- Multiple Ingress controllers installed with no `ingressClassName` set on an Ingress, leaving it
  ambiguous (or picked up by the wrong controller) which one handles it.
- An annotation copied from a different controller's documentation, silently ignored by the controller
  actually in use — no error, the behavior just doesn't happen.
- TLS secret referenced by name but never created/renewed (cert-manager not installed or misconfigured),
  causing the controller to fall back to a default/self-signed cert with no obvious error in the Ingress
  resource itself.
- Path-type mismatches (`Exact` vs. `Prefix` vs. controller-specific legacy behavior) causing routes to
  match more or less than intended.
