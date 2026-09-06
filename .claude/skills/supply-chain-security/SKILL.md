---
name: supply-chain-security
description: Software supply-chain security — SBOM generation, artifact signing/verification (cosign, Sigstore), and provenance attestation. Use when setting up image/artifact signing, generating an SBOM, or reviewing what guarantees exist about what's actually deployed.
---

# Supply-Chain Security (SBOM, cosign, Sigstore, Provenance)

Answers a specific question the other DevSecOps tools don't: **"is what's running actually what we built,
and what's in it?"** — as distinct from "does what we built have known vulnerabilities" (`trivy`/`snyk`)
or "does the code have security issues" (`sonarqube`).

## SBOM (Software Bill of Materials)

- A structured inventory of every component (direct and transitive dependencies, OS packages) in a build
  artifact — the format most scanners (`trivy`) already generate internally to find vulnerabilities; an
  explicit SBOM makes that inventory a first-class, shareable artifact instead of scanner-internal state.
- Standard formats: SPDX and CycloneDX — check which a compliance requirement or downstream consumer
  actually expects before picking one arbitrarily.

```bash
syft <image>:<tag> -o cyclonedx-json=sbom.json      # generate an SBOM for a built image
trivy image --format cyclonedx --output sbom.json <image>:<tag>   # trivy can also generate one directly
grype sbom:sbom.json                                 # scan an existing SBOM for known vulnerabilities
```

- Value beyond point-in-time scanning: when a new CVE is published against a library, an archived SBOM
  lets you instantly answer "which of our already-shipped artifacts contain this?" without re-scanning
  everything — the `nexus`/registry retention discussion applies here too (keep SBOMs alongside the
  artifacts they describe).

## Signing & Verification: cosign / Sigstore

```bash
cosign sign --key cosign.key <registry>/<image>:<tag>          # sign with a stored key
cosign sign <registry>/<image>:<tag>                             # keyless signing via Sigstore (OIDC-based
                                                                   # identity, no key management needed)
cosign verify --key cosign.pub <registry>/<image>:<tag>
cosign attest --predicate sbom.json --type cyclonedx <registry>/<image>:<tag>   # attach the SBOM as a
                                                                                  # signed attestation
```

- **Keyless signing** (Sigstore/Fulcio/Rekor) ties a signature to an OIDC identity (e.g. "this GitHub
  Actions workflow, in this repo") instead of a long-lived private key to manage/rotate/protect — the
  supply-chain-security equivalent of preferring OIDC federation over static cloud credentials elsewhere
  in this stack.
- Verification at deploy time (an admission controller — Kyverno/OPA Gatekeeper, see
  `kubernetes-access-control` skill — checking image signatures before allowing a pod to run) is what
  actually enforces "only signed images run" — signing without enforced verification is documentation,
  not a control.

## Provenance / SLSA

- Provenance attestation records *how* an artifact was built (which source commit, which build system,
  which pipeline) — cryptographically signed alongside the artifact via the same cosign attestation
  mechanism, answering "prove this image came from this exact CI run on this exact commit," not just
  "this image is unmodified since signing."
- SLSA (Supply-chain Levels for Software Artifacts) defines maturity levels for how strong these
  guarantees are — useful as a shared vocabulary/target when a compliance requirement asks for a
  specific supply-chain security posture rather than inventing bespoke criteria.

## Common Pitfalls

- Images signed but nothing in the deployment path actually verifies the signature — signing without
  enforced verification provides no real guarantee, just an audit trail nobody checks.
- SBOM generated once at initial setup and never regenerated per build — an SBOM is only accurate for the
  exact artifact it was generated from; a stale SBOM answers "what was in an old build," not the current one.
- Signing keys (for key-based, non-keyless signing) stored without the same rigor as any other secret
  (see `.claude/rules/secrets.md`, `vault` skill) — a leaked signing key defeats the entire guarantee.
- Treating "we generate an SBOM" as sufficient without ever actually querying it against newly-disclosed
  CVEs — the SBOM's value is in being queryable later, not just existing.
