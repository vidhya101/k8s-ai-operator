---
description: Generate a fast structural map of the repo (files, detected tool types, cross-references) in one pass instead of iterative exploration.
argument-hint: "[optional: subdirectory to scope the map to]"
---

Map the structure of: $ARGUMENTS (default: whole repo).

Run the `repository-discovery` skill's detection commands in one batch (not iteratively file-by-file) and
produce a structural summary:

1. One `find` pass for every manifest/config type (Terraform, Ansible, Docker, Helm/Kustomize, CI
   workflows, GitOps Applications) — see `repository-discovery` for the exact patterns.
2. For each Terraform root/module found: its provider(s), backend, and whether it references other
   modules (grep `module "..." { source = }`).
3. For each CI workflow found: what triggers it and what it deploys/applies, if evident from the file.
4. Note any file whose purpose isn't obvious from name/location alone as a follow-up to investigate, rather
   than guessing.

Output as a compact tree/table, not prose — this command exists specifically to avoid burning turns on
repeated `find`/`grep`/`Read` calls later in the session. No persisted state is written; re-run this
command if the repo structure changes significantly since a full re-scan is cheap at this repo's size.
