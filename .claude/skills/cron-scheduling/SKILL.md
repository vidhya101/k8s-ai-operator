---
name: cron-scheduling
description: Job scheduling across crontab, systemd timers, and Kubernetes CronJobs — syntax, timezone handling, and overlap/failure semantics. Use when authoring or debugging a scheduled job in any of these systems.
---

# Cron & Job Scheduling

Three common scheduling mechanisms, each with different failure/overlap semantics — pick based on where
the job actually needs to run, not by default habit.

## crontab Syntax

```text
 ┌───────────── minute (0-59)
 │ ┌───────────── hour (0-23)
 │ │ ┌───────────── day of month (1-31)
 │ │ │ ┌───────────── month (1-12)
 │ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
 │ │ │ │ │
 * * * * *  command

0 2 * * *        # 02:00 daily
*/15 * * * *      # every 15 minutes
0 9 * * 1-5       # 09:00 on weekdays
```

- crontab runs in the timezone of the system (or `CRON_TZ`/user setting) — don't assume UTC without
  checking; a job scheduled for "2am" can mean different absolute times across hosts.
- No built-in overlap protection — if a job takes longer than its interval, the next invocation starts
  anyway, potentially running concurrently with the still-running previous one. Guard with a lock
  (`flock`) if that's not safe for the job.

```bash
# Guarding against overlap:
* * * * * flock -n /tmp/myjob.lock -c '/path/to/script.sh'
```

## systemd Timers (preferred over crontab on systemd hosts)

```ini
# /etc/systemd/system/myjob.timer
[Timer]
OnCalendar=daily
Persistent=true    # run on next boot if the system was off when it should have fired

[Install]
WantedBy=timers.target
```

- Built-in overlap protection (a unit won't start again if the previous run's service unit is still
  active, unless explicitly configured otherwise), structured logging via `journalctl -u myjob.service`,
  and `Persistent=true` catches up missed runs after downtime — meaningfully better observability/safety
  than raw crontab for anything that matters.

```bash
systemctl list-timers
journalctl -u myjob.service --since "1 day ago"
```

## Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata: { name: my-job }
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid          # Forbid | Allow | Replace — pick based on job idempotency
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: job
              image: my-job:latest
              resources: { requests: { cpu: "100m", memory: "128Mi" } }
```

- `concurrencyPolicy: Forbid` prevents overlapping runs (skips a new run if the previous is still active)
  — the Kubernetes-native equivalent of the `flock` pattern above; use `Forbid` unless the job is
  genuinely safe to run concurrently with itself.
- CronJob's schedule runs in the kube-controller-manager's configured timezone (or an explicit
  `timeZone:` field on the CronJob spec in newer Kubernetes versions) — same "don't assume UTC" caution.

## Common Pitfalls

- No overlap guard on a job whose runtime can occasionally exceed its schedule interval, causing pile-up
  under load (each new invocation adds more concurrent load, worsening the original slowness).
- Timezone assumed rather than verified, causing a job to run at the wrong wall-clock time after a
  daylight-saving transition or a host/cluster located in a different timezone than expected.
- A cron job silently failing with no alerting — unlike a long-running service, a failed scheduled job
  produces no ongoing symptom to notice; needs explicit success/failure monitoring (a heartbeat metric, a
  dead-man's-switch alert, or `failedJobsHistoryLimit`/log review) rather than "no news is good news."
