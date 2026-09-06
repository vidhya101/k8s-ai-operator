#!/usr/bin/env bash
# Prints one word: kind | minikube | k3s | rke2 | kubeadm | eks | aks | gke | openshift |
#                  docker-desktop | unknown
# Uses a SINGLE `kubectl get nodes -o json` call (the cluster may be slow/remote — a second call
# that times out must not flip the answer to 'unknown').
set -Eeuo pipefail

ctx="$(kubectl config current-context 2>/dev/null || echo '')"
case "$ctx" in
  kind-*)         echo kind; exit 0;;
  minikube)       echo minikube; exit 0;;
  docker-desktop) echo docker-desktop; exit 0;;
esac

j="$(kubectl get nodes -o json 2>/dev/null || echo '{}')"
h() { printf '%s' "$j" | grep -q "$1"; }

h 'eks.amazonaws.com'                && { echo eks; exit 0; }
h 'cloud.google.com/gke'             && { echo gke; exit 0; }
h 'kubernetes.azure.com'             && { echo aks; exit 0; }
h 'node.openshift.io'                && { echo openshift; exit 0; }
h '"rke2"' || h 'rke2.io'            && { echo rke2; exit 0; }
h '"k3s"' || h 'k3s.io'              && { echo k3s; exit 0; }
# kubeadm's fingerprint: the cri-socket annotation it stamps on every node.
h 'kubeadm.alpha.kubernetes.io'      && { echo kubeadm; exit 0; }
# fallback: any node carrying the control-plane/master role but none of the above => self-managed
h 'node-role.kubernetes.io/control-plane' || h 'node-role.kubernetes.io/master' \
                                    && { echo kubeadm; exit 0; }
echo unknown
