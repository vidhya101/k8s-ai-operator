---
name: vault
description: HashiCorp Vault — secrets storage, dynamic credentials, and auth methods (Kubernetes, AWS/Azure/GCP). Use when a project uses Vault as its secret manager, for reviewing Vault policy/auth configuration, or wiring an app to fetch secrets from it.
---

# HashiCorp Vault

Centralized secrets management — static secret storage (KV), dynamic/short-lived credential generation,
and encryption-as-a-service, gated by policy-based access control. See
`.claude/rules/secrets.md` — a Vault read that returns a real secret value must never be echoed/logged
into context; only the fact that the read succeeded (or the path structure) should be surfaced.

## Secret Engines

- **KV (Key-Value)**: static secrets, versioned (KV v2) — closest analog to AWS Secrets Manager/Azure Key
  Vault for "store this value, fetch it later."
- **Dynamic secrets** (database, AWS, Azure, GCP engines): Vault generates short-lived credentials
  on-demand (e.g. a temporary database user) with an automatic TTL/revocation — meaningfully more secure
  than a long-lived static credential since a leaked dynamic credential expires quickly on its own.
- **Transit**: encryption-as-a-service (encrypt/decrypt/sign without Vault ever storing the underlying
  data) — useful for application-level encryption without the app managing its own keys.

## Auth Methods (how a workload authenticates to Vault)

- **Kubernetes auth**: a pod's ServiceAccount JWT is exchanged for a Vault token, scoped by a Vault role
  bound to a specific namespace/ServiceAccount — the Vault-native equivalent of IRSA/Workload Identity.
- **AWS/Azure/GCP auth**: a cloud workload's native identity (instance profile, managed identity, service
  account) authenticates without a separate Vault-specific credential.
- Avoid the `userpass`/long-lived token auth methods for automated workloads — those are for human/CLI
  access, not service-to-service auth.

## PKI Engine (certificate issuance)

- Vault can act as an internal Certificate Authority — issuing short-lived TLS certificates on demand via
  API call, the same "dynamic, short-lived credential" model as its database/cloud dynamic secrets
  engines, applied to certificates instead of passwords/keys.
- Complements (and can back) `cert-manager`'s Vault issuer for Kubernetes-native certificate automation —
  cert-manager handles the Kubernetes-side `Certificate`/`Secret` lifecycle, Vault's PKI engine is the
  actual CA issuing the certs underneath.

```bash
vault write pki/root/generate/internal common_name="internal.example.com" ttl=87600h
vault write pki/roles/my-role allowed_domains="internal.example.com" allow_subdomains=true max_ttl="720h"
vault write pki/issue/my-role common_name="app.internal.example.com"    # issue a short-lived cert
```

- Short-lived, auto-renewed certificates meaningfully reduce the blast radius of a leaked certificate
  compared to a long-lived one — the same short-lived-credential security benefit Vault's other dynamic
  secrets engines provide, and the same tradeoff (renewal must actually work reliably, or things break
  when certs expire) as any short-TTL credential system.

## Key Commands

```bash
vault status                            # sealed/unsealed, cluster health — safe, no secret exposure
vault kv list secret/                    # list paths, not values — safe
vault kv get secret/myapp/config          # returns actual values — treat as sensitive, don't echo into
                                           # a transcript/log; confirm before running (settings.json "ask")
vault kv put secret/myapp/config key=val  # mutating — confirm first
vault policy read <policy-name>            # inspect what a policy actually grants
vault token capabilities <path>             # what can the current token do at a given path
```

## Policy Review

- Policies should grant `read` (or the specific dynamic-secret `create`/`update` capability) scoped to
  the exact path a workload needs — a policy with `path "secret/*" { capabilities = ["read"] }` grants
  access to every secret in the KV mount, not just the one the workload should see.
- Root token usage should be limited to initial setup/break-glass scenarios, not day-to-day operations —
  if a pipeline or app is authenticating with a root token, that's a finding, not a convenience.

## Common Pitfalls

- A Vault read's output displayed/logged in full, putting a real secret value into a transcript, CI log,
  or terminal history — always the specific thing to avoid regardless of how the read was triggered.
- Kubernetes auth role bound too broadly (any ServiceAccount in a namespace, instead of the specific one
  that needs it) — same over-broad-trust-policy pattern as IRSA/Workload Identity misconfiguration.
- Dynamic secrets' TTL set longer than actually needed, eroding much of the security benefit over a
  static credential.
- Vault unsealed manually via operator action but the unseal keys not properly split/distributed (Shamir
  secret sharing) — a single-key unseal defeats the purpose of the threshold scheme.
