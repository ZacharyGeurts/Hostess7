# NEXUS-Shield 10.4.0

Boot-impl reload, auto browser on start, Training tab, Tristate/Underlay F9 installer refresh.

## Highlights

- **Auto browser on start** — panel opens in the default browser every boot/reboot (`NEXUS_PANEL_AUTO_OPEN=1`, OS browser fallback when Queen RTX is absent)
- **Boot implementation** — `nexus-boot-impl.sh` reloads stack wire + sense meld on every startup; full impl on first install
- **2026 Tristate Installer** — `nexus-install-gui.sh` opens **Underlay F9** (`/underlay-f9?sector=underlay`); desktop entries updated
- **Training tab** — integrated in NEXUS panel (`#training`); curriculum step, graphs, runtime APIs
- **Installers shipped** — `install-all.sh`, `genius_shield.sh`, `nexus-install-gui.sh`, `scripts/nexus-boot-impl.sh`

## Install

```bash
tar -xzf nexus-shield-10.4.0-source.tar.gz
cd nexus-shield-10.4.0
sudo ./install-all.sh
```

Or field dev tree:

```bash
./nexus.sh
```

## URLs

| Surface | URL |
|---------|-----|
| Field panel | http://127.0.0.1:9477/field |
| Underlay F9 / Tristate | http://127.0.0.1:9477/underlay-f9?sector=underlay |
| Training tab | http://127.0.0.1:9477/field#training |

## Release assets

- `nexus-shield-10.4.0-source.tar.gz` — full NewLatest tree (excludes stack symlinks + caches)
- `nexus-shield-10.4.0-installers.tar.gz` — installer scripts only (`install-all.sh`, `genius_shield.sh`, `nexus-install-gui.sh`, `scripts/`)