---
name: aws-serverless
description: AWS serverless and messaging — Lambda, SNS, SQS, API Gateway, and EventBridge. Use when designing or reviewing event-driven AWS architecture, distinct from container-based (EKS/ECS) workloads.
---

# AWS Serverless & Messaging

Event-driven building blocks — Lambda for compute, SQS/SNS/EventBridge for messaging, API Gateway for
HTTP entry points. See `aws` for IAM/VPC/networking fundamentals that still apply here.

## Lambda

- Cold starts matter for latency-sensitive paths — provisioned concurrency trades cost for eliminating
  them; for infrequent/async triggers (queue processing, scheduled jobs) cold start is usually a
  non-issue and not worth paying for provisioned concurrency.
- Timeout and memory are linked (memory allocation also scales CPU) — a Lambda timing out isn't always
  "needs more time," it's often "needs more memory/CPU," check both before just raising the timeout.
- Idempotency matters: Lambda can invoke a function more than once for a single event (at-least-once
  delivery from most triggers) — same discipline as the `data-engineering-reviewer`/`airflow` idempotency
  principle, applied to serverless.
- IAM execution role scoped to exactly what the function needs — the most common Lambda security gap is
  an execution role with far broader permissions than the function's actual logic uses.

## SQS (queues) vs. SNS (pub/sub) vs. EventBridge (event bus/routing)

- **SQS**: point-to-point queue, one message consumed by one consumer (or one per consumer group with
  fan-out via multiple queues) — use for decoupling a producer from a consumer that processes at its own
  pace; a Dead Letter Queue (DLQ) is essential for anything production — without one, a poison message
  (one that always fails processing) retries indefinitely or is silently dropped depending on config.
- **SNS**: pub/sub fan-out — one message delivered to every subscriber (Lambda, SQS queues, HTTP
  endpoints, email) — use when multiple independent consumers need the same event.
- **EventBridge**: rule-based event routing with content filtering — the right choice when routing logic
  itself is complex (route by event pattern/attribute to different targets) rather than simple fan-out;
  also the standard integration point for reacting to AWS resource state changes (see `aws` skill's
  EventBridge + Lambda automation section).
- A common production pattern: SNS fans out to multiple SQS queues (each consumer gets its own durable
  queue) rather than subscribing Lambda directly to SNS — durable buffering survives a consumer outage
  that a direct SNS→Lambda subscription wouldn't.

## API Gateway

- REST API vs. HTTP API: HTTP API is cheaper/faster/simpler for most use cases; REST API has more
  features (request validation, usage plans/API keys, WAF integration) — check which is actually needed
  before defaulting to the more expensive/complex REST API type.
- Throttling/usage plans at the gateway protect backend Lambdas from being overwhelmed — don't rely on
  Lambda's own concurrency limits alone as the only protection against a traffic spike or abuse.
- Authorization: IAM auth, Cognito authorizers, or a custom Lambda authorizer — pick based on who's
  calling (internal service-to-service vs. end-user-facing) rather than defaulting to one pattern everywhere.

## Common Pitfalls

- No DLQ on an SQS queue or Lambda event source mapping — a consistently failing message either blocks
  the queue (retried forever) or is silently lost, with no visibility into either happening.
- Lambda execution role using a broad managed policy (e.g. full S3 access) instead of scoped to the
  specific bucket/prefix the function actually touches.
- SNS/SQS message size/throughput assumptions not matching actual payload sizes — large payloads need to
  go through S3 with a reference in the message (the "claim check" pattern), not inline.
- EventBridge rule pattern too broad, triggering the target for events it wasn't meant to react to, or
  too narrow, silently missing events that should have matched.
