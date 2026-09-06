# syntax=docker/dockerfile:1.7
# Static Go binary on `scratch` — smallest possible attack surface: no shell, no libc, no package
# manager, nothing but the binary and CA certs for outbound TLS.

ARG GO_VERSION=1.22

# ---------- builder ----------
FROM golang:${GO_VERSION}-alpine AS builder
WORKDIR /build
RUN apk add --no-cache ca-certificates
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /app ./...

# ---------- runtime ----------
FROM scratch AS runtime
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app /app

ENV PORT=8080
EXPOSE 8080
USER 10001:10001

# scratch has no shell — liveness/readiness handled entirely by Kubernetes probes
# (k8s/app/base/deployment.yaml) hitting the binary's own HTTP health endpoint.

ENTRYPOINT ["/app"]
