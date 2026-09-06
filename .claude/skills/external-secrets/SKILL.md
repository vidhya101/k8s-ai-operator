---
name: external-secrets
description: External Secrets Operator and Sealed Secrets — syncing real secrets from an external manager (Vault/AWS/Azure/GCP) into Kubernetes Secrets, or encrypting secrets safely into Git. Use when wiring Kubernetes workloads to external secret managers, referenced from kubernetes and gitops skills.
---

# External Secrets Operator & Sealed Secrets

Two different answers to the same problem the `kubernetes`, `gitops`, and `vault` skills all reference but
don't fully detail: how does a real secret value get into a Kubernetes `Secret` without ever being
committed to Git in plaintext.

## External Secrets Operator (ESO) — pull from an external manager

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata: { name: vault-backend, namespace: my-ns }
spec:
  provider:
    vault: { server: "https://vault.internal", path: "secret", auth: { kubernetes: { role: my-app } } }
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata: { name: app-secret, namespace: my-ns }
spec:
  secretStoreRef: { name: vault-backend, kind: SecretStore }
  target: { name: app-secret }            # the K8s Secret this creates/syncs
  data:
    - secretKey: db-password
      remoteRef: { key: myapp/config, property: db_password }
```

- ESO continuously syncs from the external manager (Vault, AWS Secrets Manager, Azure Key Vault, GCP
  Secret Manager — see `vault`/`aws`/`azure`/`gcp` skills) into a real Kubernetes `Secret` — nothing about
  the actual secret value is ever stored in Git; only the *reference* (which key, from which store) is.
- Rotation in the source system propagates automatically on ESO's refresh interval — a meaningful
  advantage over a manually-updated K8s `Secret`, where rotation requires someone to remember to update it.

## Sealed Secrets — encrypt into Git safely

```bash
kubeseal --format yaml < secret.yaml > sealed-secret.yaml   # encrypt with the cluster's public key
# sealed-secret.yaml is now safe to commit — only the in-cluster controller's private key can decrypt it
```

- A different model: the *encrypted* secret is committed to Git (safe, since only the target cluster's
  private key can decrypt it), and the in-cluster `SealedSecrets` controller decrypts it into a real
  `Secret` on apply — GitOps-friendly (the encrypted form lives right in the GitOps repo, see `gitops`
  skill) without needing an external secret manager at all.
- Trade-off versus ESO: no automatic rotation from a central source (each rotation needs a new
  `kubeseal` + commit), but no dependency on an external secret manager being reachable/configured either
  — a reasonable choice for a simpler setup or where introducing Vault/a cloud secret manager is more
  operational overhead than is currently justified.

## Which to Use

- **External Secrets Operator**: when a secret manager (Vault, cloud-native) already exists as the org's
  source of truth for secrets, and rotation-without-a-new-commit matters.
- **Sealed Secrets**: when there's no external secret manager yet, or the simplicity of "encrypted value
  lives in Git, decrypted only in-cluster" outweighs the lack of centralized rotation.
- Either is correct; a raw Kubernetes `Secret` (base64, not encrypted) committed to Git is never correct
  — base64 is encoding, not encryption, and is trivially reversible.

## Common Pitfalls

- A "sealed" secret assumed safe to commit when it was never actually run through `kubeseal` — a raw
  `Secret` manifest looks similar enough to a casual glance that this mistake happens.
- ESO's `SecretStore` credentials (how ESO itself authenticates to Vault/AWS/etc.) scoped too broadly —
  same least-privilege principle as any other credential; ESO's own access should be scoped to exactly
  the secrets paths it needs to sync.
- Sealed Secrets' cluster key not backed up — losing it means every previously-sealed secret becomes
  permanently undecryptable, a real disaster-recovery gap specific to this approach.
- Refresh interval on an `ExternalSecret` set too long relative to how quickly a rotated credential
  actually needs to propagate — check this matches the actual rotation cadence expected upstream.
