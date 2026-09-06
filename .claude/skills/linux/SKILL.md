---
name: linux
description: Linux host troubleshooting and administration — systemd, resource pressure (CPU/memory/disk/IO), process/file debugging, and kernel/sysctl tuning. Use for host-level issues underneath containers/VMs/bare metal.
---

# Linux

Host-level troubleshooting reference, underneath whatever's running on top (containers, Kubernetes nodes,
VMs, bare metal).

## Resource Pressure Triage

```bash
top / htop                          # quick CPU/mem overview
vmstat 1                            # CPU, memory, swap, IO trend over time
iostat -x 1                         # per-device disk IO, look for high %util or await
free -h                             # memory, including buff/cache (often not "free" but reclaimable)
df -h / du -sh <dir>                # disk space; du to find what's actually consuming it
ss -s                                # socket summary; ss -tlnp for listening ports
dmesg -T | tail -50                  # kernel messages — OOM killer, hardware errors, driver issues
journalctl -xe                       # recent systemd journal, errors highlighted
journalctl -u <service> -f           # follow a specific service's logs
```

## systemd

```bash
systemctl status <service>
systemctl list-units --failed
systemctl daemon-reload              # after editing a unit file
journalctl -u <service> --since "1 hour ago"
```

## Common Failure Patterns

- **OOM kill**: check `dmesg` for `Out of memory: Killed process` — the killed process isn't always the
  actual memory hog; check `journalctl` timing against monitoring for which process's growth triggered it.
- **Disk full**: `df -h` shows the filesystem full, but `du` from root can be slow — check likely culprits
  first (`/var/log`, container image/layer storage, application-specific data directories) before a full
  `du -sh /*` sweep.
- **inode exhaustion**: `df -h` can show free space while `df -i` shows 100% inodes used — a different
  failure mode (many small files) that a naive space check misses.
- **Zombie/defunct processes**: usually harmless individually (parent hasn't reaped them) but a growing
  count indicates a parent process bug worth investigating, not something to kill directly (they can't be
  killed — the parent or its exit is what clears them).
- **File descriptor limits**: `ulimit -n` per-process limit hit causes "too many open files" errors under
  load that don't reproduce at low traffic — check `/proc/<pid>/limits` and the systemd unit's
  `LimitNOFILE` if relevant.

## Kernel/sysctl (network- and container-host-relevant)

```bash
sysctl net.ipv4.ip_forward           # required for a node acting as a router (e.g. K8s CNI)
sysctl net.core.somaxconn            # connection backlog queue size
sysctl vm.max_map_count              # commonly needs raising for Elasticsearch/some databases
sysctl fs.inotify.max_user_watches   # commonly needs raising for file-watching workloads (K8s kubelet, dev tools)
```

## Common Pitfalls

- Restarting a service to "fix" resource exhaustion without checking `dmesg`/journal for the actual cause
  first — the same failure recurs once the underlying leak/limit is hit again.
- Assuming `df -h` free space means write failures can't be disk-related without also checking inodes.
- Changing a `sysctl` value live without persisting it in `/etc/sysctl.d/`, so it silently reverts on
  reboot.
