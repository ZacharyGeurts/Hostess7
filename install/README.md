# NEXUS-Shield Install Payload

This folder ships **polkit policy**, **platform install scripts**, and rules consumed by `install-all.sh` / `genius_shield.sh`.

**Full installer guide:** [INSTALL-README.md](../INSTALL-README.md) (repo root)

**Quick start:**
```bash
cd ..   # repo / tarball root
sudo ./install-all.sh
```

| Path | Role |
|------|------|
| `install/polkit/` | Field polkit actions + rules |
| `install/linux/` | (via parent scripts) systemd deploy |
| `install/windows/` | Portable Windows installer |
| `install/macos/` | Portable macOS installer |

Live manual: https://zacharygeurts.github.io/NEXUS-Shield/getting-started.html