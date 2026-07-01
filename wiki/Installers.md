# Installers

Guide for **g16 1.0** — clone from GitHub or release tarball.

**Also:** [INSTALL-README.md](https://github.com/ZacharyGeurts/NEXUS-Shield/blob/main/INSTALL-README.md) in the repo.

---

## Release assets

**Recommended (g16 1.0 on main):**

```bash
git clone https://github.com/ZacharyGeurts/NEXUS-Shield.git
cd NEXUS-Shield
```

Release tarballs (when published): https://github.com/ZacharyGeurts/NEXUS-Shield/releases/tag/g16-1.0

| File | Use |
|------|-----|
| `nexus-shield-g16-1.0-source.tar.gz` | Full tree — **recommended** |
| `nexus-shield-g16-1.0-installers.tar.gz` | Scripts only |

---

## Full install

```bash
# or from tarball:
tar -xzf nexus-shield-g16-1.0-source.tar.gz
cd nexus-shield-g16-1.0
chmod +x install-all.sh genius_shield.sh nexus.sh nexus-install-gui.sh
sudo ./install-all.sh
```

**One admin approval** → copies to `/usr/local/lib/nexus-shield` → enables `nexus-genius.service` → first boot-impl → browser opens `/field`.

---

## Installer scripts

| Script | Role |
|--------|------|
| `install-all.sh` | **Main entry** — Linux full stack |
| `genius_shield.sh` | Deploy, systemd, firewall, desktop |
| `stealth_install.sh` | Wrapper → genius_shield |
| `nexus-install-gui.sh` | Opens Underlay F9 Tristate in browser |
| `nexus.sh` | Dev tree panel + browser |
| `scripts/nexus-boot-impl.sh` | Boot/reboot tech reload |
| `scripts/wire-stack.sh` | Wire SG stack siblings |

---

## After install

**Start menu:**
- **Underlay F9 — NEXUS Field** → `nexus.sh`
- **2026 Tristate Installer** → `nexus-install-gui.sh`

```bash
systemctl status nexus-genius.service
nexus status
curl -s http://127.0.0.1:9477/api/status | jq .
```

---

## Troubleshoot

| Problem | Fix |
|---------|-----|
| Panel down | `sudo systemctl restart nexus-genius.service` |
| No browser | `xdg-open http://127.0.0.1:9477/field` |
| Port busy | `NEXUS_THREAT_PANEL_PORT=9478 ./nexus.sh` |

Logs: `/var/lib/nexus-shield/panel-http.log`, `boot-impl.log`

→ **[Linux Installation](Linux-Installation)** · **[Boot Implementation](Boot-Implementation)**