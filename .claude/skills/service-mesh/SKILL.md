---
name: service-mesh
description: Service mesh concepts and Istio specifics — mTLS, traffic management, and sidecar injection. Use when a cluster runs Istio (or Linkerd) and the question involves mesh-level traffic policy, mTLS, or debugging sidecar-related behavior.
---

# Service Mesh (Istio-focused)

A service mesh moves cross-cutting network concerns (mTLS, retries, traffic splitting, observability) out
of application code into a sidecar proxy layer. Istio is the most common implementation; Linkerd is a
lighter-weight alternative with a smaller feature/complexity surface — note which one a cluster actually
runs before applying Istio-specific CRDs.

## Core Concepts

- **Sidecar injection**: Istio injects an Envoy proxy container into every pod in a labeled namespace
  (`istio-injection: enabled`); all pod traffic routes through it transparently. A pod created before the
  namespace label was set won't have a sidecar until it's recreated — a common source of "why isn't this
  pod covered by the mesh" confusion.
- **mTLS**: Istio can enforce mutual TLS between mesh services automatically (`PeerAuthentication` CRD,
  `STRICT` mode) — encrypts and authenticates service-to-service traffic without application changes.
  `PERMISSIVE` mode accepts both plaintext and mTLS during migration; leaving it permissive indefinitely
  means encryption isn't actually enforced.
- **Traffic management**: `VirtualService` (routing rules — weight-based splits, header-based routing,
  retries/timeouts) and `DestinationRule` (subsets/versions of a service, load balancing policy,
  connection pool/circuit-breaker settings) together control how traffic reaches a service's pods.

## Common Configuration

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata: { name: default, namespace: my-ns }
spec:
  mtls: { mode: STRICT }
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata: { name: my-service }
spec:
  hosts: ["my-service"]
  http:
    - route:
        - destination: { host: my-service, subset: v1 }
          weight: 90
        - destination: { host: my-service, subset: v2 }
          weight: 10               # canary: 10% of traffic to the new version
```

## Choosing a Mesh: Istio vs. Linkerd vs. Consul vs. Cilium

- **Istio**: the most feature-rich (fine-grained L7 traffic policy, extensive Envoy-based ecosystem) and
  historically the most operationally heavy (sidecar resource overhead, complexity of configuration) —
  the right default when advanced traffic management (fault injection, complex canary rules) is genuinely needed.
- **Linkerd**: deliberately minimal — simpler to operate, lower sidecar resource overhead, covers mTLS
  and basic traffic split well, less configurable for advanced L7 policy — a good fit when the actual
  requirement is "mTLS and basic observability between services" without Istio's operational surface.
- **Consul** (HashiCorp): service mesh plus service discovery/registration, notable for strong multi-
  cluster and multi-runtime support (VMs alongside Kubernetes, not just K8s-native) — a natural fit for a
  mixed VM+Kubernetes environment, less commonly the first choice for a Kubernetes-only environment.
- **Cilium** (see the `cilium` skill): sidecar-free, eBPF-based — lowest per-pod overhead, increasingly
  capable at L7 policy, but a newer entrant for the full mesh feature set compared to Istio's maturity.
- Don't default to Istio because it's the most well-known — the operational cost (sidecar overhead,
  configuration complexity) needs to be justified by an actual requirement for its advanced features
  (Section 1.2); a simpler mesh or no mesh at all is often the right call.

## Key Commands

```bash
istioctl proxy-status                          # sync status of every sidecar with the control plane
istioctl analyze -n <namespace>                 # lint mesh configuration for common misconfigurations
istioctl proxy-config routes <pod> -n <ns>       # what routing rules a specific sidecar actually has
kubectl get peerauthentication,virtualservice,destinationrule -A
```

## Common Pitfalls

- A pod running without a sidecar because it existed before namespace injection was enabled, or has an
  explicit `sidecar.istio.io/inject: "false"` annotation left over from debugging.
- `PERMISSIVE` mTLS mode never tightened to `STRICT` after migration, so encryption is available but not
  actually enforced — any plaintext client can still talk to the service.
- Sidecar resource requests/limits not set (they add real CPU/memory overhead per pod) — under-provisioned
  sidecars become a hidden source of latency/throttling that's easy to misattribute to the application.
- Mesh added to solve a problem (e.g. "we need retries") that a simpler mechanism (client-side retry
  logic, an ingress-level policy) would have solved with far less operational complexity — a mesh is a
  significant operational commitment; confirm it's actually needed before introducing one (Section 1.2).
