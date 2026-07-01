# AmmoCode — final review prep (v4.9.0 upload / 5.0.0 distro)

Two reviewers expected. Product stays **Grok16-5.0.0**; GitHub tag **v4.9.0**.

## Quick verify

```bash
cd AmmoCode
python3 -m py_compile server/*.py
npm start
# open http://127.0.0.1:9555/
```

| Check | Where |
|-------|--------|
| Ping / version | POST `{"action":"ping"}` → `upload_version: 4.9.0`, `distro_version: 5.0.0` |
| Security scan | Flyout 🛡 → Scan now |
| Defield | Security → Defield SG/Grok16 (or auto on boot) |
| Collab invite | 👥 → Host · create invite → Join |
| Screen share | Host 📺 grant → Share my GUI |
| Network | 🌐 → Discover LAN (rate-limited) |
| ZNetwork | ⛨ attach-only, no double field |
| Screenshot | File → Screenshot… (sanctioned PNG) |

## Architecture (reviewer map)

```
index.html
  lib/editor.js      — editor, settings, security UI
  lib/collab.js      — invite-only WS + voice + screen share
  lib/network.js     — mesh flyout
  lib/znetwork.js    — capture guard + hook
  lib/security.js    — vuln registry scan
server/ammocode-serve.py   — API + static
server/ammocode-collab.py  — WS hub :9556
server/ammocode-network.py — discovery, tunnel, threat
server/ammocode-security-manage.py — MITM pins
server/ammocode-field-control.py   — defield SG
```

## Doctrine files

- `data/ammocode-2027-doctrine.json` — product policy
- `data/ammocode-shield-doctrine.json` — capture deny / permitted share
- `data/ammocode-security-doctrine.json` — MITM + screenshare
- `data/ammocode-network-doctrine.json` — polite discovery
- `data/ammocode-version.json` — 4.9 upload / 5.0 distro

## Distribution model

- **Executable:** single secured binary (`npm run build` → `dist/ammocode`) — immutable at runtime, **replace file only** to upgrade
- **Settings:** `~/.config/ammocode/ammocode-settings.secure.json` — HMAC-signed, schema migrates on every run when options added/removed
- **API:** `settings_load`, `settings_save`, `settings_status`

## Known limits (call out in review)

- HTTP tunnel queue is in-memory (not persistent across restart)
- Open-network peers require manual host entry (no WAN scan)
- VS Code extension is stub webview (embed API exists separately)
- `network-lists.json` / `security-pins.json` gitignored — local operator data

## Version truth

| Field | Value |
|-------|--------|
| `upload_version` | 4.9.0 |
| `distro_version` | 5.0.0 |
| `pkgversion` | Grok16-5.0.0 |
| GitHub tag | v4.9.0 |