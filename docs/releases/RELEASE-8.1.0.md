# NEXUS-Shield 8.1.0 — Instant Field Tabs

## GitHub field brain + library (authoritative)

- **`library/dewey/**`** — 85+ book manifests on GitHub; panel loads catalog at zero cost
- **`data/field-brain/`** — superintel + library manifest snapshots synced from field when available
- **`scripts/sync-field-brain-github.sh`** — refresh `library/` + `data/field-brain` from `origin/main`, wire panel slices
- **`/api/field-brain`** — Hostess7 superintelligence status + GitHub catalog counts in Library tab

## Zero-cost instant loading

- **Field cache first** — all parallel slice APIs read published `threat-panel.json` before live scripts (`_panel_slice`)
- **25 parallel workers** — `field-panel-parallel.py` publishes every tab slice symmetrically on each field cycle
- **Instant tab switch** — no gate blocking; hover prefetch + immediate paint with cached field data
- **Detail-heavy tabs** — full field payloads available the moment a tab is approached

## Updates require sudo (no preview)

- **Panel UPDATE NOW** — sudo prompt required before apply; `/api/update/apply` returns 403 without cached sudo
- **Hostess7** — `nexus update` without `--apply` is blocked; apply runs `sudo stealth_install.sh`
- **Removed preview plan** from autonomous publish cycle (no more JSON preview spam during field publish)

## Military GUI

- **v8.1.0** — `panel_build: military-v81`, OPS FLOW bar, mission briefs per tab
- Tray fast-track tab picker, autostart watchdog, Amouranth taskbar icon

## Install

```bash
sudo ./stealth_install.sh
./nexus.sh
```

Panel: **https://127.0.0.1:9477/field**