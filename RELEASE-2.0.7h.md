# Hostess7 2.0.7h

## Bug fixes

- **paths.py** — Windows `resolve().absolute()`, packaged context without false-positive dev tree (requires `scripts/`)
- **cohesion.py** — `scripts_available()` guards; package `war_realism` fallback for pip installs
- **state.py** — migration error warnings on boot; snapshot retention (32 latest + 90-day prune)
- **Hostess7.sh** — respect external `HOSTESS7_ROOT`; war-realism → `python -m hostess7.war_realism`
- **Migration prune** — optional legacy `cache/fieldstorage/brain` cleanup (`HOSTESS7_MIGRATION_PRUNE=1`)
- **H7 optimise** — `--apply` scans `.pages-*`, `brain/`, `data/` JSON
- **Version sync** — `hostess7-sync-version.py` updates pyproject, README, RELEASE, compose

## New modules

- `src/hostess7/war_realism.py` — OODA, digital twin stub, ROE validator, `simulate_threat()`
- `src/hostess7/amouranth_bridge.py` — FieldX86 fabric stub + entropy into OODA scoring
- `hostess7-war-train` / `hostess7-cohesion` console entry points
- `./Hostess7.sh war-panel` — ROE status + cohesion dashboard JSON

## Docker / CI / embed

- War profile compose service (`--profile war`), RTX detection in `docker/entrypoint.sh`
- Healthcheck runs `hostess7.cohesion iq`
- CI: cohesion + `war_realism wargame advanced` smoke
- `scripts/verify-embed-install.sh` — core status + migration marker + war sim

## Verify

```bash
pip install -e ".[dev]"
python scripts/hostess7-sync-version.py
HOSTESS7_WAR_PROFILE=1 python -m hostess7.cohesion all
HOSTESS7_WAR_PROFILE=1 python -m hostess7.war_realism wargame advanced
./Hostess7.sh war-panel
bash scripts/verify-embed-install.sh
```

RTX 1.0.7h release assets remain compatible as an optional acceleration layer.