---
name: terragrunt
description: Terragrunt — a thin wrapper around Terraform for keeping multi-environment configuration DRY (backend config, provider config, variable inheritance). Use when a project's Terraform is organized with Terragrunt instead of plain Terraform directory-per-environment.
---

# Terragrunt

A wrapper around Terraform that solves a specific pain point `terraform-best-practices` names but doesn't
fully resolve on its own: keeping backend configuration, provider version pins, and common variables from
being copy-pasted across every environment directory.

## Core Model

```hcl
# terragrunt.hcl (at the environment level, e.g. environments/prod/us-east-1/vpc/)
include "root" {
  path = find_in_parent_folders()      # inherits shared backend/provider config from a root terragrunt.hcl
}

terraform {
  source = "../../../modules//vpc"      # points at the actual Terraform module
}

inputs = {
  cidr_block  = "10.0.0.0/16"
  environment = "prod"
}
```

```hcl
# root terragrunt.hcl — backend/provider config defined once, inherited everywhere
remote_state {
  backend = "s3"
  generate = { path = "backend.tf", if_exists = "overwrite" }
  config = {
    bucket = "my-terraform-state"
    key    = "${path_relative_to_include()}/terraform.tfstate"    # unique key per environment, derived
    region = "us-east-1"
  }
}
```

- Backend configuration (bucket, locking, key naming) is defined once at the root and inherited — this is
  the main thing Terragrunt adds over plain Terraform's directory-per-environment pattern
  (`terraform-best-practices`), where each environment's backend block is otherwise hand-copied and prone
  to drift/typos.
- `inputs` map replaces manually maintaining a separate `.tfvars` per environment with the same variable
  names — reduces (but doesn't eliminate) the same duplication concern.

## Key Commands

```bash
terragrunt plan                        # wraps terraform plan with the resolved inherited config
terragrunt apply
terragrunt run-all plan                 # plan across every module in a directory tree — useful for
                                         # reviewing a change that spans multiple Terragrunt units
terragrunt run-all apply --terragrunt-parallelism 3   # careful — see pitfalls below
```

## Common Pitfalls

- `run-all apply` executed broadly across many environments/modules in one command — the parallel,
  multi-environment blast radius of a single mistake is much larger than a plain `terraform apply` in one
  directory; treat `run-all apply` with at least the same caution `.claude/rules/safety.md` requires for
  any apply, and prefer running it scoped rather than against everything at once.
- Deep inheritance chains (`include` pointing through several levels of parent `terragrunt.hcl` files)
  becoming hard to trace — what value a given environment actually resolves to can require reading
  several files; keep the inheritance depth shallow enough to still be reviewable.
- Terragrunt version and the wrapped Terraform version drifting out of compatibility — pin both
  explicitly, the same version-pinning discipline `terraform-best-practices` requires for Terraform itself.
- Treating Terragrunt as a reason to skip proper Terraform module design (`terraform-best-practices`) —
  it manages *inheritance/DRY-ness of configuration*, not module quality; badly designed modules are still
  badly designed modules underneath a Terragrunt wrapper.
