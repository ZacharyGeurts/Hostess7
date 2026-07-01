# NEXUS-Shield 8.2.0 — QOL Experience Smoothing

## GUI experience smoothing (v8.2)

- **`nexus-military-v82.css/js`** — presentation layer: view fade transitions, tab load pulse, thin field-fetch progress bar, toast notifications, smooth scrollbars
- **Instant field cache paint** — session field blob paints tabs before network (`/api/nexus-field` single read)
- **OPS FLOW kill-chain badge** — live **KILL · AUTOKILL · RE-KILL** status in the ops bar (presentation only; logic unchanged)
- **Reduced duplicate refresh** — one bootstrap refresh cycle; no parallel publish spam on boot
- **`prefers-reduced-motion`** — disables animations when the OS requests it

## Tray & taskbar (from 8.1 → polished in 8.2)

- **Native flyout menu** — tray tabs open from the taskbar icon (not a popup window)
- **Dark Amouranth face icon** — tiny midnight tile, face maxed at 22/24/32 px taskbar resolution
- **AppIndicator-first** — visible on GNOME; `panel-tray-icon.py` renderer

## Field loading (zero-cost)

- **`/api/nexus-field`** — one uncompressed JSON read for all tab slices
- **Tab load %** — instant from full field blob (no more stuck at 0%)
- **Cache-first slices** — `threat-panel.json` before live scripts

## Kill chain — unchanged (still armed)

- **AUTOKILL** — `nexus_field_attack_autokill` / `autokill_certain` at 100% strike certainty
- **RE-KILL** — `nexus_field_attack_rekill_cycle` + `/api/attack-kit/rekill` for validated same-host returners
- **KILL / NO-KILL** — Host Attack map buttons and HeavyBoi ingest unchanged

## Updates require sudo

- Panel **UPDATE NOW** and Hostess7 `nexus update --apply` require sudo (no preview-only path)

## Install

```bash
sudo ./stealth_install.sh
./nexus.sh
```

Panel: **https://127.0.0.1:9477/field**