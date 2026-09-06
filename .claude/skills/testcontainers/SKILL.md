---
name: testcontainers
description: Testcontainers — spinning up real, ephemeral dependencies (databases, queues, Kafka) in Docker for integration tests, instead of mocks or shared test infrastructure. Use when writing integration tests that need a real dependency, per the testing skill's integration-test tier.
---

# Testcontainers

Runs real dependencies (Postgres, Redis, Kafka, LocalStack for AWS services, or any Docker image) in
disposable containers, scoped to a test run — the concrete mechanism for the `testing` skill's
integration-test tier ("does the code correctly talk to a real database"), without needing a shared,
stateful test database that different test runs can interfere with.

## Core Pattern

```java
@Testcontainers
class OrderRepositoryTest {
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Test
    void savesOrder() {
        var repo = new OrderRepository(postgres.getJdbcUrl());
        repo.save(new Order(...));
        assertThat(repo.findAll()).hasSize(1);
    }
}
```

```python
# Python equivalent
from testcontainers.postgres import PostgresContainer

with PostgresContainer("postgres:16") as postgres:
    conn = psycopg2.connect(postgres.get_connection_url())
    # run real queries against a real, throwaway Postgres instance
```

- Each test class/run gets a **fresh container**, started before tests and torn down after — eliminates
  the classic shared-test-database problems (test pollution, order-dependent test failures, "works on my
  machine because my local DB has different data than CI's").
- Works for any Docker image, not just databases — Kafka, Redis, LocalStack (AWS service emulation),
  even a full custom application image for a broader integration test.

## Where This Fits

```text
Unit tests           — mocked dependencies, fastest, most numerous
Testcontainers tests   — real dependency in a disposable container, verifies actual integration
                         behavior (a real SQL dialect quirk, a real Kafka consumer group rebalance)
                         that a mock can't catch
E2E tests               — the full real system, fewest, most expensive
```

Testcontainers-based tests are slower than mocked unit tests (container startup cost) but much cheaper
and more reliable than standing up full e2e environments — the practical middle tier the `testing` skill's
pyramid describes.

## Common Pitfalls

- Container reuse/caching not configured for a large test suite, paying full container-startup cost per
  test class instead of sharing one container across a test run where isolation permits it — a real CI
  time cost at scale.
- Using Testcontainers for what's actually simple logic a mock/unit test would verify just as well and
  much faster — reach for it specifically for integration-boundary behavior, not as a default for
  everything (Section 1.2).
- CI environment without Docker-in-Docker or an accessible Docker daemon — Testcontainers needs a real
  Docker socket available; a CI runner without one will fail these tests with an unhelpful connection
  error rather than an obvious "Docker isn't available here."
- Tests that don't properly clean up/isolate state *within* a shared container (when reuse is enabled)
  reintroducing the same test-pollution problem disposable containers were meant to eliminate.
