# NEXUS-Shield Installers — v10.4.1

Installer guide for release tarballs and in-tree scripts. For architecture and API I/O see the [Field I/O manual](https://zacharygeurts.github.io/NEXUS-Shield/io.html).

---

## Release assets

| File | Size | Contents |
|------|------|----------|
| `nexus-shield-10.4.1-source.tar.gz` | ~96 MB | Full NEXUS tree (panel, lib, Hostess7, Queen, scripts) |
| `nexus-shield-10.4.1-installers.tar.gz` | ~14 KB | Installer scripts only |

Download: https://github.com/ZacharyGeurts/NEXUS-Shield/releases/tag/v10.4.1

---

## Quick install (recommended)

```bash
tar -xzf nexus-shield-10.4.1-source.tar.gz
cd nexus-shield-10.4.1
chmod +x install-all.sh genius_shield.sh nexus.sh nexus-install-gui.sh
sudo ./install-all.sh
```

**What happens:**
1. One OS admin approval (polkit or sudo)
2. Files copy to `/usr/local/lib/nexus-shield`
3. `nexus-genius.service` enabled and started
4. First-install boot-impl (wire, migrate, meld)
5. Browser opens `http://127.0.0.1:9477/field`

---

## Installer scripts

| Script | Role |
|--------|------|
| `install-all.sh` | **Main entry** — Linux full stack install |
| `genius_shield.sh` | Core deploy: copy tree, systemd, firewall, desktop |
| `stealth_install.sh` | Alias wrapper → `genius_shield.sh` |
| `nexus-install-gui.sh` | Opens **Underlay F9** Tristate installer in browser |
| `nexus.sh` | Field dev start — panel + browser + tray |
| `scripts/nexus-boot-impl.sh` | Boot/reboot tech reload (systemd ExecStartPre) |
| `scripts/wire-stack.sh` | Symlink SG stack siblings into tree |
| `scripts/migrate-nexus-state.sh` | Move repo `.nexus-state` → runtime dir |

### Installers-only tarball

If you already have a NEXUS tree and only need fresh installer scripts:

```bash
tar -xzf nexus-shield-10.4.1-installers.tar.gz
cd nexus-shield-10.4.1-installers
# Copy scripts into your existing tree, then:
sudo ./install-all.sh
```

---

## After install

| Surface | URL |
|---------|-----|
| Field panel | http://127.0.0.1:9477/field |
| Tristate / Underlay F9 | http://127.0.0.1:9477/underlay-f9?sector=underlay |
| Training tab | http://127.0.0.1:9477/field#training |

**Start menu:**
- **Underlay F9 — NEXUS Field** → `./nexus.sh`
- **2026 Tristate Installer** → `nexus-install-gui.sh`

**Service:**
```bash
systemctl status nexus-genius.service
journalctl -u nexus-genius.service -f
```

---

## Boot behavior

Every reboot:
1. `ExecStartPre` runs `scripts/nexus-boot-impl.sh` (refresh: re-wire, paths, meld)
2. `nexus-daemon.sh` starts watchers + panel
3. Browser opens once per boot (`panel-launched.boot` marker)

First install additionally: state migrate, manifest sign, `first-boot.complete` marker.

Force full re-impl:
```bash
sudo rm /var/lib/nexus-shield/first-boot.complete
sudo systemctl restart nexus-genius.service
```

---

## Environment

| Variable | Default | Notes |
|----------|---------|-------|
| `NEXUS_INSTALL_ROOT` | `/usr/local/lib/nexus-shield` | Installed path |
| `NEXUS_STATE_DIR` | `/var/lib/nexus-shield` | Runtime state |
| `NEXUS_THREAT_PANEL_PORT` | `9477` | Panel HTTP |
| `NEXUS_PANEL_AUTO_OPEN` | `1` | Browser on boot |
| `SG_ROOT` | install root | Stack path resolution |

Dev checkout (no sudo):
```bash
export NEXUS_FIELD_STANDALONE=1
./nexus.sh
# state → .nexus-state/ in tree
```

---

## Verify & troubleshoot

```bash
nexus status          # health + panel URL
nexus verify          # MANIFEST integrity
curl -s http://127.0.0.1:9477/api/status | jq .

# Panel log
tail -f /var/lib/nexus-shield/panel-http.log

# Boot impl log
cat /var/lib/nexus-shield/boot-impl.log
cat /var/lib/nexus-shield/boot-impl.last
```

| Problem | Fix |
|---------|-----|
| Panel not up | `sudo systemctl restart nexus-genius.service` |
| Browser didn't open | `./nexus.sh` or `xdg-open http://127.0.0.1:9477/field` |
| Port 9477 busy | `NEXUS_THREAT_PANEL_PORT=9478 ./nexus.sh` |
| Permission denied on state | `sudo usermod -aG nexus $USER` then log out/in |

---

## Requirements

- Linux desktop (systemd, nftables)
- `python3`, `curl`, `inotify-tools`, `nftables`
- Optional: `zenity` (Tristate fallback wizard), `cmake` (ZNetwork build)

---

## License

**NEXUS-Shield — MIT** (Zachary Geurts, 2026)

AMOURANTHRTX field engine is **GPL v3 or commercial** — not bundled as MIT-free.