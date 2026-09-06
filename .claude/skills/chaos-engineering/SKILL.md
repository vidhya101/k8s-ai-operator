---
name: chaos-engineering
description: Chaos engineering practice and tooling (Chaos Mesh, Litmus) — designing and running controlled failure injection experiments to validate resilience claims. Use when planning, reviewing, or running a chaos experiment, or when a resilience claim (self-healing, multi-AZ) needs actual verification rather than assumption.
---

# Chaos Engineering

Proactively injecting controlled failures to verify a system actually behaves the way its design assumes
— the concrete verification step behind claims made in `CLAUDE.md`'s "self-healing"/"multi-AZ" resilience
section and the `architecture-review` skill's "verify the failure scenario" step.

## Core Principles

- **Start with a hypothesis**: "if we kill this pod, traffic should fail over within N seconds with no
  user-visible error" — a chaos experiment without a stated expected outcome isn't testing anything, it's
  just breaking things.
- **Minimize blast radius**: start in a non-production or a tightly-scoped production experiment (a
  single pod, a small traffic percentage) before anything broader — chaos engineering's goal is learning
  safely, not causing an actual incident.
- **Have a stop condition and rollback**: an automated abort if the experiment causes worse impact than
  expected (error rate crossing a hard ceiling) — never run an experiment with no way to stop it quickly.
- **Measure against the actual SLO**: did the system stay within its error budget during the experiment?
  A vague "seemed fine" isn't a result; compare against the same metrics the `sre` skill's SLIs track.

## Common Experiment Types

```text
Pod/container failure       — kill a pod, verify the Deployment/StatefulSet replaces it and readiness
                               correctly gates traffic during the gap (see kubernetes skill's probes)
Node failure                — cordon/drain a node, verify PodDisruptionBudget-respecting rescheduling
                               and multi-AZ spread actually kept the service up
Network faults               — inject latency/packet loss/partition between services, verify timeout/
                               retry/circuit-breaker behavior (see service-mesh skill if one is in use)
Resource exhaustion          — CPU/memory stress on a pod or node, verify limits/OOMKill/eviction behave
                               as expected rather than cascading
Dependency failure            — simulate a downstream (database, third-party API) becoming unavailable,
                               verify the caller degrades gracefully instead of cascading the failure
AZ/region failure (advanced)  — the most realistic test of multi-AZ/multi-region resilience claims, and
                               the highest blast-radius — plan and schedule with the same rigor as an
                               actual incident drill
```

## Tooling

- **Chaos Mesh**: Kubernetes-native, CRD-based (`PodChaos`, `NetworkChaos`, `StressChaos`, etc.) — define
  an experiment as a Kubernetes resource, works naturally alongside GitOps for versioned, repeatable
  experiments.
- **Litmus**: another Kubernetes-native option, ChaosHub provides a library of pre-built experiment
  templates — similar model to Chaos Mesh, choice between them is mostly ecosystem/preference.

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata: { name: kill-one-api-pod }
spec:
  action: pod-kill
  mode: one
  selector: { namespaces: [my-ns], labelSelectors: { app: my-api } }
  duration: "30s"
```

## Common Pitfalls

- Running an experiment against production with no prior non-production validation of the experiment
  itself — the experiment's own mechanics (does the chaos tool work as configured) should be validated
  somewhere safe first.
- No monitoring/alerting actually watching during the experiment — the whole point is observing real
  system behavior under fault; running one blind defeats the purpose.
- Treating a single successful experiment as permanent proof of resilience — infrastructure and code
  change; a resilience claim validated 6 months ago isn't necessarily still true today. Chaos experiments
  are most valuable run repeatedly (e.g. scheduled game days), not as a one-time checkbox.
- Skipping the "start with a hypothesis" step and running broad, undirected chaos — produces interesting
  incidents but not necessarily actionable learning about a specific resilience claim.
