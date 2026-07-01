# Hostess7 Architecture (1.0.7h)

## Overview

Hostess7 is a sovereign field brain: one dispatcher, one brain entry, unified state, embeddable as package, container, or user service.

```
┌─────────────────────────────────────────────────────────────┐
│  Hostess7.sh (dispatcher) — 80+ commands                    │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┬─────────────────┐
    ▼                 ▼              ▼                 ▼
 hostess7-core   field_super-    hostess7_web     field_agents7
 (supervisor)    intelligence    (Flask :8080)    (daemon)
                 (brain)              │
                     │                ├── /api/ask
                     │                ├── /api/brain
                     ▼                └── /api/status/full
              domain plugins
         (legal, medical, warfare, truth, …)
                     │
                     ▼
         brain/state (unified cortex + snapshots)
         cache/fieldstorage/brain (corpus JSON)
```

## Layers

| Layer | Path | Role |
|-------|------|------|
| Dispatcher | `Hostess7.sh` | Routes commands; sets `HOSTESS7_ROOT`, `HOSTESS7_BRAIN_STATE` |
| Package | `src/hostess7/` | Boot, core supervisor, daemon loop, cohesion tests, paths |
| Brain | `scripts/field_superintelligence.py` | Ask/ingest/learn across all domains |
| Web | `scripts/hostess7_web.py` | Flask UI + REST API |
| State | `brain/state/` | `cortex.json` + versioned snapshots |
| Storage | `cache/fieldstorage/` | Brain JSON, textbooks, ZAC restore target |

## Boot chain

1. `hostess7_boot.py` — deps, zac-restore, stack-learn, agents on, alert-posture, web-start
2. `hostess7-core start` — same via package + snapshot
3. `hostess7-daemon` — background reflect loop (online learn, self-brief)

Doctrine order: `data/field-stack-doctrine.json` → KILROY kernel first.

## Embed paths

- **pip:** `pip install -e .` → `hostess7-boot`, `hostess7-core`, `hostess7-web`, `hostess7-daemon`
- **Docker:** `docker compose up` — state volume at `/var/lib/hostess7/state`
- **User service:** `./Hostess7.sh embed` → systemd user unit + boot + daemon

## Ports

| Port | Service |
|------|---------|
| 8080 | Hostess7 web (`/api/*`) |
| 9477 | KILROY / NEXUS panel |
| 9481 | Queen world shell |
| 9488 | Training viewer |

## Cohesion

Run on boot or CI:

```bash
./Hostess7.sh benchmark-iq
./Hostess7.sh validate-truth
./Hostess7.sh cohesion
```

Target: IQ ≥ 6.0 operational, ≥ 8.0 war-ready.