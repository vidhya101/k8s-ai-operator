---
name: repository-discovery
description: Detect an unfamiliar repository's tech stack, dependency manifests, and existing infra/CI/CD state before making any change. Use at the start of any task in a repo you haven't already explored this session — this is the mechanics behind CLAUDE.md Section 2's onboarding workflow.
---

# Repository Discovery

The concrete detection steps behind `CLAUDE.md` Section 2 (Repository Onboarding Workflow) and the
`/onboard` command. Use this whenever working in a repo — or a part of a repo — not already understood
this session.

## Detect the Stack

```bash
find . -maxdepth 3 -type f \
  \( -name "requirements.txt" -o -name "pyproject.toml" -o -name "package.json" \
     -o -name "go.mod" -o -name "pom.xml" -o -name "build.gradle*" -o -name "Gemfile" \
     -o -name "Cargo.toml" -o -name "*.tf" -o -name "*.tfvars" -o -name "ansible.cfg" \
     -o -name "requirements.yml" -o -name "Dockerfile*" -o -name "docker-compose*.yml" \
     -o -name "Chart.yaml" -o -name "kustomization.yaml" -o -iname "Jenkinsfile" \) \
  -not -path "./.git/*" -not -path "*/node_modules/*" -not -path "./.terraform/*" | sort

find . -maxdepth 3 -path "*/.github/workflows/*.yml" 2>/dev/null
find . -maxdepth 4 -path "*argocd*" -o -path "*Application*.yaml" 2>/dev/null
```

## Check Existing State (don't duplicate what's already there)

```bash
git status --short && git branch --show-current && git log --oneline -10
# Terraform
find . -name "*.tfstate" -o -name ".terraform.lock.hcl"     # local state present? backend config?
grep -rl "backend " --include="*.tf" .                        # remote backend configured?
# Kubernetes / GitOps
kubectl config current-context 2>/dev/null                    # is a cluster already targeted?
find . -iname "Application.yaml" -o -path "*argocd*"          # existing GitOps Application defined?
# CI/CD
ls .github/workflows/ 2>/dev/null
```

## Install/Sync Dependencies (whatever manifests were found)

```bash
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f package.json ] && npm ci
[ -f go.mod ] && go mod download
[ -f *.tf ] && terraform init
[ -f requirements.yml ] && ansible-galaxy install -r requirements.yml
```

Report which installs succeeded and which failed — don't silently skip a failed install and proceed as
if dependencies are ready.

## Synthesize

State, before making any change: what the service/repo does, its runtime and entry point, its external
dependencies, its existing infra/CI/CD state, and anything ambiguous that needs to be asked about rather
than assumed (see `CLAUDE.md` Section 1.1's "do not silently choose" list).

## Common Pitfalls

- Writing new Terraform/CI/CD against a repo without checking for an existing backend/pipeline first,
  creating a parallel, conflicting setup.
- Assuming the tech stack from the repo name/description instead of what the manifests actually show.
- Skipping discovery on a repo "because it's small" — a small repo can still have an existing convention
  (branching, naming, environment structure) worth matching.
