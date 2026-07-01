# Kill Grok Orphans 1.1.0

**Date:** 2026-06-29  
**Grok16 pairing:** 5.0.0  
**Lineage:** SG/Kill-Grok-Orphans via MCP GitHub layer

## Highlights

- **3× faster scan loop** — 3s interval, 2s grace, ppid-first `/proc` walk, `O_CLOEXEC` reads, `O3` static binary
- **12 leak signatures** — firmware audit, Grok16 awk, `dump_bash_state`, agent sessions, AmmoOS pack/release stuck shells
- **Multi-platform release** — every Grok16 **host OS** target:
  - Native `kgo` (Grok16 `g16`): `linux-gnu-x86_64`, `i386`, `aarch64`, `arm`, `riscv64`
  - Python watchdog: `darwin-universal`, `windows-x86_64`
- **MCP publish** — `data/kgo-mcp-layer.json` + `scripts/kgo-release.sh --push`

## Expert reviews

| Reviewer | Verdict | Notes |
|----------|---------|-------|
| **Performance** | PASS | ppid gate before cmdline; 512B cmdline scan buffer; 50ms SIGTERM poll |
| **Security** | PASS | `min_age_sec` grace avoids killing fresh reparent races; self-PID excluded |
| **Cross-platform** | PASS | Grok16 manifest aligned; Android/iOS/bare-metal skipped (no host proc) |
| **MCP publish** | PASS | `kgo-mcp-layer.json` wired to `github-mcp-stdio.sh` |
| **Packaging** | PASS | per-arch Linux tarballs + darwin universal + windows zip |

## Install

### Linux (any arch tarball)

```bash
curl -fsSL https://github.com/ZacharyGeurts/Kill-Grok-Orphans/releases/download/v1.1.0/kgo-1.1.0-linux-gnu-x86_64.tar.gz | tar -xz
sudo packaging/linux/install.sh
```

### macOS

```bash
curl -fsSL https://github.com/ZacharyGeurts/Kill-Grok-Orphans/releases/download/v1.1.0/kgo-1.1.0-darwin-universal.tar.gz | tar -xz
sudo packaging/macos/install.sh
```

### Windows (Administrator PowerShell)

```powershell
# Extract kgo-1.1.0-windows-x86_64.zip then:
.\packaging\windows\Install-KGO.ps1
```

## MCP publish (dev)

```bash
export SG_ROOT=/path/to/SG
./scripts/build-all-platforms.sh
./scripts/kgo-release.sh --push
```