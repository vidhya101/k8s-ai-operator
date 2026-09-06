---
name: kong-api-gateway
description: Kong — standalone API gateway for rate limiting, auth, and traffic management in front of services, distinct from a cloud-native API Gateway (aws-serverless) or a service mesh's east-west traffic control (service-mesh).
---

# Kong (API Gateway)

A dedicated API gateway sitting at the edge — north-south traffic (external clients → your services) —
handling auth, rate limiting, and routing centrally instead of in each service. Distinct from
`aws-serverless`'s API Gateway (cloud-native, tightly coupled to Lambda/AWS) and from `service-mesh`
(east-west, service-to-service traffic inside the cluster) — Kong (and similar gateways like Apigee) is
the self-hostable, cloud-agnostic option for the edge layer specifically.

## Core Model

- **Services** (Kong's term for an upstream backend) and **Routes** (how external requests map to a
  Service) are the base routing config — conceptually similar to an Ingress resource's host/path rules,
  but with Kong's plugin ecosystem layered on top for cross-cutting concerns.
- **Plugins** attach behavior to a Service/Route/globally: rate limiting, authentication (key-auth, JWT,
  OAuth2), request/response transformation, logging — the mechanism for centralizing concerns that would
  otherwise be duplicated per-service application code.

```yaml
# Declarative config (or via Admin API)
services:
  - name: orders-service
    url: http://orders.internal:8080
    routes:
      - name: orders-route
        paths: ["/api/orders"]
    plugins:
      - name: rate-limiting
        config: { minute: 100, policy: local }
      - name: key-auth
```

## Rate Limiting & Quota Management

- Centralizing rate limiting at the gateway (rather than each service implementing its own) means one
  consistent policy and one place to tune it under load — protects backend services from being
  overwhelmed regardless of whether the overload is legitimate traffic or abuse.
- Distributed rate limiting (policy: `redis` instead of `local`) is needed once Kong itself runs as
  multiple replicas — `local` policy counts per-node, which under-enforces the intended limit across a
  multi-node gateway deployment; a common, easy-to-miss configuration gap.

## Common Pitfalls

- `local` rate-limiting policy used with a multi-replica Kong deployment, silently multiplying the
  effective rate limit by the replica count instead of enforcing the intended global limit.
- Auth plugin (key-auth/JWT/OAuth2) configured on the gateway but a backend service still separately
  trusting unauthenticated requests if reached directly (bypassing the gateway) — the gateway's auth is
  only a real boundary if backend services aren't also reachable through another path.
- Kong itself becoming a single point of failure with no HA configuration — it's now sitting in the
  critical path for every request that goes through it; same availability discipline as any other
  critical-path component (`kubernetes` skill's PodDisruptionBudget/anti-affinity principles apply).
- Plugin configuration drifting from what's actually intended because it's managed ad hoc via the Admin
  API instead of declaratively (decK or Kubernetes Ingress Controller CRDs) and version-controlled —
  same "config as code, not manual API calls" principle as everywhere else in this stack.
