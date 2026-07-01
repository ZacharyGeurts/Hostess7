# Hostess7 1.0.7h — RTX Executables (multi-platform)

**Tag:** `v1.0.7h` · **Repo:** [ZacharyGeurts/Hostess7](https://github.com/ZacharyGeurts/Hostess7)

Native binaries and bootstrap kits for **RTX-capable systems** (NVIDIA RTX, Intel Arc LE, AMD) via Queen FieldGpuDispatch + SPIR-V. Build/pack does **not** require an RTX GPU on the build machine (`G16_RTX_GATE_FORCE=1`).

## Assets

| Platform | File | Mode |
|----------|------|------|
| Linux x86_64 | `hostess7-1.0.7h-rtx-linux-gnu-x86_64.tar.gz` | native (queen-browser when built) |
| Linux ARM64 | `hostess7-1.0.7h-rtx-linux-gnu-aarch64.tar.gz` | bootstrap |
| Windows x86_64 | `hostess7-1.0.7h-rtx-windows-x86_64.zip` | bootstrap / native .exe when built |
| macOS Apple Silicon | `hostess7-1.0.7h-rtx-darwin-aarch64.tar.gz` | bootstrap |
| macOS Intel | `hostess7-1.0.7h-rtx-darwin-x86_64.tar.gz` | bootstrap |
| FreeBSD amd64 | `hostess7-1.0.7h-rtx-freebsd-amd64.tar.gz` | bootstrap |
| Index | `hostess7-1.0.7h-rtx-platforms.json` | platform manifest + checksums |

Each archive includes `.sha256` sidecar checksums.

## Quick start (Linux x86_64)

```bash
tar -xzf hostess7-1.0.7h-rtx-linux-gnu-x86_64.tar.gz
cd hostess7-1.0.7h-rtx-linux-gnu-x86_64
./bin/queen-browser --queen
# → http://127.0.0.1:9481/world/browser.html
```

## Build on target (bootstrap platforms)

```bash
./bootstrap/build-rtx.sh
# or full stack:
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7 && ./Hostess7.sh boot
./Hostess7.sh queen-field-build rtx
```

Windows: use WSL2 with the Linux x86_64 tarball, or `bootstrap/build-rtx.ps1`.

## Pack / publish

```bash
BUILD_RTX=0 ./Hostess7.sh rtx-release pack   # pack existing binaries only
PUSH_RTX=1 ./Hostess7.sh rtx-release push    # upload to v1.0.7h
```

## Also in this release

- **GitHub brain** (isolated mirror): https://zacharygeurts.github.io/Hostess7/
- **Sovereign stack:** `./Hostess7.sh boot` on loopback