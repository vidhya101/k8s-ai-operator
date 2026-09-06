---
name: docker
description: Build, run, and troubleshoot Docker containers and images — Dockerfile fundamentals, docker-compose, networking, and volumes. Use for general container build/run questions; use docker-multi-stage and docker-security for those specific concerns.
---

# Docker

General container build/run/debug reference. See `docker-multi-stage` for build-stage design and
`docker-security` for the hardening checklist.

## Core Principles

- One primary process per container; sidecar/init processes only when the pattern genuinely calls for it.
- Explicit tags/digests everywhere (base images, `docker-compose` service images) — never bare `latest`
  in anything meant to be reproducible.
- `.dockerignore` excludes `.git`, secrets, local env files, and anything not needed in the build context.
- Configuration via environment variables / mounted config, not baked into the image — the same image
  should run in dev/stage/prod with different config, not be rebuilt per environment.

## Key Commands

```bash
docker build -t <name>:<tag> .
docker run --rm -p <host>:<container> <name>:<tag>
docker ps -a                       # including stopped containers
docker logs -f <container>
docker exec -it <container> sh     # or bash if present
docker inspect <container>         # full config, mounts, network, env
docker history --no-trunc <image>  # every layer, useful for spotting baked-in secrets/bloat
docker network ls / inspect        # container networking topology
docker compose up -d / down / logs -f
```

## Networking & Volumes

- Default bridge network is fine for a single container; use a user-defined network (or compose's default
  project network) for multi-container communication by service name.
- Named volumes for anything that must survive container recreation (databases, uploaded files); bind
  mounts mainly for local development, not production state.
- Only publish (`-p`) the ports that need to be reachable from outside the container/network — everything
  else should stay on the internal network, reachable only by service name to other containers.

## Common Pitfalls

- `docker-compose.yml` committing real credentials in `environment:` instead of an `.env` file that's
  gitignored, or a secret manager.
- Bind-mounting the entire project directory into a production container, exposing source/config beyond
  what's needed at runtime.
- Forgetting `--rm` on ad hoc debug containers, leaving a pile of stopped containers accumulating.
- Relying on container restart policy alone for reliability instead of also fixing why it's crashing.
