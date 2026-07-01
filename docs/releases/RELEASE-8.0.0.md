# NEXUS-Shield 8.0.0 — Military Grade C2

## Military GUI v8

- **`nexus-military-v8.css`** — dark olive/green/brown field C2 theme
- **`nexus-military-v8.js`** — OPS FLOW bar, mission briefs per tab, live version stamp
- Panel header and `/api/status` report **v8.0.0** with `panel_build: military-v8`
- Parallel tab/field loading — core status shell + independent slice fetches

## GitHub update lock

- **`github-update.lock`** — panel UPDATE NOW acquires lock before git pull + install
- **`lib/nexus-update-apply.sh`** — background apply: fetch, pull, `stealth_install`, restart
- Sudo prompts via pkexec, zenity, kdialog, or terminal when root is required
- `POST /api/update/sudo-prompt` for password retry from the panel

## System tray

- **Amouranth face** tray icon (`nexus-tray-amouranth.png`) — military green/bronze ring
- **Left or right click** → fast-track tab picker (single click opens tab; no quit/cancel dialogs)
- **Autostart + watchdog** — tray icon on login; auto-restart if the process exits
- **Icon cache refresh** — stamp-based tray PNG so updates reshow the correct face
- **`./nexus.sh --tab signals`** — open any tab from CLI
- **OCR validated** — `scripts/panel-ocr-validate.py` confirms v8.0.0 military GUI before release

## Field & panel

- Parallel field slice publish (`field-panel-parallel.py`) — 25+ slices in parallel
- Library catalog, 0.25 m GPS triangulation (`NEXUS_FIELD_TRI_CEP_M=0.25`)
- MERCILESS lethal enforcement · field-first GUI publish

## Install

```bash
git clone git@github.com:ZacharyGeurts/NEXUS-Shield.git
cd NEXUS-Shield
chmod +x stealth_install.sh nexus.sh
sudo ./stealth_install.sh
./nexus.sh
```

Panel: **https://127.0.0.1:9477/field**

Update: click **UPDATE NOW** in the panel (uses `github-update.lock`).