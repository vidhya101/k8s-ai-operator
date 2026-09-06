---
name: ansible
description: Write, review, and troubleshoot Ansible playbooks and roles — idempotency, inventory, vault, and dynamic inventory for cloud hosts. Use for configuration management, host bootstrapping, or kubeadm node provisioning tasks.
---

# Ansible

Configuration management and host bootstrapping. Ansible configures hosts/nodes; once a Kubernetes
cluster is running, application state belongs to GitOps (`argocd` skill), not to a playbook re-run.

## Core Principles

- Idempotency is mandatory: running a playbook twice must produce the same end state with no side effects
  on the second run. Prefer built-in modules (`apt`, `yum`, `copy`, `template`, `service`, `user`, ...)
  over `command`/`shell`, which are not idempotent by default and need explicit `creates`/`when` guards.
- `--check --diff` (dry run) before any run against a host that matters.
- Secrets via Ansible Vault or an external lookup (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault
  lookup plugins) — never plaintext credentials in `group_vars`/`host_vars`.
- Roles for anything reused across playbooks/projects; a flat playbook is fine for a genuinely single-use
  task.

## Inventory

- Dynamic inventory (`amazon.aws.aws_ec2`, `azure.azcollection.azure_rm`, `google.cloud.gcp_compute`)
  over static IP lists wherever hosts are cloud-managed — static inventory drifts the moment autoscaling
  replaces an instance.
- Separate inventory (or inventory group) per environment; group_vars scoped per environment, not one
  global vars file with `when: env == "prod"` conditionals sprinkled through tasks.

## Playbook Constructs

```yaml
- name: Install and start nginx
  hosts: webservers
  vars:
    packages: [nginx, curl]
  tasks:
    - name: Install packages
      ansible.builtin.apt: { name: "{{ item }}", state: present }
      loop: "{{ packages }}"
      when: ansible_os_family == "Debian"       # conditional — skip cleanly on non-matching hosts
      notify: Restart nginx                      # triggers the handler below, only if this task changed something

  handlers:
    - name: Restart nginx
      ansible.builtin.service: { name: nginx, state: restarted }
```

- **Handlers** run at most once per play, at the end (or when explicitly flushed), and only if a task
  that `notify`s them actually reported `changed` — the standard pattern for "restart the service, but
  only if its config actually changed," instead of restarting unconditionally on every run.
- **Loops** (`loop:`, or the older `with_items:`) iterate a task over a list instead of duplicating the
  task block; **conditionals** (`when:`) skip a task based on facts/variables — both keep a playbook from
  needing near-duplicate tasks per host type/OS/environment.
- **Variable precedence**: `host_vars/<host>.yml` overrides `group_vars/<group>.yml`, which overrides
  role defaults — a variable "not taking effect" is very often being overridden by a higher-precedence
  source elsewhere, not failing to be set at all.
- **Collections** package reusable roles/modules/plugins for distribution (e.g. `amazon.aws`,
  `azure.azcollection`, `community.general`) — installed via `ansible-galaxy collection install` (or
  listed in `requirements.yml` alongside roles) rather than vendored by hand.

## Key Commands

```bash
ansible-playbook --syntax-check playbook.yml
ansible-lint playbook.yml
ansible-playbook --check --diff -i inventory playbook.yml   # dry run
ansible-playbook -i inventory playbook.yml --limit <host>   # scope a real run
ansible-vault encrypt group_vars/prod/secrets.yml
ansible-galaxy install -r requirements.yml
```

## kubeadm Node Bootstrapping (common Ansible use case)

Typical division of labor: Ansible installs the container runtime, `kubeadm`/`kubelet`/`kubectl`
packages, disables swap, configures kernel modules/sysctl for networking, and runs `kubeadm init`/
`kubeadm join` — see the `kubeadm` skill for the cluster-level sequencing and HA control-plane concerns.

## Common Pitfalls

- `shell`/`command` tasks with no `creates`/`changed_when`, so every run reports "changed" and isn't
  actually idempotent even if the underlying action is harmless to repeat.
- Secrets checked into `group_vars` unencrypted "just for now."
- One giant playbook instead of roles, making it impossible to reuse the "install Docker" step elsewhere.
- Static inventory IPs that silently go stale after an autoscaling event replaces the instance.
