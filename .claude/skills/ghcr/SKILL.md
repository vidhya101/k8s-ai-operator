---
name: ghcr
description: GitHub Container Registry (GHCR) — authentication from CI, image visibility/retention, and linking images to a repository. Use when publishing/pulling container images via GHCR specifically.
---

# GHCR (GitHub Container Registry)

Container registry tied to a GitHub org/user namespace — the natural default when CI is already GitHub
Actions (see `github-actions` skill), since authentication is built in via `GITHUB_TOKEN`.

## Authentication

```bash
# From GitHub Actions — GITHUB_TOKEN is sufficient for push to a repo-linked package by default
echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# Local/manual — use a Personal Access Token with `write:packages`/`read:packages` scope, not a password
echo "$GHCR_PAT" | docker login ghcr.io -u <username> --password-stdin
```

- Prefer `GITHUB_TOKEN` (scoped automatically to the triggering workflow run, short-lived) over a
  long-lived PAT wherever the push happens from GitHub Actions itself.

## Image Naming & Visibility

```text
ghcr.io/<org-or-user>/<image-name>:<tag>
```

- New packages inherit the linked repository's visibility settings by default but can be configured
  independently — confirm whether an image should be public or private explicitly rather than assuming.
- Linking a package to its source repository (via the package settings, or automatically when pushed from
  that repo's Actions workflow) surfaces provenance and enables repo-based access control.

## Tagging & Retention

- Tag with an immutable identifier (git SHA, or SHA + semver) for anything deployed — never deploy from
  a floating `latest`/branch-name tag (same principle as `CLAUDE.md` Section 8).
- GHCR has no built-in automatic retention/cleanup by default — untagged/old images accumulate
  indefinitely unless a cleanup workflow (e.g. `actions/delete-package-versions`) is scheduled.

## Common Pitfalls

- A long-lived PAT with broad scope used for CI push instead of the workflow-scoped `GITHUB_TOKEN`.
- Package visibility left at a default that doesn't match intent (a public package for an internal-only
  image, or vice versa).
- No retention policy, letting the package accumulate every CI build's image indefinitely and inflating
  storage/costs and making the tag list unusable for humans.
- Pulling from GHCR in a cluster without an `imagePullSecret` configured for a private package, causing
  `ImagePullBackOff` that looks like a networking issue but is an auth issue.
