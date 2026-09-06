# syntax=docker/dockerfile:1.7
# Static SPA build (React/Vite/CRA) served by nginx running as an unprivileged user on an
# unprivileged port — no root anywhere in the runtime stage.

ARG NODE_VERSION=20

# ---------- build ----------
FROM node:${NODE_VERSION}-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build \
    # Normalize CRA's ./build output to ./dist so the runtime stage has one path to copy.
    && ( [ -d build ] && [ ! -d dist ] && mv build dist || true )

# ---------- runtime ----------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY docker/templates/nginx.react.conf /etc/nginx/conf.d/default.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

EXPOSE 8080
USER 101

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O - http://127.0.0.1:8080/healthz || exit 1

ENTRYPOINT ["nginx", "-g", "daemon off;"]
