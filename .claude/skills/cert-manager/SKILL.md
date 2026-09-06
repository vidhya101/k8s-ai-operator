---
name: cert-manager
description: cert-manager — automated TLS certificate issuance and renewal for Kubernetes, integrating with Let's Encrypt or an internal CA. Use when setting up or debugging TLS for an Ingress/Gateway, or when a certificate expired unexpectedly.
---

# cert-manager

Automates what used to be a manual, easy-to-forget process — requesting, renewing, and rotating TLS
certificates — as Kubernetes-native resources. Referenced from the `ingress-controller` skill's TLS
section; this is the mechanism behind it.

## Core Resources

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata: { name: letsencrypt-prod }
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef: { name: letsencrypt-prod-key }
    solvers:
      - http01: { ingress: { class: nginx } }    # or dns01 for wildcard certs / no-public-HTTP scenarios
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata: { name: app-tls, namespace: my-ns }
spec:
  secretName: app-tls-secret            # what an Ingress's tls.secretName then references
  issuerRef: { name: letsencrypt-prod, kind: ClusterIssuer }
  dnsNames: ["app.example.com"]
```

- Commonly, an Ingress annotation (`cert-manager.io/cluster-issuer: letsencrypt-prod`) triggers automatic
  `Certificate` creation instead of writing the `Certificate` resource by hand — check which pattern a
  given cluster uses.

## Issuer Types

- **ACME (Let's Encrypt)**: free, automated, publicly-trusted certs — `http01` challenge needs the
  Ingress publicly reachable on port 80 to prove domain ownership; `dns01` challenge (via a DNS provider
  API) works without public HTTP exposure and is required for wildcard certificates.
- **Internal CA / Vault issuer**: for internal-only services where a publicly-trusted cert isn't needed
  or wanted — integrates with the `vault` skill's PKI engine, or a self-managed CA.
- `Issuer` (namespace-scoped) vs. `ClusterIssuer` (cluster-wide) — same scoping distinction as `Role` vs.
  `ClusterRole` in `kubernetes-access-control`.

## Common Pitfalls

- Rate limits on Let's Encrypt's production ACME endpoint hit during testing/iteration — use the staging
  ACME server (`acme-staging-v02...`) while iterating on configuration, switch to production only once
  it's working, to avoid getting rate-limited on the real endpoint.
- `http01` challenge failing because the Ingress isn't actually publicly reachable yet (DNS not pointed at
  it, or a firewall blocking port 80) — the certificate request silently stays pending with no clear
  Kubernetes-level error until you check `kubectl describe certificaterequest`.
- Certificate renewal assumed automatic with no monitoring — cert-manager renews well before expiry by
  default, but a stuck/failing renewal (issuer misconfiguration, changed DNS) can still lead to an
  expired cert if nothing alerts on renewal failures specifically.
- `dns01` solver configured with overly broad DNS-provider API credentials — same least-privilege
  principle as any other credential; scope to exactly the zone/record type needed.
