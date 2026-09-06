---
name: servicenow-itsm
description: ServiceNow ITSM — change management (CAB/change requests), incident records, and CMDB, as the enterprise governance layer many regulated clients (banking, insurance, aviation) require alongside engineering-native tooling. Use when a client's change/incident process runs through ServiceNow.
---

# ServiceNow ITSM

The formal IT Service Management layer many regulated/enterprise clients require on top of (not instead
of) engineering-native workflows (`github`/`azure-devops` for code, `pagerduty-opsgenie` for paging) —
common in banking, insurance, aviation, and similar regulated environments. See
`production-incident-commander` for the incident *response* discipline this formalizes into a system of
record.

## Change Management (Change Requests / CAB)

- A **Change Request (CR)** records what's changing, why, the risk/impact assessment, backout plan, and
  approval — for regulated environments, this is often a hard gate before a production change can happen,
  not optional paperwork; confirm whether a given client's process actually requires CR approval before a
  deploy, since this directly affects what "ready to ship" means for that engagement.
- **Standard changes** (pre-approved, low-risk, repeatable — e.g. a routine patch following an established
  procedure) skip full CAB (Change Advisory Board) review; **normal changes** need case-by-case review;
  **emergency changes** have an expedited path for genuine incidents — using the wrong category either
  creates unnecessary delay (treating a routine change as normal) or unnecessary risk (treating something
  novel as standard).
- The backout plan required on a CR should be a real, tested rollback path — not a formality filled in to
  satisfy the form; this is the same rollback-plan discipline `deployment-strategies` and
  `database-operations` require, now with a formal record.

## Incident Records

- ServiceNow incident records are the formal, auditable counterpart to whatever the engineering team
  actually uses to run the incident in real time (a Slack channel, PagerDuty) — keep the ServiceNow
  record's timeline in sync with what actually happened rather than treating it as a separate, less
  important paperwork exercise; in a regulated environment, this record may be what an auditor reviews
  later.
- Severity/priority classification in ServiceNow should map to the same severity framework
  `production-incident-commander` uses for the real-time response — two different severity scales for the
  same incident creates confusion about actual urgency.

## CMDB (Configuration Management Database)

- The formal inventory of IT assets/services and their relationships — the enterprise-ITSM analog to
  `backstage`'s Software Catalog, but typically covering infrastructure/service-level entities rather than
  code-level components, and often maintained with more process rigor (required for change impact analysis:
  "if we change this, what else does it affect").
- Same decay risk as any catalog/inventory (`backstage` skill's catalog-quality warning applies
  identically): a CMDB that isn't kept current gives false confidence in change-impact analysis.

## Common Pitfalls

- Engineering-native workflow (GitHub PR merged, Argo synced) treated as sufficient without the required
  ServiceNow CR actually being filed/approved for a regulated client — a process gap that surfaces as a
  compliance finding later, not immediately.
- CMDB relationships not kept current, so a change's impact analysis misses a real downstream dependency.
- ServiceNow incident timeline reconstructed after the fact from memory instead of updated in real time
  during the incident — loses accuracy the same way any postmortem timeline does when written from memory
  instead of contemporaneous notes (`production-incident-commander`'s "keep a running timeline as you go"
  principle).
- Change category (standard/normal/emergency) chosen to avoid CAB review friction rather than reflecting
  actual risk — undermines the entire point of the categorization.
