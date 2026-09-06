---
name: pagerduty-opsgenie
description: PagerDuty/Opsgenie — on-call scheduling, escalation policies, and alert routing configuration. Use when setting up or reviewing on-call rotations/escalation policies, complementing the sre and production-incident-commander skills' process discipline with the actual tooling.
---

# PagerDuty / Opsgenie (On-Call & Escalation)

The tooling behind `sre`'s on-call discipline and what `production-incident-commander` assumes is already
routing pages correctly — schedules, escalation policies, and alert-to-service routing.

## Core Concepts (shared model across both tools)

- **Schedule**: who's on call and when — rotation type (weekly, daily, follow-the-sun across time zones)
  should match the team's actual size/distribution; a rotation too short burns people out, one too long
  means infrequent on-call practice and rustier incident response when it does happen.
- **Escalation policy**: what happens if the primary on-call doesn't acknowledge within a set time —
  escalates to a secondary, then a manager, etc. A service with an alert but no escalation policy (or one
  pointing at a single person with no backup) has a real availability gap the moment that person is
  unreachable.
- **Service**: the routing unit — alerts come in tagged to a specific service, which has its own
  on-call schedule/escalation policy; alerts should route to the team that can actually act on them, not
  a general catch-all rotation that then has to figure out who to forward to.

## Alert Routing from Observability

```text
Prometheus Alertmanager → PagerDuty/Opsgenie integration → routes to the Service → 
  escalation policy → current on-call
```

- This is the concrete implementation of the `prometheus` skill's Alertmanager routing section and the
  `observability-engineer` agent's "alerts route to the team's actual on-call tool" checklist item —
  Alertmanager's `receivers` config points at a PagerDuty/Opsgenie integration key per service/team.
- Alert **deduplication** at this layer (both tools support it) prevents the same underlying alert from
  paging repeatedly if it keeps re-firing — complements, doesn't replace, Alertmanager's own
  `group_by`/`inhibit_rules`.

## Escalation Policy Design

- Test escalation policies, not just create them — the same "test failover, don't just monitor lag"
  principle `database-operations` applies to database replication applies here: an escalation policy
  that's never actually been triggered in anger might have a broken integration or an out-of-date contact
  that only surfaces during a real incident.
- Maintenance windows / scheduled downtime silencing — configure these explicitly during planned
  maintenance rather than having engineers ignore expected pages, which trains the habit of ignoring
  pages generally (alert fatigue, the same concern the `aiops` skill raises about noisy alerting).

## Common Pitfalls

- Escalation policy with a single point of failure (one person, no secondary) — the exact gap `sre`'s
  on-call sustainability principle warns about, now concretely a missing tier in the tool's config.
- Service-to-team alert routing misconfigured, so pages reach a team that can't actually act on the
  underlying system — wastes response time during exactly the moment it matters least to waste it.
- No scheduled maintenance-window silencing, so routine planned work generates real pages that train
  responders to expect (and potentially dismiss) noise.
- On-call schedule not matched to team size/timezone reality — a rotation that looks fine on paper but
  concentrates burden on one person's overnight hours disproportionately.
