---
description: Full Terraform/Ansible IaC review — plan sanity, security, state hygiene, and Checkov findings.
argument-hint: "[path to module or environment, defaults to whole repo]"
---

Review the infrastructure code at: $ARGUMENTS (default: entire repository).

1. Use the `terraform` and `terraform-state`/`terraform-security`/`terraform-best-practices` skills as
   applicable, plus the `ansible` skill if playbooks are present.
2. Delegate the deep review to the `terraform-reviewer` agent (and `principal-devsecops` for policy/scan
   findings) — do not just skim the files yourself, get their structured findings.
3. Run `terraform fmt -check`, `terraform validate`, and `checkov -d <path>` if available; if a plan can
   be generated safely (no credentials issue, non-prod), run `terraform plan` and review the diff.
4. Report: blocking issues (would cause an incident or is a security gap), non-blocking improvements, and
   anything skipped because it needed cloud credentials or state access that wasn't available.

Do not run `terraform apply` at any point in this command.
