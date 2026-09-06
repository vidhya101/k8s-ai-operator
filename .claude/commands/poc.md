---
description: Scaffold a proof-of-concept with production-grade structure (not throwaway code) using the relevant stack skills.
argument-hint: "<what the PoC needs to demonstrate>"
---

Scaffold a PoC for: $ARGUMENTS

1. State what the PoC needs to prove/demonstrate in one sentence before writing anything — a PoC with an
   unclear goal turns into unscoped exploration.
2. Use the minimum stack needed to demonstrate it (Section 1.2 — no speculative extra tooling because a
   real project "would probably need it eventually"); pull in the relevant skill(s) for whatever stack is
   actually chosen (`terraform`, `docker-multi-stage`, `kubernetes`, etc.) so the scaffold follows this
   repo's real conventions from the start rather than needing a rewrite to become production-ready.
3. Still apply the non-negotiables even in a PoC: no secrets committed, no plaintext credentials, resource
   requests/limits on any container/pod, basic error handling at real boundaries — a PoC that becomes the
   basis for the real thing (common outcome) shouldn't need a security pass bolted on after the fact.
4. Clearly label what's intentionally cut for PoC scope (no HA, no multi-env, single region) versus what's
   already production-shaped, so it's obvious what still needs work before this is more than a PoC.

Confirm the target stack/cloud/environment first if it isn't already stated — don't silently pick one
(Section 1.1).
