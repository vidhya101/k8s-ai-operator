---
name: feature-flags
description: Feature flag management — LaunchDarkly, Unleash, and the vendor-neutral OpenFeature standard — for decoupling deployment from release. Use when designing a feature-flag rollout strategy, or reviewing flag hygiene/technical debt.
---

# Feature Flags (LaunchDarkly, Unleash, OpenFeature)

Decouples **deployment** (code reaching production) from **release** (a feature becoming active for
users) — code can be deployed dark (flag off) and enabled later via a config change, without a redeploy.
This is also the practical enabler behind much of `cicd-pipeline-design`'s progressive-delivery discussion
and `deployment-strategies`' canary rollout pattern, implemented at the application-logic level instead of
(or alongside) infrastructure-level traffic splitting.

## Core Model

```javascript
if (await flagClient.variation("new-checkout-flow", user, false)) {
  return renderNewCheckout();
}
return renderLegacyCheckout();
```

- **Boolean flags**: simplest case, on/off, often per-environment or per-percentage-rollout.
- **Multivariate flags**: return one of several values (an experiment variant, a config value) rather than
  just true/false — useful for A/B testing or gradual config rollout, not just feature gating.
- **Targeting rules**: enable a flag for a specific user segment (internal users, a percentage rollout, a
  specific customer for a beta) — the mechanism for a controlled, gradual release rather than all-or-nothing.

## OpenFeature (vendor-neutral standard)

- A CNCF standard SDK/API for feature flagging — application code targets the OpenFeature API, and a
  pluggable "provider" connects to whichever actual backend (LaunchDarkly, Unleash, a custom in-house
  system) is in use. Reduces vendor lock-in: switching flag providers becomes a provider-config change,
  not a rewrite of every flag check throughout the codebase.

## Flag Hygiene (the part that decays if ignored)

- **Flag debt**: every flag left in code after its rollout is fully decided (either fully shipped or fully
  reverted) is dead conditional logic that makes the codebase harder to reason about — same "remove what
  your own changes make obsolete" principle from `CLAUDE.md` Section 1.3, applied to flags specifically:
  a completed rollout's flag and its now-dead branch should be cleaned up, not left indefinitely.
- **Kill switches** (an operational flag to instantly disable a feature during an incident) are a
  different category from release flags and are often intentionally long-lived — don't apply the same
  "clean this up" pressure to a flag whose whole purpose is being available during a future incident.

## Common Pitfalls

- Flags left in code long after the rollout decision is made, accumulating as permanent technical debt
  and increasing the number of possible code paths that actually need testing.
- A flag evaluated inconsistently within a single user's session/request (checked multiple times,
  potentially returning different values mid-flow if targeting rules or the flag itself changes) — causing
  confusing, hard-to-reproduce inconsistent behavior; evaluate once per request/session and pass the
  result through, don't re-check repeatedly.
- No audit trail/review process on who can flip a flag — a flag is effectively a production config change
  and deserves the same change-review consideration as any other production-affecting action, especially
  once flags control anything beyond cosmetic UI differences.
- Flag provider outage/latency treated as unhandled — flag evaluation should fail safe (a sensible
  default) if the flag service is unreachable, not block or crash the application.
