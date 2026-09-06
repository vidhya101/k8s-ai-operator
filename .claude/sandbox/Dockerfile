# devops-sandbox: single toolchain image for regression testing.
#
# Purpose: give the `sandbox-verifier` agent (and any manager that needs to
# actually run a real command in a real environment) one image where every tool
# in this repo's stack is preinstalled. No "let me install terraform real quick"
# during a verification run — everything's already there.
#
# Non-goals:
#   - Not a build image for shipping apps (too large).
#   - Not for running production workloads (root-less but toolchain-heavy).
#   - Not a K8s node image (kubelet omitted — this is a CLIENT toolbox, not a node).
#
# Build:
#   docker build -t devops-sandbox:latest -f .claude/sandbox/Dockerfile .claude/sandbox/
#
# Use (from sandbox-verifier):
#   docker run --rm -it \
#     -v "$PWD":/workspace \
#     -v "$HOME/.aws":/home/dev/.aws:ro \
#     -v "$HOME/.kube":/home/dev/.kube:ro \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -w /workspace \
#     devops-sandbox:latest bash
#
# Mounts explained:
#   /workspace              → the repo under test (RW so the verifier can create scratch state)
#   /home/dev/.aws (ro)     → AWS credentials read-only (see .claude/config/environment.md)
#   /home/dev/.kube (ro)    → kubeconfig read-only
#   /var/run/docker.sock    → so kind / docker builds work inside (Docker-out-of-Docker pattern)

FROM ubuntu:24.04

# Use bash for RUN and set safer defaults
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH

# --- Base OS packages ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      # core shell / net / archive
      ca-certificates curl wget git unzip zip tar gzip bzip2 xz-utils \
      # text processing
      jq \
      # build essentials (for pip installs that need to compile, and for gcc-in-container needs)
      build-essential pkg-config \
      # networking / debugging
      dnsutils iputils-ping netcat-openbsd traceroute mtr-tiny tcpdump \
      # process / system introspection
      procps psmisc lsof strace htop \
      # openssh client for git-over-ssh and remote debugging
      openssh-client \
      # gnupg for repo keys
      gnupg lsb-release \
      # sudo (used only inside container by dev user; not for host escalation)
      sudo \
      # python + pip (system-managed; use uv for isolated envs)
      python3 python3-pip python3-venv \
      # java + jdk (OpenJDK 21 LTS, current default in 24.04)
      openjdk-21-jdk-headless \
      # maven for java project builds
      maven \
      # editors for interactive debugging
      vim-tiny less \
      # ruby (for community tools that rely on it)
      ruby \
      # postgres client (psql) + mysql/mariadb client
      postgresql-client mariadb-client \
      # yaml linter
      yamllint \
      # shellcheck for bash lint
      shellcheck \
    && rm -rf /var/lib/apt/lists/*

# --- yq (Go binary — apt package is old + confusingly-named) ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_${ARCH}" \
      -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq

# --- Node.js 20 LTS (via NodeSource) ---
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# --- Go 1.23 ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    GO_VERSION=1.23.4 && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://go.dev/dl/go${GO_VERSION}.linux-${ARCH}.tar.gz" | tar -C /usr/local -xz
ENV PATH=/usr/local/go/bin:${PATH}
ENV GOPATH=/home/dev/go
ENV PATH=${GOPATH}/bin:${PATH}

# --- Docker CLI (client only — mounts the host socket for Docker-out-of-Docker) ---
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y --no-install-recommends \
      docker-ce-cli docker-buildx-plugin docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# --- kubectl (latest stable) ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    KV=$(curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://dl.k8s.io/release/stable.txt) && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://dl.k8s.io/release/${KV}/bin/linux/${ARCH}/kubectl" \
      -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl

# --- Helm ---
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# --- kind (Kubernetes-in-Docker) ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://kind.sigs.k8s.io/dl/latest/kind-linux-${ARCH}" \
      -o /usr/local/bin/kind && chmod +x /usr/local/bin/kind

# --- kubeconform (K8s manifest schema validator) ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-${ARCH}.tar.gz" \
      | tar -xz -C /usr/local/bin kubeconform

# --- Terraform (via HashiCorp apt repo — always current) ---
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://apt.releases.hashicorp.com/gpg | \
      gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
      https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y --no-install-recommends \
      terraform vault && \
    rm -rf /var/lib/apt/lists/*

# --- Terragrunt ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://github.com/gruntwork-io/terragrunt/releases/latest/download/terragrunt_linux_${ARCH}" \
      -o /usr/local/bin/terragrunt && chmod +x /usr/local/bin/terragrunt

# --- tflint ---
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

# --- Ansible + ansible-lint + friends (isolated in a dedicated venv) ---
# Ubuntu 24.04 enforces PEP 668 — the system Python is externally-managed by apt.
# `pip install --break-system-packages` still can't uninstall apt-owned deps like
# python3-pathspec, which checkov pulls in transitively. A dedicated venv sidesteps
# that entirely and matches upstream Python guidance for 24.04+.
RUN python3 -m venv /opt/toolchain && \
    /opt/toolchain/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/toolchain/bin/pip install --no-cache-dir \
      ansible ansible-lint pre-commit checkov awscli
# Note: `yq` (Go binary from mikefarah/yq) is installed separately at /usr/local/bin/yq
# above; the PyPI `yq` package is a different tool and would collide, so it is omitted here.
ENV PATH=/opt/toolchain/bin:${PATH}

# --- uv (fast Python packaging / venv manager) ---
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://astral.sh/uv/install.sh | env INSTALLER_NO_MODIFY_PATH=1 sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# --- Trivy (vulnerability + IaC misconfig scanner) ---
# get.trivy.dev short URL returns HTTP 400 as of 2026 — use the canonical install
# script hosted in aquasecurity/trivy directly. Same -b flag; different source.
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 \
      https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
      | sh -s -- -b /usr/local/bin

# --- cosign (image signing) + syft (SBOM) ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-${ARCH}" \
      -o /usr/local/bin/cosign && chmod +x /usr/local/bin/cosign && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://raw.githubusercontent.com/anchore/syft/main/install.sh | \
      sh -s -- -b /usr/local/bin

# --- k6 (load testing) ---
# Pin to a specific version — GitHub's `latest/download/` redirects to whatever
# the current release is, but the tarball filename contains the version, so an
# unpinned URL 404s the moment k6 ships a new release.
RUN K6_VERSION=v1.3.0 && ARCH="$(dpkg --print-architecture)" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 \
      "https://github.com/grafana/k6/releases/download/${K6_VERSION}/k6-${K6_VERSION}-linux-${ARCH}.tar.gz" \
      | tar -xz --strip-components=1 -C /usr/local/bin "k6-${K6_VERSION}-linux-${ARCH}/k6"

# --- GitHub CLI ---
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
      https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y --no-install-recommends gh && \
    rm -rf /var/lib/apt/lists/*

# --- ArgoCD CLI ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-${ARCH}" \
      -o /usr/local/bin/argocd && chmod +x /usr/local/bin/argocd

# --- age + sops (SOPS-encrypted config decryption) ---
RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" && \
    SOPS_VERSION=v3.9.1 && \
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --retry-all-errors --retry-max-time 300 --max-time 180 "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.${ARCH}" \
      -o /usr/local/bin/sops && chmod +x /usr/local/bin/sops && \
    apt-get update && apt-get install -y --no-install-recommends age && \
    rm -rf /var/lib/apt/lists/*

# --- Non-root user for actually running commands ---
# UID/GID 1000 is the Ubuntu default for the first regular user and usually matches
# the host user on Linux; on macOS with Docker Desktop the mapping is handled by the VM.
# Ubuntu 24.04+ base images ship a default `ubuntu` user at UID 1000, so we remove
# it first to reclaim the ID for our own `dev` user.
RUN (userdel -r ubuntu 2>/dev/null || true) && \
    groupadd -g 1000 dev && \
    useradd -u 1000 -g 1000 -m -s /bin/bash dev && \
    # dev is in sudo group but has NOPASSWD for in-container escalation only
    usermod -aG sudo dev && \
    echo 'dev ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/dev && chmod 440 /etc/sudoers.d/dev && \
    # dev is in docker group so it can talk to the mounted docker socket.
    # Check by name (not GID) — Ubuntu 24.04 uses GID 999 for another system group,
    # and on macOS Docker Desktop the socket goes through the VM so exact GID match
    # doesn't matter. If `docker` group doesn't exist by name, create it with any
    # free GID; either way, add `dev` to it.
    (getent group docker >/dev/null || groupadd docker) && \
    usermod -aG docker dev

USER dev
WORKDIR /workspace

# Print a small banner on interactive shells so it's obvious you're in the sandbox
RUN echo 'echo "🧰 devops-sandbox — see /workspace/.claude/sandbox/README.md for usage"' \
      >> /home/dev/.bashrc

# Quick sanity command so `docker run devops-sandbox:latest` (no args) shows what's inside
CMD ["bash", "-c", "\
echo '=== devops-sandbox toolchain ===' && \
echo 'OS: '$(lsb_release -ds) && \
echo 'python: '$(python3 --version) && \
echo 'node: '$(node --version) && \
echo 'go: '$(go version | cut -d' ' -f3) && \
echo 'java: '$(java -version 2>&1 | head -1) && \
echo 'docker: '$(docker --version | head -1) && \
echo 'kubectl: '$(kubectl version --client=true 2>/dev/null | head -1) && \
echo 'helm: '$(helm version --short) && \
echo 'kind: '$(kind version) && \
echo 'terraform: '$(terraform version | head -1) && \
echo 'ansible: '$(ansible --version | head -1) && \
echo 'trivy: '$(trivy --version | head -1) && \
echo 'gh: '$(gh --version | head -1) && \
echo 'argocd: '$(argocd version --client --short 2>&1 | head -1) && \
echo '' && \
echo 'For an interactive shell: docker run --rm -it devops-sandbox:latest bash' \
"]
