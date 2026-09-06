---
name: cilium
description: Cilium — eBPF-based CNI providing networking, NetworkPolicy enforcement, and an optional service mesh (no sidecar required). Use when a cluster's CNI is Cilium, or when comparing eBPF-based networking/mesh against the sidecar model in service-mesh.
---

# Cilium (eBPF Networking, NetworkPolicy, and Mesh)

An eBPF-based CNI that handles pod networking, NetworkPolicy enforcement, and — increasingly — service
mesh functionality directly in the Linux kernel, without requiring a sidecar proxy per pod the way Istio
does. See `kubernetes-access-control` for the general NetworkPolicy/admission-control model and
`service-mesh` for the sidecar-based alternative Cilium's mesh mode competes with.

## Why eBPF Instead of iptables/Sidecars

- Traditional kube-proxy uses iptables rules for Service routing — this scales poorly with very large
  numbers of Services/endpoints (rule evaluation is roughly linear). Cilium's eBPF datapath uses efficient
  kernel-level hash tables instead, meaningfully better at scale.
- **Sidecar-free mesh**: Cilium can provide mTLS, L7 traffic policy, and observability at the kernel/node
  level (via eBPF) instead of injecting a proxy container into every pod — lower per-pod resource
  overhead than Istio's sidecar model, at the cost of some L7 feature depth Istio's mature Envoy-based
  proxy still leads on for very fine-grained HTTP-layer traffic management.

## NetworkPolicy (CiliumNetworkPolicy — L3/L4/L7)

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata: { name: allow-frontend-to-api }
spec:
  endpointSelector: { matchLabels: { app: api } }
  ingress:
    - fromEndpoints: [{ matchLabels: { app: frontend } }]
      toPorts:
        - ports: [{ port: "8080", protocol: TCP }]
          rules:
            http: [{ method: "GET", path: "/v1/.*" }]   # L7 policy — plain K8s NetworkPolicy is L3/L4 only
```

- `CiliumNetworkPolicy` extends plain Kubernetes `NetworkPolicy` (which is L3/L4 — IP and port only) with
  L7-aware rules (HTTP method/path, gRPC method, Kafka topic) — a meaningfully finer-grained
  default-deny posture than plain NetworkPolicy alone can express.

## Hubble (observability)

- Cilium's built-in observability layer — flow visibility (`hubble observe`) into actual allowed/denied
  connections at the eBPF level, without needing separate tracing instrumentation for network-level
  questions ("is traffic even reaching this pod, and was it allowed or dropped").

```bash
cilium status                          # Cilium agent health across the cluster
hubble observe --namespace my-ns       # live flow log: what's connecting to what, allowed/denied
cilium connectivity test                # end-to-end connectivity/policy validation
```

## Common Pitfalls

- Migrating from kube-proxy/iptables to Cilium's kube-proxy replacement mode without validating existing
  NetworkPolicies translate as expected — worth a `cilium connectivity test` pass before trusting the
  migration in production.
- Assuming Cilium's sidecar-free mesh mode has full feature parity with Istio's Envoy-based mesh for
  complex L7 traffic management (advanced retries, fault injection) — check the specific feature is
  actually supported in the mesh mode being used before designing around it.
- eBPF requires a sufficiently recent kernel — running Cilium on older kernel versions can silently fall
  back to reduced-functionality modes; verify kernel version compatibility before deployment, not after.
- Default-allow assumed absent once Cilium is installed — like plain NetworkPolicy, Cilium doesn't
  default-deny on its own; explicit policies are still required (`kubernetes-access-control`'s core
  principle applies identically here).
