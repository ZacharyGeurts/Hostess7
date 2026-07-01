# Linux Installation

**v10.4.3** — Recommended path uses release tarball + `install-all.sh`.

→ **[Installers](Installers)** for full script reference.

---

## Requirements

- Linux with systemd
- `python3`, `curl`, `nftables`, `inotify-tools`
- Optional: `zenity` (Tristate fallback), `cmake` (ZNetwork build)

---

## Install from release

```bash
tar -xzf nexus-shield-10.4.3-source.tar.gz
cd nexus-shield-10.4.3
sudo ./install-all.sh
```

Installs to `/usr/local/lib/nexus-shield`, state in `/var/lib/nexus-shield`, service `nexus-genius.service`.

---

## Install from git clone

```bash
git clone https://github.com/ZacharyGeurts/NEXUS-Shield.git
cd NEXUS-Shield
chmod +x install-all.sh nexus.sh
sudo ./install-all.sh
```

Dev tree without full install:

```bash
export NEXUS_FIELD_STANDALONE=1
./nexus.sh
```

---

## Verify

```bash
nexus status
nexus verify
systemctl is-active nexus-genius.service
curl -s http://127.0.0.1:9477/api/status | jq .
```

---

## Uninstall

```bash
sudo systemctl stop nexus-genius.service
sudo systemctl disable nexus-genius.service
sudo rm -f /etc/systemd/system/nexus-genius.service
sudo rm -rf /usr/local/lib/nexus-shield
sudo rm -rf /var/lib/nexus-shield   # optional — removes trust/block memory
sudo systemctl daemon-reload
```

Keep `/var/lib/nexus-shield` if you plan to reinstall and preserve trust memory.

---

## Desktop entries

After install (via `genius_shield.sh` + os-assist):

- `/usr/share/applications/nexus-shield.desktop`
- `/usr/share/applications/nexus-tristate-installer.desktop`
- `~/.local/share/applications/` copies for install user