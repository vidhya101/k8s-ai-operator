---
description: Review cloud cost governance — rightsizing, unused resources, storage lifecycle, and cost allocation tagging.
argument-hint: "[optional: specific service/account/resource group to focus on]"
---

Review cost posture for: $ARGUMENTS (default: whatever cloud resources are visible via this repo's
Terraform/IaC and, if credentials are available, the live account).

Delegate to the `principal-finops-engineer` agent, using the `aws`/`azure`/`gcp` skills for
provider-specific resource/tagging conventions.

1. Look for the common waste patterns first: oversized instances/pods relative to actual utilization,
   orphaned resources (unattached volumes, idle load balancers, old unlifecycled snapshots), and storage/
   log retention with no lifecycle policy.
2. Check cost-allocation tagging completeness — spend that can't be attributed to an owning team/project
   is itself a finding, not just a minor hygiene gap.
3. If reserved/committed-use spend is in scope, weigh it against the workload's actual stability — a
   commitment sized for a volatile/bursty workload is a cost risk, not a savings guarantee.
4. Explicitly flag any potential cost cut that would reduce redundancy, availability, or security posture
   (e.g. removing multi-AZ replicas, shrinking a backup retention window) as a trade-off requiring the
   user's sign-off — never present a reliability/security reduction as a clean win.

End with findings ranked by estimated savings vs. effort, each naming the specific resource/pattern and a
concrete fix.
