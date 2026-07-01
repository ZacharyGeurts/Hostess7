# Panel Guide

**g16 1.0** — Host desktop at `http://127.0.0.1:9477/field` · full C2 at `http://127.0.0.1:9477/command`. Click **?** on any control for plain-English help.

**Open:** `./nexus.sh` · desktop icon · auto-opens host desktop on boot.

→ **[Host Desktop](Host-Desktop)** for first-page apps + startbar

---

## Monitor

![Monitor](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/screenshots/panel-monitor.png)

Connection gatekeeper — 10-axis scoring per live TCP flow.

| Verdict | Meaning |
|---------|---------|
| USER_OK | Normal browsing / trusted process |
| EPHEMERAL | Short-lived traffic |
| SUSPICIOUS | Review, not auto-blocked |
| HARM_CANDIDATE | You decide — block or trust |

**Actions:** Trust forever · Stop this site · Inspect deep packet view.

---

## Training

**Hash:** `#training` · API: `/api/hostess7/training/bundle`

- Curriculum steps (one step per call — no hang)
- Track cards, evaluation graphs, runtime progress
- Self-interaction and IQ assess endpoints

---

## Settings

![Settings](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/screenshots/panel-settings.png)

Panel writes `settings.override` in state dir. Key toggles:

| Setting | Default | Notes |
|---------|---------|-------|
| `NEXUS_PANEL_AUTO_OPEN` | ON | Browser each boot |
| Paranoia auto-block | OFF | Log-first for consumers |
| Watchers | ON | Shadow, entropy, behavior |

→ **[Configuration](Configuration)**

---

## Logs

![Logs](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/screenshots/panel-logs.png)

Unified `nexus-alerts.log` + vigil tails. Refresh anytime.

---

## Other tabs (high level)

| Tab | Role |
|-----|------|
| Threats / map | Globe pins, host attack |
| Intel | Honorability, dossiers |
| DNS | Field DNS, admin portal |
| Library | Hostess7 field books |
| System | Shutdown guard, plugins |

---

## Keyboard

- `?` — tooltips
- `F9` — jump to Underlay sector (in Underlay F9 page)
- `/` — search in library