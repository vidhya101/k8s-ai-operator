---
name: rabbitmq
description: RabbitMQ — AMQP-based message broker with exchanges, queues, and routing, plus dead-letter handling. Use for message-broker design/troubleshooting when the system is RabbitMQ (or another AMQP broker) rather than Kafka's log-based model.
---

# RabbitMQ

A traditional message broker (AMQP protocol) — fundamentally different delivery model from `kafka`: once
a message is consumed and acknowledged, it's gone from the queue (no replay from an offset), and routing
happens via flexible exchange/binding rules rather than partition-based topics. Pick based on need: Kafka
for high-throughput event streams with replay/retention; RabbitMQ for flexible routing and traditional
task-queue semantics. NATS/Pulsar are lighter-weight alternatives in the same broker category, worth a
look when RabbitMQ's clustering complexity isn't needed but a broker (not just a raw queue) still is.

## Core Model

- **Exchange**: receives published messages and routes them to queue(s) based on type — `direct` (exact
  routing key match), `topic` (pattern-matched routing key, e.g. `orders.*.created`), `fanout` (broadcast
  to every bound queue), `headers` (route by message header values instead of routing key).
- **Queue**: where routed messages actually sit until consumed — bound to one or more exchanges via a
  **binding** (with an optional routing key pattern for topic/direct exchanges).
- **Acknowledgment**: a consumer explicitly acks a message after successful processing; an unacked
  message (consumer crash, connection drop) is redelivered — same idempotency requirement as any
  at-least-once system (`kafka`, `airflow`, `aws-serverless`'s SQS section all share this discipline).

## Dead Letter Queues (DLQ)

```yaml
# Queue argument, not a separate resource:
x-dead-letter-exchange: dlx
x-dead-letter-routing-key: failed
```

- A message that's rejected/nacked without requeue, or exceeds its TTL, or exceeds a queue's max length,
  routes to the configured dead-letter exchange instead of being silently dropped — essential for
  production; a queue with no DLQ configured either loops a poison message forever (if requeued on
  failure) or loses it silently (if not) — the identical concern `aws-serverless` raises for SQS.

## Clustering & Quorum Queues

- **Quorum queues** (the modern recommended replicated queue type, replacing classic mirrored queues) use
  a Raft-based consensus protocol for replication — provides real durability guarantees across broker node
  failures; classic non-mirrored queues live on a single node and are lost if that node fails.
- Cluster-wide policies (`ha-mode`, or quorum queue replication factor) should be set deliberately per
  queue's actual durability requirement — not every queue needs the overhead of full replication.

## Common Pitfalls

- No DLQ configured, so a message that a consumer can never successfully process either loops
  indefinitely or vanishes with no trace.
- Classic (non-quorum, non-mirrored) queues used for anything where losing the queue's contents on a
  single node failure is unacceptable — quorum queues are the durable choice for production use.
- Consumers not idempotent, relying on "acks are usually reliable" instead of correctly handling the
  at-least-once redelivery that a crash/network blip causes.
- Unbounded queue growth with no `x-max-length`/TTL policy, because nothing is consuming fast enough —
  same "no consumer lag monitoring" blind spot `kafka` warns about, manifesting as memory/disk pressure
  on the broker instead of a lag metric.
