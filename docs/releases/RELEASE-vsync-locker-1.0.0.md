# VSYNC-Locker 1.0.0

Sovereign display timing protector — [ZacharyGeurts/VSYNC-Locker](https://github.com/ZacharyGeurts/VSYNC-Locker).

Also integrates with AmmoOS **2.0.0-beta5** and Grok16 **5.2.0** when installed in a full field stack.

## What it does

- Locks VSYNC/vblank cadence for the field stack
- Baselines sovereign pointers, keyboards, and controls
- Unpredictable anti-perfect-sync drift (host-bound entropy)
- Background guard — double-click once, stays on patrol
- KILL on trespass (rogue VSYNC ops, foreign input, allowlist spoof)

## Platforms (all packages in this release)

| Platform | Asset |
|----------|--------|
| Linux x86_64 | `vsync-locker-1.0.0-linux-gnu-x86_64.tar.gz` |
| Linux aarch64 | `vsync-locker-1.0.0-linux-gnu-aarch64.tar.gz` |
| Linux arm | `vsync-locker-1.0.0-linux-gnu-arm.tar.gz` |
| Linux riscv64 | `vsync-locker-1.0.0-linux-gnu-riscv64.tar.gz` |
| Linux i386 | `vsync-locker-1.0.0-linux-gnu-i386.tar.gz` |
| macOS (Apple Silicon) | `vsync-locker-1.0.0-darwin-aarch64.tar.gz` |
| macOS (Intel) | `vsync-locker-1.0.0-darwin-x86_64.tar.gz` |
| Windows x86_64 | `vsync-locker-1.0.0-windows-x86_64.zip` |
| FreeBSD amd64 | `vsync-locker-1.0.0-freebsd-amd64.tar.gz` |
| Android aarch64 (Termux) | `vsync-locker-1.0.0-android-aarch64.tar.gz` |

Linux builds include a **Grok16-compiled** `bin/vsync-launch` native stub where the toolchain is available.

## Quick install (Linux)

```bash
tar -xzf vsync-locker-1.0.0-linux-gnu-x86_64.tar.gz
cd vsync-locker-1.0.0-linux-gnu-x86_64  # extracted folder name = tarball contents
sudo packaging/vsync-locker/linux/install.sh
```

Or inside a full AmmoOS tree:

```bash
python3 lib/field-vsync-locker.py install-desktop
python3 lib/field-vsync-locker.py launch
```

## Release-safe

Open-source hardened — security from host-bound secrets and integrity seals, not obscurity.