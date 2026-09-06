# syntax=docker/dockerfile:1.7
# Same posture as docker/templates/go.Dockerfile (static binary on scratch) — the operator is
# just another Go workload from a supply-chain-security point of view, built and pushed through
# the exact same reusable-ci-cd.yml pipeline as any application it manages.

ARG GO_VERSION=1.22

FROM golang:${GO_VERSION}-alpine AS builder
WORKDIR /build
RUN apk add --no-cache ca-certificates
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /manager .

FROM scratch AS runtime
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /manager /manager

USER 65532:65532
ENTRYPOINT ["/manager"]
