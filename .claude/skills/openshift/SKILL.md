---
name: openshift
description: Red Hat OpenShift-specific concerns — SecurityContextConstraints, Routes, BuildConfigs, and the oc CLI. Use alongside the kubernetes skill when the target platform is OpenShift; its defaults are stricter and its idioms differ from raw Kubernetes.
---

# OpenShift

OpenShift is Kubernetes with stricter defaults and its own idioms — treat manifests written for vanilla
Kubernetes as a starting point, not something that will work unmodified.

## SecurityContextConstraints (SCC)

- OpenShift's default `restricted` SCC forbids running as root, forbids arbitrary UID, and restricts
  capabilities — a container image that assumes root (common in naive Dockerfiles) will fail to start,
  not silently run as root. Fix the image (non-root user, arbitrary-UID-compatible file permissions —
  group `0` with group-writable permissions is the common pattern) rather than requesting a broader SCC.
- Only request a more permissive SCC (`anyuid`, `privileged`) when there's a genuine technical need
  (e.g. a workload that must bind a privileged port or access host devices) — this is a security posture
  decision, confirm with the user rather than granting it to unblock a deploy.

## Routes vs. Ingress

- OpenShift's native `Route` object predates and largely substitutes for `Ingress` — supports edge/
  passthrough/re-encrypt TLS termination natively. Standard `Ingress` resources also work (OpenShift runs
  an Ingress controller), but `Route` is the more idiomatic and feature-complete choice on this platform.

## BuildConfigs (Source-to-Image)

- OpenShift can build container images in-cluster from source via `BuildConfig` + Source-to-Image (S2I),
  as an alternative to a separate CI pipeline building and pushing an image. Whether a given project uses
  S2I or an external CI/CD pipeline (Section 7 of `CLAUDE.md`) should already be evident from the repo —
  don't introduce S2I into a project that already has an external pipeline without a reason.

## Key Commands

```bash
oc login <api-url>
oc get scc                                  # list available SecurityContextConstraints
oc adm policy who-can use scc <scc-name>
oc get route -n <project>
oc describe buildconfig <name> -n <project>
oc new-app <image-or-source>                # quick app creation, mainly for dev/demo use
oc adm top pod -n <project>
```

Note: `oc` is a superset of `kubectl` — plain `kubectl` commands work against OpenShift too, but `oc`
exposes the OpenShift-specific resources (Route, BuildConfig, SCC, Project) that `kubectl` doesn't know
about natively.

## Common Pitfalls

- Deploying an image built for a generic Kubernetes cluster (assumes root, fixed UID) straight to
  OpenShift and getting an opaque SCC denial instead of a clear "runs as root" error — check `oc get
  events` and the pod's SCC annotation for the real cause.
- Using `Ingress` and `Route` for the same hostname simultaneously, causing conflicting routing behavior.
- Treating `Project` (OpenShift's wrapper around `Namespace` with extra RBAC/quota defaults) as identical
  to a plain namespace when reasoning about default permissions.
