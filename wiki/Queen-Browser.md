# Queen Browser

**Queen Browser** is the AmmoOS field web engine — full browser chrome at `http://127.0.0.1:9481/world/browser.html` with the host desktop inside the Start tab. Engine path is **Field Gecko** (`Queen/field-gecko`); every user-facing surface says **Queen Browser**, never a third-party browser name.

**Queen Room** (movies + CHIPS emulator launch) lives at `http://127.0.0.1:9481/world/queen-game-room.html`.

## Stack layers (bottom → top)

| Layer | Role |
|-------|------|
| **Hardware** | Witness + wire — **no breaks**, own drivers, never harm host OS |
| **NEXUS C2** | `:9477` — command, gates, trust strike, security fixes |
| **ZNetwork** | 100% internet pipe — relayer + exploit shield help defend |
| **Queen Browser** | `:9481` — Field Gecko secured browser shell |
| **AmmoOS** | **Inside Queen Browser** Start tab — not a sibling product |

Doctrine: `data/field-stack-layer-doctrine.json` · API: `/api/field-stack-layer`

---

## User guide

**[Queen Browser User Guide](http://127.0.0.1:9481/world/queen-browser-guide.html)** — imports, shortcuts, gates, Field Gecko.

**Queen Room:** movies theater + emulator systems — launch from the browser or Start menu.

---

## Architecture

```
Queen Browser :9481/world/browser.html  (chrome — tabs, nav, drop/rise)
  └─ Start tab iframe → http://127.0.0.1:9477/field  (host desktop)
       └─ launches apps in Queen Browser tabs when embedded
  └─ Queen Room → /world/queen-game-room.html  (movies · CHIPS emulators)
```

Full C2 remains at `http://127.0.0.1:9477/command` — reachable from host desktop pinned apps or Queen Browser nav.

---

## Migrating bookmarks & profiles

| Step | Action |
|------|--------|
| Import bookmarks | Click **IMPORT** in the browser bar, or drop `bookmarks.html` into `.nexus-state/imports/` |
| Import passwords | Drop `passwords.csv` into `.nexus-state/imports/` — vault stays local |
| Default browser | Shift+click **IMPORT** to register Queen Browser as system default |
| Field import | Queen Browser sweeps host profiles into the field — labeled "Field import · host gecko" in import UI |

---

## Drop / Rise

Queen Browser shell buttons call the panel underlay surface API:

```bash
curl -s http://127.0.0.1:9477/api/field-underlay-surface | jq .
```

| Control | Effect |
|---------|--------|
| **Drop ⬇** | Field underlay sinks beneath host desktop |
| **Rise ⬆** | Field OS slice rises to foreground |

Handler: `lib/field-underlay-surface.py` · Shell: `Queen/world/queen-browser-shell.js`

---

## Launch

```bash
Queen/scripts/run-queen.sh
# Field Gecko native engine (when built):
Queen/field-gecko/bin/launch-field-gecko.sh
```

Defaults: `QUEEN_BROWSER_START` and `QUEEN_BROWSER_HOME` → `/field` on panel `:9477`.

→ **[Host Desktop](Host-Desktop)** · **[Underlay F9 Tristate](Underlay-F9-Tristate)**
