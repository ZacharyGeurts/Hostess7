# NEXUS-Shield 10.4.1

Patch release (+0.0.1) — panel layout, launcher consolidation, `/field` routing.

## Highlights

- **Field Clarity integrated** — inspector moved from floating right overlay into **System → Settings** (collapsible)
- **Command intel folded** — IQ / field intel / map behind collapsible **Assessments** section
- **Single launcher** — `nexus.sh` only; thin wrappers for legacy entry points
- **Single installer** — `install-all.sh`; `stealth_install.sh` wraps it
- **`/field` routing** — main C2 panel (`threat-panel.html`), not Underlay F9
- **Queen Browser** — Field Gecko engine profile (real browser shell, field security gates)
- **Desktop icon** — `nexus-field.png` taskbar / start menu entry

## Install

```bash
tar -xzf nexus-shield-10.4.1-source.tar.gz
cd nexus-shield-10.4.1
sudo ./install-all.sh
```

Or from dev tree:

```bash
./nexus.sh
```

## URLs

| Surface | URL |
|---------|-----|
| Field panel | http://127.0.0.1:9477/field |
| Field clarity | http://127.0.0.1:9477/field#system/settings |
| Underlay F9 | http://127.0.0.1:9477/underlay-f9?sector=underlay |

## Release assets

- `nexus-shield-10.4.1-source.tar.gz` — full tree
- `nexus-shield-10.4.1-installers.tar.gz` — installer scripts only