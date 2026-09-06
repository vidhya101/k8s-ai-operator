# Rule: Environment Awareness

This setup is used across many clients and repos — never assume which environment, account, or cluster
is in scope. Detect it every time; don't carry an assumption over from a previous session or repo.

- Before running any command that targets infrastructure, determine and state: which environment
  (dev/stage/prod or client-specific naming), which cloud account/subscription/project, which Terraform
  workspace/state file, and which `kubectl` context is current (`kubectl config current-context`).
- If the target looks like production (name contains `prod`/`production`, or is the account/project the
  repo's docs designate as production), apply extra caution: prefer read-only investigation first,
  require explicit confirmation before any mutating command, and prefer the smallest reversible change.
- If multiple `.tfvars`, workspaces, or overlay directories exist (e.g. `environments/dev`,
  `environments/prod`, Kustomize overlays, Helm values-per-env files) and the task doesn't specify which
  one, ask rather than guessing — applying the wrong environment's config is a production incident.
- Do not switch `kubectl` context, `aws`/`az`/`gcloud` active profile, or Terraform workspace without
  saying so — a silent context switch means the next command runs somewhere the user didn't expect.
- When a repo has no clear environment separation at all, say so explicitly rather than assuming one
  (e.g. "this repo appears to manage a single, undifferentiated environment — confirm before applying").
