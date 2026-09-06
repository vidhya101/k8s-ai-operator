---
name: contract-testing
description: Consumer-driven contract testing with Pact — verifying service integrations without full end-to-end environments. Use when designing tests across service boundaries in a microservices architecture, as a middle ground between mocked unit tests and expensive e2e tests.
---

# Contract Testing (Pact)

Solves a specific gap in the `testing` skill's pyramid: unit tests with mocks verify a consumer's logic in
isolation but can't catch a real API mismatch with the provider; full e2e tests catch mismatches but are
slow, flaky, and need every service actually running. Contract testing verifies the *interface* between
services without either service needing the other running.

## Core Model

- **Consumer** writes a test against a mock of the provider, and that test run generates a **contract**
  (a Pact file: the exact requests the consumer makes and the responses it expects).
- **Provider** replays the contract's requests against its real implementation and verifies its actual
  responses match what the contract expects — run independently of the consumer, often in the provider's
  own CI pipeline.
- **Pact Broker** (or Pact Flow) is the shared registry where contracts are published and verification
  results are recorded — this is what makes "can we safely deploy" a queryable fact across teams instead
  of manual coordination.

```javascript
// Consumer side — generates the contract
const provider = new PactV3({ consumer: "OrderService", provider: "PaymentService" });
provider
  .given("a valid payment method exists")
  .uponReceiving("a request to charge a payment")
  .withRequest({ method: "POST", path: "/charge", body: { amount: 100 } })
  .willRespondWith({ status: 200, body: { status: "charged" } });
```

## "Can I Deploy" (the real payoff)

- Pact's `can-i-deploy` tooling checks, against the broker, whether the specific versions of consumer and
  provider about to be deployed have a **verified** contract between them — turns "will this deployment
  break the other team's service" into an automated CI gate instead of a Slack message and hope.

```bash
pact-broker can-i-deploy --pacticipant OrderService --version <sha> --to-environment production
```

## When This Fits (and when it doesn't)

- Fits naturally in a microservices architecture with multiple teams owning different services that call
  each other — the coordination cost of "did the provider team just break us" scales with team count, and
  contract testing directly addresses that.
- Doesn't replace integration/e2e tests for testing actual business logic correctness across a real
  multi-service flow — it verifies the *interface* is honored, not that the overall system behavior is
  correct end to end; both still have a place in the `testing` skill's pyramid.
- Introducing it for a single-team, single-service system is unnecessary overhead (Section 1.2) — the
  value is specifically in the cross-team/cross-service coordination problem.

## Common Pitfalls

- Contracts written to over-specify exact response bodies (every field, exact values) instead of the
  actual shape/types the consumer depends on — makes the contract brittle to any provider change, even
  ones that wouldn't actually break the consumer.
- Provider verification not run in the provider's own CI — a contract published but never actually
  verified against the real provider gives false confidence.
- `can-i-deploy` not wired into the actual deploy pipeline as a gate — the check exists but doesn't
  block anything, the same "gate that doesn't actually gate" issue flagged elsewhere in this stack's
  scanning tools.
