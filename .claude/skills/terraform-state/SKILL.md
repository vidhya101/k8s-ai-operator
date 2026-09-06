---
name: terraform-state
description: Manage, inspect, and safely recover Terraform state — remote backends, locking, drift, import, and state surgery (mv/rm/import). Use when state looks out of sync, a lock is stuck, a resource needs importing, or a backend migration is needed.
---

# Terraform State

State is the source of truth Terraform uses to map config to real resources. Treat every state mutation
as high-risk — a bad `state rm`/`state mv` can permanently orphan or double-manage a resource.

## Core Principles

- Never edit `.tfstate` by hand. Use `terraform state`/`import`/`moved` blocks.
- Never commit `.tfstate` to git — it can contain secrets in plaintext.
- Always inspect before mutating: `terraform state list`, `terraform state show <addr>`, `terraform plan`.
- Prefer `moved` blocks (declarative, versioned, reviewable in a PR) over ad hoc `terraform state mv`.
- Confirm which backend/workspace is active before any state command — a state command against the wrong
  workspace is silent corruption of the wrong environment.

## Backends

- Remote + locking backend for anything with more than one operator: S3 + DynamoDB (AWS), `azurerm`
  storage account with blob lease locking (Azure), GCS with native locking (GCP), Terraform Cloud/Enterprise.
- Local state is acceptable only for a single-operator throwaway/learning setup — flag it if found in a
  repo that otherwise looks team-maintained.
- Backend migration (`terraform init -migrate-state`) rewrites where state lives — back up the existing
  state file first (`terraform state pull > backup.tfstate`) and confirm before running.

## Key Commands

```bash
terraform state list                       # inventory of managed resources
terraform state show <addr>                # current attributes Terraform believes are true
terraform state pull > backup.tfstate       # snapshot before any risky operation
terraform plan -refresh-only                # see drift without changing anything
terraform import <addr> <id>                # bring an existing resource under management
terraform state mv <old_addr> <new_addr>    # rename/move within state (prefer `moved` block in code)
terraform state rm <addr>                   # stop managing without destroying (orphans it — confirm first)
terraform force-unlock <lock_id>            # only after confirming no other operation is actually running
```

## Common Pitfalls

- Running `import` without first writing the matching resource block — Terraform will plan to destroy and
  recreate on the next apply if the config doesn't match reality.
- `state rm` used to "fix" a plan instead of understanding why the plan is wrong — this just stops
  Terraform from managing the resource, it doesn't fix drift.
- A stuck lock force-unlocked while another apply is genuinely still running — always verify first
  (check CI for an in-flight run) before force-unlocking.
- Splitting one state file into multiple without using `state mv`/`moved`, causing Terraform to see
  "new" resources and plan to recreate what already exists.
