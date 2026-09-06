---
name: metallb
description: MetalLB — LoadBalancer Service implementation for bare-metal/on-prem Kubernetes clusters, where no cloud provider exists to provision a real load balancer. Use alongside kubeadm for on-prem clusters needing LoadBalancer-type Services.
---

# MetalLB

On EKS/AKS/GKE, a `Service` of `type: LoadBalancer` provisions a real cloud load balancer automatically.
On a `kubeadm`/on-prem/bare-metal cluster, there's no cloud provider to do that — a `LoadBalancer` Service
stays stuck in `<pending>` forever without something like MetalLB filling that role.

## Modes

- **Layer 2 mode**: one node answers ARP/NDP for the service IP; simpler to set up, but failover on that
  node's failure has a brief interruption (another node takes over ARP responsibility) and all traffic
  for a given IP funnels through one node at a time — a scalability ceiling for high-throughput services.
- **BGP mode**: MetalLB peers with the network's actual routers via BGP, advertising service IPs with
  real ECMP load balancing across nodes — no single-node bottleneck, but requires router-side BGP
  configuration coordination with network infrastructure/ops, not just a Kubernetes-side change.

## Configuration

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata: { name: default-pool, namespace: metallb-system }
spec:
  addresses: ["192.168.1.240-192.168.1.250"]   # a range carved out of the LAN, not otherwise DHCP-assigned
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata: { name: l2-adv, namespace: metallb-system }
spec:
  ipAddressPools: [default-pool]
```

- The address pool must be a range genuinely reserved for MetalLB (excluded from DHCP, not used by
  anything else on the network) — coordinate with whoever manages the physical/virtual network before
  picking a range, this isn't a purely Kubernetes-side decision.

## Common Pitfalls

- Address pool overlapping with DHCP-assigned addresses, causing IP conflicts that manifest as
  intermittent, hard-to-diagnose connectivity issues unrelated-looking to MetalLB.
- Layer 2 mode assumed to load-balance across nodes the way a real cloud LB does — it doesn't; all
  ingress traffic for a given service IP goes through whichever single node currently holds it.
- BGP mode configured cluster-side with no matching router-side peering configuration — the `BGPPeer`
  resource exists but nothing actually establishes a session, and the failure looks like a Kubernetes
  issue when it's a network-side gap.
- Confusing MetalLB (Service-level, layer 2/3 IP assignment) with an Ingress controller (HTTP-level
  routing, see `ingress-controller` skill) — MetalLB is what gives an Ingress controller's own
  `LoadBalancer` Service a real external IP in the first place; they solve different, complementary layers.
