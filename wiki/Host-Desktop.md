# Host Desktop

**g16 1.0** — First page at `http://127.0.0.1:9477/field`. Mirror incumbent OS apps with field startbar overlay.

---

## What you see

- **All programs** from host `.desktop` entries — icons and names the operator already knows.
- **Field apps** always present — NEXUS Field Command (`/command`), Underlay F9, Queen Browser.
- **Startbar** — bottom overlay: taskbar, clock, long-press (480 ms), right-click context menu.
- **OS theme** — prefers guest GTK/icon theme when detectable.

When embedded in Queen Browser Start tab, app launches open in Queen tabs instead of a separate window.

---

## API

```bash
curl -s http://127.0.0.1:9477/api/field-host-desktop | jq .
curl -s http://127.0.0.1:9477/api/field-host-desktop/icon/<token> -o icon.png
```

| Route | Method | Role |
|-------|--------|------|
| `/api/field-host-desktop` | GET | App list, theme, startbar config |
| `/api/field-host-desktop/icon/<token>` | GET | Resolved icon bytes |

Handler: `lib/field-host-desktop.py` · Doctrine: `data/field-host-desktop-doctrine.json`

---

## Routing

| Path | File |
|------|------|
| `/field` | `panel/field-desktop.html` |
| `/command` | `panel/threat-panel.html` |

Legacy `/field` used to open the threat panel directly; **g16** routes `/field` → host desktop and `/command` → full C2.

→ **[Panel Guide](Panel-Guide)** for command deck tabs