# Hostess7 Architecture (2.0.7h)

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
         brain/state (SOURCE OF TRUTH)
           ├── cortex.json
           ├── migration.json
           ├── snapshots/ (32 retain + age prune)
           └── legacy/fieldstorage_brain (migrated corpus)
```

## 2.0 data model

| Path | Role |
|------|------|
| `brain/state/` | **Canonical** — cortex, snapshots, migration marker |
| `brain/state/cortex.json` | Boot memory, snapshot index |
| `brain/state/migration.json` | Legacy import audit (errors surface as warnings) |
| `cache/fieldstorage/brain/` | Legacy read path; pruned after migration when enabled |

Path resolution order: **env → package detect → dev tree (requires scripts/) → fallback**.

`packaged_context()` in `hostess7` reports whether scripts are missing (pip wheel) so cohesion uses package modules instead of subprocess.

## War realism (2.0.7h)

| Module | Role |
|--------|------|
| `hostess7.war_realism` | OODA, ROE, `simulate_threat()`, wargame metrics |
| `hostess7.amouranth_bridge` | FieldX86 fabric stub, entropy injection |
| `hostess7.cohesion` | IQ + truth + war smoke (pip-safe) |

CLI: `hostess7-war-train`, `./Hostess7.sh war-realism`, `./Hostess7.sh war-panel`

## Layers

| Layer | Path | Role |
|-------|------|------|
| Dispatcher | `Hostess7.sh` | Routes commands; respects external `HOSTESS7_ROOT` |
| Package | `src/hostess7/` | Boot, core, daemon, cohesion, war_realism, paths, state |
| Brain | `scripts/field_superintelligence.py` | Ask/ingest/learn (full tree only) |
| Web | `scripts/hostess7_web.py` | Flask UI + REST API |
| State | `brain/state/` | Cortex + snapshots — single source of truth |

## Boot chain

1. `brain_state_dir()` — migrate legacy → unified, warn on errors
2. `hostess7_boot.py` — deps, zac-restore, stack-learn, agents, web (when scripts present)
3. `hostess7-cohesion` — IQ + truth + war profile smoke
4. `hostess7-daemon` — background reflect loop

## Embed paths

- **pip:** `pip install -e .` → `hostess7-boot`, `hostess7-core`, `hostess7-cohesion`, `hostess7-war-train`
- **Docker:** `docker compose up` — war profile via `--profile war`, cohesion healthcheck
- **User service:** `./Hostess7.sh embed` → systemd user unit

## Ports

| Port | Service |
|------|---------|
| 8080 | Hostess7 web (`/api/*`) |
| 9477 | KILROY / NEXUS panel |
| 9481 | Queen world shell |
| 9488 | Training viewer |

## Cohesion targets

- IQ ≥ 6.0 operational, ≥ 8.0 war-ready
- War profile: ROE compliance ≥ 80% on wargame smoke