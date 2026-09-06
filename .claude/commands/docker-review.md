---
description: Review a Dockerfile/image for multi-stage correctness, size, and security.
argument-hint: "[path to Dockerfile, defaults to ./Dockerfile]"
---

Review the container build at: $ARGUMENTS (default: `./Dockerfile` and any `docker-compose*.yml`).

Delegate to the `docker-reviewer` agent using the `docker`, `docker-security`, and `docker-multi-stage`
skills. Check specifically:

- Is the build genuinely multi-stage (builder vs. minimal runtime), or does the runtime image carry
  compilers/build tools it doesn't need?
- Base image pinned (digest or specific version), not `latest`?
- Runs as non-root `USER`?
- `.dockerignore` present and excludes secrets/`.git`/local env files?
- Any secret baked into a layer (check `docker history --no-trunc` if the image can be built)?
- Every exposed port justified — list each one, its purpose, and whether it should be public,
  cluster-internal, or loopback-only (see `CLAUDE.md` Section 4.2 port/network checklist).
- If `trivy image` is available, run it against the built image and fold findings into the report.

Build the image if it isn't already built, and confirm it actually starts and passes its health check
before concluding the review.
