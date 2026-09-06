---
name: falco
description: Falco — runtime security monitoring for containers/Kubernetes, detecting anomalous syscall-level behavior at runtime. Use for runtime threat detection, distinct from build-time scanning (trivy) which only catches known vulnerabilities, not live anomalous behavior.
---

# Falco (Runtime Security)

Detects anomalous behavior **while a container is running**, at the kernel syscall level (via eBPF) —
the runtime complement to `trivy`'s build-time scanning: Trivy catches known CVEs in what you're about to
ship; Falco catches unexpected behavior in what's already running, including exploitation of vulnerabilities
Trivy never flagged (zero-days, misconfigurations, compromised dependencies calling out unexpectedly).

## Core Model

- Falco rules match patterns of syscall activity (a shell spawned inside a container, a sensitive file
  read, an outbound connection to an unexpected destination) against live kernel events — this is runtime
  detection, not static analysis; it sees what a container actually *does*, not what its image *contains*.

```yaml
- rule: Terminal shell in container
  desc: A shell was spawned inside a container — often a sign of an attacker with a foothold
  condition: >
    spawned_process and container and shell_procs and proc.tty != 0
  output: >
    Shell spawned in container (user=%user.name container=%container.name shell=%proc.name)
  priority: WARNING
```

## What It Catches That Build-Time Scanning Can't

- A supply-chain compromise where a dependency behaves maliciously only at runtime (not detectable by
  scanning its static contents) — the exact class of risk `supply-chain-security`'s SBOM/signing controls
  reduce the *likelihood* of but can't fully eliminate; Falco is the runtime backstop.
- Privilege escalation attempts, unexpected network connections from a workload that should never make
  outbound calls, a container writing to a path it has no legitimate reason to touch.
- Exploitation of a vulnerability that existed but wasn't yet known/scanned for at build time.

## Integration

- Typically deployed as a DaemonSet, alerting via its own output (log, gRPC, webhook to Alertmanager/
  Slack/PagerDuty) — wire it into the same alerting path the `production-incident-commander` agent and
  `prometheus`/`observability-engineer` skills already use, not a separate, easily-ignored channel.
- Falcosidekick is the common bridge from Falco's raw output to actual destinations (Slack, PagerDuty,
  Elasticsearch, a webhook) — Falco alone just detects and logs; something needs to route those detections
  somewhere a human or automation actually sees them.

## Common Pitfalls

- Default ruleset left unmodified for the specific workloads running — a default rule set generates
  noise for legitimate behavior specific to an environment (e.g. a deliberately shell-capable debug
  sidecar); tune rules against real, known-legitimate behavior rather than accepting the noise or
  disabling rules wholesale.
- Falco deployed but its output going nowhere anyone monitors — the same "detection with no routed
  alerting" gap flagged for every other tool in this stack; a Falco alert nobody sees is equivalent to no
  detection at all.
- Treated as a replacement for build-time scanning instead of a complement — Falco catches *behavior*,
  not the presence of a known vulnerability before it's ever exploited; both layers are needed.
- Rules not version-controlled/reviewed the same way any other security policy-as-code
  (`checkov`/`opa`/`kyverno`) would be — a runtime detection rule is still a piece of security
  configuration deserving the same change-review discipline.
