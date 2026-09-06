# Sandbox — Regression-Testing Toolchain Image

One Docker image where every tool this repo's stack references is preinstalled. Purpose: give the
`sandbox-verifier` agent (and any manager needing to run a real command in a real environment) a
scratch execution surface with **no setup time**. No "let me install terraform quick" during a
verification.

## What's inside

- **OS**: Ubuntu 24.04 LTS
- **Languages/runtimes**: Python 3.12 + `uv`, Node.js 20 LTS, Go 1.23, OpenJDK 21 + Maven, Ruby
- **DevOps CLIs**: Docker CLI + buildx + compose plugin, kubectl, Helm, kind, kubeconform,
  Terraform, Terragrunt, tflint, Ansible + ansible-lint, ArgoCD CLI, Vault, GitHub CLI (`gh`)
- **Security scanners**: Trivy, Checkov, cosign, syft (SBOM), yamllint, shellcheck
- **Load / chaos**: k6
- **Encryption**: age + sops
- **Utilities**: unzip, zip, wget, curl, jq, yq, dig, mtr, tcpdump, htop, lsof, strace, less, vim
- **DB clients**: psql, mysql/mariadb-client
- **Non-root user**: `dev` (uid 1000), in `docker` and `sudo` groups (NOPASSWD sudo inside
  container only — not host escalation)

Not included on purpose:
- **kubelet** — this is a client toolbox, not a K8s node. Use `kind` for a local cluster
  instead.
- **Client-specific credentials** — mount them read-only per §Usage below.
- **Ollama / model weights** — huge; run Ollama on host or `monitor` VM and point the sandbox at
  `OLLAMA_HOST` per `.claude/config/environment.md`.

## Build

```bash
# From the repo root that contains .claude/
docker build -t devops-sandbox:latest -f .claude/sandbox/Dockerfile .claude/sandbox/
```

First build takes ~10-15 minutes on a decent connection (downloads several large tarballs).
Subsequent builds use the layer cache and are near-instant unless base packages change.

## Usage — one-shot smoke run

```bash
docker run --rm devops-sandbox:latest
# Prints tool versions and exits — quick sanity check the image is intact
```

## Usage — interactive shell

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v "$HOME/.aws":/home/dev/.aws:ro \
  -v "$HOME/.kube":/home/dev/.kube:ro \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -w /workspace \
  devops-sandbox:latest bash
```

Mounts explained:

- `$PWD → /workspace` — the repo you're working on, RW so the sandbox can create scratch state
  (Terraform's `.terraform/`, kind clusters, etc.)
- `$HOME/.aws → /home/dev/.aws:ro` — AWS creds read-only; the sandbox can use them but can't
  overwrite them
- `$HOME/.kube → /home/dev/.kube:ro` — same for kubeconfig
- `/var/run/docker.sock` — Docker-out-of-Docker so `kind create cluster` and `docker build` work
  from inside the sandbox (uses the HOST's Docker daemon; not Docker-in-Docker)

**Don't mount** `$HOME/.ssh` unless the sandbox actually needs it — reduces credential blast
radius if a compromised process runs inside.

## Usage — from `sandbox-verifier` agent

The agent's job is to prove desired = actual before promoting a change. In this image:

```bash
# Terraform verification
docker run --rm \
  -v "$PWD":/workspace -w /workspace \
  -e AWS_PROFILE=sandbox \
  -v "$HOME/.aws":/home/dev/.aws:ro \
  devops-sandbox:latest \
  bash -c "terraform init && terraform plan -out=tfplan && terraform show -json tfplan > plan.json"

# Kubernetes manifest verification against a fresh kind cluster
docker run --rm \
  -v "$PWD":/workspace -w /workspace \
  -v /var/run/docker.sock:/var/run/docker.sock \
  devops-sandbox:latest \
  bash -c "kind create cluster --name verify-$$ && \
           kubectl apply --dry-run=server -f manifests/ && \
           kubeconform -strict manifests/ && \
           kind delete cluster --name verify-$$"

# Ansible dry run
docker run --rm \
  -v "$PWD":/workspace -w /workspace \
  -v "$HOME/.ssh":/home/dev/.ssh:ro \
  devops-sandbox:latest \
  bash -c "ansible-playbook --syntax-check playbook.yml && \
           ansible-lint playbook.yml && \
           ansible-playbook --check --diff -i inventory playbook.yml"
```

## Adding tools

If a project needs a tool this image doesn't include, don't manually install it inside a
running container — that gets lost on `--rm`. Add it to the Dockerfile with a rationale in a
comment, rebuild, and commit.

Prefer official package repos or checksummed binary downloads over `curl | sh` (a few `curl |
sh` calls in the current Dockerfile are for tools whose install scripts are the vendor-endorsed
mechanism — this is a documented tradeoff, not laziness).

## Alternatives

- **Nix / devcontainer**: better reproducibility per platform, more setup investment. If this
  image proves useful and you want fully-deterministic builds, migrate to a Nix flake or a
  `devcontainer.json` next.
- **Vagrant VM (existing `tools` VM)**: is where Postgres already runs. The `tools` VM has less
  headroom (4 GB, sonarqube crashing) — the sandbox image is a lower-footprint alternative for
  regression-testing work that doesn't need to be persistent.

## Common pitfalls

- **Docker-out-of-Docker vs. Docker-in-Docker**: mounting `/var/run/docker.sock` means `docker`
  inside the container talks to the HOST Docker daemon — containers you launch from inside are
  actually run by the host. Fine for `kind` and image builds; means container network is host's
  network, not the sandbox's.
- **Credentials leaked into image layers**: never `RUN echo $SECRET > ~/.aws/credentials` in the
  Dockerfile — bake credentials at RUN time via mount only, never build time.
- **Old image**: `docker pull` doesn't affect locally-built tags. Rebuild after any Dockerfile
  edit; `docker system prune -f` if the layer cache gets confused.
- **Trivy DB stale**: the Trivy vuln DB updates independently of the image. On first scan inside
  a fresh container, Trivy downloads its DB — takes a minute.
