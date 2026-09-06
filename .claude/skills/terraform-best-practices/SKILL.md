---
name: terraform-best-practices
description: Terraform module design, project structure, naming, and workflow conventions. Use when structuring a new Terraform project, deciding on module boundaries, or reviewing for maintainability.
---

# Terraform Best Practices

Structural and workflow conventions — pair with `terraform-security` for the security lens and
`terraform-state` for state-specific operations.

## Project Structure

- Directory-per-environment (`environments/dev`, `environments/prod`) or workspaces — pick one pattern per
  repo and stay consistent; don't mix both without a clear reason.
- Modules for genuinely repeated patterns (used in 2+ places or explicitly designed for reuse across
  teams/repos) — not for a single-use resource block; a one-off doesn't need a module wrapper (Section 1.2).
- Standard file layout inside a root module: `main.tf` (or split by resource type), `variables.tf`,
  `outputs.tf`, `providers.tf`/`versions.tf`, `terraform.tfvars`/`*.auto.tfvars` for environment values.

## Conventions

- Pin `required_version` and every `required_providers` entry with a version constraint.
- Name resources descriptively and consistently (`<project>-<env>-<resource>` or the repo's existing
  pattern) — check existing naming before introducing a new scheme.
- Tag/label everything the provider supports tagging on: owner, environment, cost-center, managed-by=terraform.
- Use `variables.tf` with `type`, `description`, and `default` (only where a sane default exists) for every
  input; avoid untyped variables.
- Outputs should expose what downstream consumers (other modules, CI, humans) actually need — not every
  internal attribute.

## Workflow

```bash
terraform fmt -recursive          # formatting, run before every commit
terraform validate                # syntax/internal consistency, no cloud calls
terraform plan -out=tfplan        # review before apply, save the plan to apply exactly what was reviewed
terraform apply tfplan            # apply the reviewed plan, not a fresh unreviewed plan
```

Always apply a saved plan file, not a fresh `terraform apply` — between review and apply, drift or a
concurrent change could otherwise make the applied plan different from what was reviewed.

## Common Pitfalls

- A module with 15 optional variables "for flexibility" that no consumer actually varies — collapse to
  what's used.
- Copy-pasted resource blocks across environments instead of one module parameterized by environment —
  makes every fix a 3x find-and-replace.
- Provider configuration duplicated per module instead of passed from the root — makes multi-account/
  multi-region setups error-prone.
- No `description` on variables/outputs, forcing every consumer to read the resource body to know what a
  variable does.
