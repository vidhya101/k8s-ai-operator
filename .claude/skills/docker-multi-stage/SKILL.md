---
name: docker-multi-stage
description: Design multi-stage Dockerfiles that separate build tooling from a minimal runtime image. Use when writing a new Dockerfile, or when an existing image is unnecessarily large or carries compilers/build tools into production.
---

# Docker Multi-Stage Builds

The standard pattern for shipping a minimal, secure runtime image while still using a full toolchain
to build it.

## Pattern

```dockerfile
# ---- Stage 1: builder ----
FROM <language-toolchain>:<pinned-version> AS builder
WORKDIR /src
COPY <dependency-manifest> .
RUN <install deps>
COPY . .
RUN <build/compile command>

# ---- Stage 2: runtime ----
FROM <minimal-base>:<pinned-version> AS runtime
RUN addgroup -S app && adduser -S app -G app       # if base lacks a non-root user
WORKDIR /app
COPY --from=builder /src/<built-artifact> .
USER app
EXPOSE <only the ports actually served>
HEALTHCHECK CMD <lightweight health check>
ENTRYPOINT ["<run the artifact>"]
```

## Base Image Choice for the Runtime Stage

- Compiled binaries (Go, Rust, static binaries): `scratch` or `distroless/static` — no shell, no package
  manager, smallest possible attack surface.
- Interpreted/JIT runtimes needing some OS libs (Python, Node, JVM): the distroless variant for that
  language, or `-slim`/`-alpine` if distroless isn't practical for the app's needs.
- Never carry the SDK/full toolchain image into the runtime stage — that's the signal a build isn't
  actually multi-stage yet, even if it has multiple `FROM` lines.

## Verification (do this every time, not just once)

```bash
docker build -t app:test .
docker images app:test                 # check size is in line with expectations
docker run --rm app:test <smoke-test-command-or-health-endpoint>
docker run --rm app:test id            # confirm non-root
docker history --no-trunc app:test     # confirm no secret baked in, no unexpected layer bloat
```

Rebuild and re-verify after every Dockerfile change — a multi-stage build that "should" be minimal can
still accidentally `COPY . .` more than intended into the final stage.

## Common Pitfalls

- `COPY --from=builder . .` (copying everything) instead of copying only the specific built artifact —
  drags build-context cruft into the runtime image.
- Named build args/stages that look multi-stage but the final `FROM` is still the full builder image
  because a later stage was appended without changing which stage is last (Docker uses the *last* `FROM`
  as the default build target unless `--target` is specified).
- Dependency install (`RUN <install>`) placed after `COPY . .` instead of before — invalidates the layer
  cache on every source change, making builds slower than necessary (not a correctness bug, but worth
  fixing when reviewing).
