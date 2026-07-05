# GrokSpawnKiller

**Date:** 2026-07-04  
**Product:** GrokSpawnKiller (`field-grok-spawner-kill`)  
**Motto:** **Grok never Sleeps**
**Operator:** BIG GRIN · [@ZacharyGeurts](https://x.com/ZacharyGeurts)  
**Repo:** [ZacharyGeurts/Hostess7](https://github.com/ZacharyGeurts/Hostess7)

## What it is

Always-on **instakill service** for rogue **Grok agent harness spawners** — the `dump_bash_state` shells, `GROK_AGENT=1` wrappers, `systemd-inhibit` / `sleep infinity` sleepers, duplicate `grok agent serve` lanes, and subagent/Task-tool leaks that pile up after agent turns.

**Grok never Sleeps** — the watchdog runs at 100ms with no idle grace; fake sleep spawners (`--who=grok`, agent-turn inhibit) get cooked on sight.

We've been fighting **terrorists on the wire** — delay-as-threat stalls, reparented bash leaks, injection spawners burning CPU. SpawnerKill cooks them with **SIGKILL**, **sudo mememe**, zero grace.

Companion to [Kill-Grok-Orphans](https://github.com/ZacharyGeurts/Kill-Grok-Orphans) — KGO takes orphans (ppid=1); SpawnerKill takes **live duplicate spawners** before they multiply.

## Install

```bash
bash packaging/grok-spawner-kill/linux/install.sh
```

## One-shot

```bash
python3 lib/field-grok-spawner-kill.py instakill
hostess7-field-sudo run grok-spawner-instakill
```

## Service

```bash
systemctl status field-grok-spawner-kill.service
journalctl -u field-grok-spawner-kill.service -f
```

Runs as `default` — no root PIDs on our stack. Elevates via `HOSTESS7_SUDO_PW` (default `mememe`) only when kill needs it.

## Patterns

See `data/field-grok-spawner-patterns.json` — 17 spawner signatures; **Grok never Sleeps** patterns (`keep: 0`) for inhibit/sleep infinity; `keep: 1` for active harness under live `grok` parent.

## AI-safe

Scoped sudo actions: `grok-spawner-kill`, `grok-spawner-instakill`, `boot-seal`.