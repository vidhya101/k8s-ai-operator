---
name: terraform
description: Design, review, troubleshoot, validate, and improve Terraform infrastructure safely across AWS, Azure, GCP, Kubernetes, and other providers.
---

# Terraform Engineering Skill

Use this skill for Terraform design, review, troubleshooting, validation, refactoring, module development, state analysis, security review, and infrastructure planning.

## Core Principles

- Inspect before modifying.
- Never apply infrastructure automatically.
- Never destroy infrastructure automatically.
- Never manipulate Terraform state without explicit approval.
- Never read or expose secret values from state.
- Prefer small, reversible changes.
- Preserve existing resource addresses where possible.
- Prefer declarative configuration over manual state commands.
- Validate every change.
- Review the plan before any apply.
- Do not assume the cloud provider, account, subscription, project, region, workspace, or environment.

## Repository Discovery

Before changing Terraform, identify:

- Terraform root modules
- child modules
- provider configuration
- Terraform version constraints
- provider version constraints
- backend configuration
- state location
- workspace usage
- environment structure
- variable files
- outputs
- data sources
- modules
- resource naming
- tagging strategy
- CI/CD integration
- security scanning tools
- documentation
- existing user changes

Useful commands:

```bash
pwd
find . -maxdepth 4 -type f \
  -not -path './.git/*' \
  -not -path './.terraform/*' \
  | sort
git status --short
git branch --show-current
terraform version
terraform providers
terraform workspace show
terraform state list
```

See `terraform-state` for state-specific operations, `terraform-security` for the security review
checklist, and `terraform-best-practices` for project structure/module conventions.

## Reverse-Engineering Existing Infrastructure (Terraformer)

When infrastructure was created manually (console, ad hoc CLI) and needs to come under Terraform
management — a common state to inherit, and a real documentation/configuration-drift risk in its own
right — `terraformer` generates Terraform code from the live resources instead of writing it by hand:

```bash
terraformer import aws --resources=vpc,subnet,sg,ec2_instance --regions=us-east-1
terraformer import azure --resources=resource_group,virtual_network --regions=eastus
```

- Terraformer produces both the `.tf` resource definitions *and* imports them into a local state file —
  review the generated code before treating it as final: auto-generated resource names/organization are
  rarely as clean as hand-written Terraform, and it's worth refactoring into proper modules per
  `terraform-best-practices` rather than committing the raw generated output as-is.
- Scope the `--resources`/`--regions` flags deliberately rather than importing an entire account at once
  — a full-account import produces an enormous, unreviewable diff and pulls in resources that may not
  need to be Terraform-managed at all (e.g. resources another team owns).
- After generating, run `terraform plan` immediately — it should show no changes (the generated code
  should exactly match the imported state); any drift the plan shows is a signal the generated code needs
  correction before it's trusted as the source of truth going forward.
- This is a one-time migration workflow, not an ongoing sync mechanism — once resources are under
  Terraform management via the generated code, all further changes should go through normal
  plan/review/apply, not repeated re-imports.

## Common Pitfalls

- Treating Terraformer's raw output as final instead of refactoring it into the project's actual module
  conventions — it's a starting point for migration, not finished, idiomatic Terraform.
- Importing too broad a resource scope at once, producing an unreviewable initial state and pulling in
  resources outside the intended ownership boundary.
- Skipping the post-import `terraform plan` check — the one step that actually confirms the generated
  code and the real infrastructure agree before anyone starts trusting it.