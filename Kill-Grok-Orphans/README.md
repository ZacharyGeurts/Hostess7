# Kill Grok Orphans

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/ZacharyGeurts/Kill-Grok-Orphans)](https://github.com/ZacharyGeurts/Kill-Grok-Orphans/releases)

**Always-on watchdog that kills reparented Grok orphan processes** — the runaway `grok-firmware-audit.sh` and `Grok16/bin/awk` bash wrappers that leak from boot-simulate and pile up at 30% CPU each.

Built with [Grok16](https://github.com/ZacharyGeurts/Grok16) (`g16`) on Linux — **1.1.0** fast scan, 12 leak signatures, multi-platform release. Python watchdog ships for macOS and Windows.

## What it kills

| Pattern | Why |
|---------|-----|
| `grok-firmware-audit.sh` | Orphaned firmware audit from boot-simulate |
| `Grok16/bin/awk` | Runaway awk bash shim children |
| `Grok16/bin/` + shell | Orphaned Grok16 bin wrappers |
| `boot-simulate.sh` | Orphaned boot-simulate subprocess |
| `dump_bash_state` | Orphaned Grok agent shell |
| `.grok/sessions` | Orphaned Grok CLI session bash |
| `ammoos-release.sh` / `pack-ammoos-release.sh` | Stuck AmmoOS publish orphans |

An orphan is a process whose parent is **init** (Linux/macOS ppid=1) or **System** (Windows ppid=0/4) — reparented with no live supervisor.

## Quick install

### Linux (systemd, requires root)

```bash
curl -fsSL https://github.com/ZacharyGeurts/Kill-Grok-Orphans/releases/latest/download/kgo-1.1.0-linux-gnu-x86_64.tar.gz | tar -xz
cd Kill-Grok-Orphans  # or extracted folder
sudo packaging/linux/install.sh
```

### macOS (launchd, requires admin)

```bash
git clone https://github.com/ZacharyGeurts/Kill-Grok-Orphans.git
cd Kill-Grok-Orphans
sudo packaging/macos/install.sh
```

### Windows (Scheduled Task, requires Administrator)

```powershell
git clone https://github.com/ZacharyGeurts/Kill-Grok-Orphans.git
cd Kill-Grok-Orphans
.\packaging\windows\Install-KGO.ps1
```

## Auth on each OS

Killing reparented orphans requires **elevated privileges** on every platform:

| OS | Auth mechanism | Install command |
|----|----------------|-----------------|
| Linux | `sudo` / systemd as root | `sudo packaging/linux/install.sh` |
| macOS | `sudo` / launchd daemon as root | `sudo packaging/macos/install.sh` |
| Windows | Administrator + SYSTEM task | Run PowerShell as Admin |

One-shot scan without installing the daemon:

```bash
sudo kgo --once --dry-run          # Linux native
sudo kgo-watchdog --once --dry-run # macOS / fallback
```

## Build from source (Grok16)

```bash
export GROK16_ROOT=/path/to/Grok16
make
sudo make install
```

Compiler: `g16 -std=gnu17 -O3` (Grok16 5.0.0). All platforms: `./scripts/build-all-platforms.sh`

## Configuration

`/etc/kgo/kgo-patterns.json` — edit patterns, scan interval, kill grace period.

## Docs

- [Wiki (GitHub Pages)](https://zacharygeurts.github.io/Kill-Grok-Orphans/wiki/)
- [Wiki source](https://github.com/ZacharyGeurts/Kill-Grok-Orphans/tree/main/wiki)
- [Site](https://zacharygeurts.github.io/Kill-Grok-Orphans/)

## License

MIT — Zachary Robert Geurts