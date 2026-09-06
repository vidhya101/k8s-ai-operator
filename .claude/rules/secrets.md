# Rule: Secrets & Sensitive Data

Applies regardless of which cloud, secret manager, or tech stack the repo uses.

- Never read, print, log, or echo the contents of: `.tfstate`/`.tfstate.*`, `*.pem`/`*.key`, `.env`/`.env.*`,
  kubeconfig files, `~/.aws/credentials`, `~/.azure/`, `~/.config/gcloud/`, or any file matching a
  private-key/credential pattern. `settings.json` denies reading the common ones — treat that as a floor,
  not the full list; apply the same caution to anything that looks like a credential even if unlisted.
- Never write a real secret value (API key, password, token, connection string, private key) into a file
  that will be committed — Terraform `.tf`/`.tfvars`, Ansible playbooks/vars, Kubernetes manifests, CI
  workflow YAML, or application config. Reference secrets by lookup (SSM Parameter Store, Secrets Manager,
  Azure Key Vault, GCP Secret Manager, Vault, Ansible Vault, K8s External Secrets Operator) instead.
- If a secret is discovered already committed in the repo or in Terraform state, stop and report it —
  do not attempt to "fix" it by force-pushing history rewrites or deleting state without the user's
  explicit direction; secret rotation is also required and is the user's call, not an automatic action.
- When showing command output that might contain a secret (e.g. `kubectl get secret -o yaml`,
  `terraform output`, a `.env` diff), redact the value before displaying it.
- Never invent or assume a secret's value to "unblock" a task — if a required credential is missing,
  say so and ask where it should come from.
