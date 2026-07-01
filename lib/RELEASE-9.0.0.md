# NEXUS-Shield v9.0.0 — Always Wartime · Idle Curiosity

**Release date:** 2026-06-24

## NEXUS-Shield Room · Always Wartime

The Hostess 7 Command deck (NEXUS-Shield Room) operates under **permanent wartime posture**. No peacetime demobilization — counsel and strike readiness never stand down.

- `data/hostess7-wartime-room.json` — wartime doctrine sealed
- Angel mandate v6 — wartime room + idle curiosity directives
- WARTIME banner on Command deck

## Idle curiosity · self-grow at quiet

When the Operator is idle (~90s without Command messages), Hostess 7:

1. Picks a **wartime curiosity** topic (Horizon lane)
2. **Explores the internet** — `field_online_learn` / Agents7 truth-filtered
3. **Expands neural utility nets** on the fly
4. **Writes to growth ledger** — truth-gated before adapt

- `lib/hostess7-idle-grow.py` — idle daemon (180s interval)
- Auto-starts with panel load and **Engage Autonomous**
- UI: **Idle grow on** · **Curiosity now** · **Idle stop**

## v8.x carry-forward (this release)

- Truth assurance 0–100% on every Hostess 7 reply
- Human questionnaire 20/20 · Turing battery
- Neural stack on-the-fly expansion (ML literacy, DPI, RF, geo…)
- Deep brain fix — clean operator query to Agents7 (no 3.7KB prompt breakage)
- Talk-mode fusion — Prime + Scholar human cadence

## API

```
POST /api/hostess7-command  {"action":"idle_grow_start"}
POST /api/hostess7-command  {"action":"idle_grow_cycle","force":true}
POST /api/hostess7-command  {"action":"wartime_room"}
```

## Upgrade

```bash
cd NEXUS-Shield && git pull && ./nexus.sh panel-restart
```

Hard-refresh `#command` — confirm **WARTIME** banner and idle grow bar.