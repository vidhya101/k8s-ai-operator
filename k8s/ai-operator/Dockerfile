# Multi-stage: build wheels, then a slim runtime with kubectl + helm + kustomize + istioctl.
FROM python:3.12-slim AS build
WORKDIR /w
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

ARG KUBECTL_VERSION=v1.31.1
ARG HELM_VERSION=v3.16.1
ARG KUSTOMIZE_VERSION=v5.5.0
ARG ISTIO_VERSION=1.23.2
ARG TARGETARCH=amd64

RUN set -eux; \
    apt-get update; apt-get install -y --no-install-recommends curl ca-certificates git tar; \
    curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl"; \
    chmod +x /usr/local/bin/kubectl; \
    curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz" | tar xz -C /tmp; \
    mv "/tmp/linux-${TARGETARCH}/helm" /usr/local/bin/helm; \
    curl -fsSL "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_${TARGETARCH}.tar.gz" | tar xz -C /usr/local/bin; \
    curl -fsSL "https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/istio-${ISTIO_VERSION}-linux-${TARGETARCH}.tar.gz" | tar xz -C /tmp; \
    mv "/tmp/istio-${ISTIO_VERSION}/bin/istioctl" /usr/local/bin/istioctl; \
    apt-get purge -y curl tar; apt-get autoremove -y; rm -rf /var/lib/apt/lists/* /tmp/*

COPY --from=build /install /usr/local
COPY src/ /app/src/
COPY config/ /app/config/

# non-root; the manifest also sets runAsUser 65532 + readOnlyRootFilesystem
RUN useradd -u 65532 -m nonroot && mkdir -p /workspace /memory && chown -R 65532 /workspace /memory /app
USER 65532
ENV HOME=/tmp PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
EXPOSE 8080
ENTRYPOINT ["kopf", "run", "--standalone", "--liveness=http://0.0.0.0:8080/healthz", "/app/src/operator.py"]
