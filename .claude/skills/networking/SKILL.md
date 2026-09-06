---
name: networking
description: General networking troubleshooting and design — DNS, TLS, load balancing, firewalls/security groups, and connectivity debugging across cloud and on-prem. Use for "can't connect" issues or when designing network topology, independent of a specific cloud provider.
---

# Networking

Cloud- and platform-agnostic networking reference. See `aws`/`azure`/`gcp` for provider-specific
networking constructs and `kubernetes` for in-cluster networking (Services, NetworkPolicies, Ingress).

## Design Principles

- Plan IP address space (VPC/VNet CIDR, subnet sizing) for expected scale before creation — resizing
  after the fact is disruptive across every cloud.
- Public/private tiering: only resources that must be internet-facing get a public IP/public subnet;
  everything else reaches the internet (if needed at all) via NAT, egress proxy, or not at all.
- Default-deny at every layer that supports it (security group, NSG, firewall rule, NetworkPolicy) with
  explicit allows, rather than default-allow with exceptions.
- DNS and TLS are part of the design, not an afterthought — decide the domain/certificate strategy
  (managed cert, cert-manager, manual) before services need to be reachable by name.

## Debugging Connectivity ("can't connect" checklist)

```text
1. Is the destination actually listening?    ss -tlnp / netstat -tlnp on the target host, or
                                              kubectl get endpoints for a K8s Service
2. Is there a route?                         traceroute/mtr, or check route tables / peering / VPN status
3. Is a firewall/security group/NSG blocking it?   Check both ends — egress on the source, ingress on
                                              the destination; cloud firewalls are usually stateful but
                                              some (NACLs) are not
4. Is DNS resolving correctly?               dig / nslookup — from the actual failing host/pod, not
                                              your local machine, since resolution can differ
5. Is TLS the failure point, not TCP?        openssl s_client -connect host:port — separates a TCP-level
                                              block from a cert/TLS negotiation failure
6. Is a proxy/load balancer in the path doing something unexpected?   Check its health check status,
                                              backend pool membership, and any path/header rewrite rules
```

## Key Commands

```bash
dig <host> / nslookup <host>
curl -v https://<host>:<port>              # TCP connect + TLS handshake + HTTP response, all visible
openssl s_client -connect <host>:<port> -servername <host>
traceroute <host> / mtr <host>
ss -tlnp                                    # what's listening locally
tcpdump -i <iface> host <ip> and port <port>   # packet-level, last resort but definitive
```

## Common Pitfalls

- Security group/NSG allows the port but the application is only listening on `127.0.0.1`, not
  `0.0.0.0`/the container's routable interface — looks like a firewall issue, isn't.
- A load balancer's health check hitting a different port/path than the actual traffic, so it reports
  healthy while real requests fail (or vice versa, marking healthy backends unhealthy).
- DNS TTL cached longer than expected after a cutover, so some clients still resolve to the old endpoint
  well past the "propagation" window people assume.
- Asymmetric routing (return traffic taking a different path than outbound) breaking stateful firewalls
  that expect to see both directions of a connection.
