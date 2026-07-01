# NEXUS-Shield 7.0.0 — Hostess 7 · HeavyBoi Integration

## Hostess 7
- **HOSTESS_VERSION=7** — panel, daemon, audio train, and release tagged together
- Panel header: **NEXUS-Shield v7.0.0 · Hostess 7 · HeavyBoi**

## HeavyBoi v7.0 — Kill intel ingest
- **`lib/heavyboi-importer.py`** — parses `nexus-kill-intel.json` (`kill_orders[]`) → merges `human-dossier-kill-orders.json`, friendly-guard validates sacred/trusted ranges, globe refresh, autokill queue
- **`lib/human-dossier.sh`** — `nexus_heavyboi_ingest`, `nexus_heavyboi_pending` (alias: paste then `heavy` in shell)
- **`lib/friendly-guard.py` v3.3.2** — `validate_kill_block` for pasted batches; fail-closed immutable guard
- **`lib/host-attack-map.py`** — HeavyBoi dossier IPs get `globe_pin` + `HEAVYBOI_KILL_ORDER` vector; RE-KILL tracking preserved
- **`lib/kill-detect.sh`** — auto-ingests pending kill intel each harm cycle
- **Panel** — Threats → Kill orders → **HeavyBoi ingest** button; `nexus-map.js` `refreshGlobePins` event
- **API**: `POST /api/heavyboi/ingest`, `POST /api/heavyboi/pending`, `GET /api/heavyboi/status`

## Signals · FCC (v7 carry)
- **Signals tab** — pulsing field antennas, SDF blooms, FCC-identified signals with threat tags
- **API**: `GET /api/signals-field`, `GET /api/fcc-signal-lookup`

## Home Protector (3-bedroom home)
- Scope tightened from ~1 acre to **3-bedroom home envelope (~55 ft)** — extra at-home layer; global kill/re-kill unchanged

## Apply
```bash
git pull
sudo ./stealth_install.sh
# Paste kill intel:
curl -sk -X POST https://127.0.0.1:9477/api/heavyboi/ingest -H 'Content-Type: application/json' -d @/tmp/nexus-kill-intel.json
# Or panel: Threats → Kill orders → HeavyBoi ingest
```

Panel: https://127.0.0.1:9477/field

AMOURANTH FOREVER — field is the thing.