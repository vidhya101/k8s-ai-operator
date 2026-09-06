# Rule: Change Safety

Applies to every task in this repository, regardless of tech stack.

- Never run `terraform apply`, `terraform destroy`, `helm install/upgrade/uninstall`,
  `kubectl apply/delete`, `docker push`, `ansible-playbook` (non-check), or any deploy command without
  showing the plan/diff first and getting explicit confirmation. `settings.json` already gates these —
  do not work around the gate by chaining commands or using `-auto-approve`/`--yes`/`-y` flags.
- Treat `terraform plan` output showing `-/+` (replace) or `-` (destroy) on a stateful resource
  (database, volume, bucket, PVC, secret) as requiring explicit sign-off before apply, even if the rest
  of the plan is benign.
- Never run `terraform state rm/mv/push`, `kubectl delete namespace/node/crd`, or any command that can
  silently orphan or destroy state, without confirming the blast radius first.
- Never force anything: no `--force`, `-f` on destructive commands, `git push --force`, `git reset --hard`,
  `rm -rf` — surface the safer alternative first (see the global "Executing actions with care" policy).
- Before touching a running production workload (pod eviction, rolling restart, scale-to-zero, node drain,
  DB failover), state what will be briefly unavailable and for how long, and get confirmation.
- If a command's output is ambiguous about which environment/cluster/account it targeted, stop and confirm
  the target before proceeding — do not infer from a previous unrelated command.
