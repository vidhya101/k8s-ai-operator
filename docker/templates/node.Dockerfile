# syntax=docker/dockerfile:1.7
# Multi-stage Node.js image: install+build with full toolchain, ship only production
# node_modules + build output on a distroless runtime (no shell, no package manager in prod).

ARG NODE_VERSION=20

# ---------- deps ----------
FROM node:${NODE_VERSION}-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

# ---------- build ----------
FROM node:${NODE_VERSION}-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build --if-present

# ---------- runtime (distroless, non-root by default) ----------
FROM gcr.io/distroless/nodejs${NODE_VERSION}-debian12 AS runtime
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json

ENV NODE_ENV=production PORT=8080
EXPOSE 8080
USER nonroot

# distroless has no shell, so HEALTHCHECK/CMD-with-curl isn't possible here — rely on the
# Kubernetes liveness/readiness probes defined in k8s/app/base/deployment.yaml instead.

ENTRYPOINT ["/nodejs/bin/node", "dist/main.js"]
