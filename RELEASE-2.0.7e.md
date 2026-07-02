# Hostess7 2.0.7e — War Realism + Packaging Hardening

**Version:** `2.0.7e` · **Main project** · Old stack repos = Old Projects

## What shipped

### 2.0 foundation (carried forward)
- Hostess7 as **Main Project**; AmmoOS/Grok16/Queen/KILROY = Old Projects (`docs/old-projects.html`)
- Python package: `pyproject.toml`, `src/hostess7/`, console scripts (`hostess7-boot`, `hostess7-web`, `hostess7-core`, `hostess7-daemon`)
- Unified brain state: `brain/state/` (cortex + snapshots + migration audit)
- Cohesion benchmark: IQ + truth grades (`war-ready` / `operational` / `bootstrapping`)
- Embed: Docker, systemd daemon, tarball pack

### 2.0.7e — review fixes
- **paths.py hardened**: `HOSTESS7_ROOT` env → dev tree detect → packaged fallback; always exports `HOSTESS7_BRAIN_STATE`
- **State migration**: first boot copies legacy `cache/fieldstorage/brain` → `brain/state/legacy/` with `migration.json` audit log
- **Cohesion war profile**: `HOSTESS7_WAR_PROFILE=1` adds war realism + protect-friendlies to benchmark
- **core CLI**: `hostess7-core cohesion|brain|status` with packaged-context guard when `scripts/` missing
- **Version sync**: `scripts/hostess7-sync-version.py` — single source `src/hostess7/__init__.py`

### War realism (core directive)
- **`scripts/field_warfare_realism.py`**: OODA loop simulator, opponent digital twins (state actor, non-state, hybrid swarm, insider)
- **Lethal ROE module**: friendlies protection gate — non-lethal exhausted, imminent threat, neural guardian + truth filter + Owner log
- **Wargaming metrics**: kill ratio, friendly survival %, doctrine adherence, ROE compliance
- **API**: `GET/POST /api/war-train`, `GET/POST /api/protect-friendlies`
- **CLI**: `./Hostess7.sh war-realism [wargame|protect-friendlies|panel]`

## H7 compression (push lane)

Before every `publish-source`, the pipeline runs **`hostess7-h7-optimise.py`**:

- **JSON** (`docs/github-brain`, `docs/api`, `data/`) → in-place **H7s/1** (skips already disguised)
- **PNG** (Pages assets) → lossless **IDAT recompress** (stays valid `.png` for static serve)
- **Field visuals** (`--profile=combinatronic` from monorepo) → H7s for large PNGs, recompress for small

```bash
./Hostess7.sh h7-optimise              # dry-run savings report
./Hostess7.sh h7-optimise --apply      # apply before push
./Hostess7.sh publish-source           # sync + optimise + push main + gh-pages (no tag)
```

## Quick verify

```bash
pip install -e ".[dev]"
python scripts/hostess7-sync-version.py
python -m hostess7.cohesion all
./Hostess7.sh war-realism wargame intermediate
curl -s http://127.0.0.1:8080/api/war-train | python -m json.tool
```

## 2.0-native vs legacy

| 2.0.7e native (Python package) | Legacy (Hostess7.sh orchestrator) |
|----------------------------------|-----------------------------------|
| `hostess7-core status\|brain\|cohesion` | `./Hostess7.sh boot` |
| `hostess7-boot` / `hostess7-web` | `./Hostess7.sh on`, `web`, 100+ commands |
| `brain/state/` cortex + snapshots | `cache/fieldstorage/brain/` (migrated to legacy/) |
| `/api/brain`, `/api/war-train` | `./Hostess7.sh warfare`, `warfare-train` |

Field is THE thing.