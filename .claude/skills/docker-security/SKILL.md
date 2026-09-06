---
name: docker-security
description: Harden Docker images and containers — non-root users, capability dropping, secret handling, and vulnerability scanning with Trivy. Use when security-reviewing a Dockerfile/image or hardening a container before production deployment.
---

# Docker Security

Security hardening checklist for container images and runtime configuration.

## Build-Time Hardening

- Non-root `USER` set explicitly; if the base image has no non-root user, create one
  (`RUN addgroup -S app && adduser -S app -G app` or distro equivalent) and `USER app` before `CMD`.
- Base image pinned to a digest or specific minimal version (distroless, `-slim`, `-alpine`), not `latest`.
- No secret baked into any layer — check with `docker history --no-trunc <image>`; use
  `--mount=type=secret` for build-time secrets, never `ARG`/`ENV` for credentials (ARG values persist in
  image history even if unset later).
- Multi-stage build so the runtime image has no compiler/package manager/build tool attack surface
  (see `docker-multi-stage`).
- Minimize installed packages in the final stage; remove package manager caches in the same layer they're
  created.

## Runtime Hardening

```bash
docker run --read-only --tmpfs /tmp \
  --cap-drop=ALL --cap-add=<only what's needed> \
  --security-opt no-new-privileges \
  --user <uid>:<gid> \
  <image>
```

- Drop all Linux capabilities by default, add back only the specific ones required (e.g.
  `NET_BIND_SERVICE` for binding to a low port as non-root) — never run `--privileged` in production.
- Read-only root filesystem where the app allows it; use `tmpfs` mounts for any directory that genuinely
  needs to be writable at runtime (logs, cache).
- Resource limits (`--memory`, `--cpus`) set, matching what the orchestrator's requests/limits will be in
  production, so local testing reflects real constraints.

## Scanning

```bash
trivy image <name>:<tag>              # CVEs in OS packages + application dependencies
trivy image --severity HIGH,CRITICAL <name>:<tag>
trivy config .                         # Dockerfile/compose misconfiguration scan
```

Fail the build on HIGH/CRITICAL findings with an available fix by default; confirm the exact threshold
with the user rather than assuming — see `.claude/rules/safety.md`, this is a policy decision.

## Common Pitfalls

- `USER` set in the Dockerfile but the entrypoint script does something requiring root before `exec`ing
  into the app, silently running as root anyway — verify with `docker exec <container> whoami/id` on the
  actual running container, not just by reading the Dockerfile.
- A debug/admin port (pprof, JMX, an unauthenticated metrics endpoint) exposed in the image that only
  should be reachable inside the cluster network, not published externally.
- Trivy scan run once at image-build time but never re-run against images already sitting in the registry
  as new CVEs are published against their pinned dependencies.
