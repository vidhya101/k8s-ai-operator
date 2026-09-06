---
name: compliance-frameworks
description: Compliance and hardening frameworks — CIS Benchmarks, Cloud Well-Architected Frameworks, and SOC2/ISO27001/PCI-DSS/NIST mapping. Use when a client requirement references a specific framework/standard, to translate it into concrete infrastructure/process checks rather than treating it as vague box-checking.
---

# Compliance & Hardening Frameworks

Translates "we need to be compliant with X" into concrete, checkable infrastructure and process controls.
See `terraform-security`/`docker-security`/`kubernetes-access-control` for the technical controls these
frameworks ultimately point back to — this skill is about mapping requirement to control, not a
replacement for the technical skills that implement the control.

## CIS Benchmarks

- Prescriptive, technical hardening baselines per technology (CIS Kubernetes Benchmark, CIS Docker
  Benchmark, CIS AWS Foundations Benchmark, CIS Distribution-specific OS benchmarks) — each is a long,
  specific checklist (disable this kernel module, set this file permission, require this IAM setting).
- `kube-bench` (Kubernetes), `docker-bench-security` (Docker) automate checking a running system against
  the relevant CIS benchmark — run these rather than manually walking a checklist by hand.
- Not every CIS control is appropriate for every environment (some are genuinely disruptive to specific
  legitimate use cases) — CIS itself publishes "Level 1" (broadly applicable) vs. "Level 2" (stricter,
  more operationally involved) profiles; treat a Level 2 deviation as a decision to document, not
  something to silently skip or silently force through.

## Cloud Well-Architected Frameworks

- AWS/Azure/GCP each publish a Well-Architected Framework — pillars covering operational excellence,
  security, reliability, performance efficiency, cost optimization (and sustainability, in AWS's version).
  Useful as a structured review lens for an architecture (see `architecture-review` skill) even outside a
  formal compliance requirement — a good checklist for "did we consider X" across a design.
- AWS provides a formal Well-Architected Tool for structured reviews; the value is in the questions it
  forces you to answer explicitly, not the tool itself — the same review can be done manually against the
  published pillars.

## SOC2 / ISO27001 / PCI-DSS / NIST Mapping

- These are **audit frameworks**, not technical checklists — they specify *outcomes* (access is
  reviewed periodically, changes are logged and reviewable, data is encrypted) that map to many possible
  technical implementations. The mapping work is: for each control the framework requires, identify the
  specific technical/process evidence that satisfies it (e.g. "access reviewed periodically" → IAM access
  review process + `cloud-iam-hardening`-style least-privilege enforcement + an audit log).
- PCI-DSS specifically has prescriptive network segmentation and cardholder-data-handling requirements
  that directly inform `networking`/`aws`/`azure` VPC and security-group design — if a system genuinely
  handles card data, get PCI scope confirmed explicitly before designing network boundaries, since scope
  determines which parts of the architecture the strictest controls apply to.
- Never claim compliance status on the user's behalf — this skill helps map requirements to controls;
  actual attestation/certification is an audit outcome involving people and evidence beyond what
  infrastructure configuration alone can assert.

## Common Pitfalls

- Treating a compliance framework as a one-time checklist instead of an ongoing control (access reviews,
  log retention, patching cadence all need to keep happening, not just be true once at audit time).
- CIS Benchmark scan run once and never re-run as the environment changes — configuration drift is exactly
  what these baselines are meant to catch on an ongoing basis, not just at initial hardening.
- Assuming a managed cloud service is automatically compliant just because the cloud provider has its own
  compliance certifications — the shared responsibility model means the provider's certification covers
  their side; the configuration of what you built on top is still yours to get right.
- A compliance requirement driving a technical decision without the actual control being verified as
  correctly implemented — e.g. "we need encryption at rest for SOC2" satisfied by enabling a setting
  without confirming it's actually applied to every relevant resource.
