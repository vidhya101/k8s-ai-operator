---
description: Run the repository onboarding workflow — detect stack, install deps, learn the codebase, and summarize findings before any change is made.
argument-hint: "[optional: focus area, e.g. 'just the docker build']"
---

Run the onboarding workflow from `CLAUDE.md` Section 2 against this repository right now: $ARGUMENTS

1. Detect every dependency manifest and IaC/CI/CD file present (do not assume the stack — enumerate what's
   actually there: language package manifests, Terraform/Ansible, Dockerfiles, Helm/Kustomize, CI workflow
   files, existing Argo Applications).
2. Install/sync dependencies for whatever was found; report which installs succeeded and which failed.
3. Read enough of the codebase to state: what the service does, its entry point and runtime, its external
   dependencies, and its current deployment target if any.
4. Check for existing Terraform state, an existing CI pipeline, and existing K8s manifests/Helm
   charts/Argo Applications — flag anything that looks like it would be duplicated by new work.
5. If a container image is part of this repo, build it and report pass/fail plus exposed ports.

Do not write or modify any files during this command — this is discovery only. End with a concise summary
organized under: Stack detected / Dependencies status / What this service does / Existing infra & CI/CD
state / Open questions or missing information (per `CLAUDE.md` Section 1.1, do not silently fill gaps).
