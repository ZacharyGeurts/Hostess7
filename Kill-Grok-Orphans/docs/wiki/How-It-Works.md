# How It Works

## Orphan definition

A **Grok orphan** is a process that:

1. Has been **reparented to init** — no live supervisor owns it anymore
2. Matches a **Grok leak signature** in `kgo-patterns.json`

| Platform | Orphan parent PID |
|----------|-------------------|
| Linux | `1` (systemd/init) |
| macOS | `1` (launchd) |
| Windows | `0` or `4` (System) |

## Known leak signatures

These patterns were identified from the SG/KILROY stack:

- **`grok-firmware-audit.sh`** — spawned by `boot-simulate.sh`, leaks hundreds of copies
- **`Grok16/bin/awk`** — bash wrapper children at ~30% CPU each
- **`Grok16/bin/` shell shims** — orphaned Grok16 bin bash wrappers
- **`boot-simulate.sh`** — orphaned boot simulation subprocess

## Scan loop

Every `interval_sec` (default 5):

1. Enumerate all processes (`/proc` on Linux, `psutil` elsewhere)
2. Filter to orphans matching configured patterns
3. Send `SIGTERM`, wait `grace_sec`, then `SIGKILL` if still alive
4. Log each kill to syslog (Linux) or log file (macOS/Windows)

## Native vs Python

| Component | Platform | Built with |
|-----------|----------|------------|
| `kgo` | Linux | Grok16 `g16` |
| `kgo-watchdog` | Linux fallback, macOS, Windows | Python 3 + psutil |