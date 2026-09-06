#!/usr/bin/env bash
# Prints one word: kind | minikube | k3s | kubeadm | eks | aks | gke | openshift | docker-desktop | unknown
set -Eeuo pipefail

ctx="$(kubectl config current-context 2>/dev/null || echo '')"
nodes_json="$(kubectl get nodes -o json 2>/dev/null || echo '{}')"
labels="$(printf '%s' "$nodes_json" | grep -o '"[a-z0-9./-]*":' | tr -d '":' || true)"

case "$ctx" in
  kind-*)        echo kind; exit 0;;
  minikube)      echo minikube; exit 0;;
  docker-desktop) echo docker-desktop; exit 0;;
esac
printf '%s\n' "$labels" | grep -q 'eks.amazonaws.com'         && { echo eks; exit 0; }
printf '%s\n' "$labels" | grep -q 'cloud.google.com/gke'      && { echo gke; exit 0; }
printf '%s\n' "$labels" | grep -q 'kubernetes.azure.com'      && { echo aks; exit 0; }
printf '%s\n' "$labels" | grep -q 'node.openshift.io'         && { echo openshift; exit 0; }
printf '%s\n' "$nodes_json" | grep -q 'k3s'                    && { echo k3s; exit 0; }
kubectl get nodes -o wide 2>/dev/null | grep -qi 'control-plane' && { echo kubeadm; exit 0; }
echo unknown
