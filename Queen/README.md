# Queen Browser

[![AmmoOS](https://img.shields.io/badge/pairs-AmmoOS_2.0.0--beta3-22c55e)](https://github.com/ZacharyGeurts/AmmoOS)
[![Hub](https://img.shields.io/badge/hub-zacharygeurts.github.io/Queen-3ecf8e)](https://zacharygeurts.github.io/Queen/)

**Secured browser shell — AmmoOS lives inside the Start tab.**

Stack: [STACK-NAV](https://github.com/ZacharyGeurts/AmmoOS/blob/main/STACK-NAV.md) · [Queen hub repo](https://github.com/ZacharyGeurts/Queen) · [Profile stack](https://zacharygeurts.github.io/ZacharyGeurts/stack.html)

<p align="center"><img src="../panel/assets/ammoos-field.png" alt="Queen taskbar icon" width="96" height="96" /></p>

Sovereign browser stack for **AmmoOS**: full web surface, every egress gated, codecs in-tree.

## Vendor clones

| Path | Upstream | Role |
|------|----------|------|
| `vendor/ffmpeg` | [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) | MP4/H.264/AAC decode — mandatory codec path |
| `vendor/ladybird` | [LadybirdBrowser/ladybird](https://github.com/LadybirdBrowser/ladybird) | Independent browser engine (millennium ship) |
| `vendor/servo` | [servo/servo](https://github.com/servo/servo) | Rust layout/engine track |

```bash
./clone-all.sh          # shallow clones (re-run safe)
./build.sh              # Queen shell + shaders + ffmpeg static (optional stages)
```

## Queen shell (`engine/`)

- **2026 GUI** — aqua/rose field chrome, compshader boot (`shaders/compute/QueenBoot.comp`)
- **AMOURANTHRTX RTX** — loads `QueenBoot.spv` via same FieldSocket push-constant layout as AmmoOS panel
- **Plugins** — `plugins/builtin-manifest.json` (all built-in; external plugins supported)
- **AmmoOS field** — Truth DNS, gatekeeper, honorability via `nexus/` symlinks + env (legacy paths retained)

## Build stages

```bash
# 1 — Queen browser shell (SDL3 + optional Vulkan compshader)
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)

# 2 — FFmpeg (static libs for Queen media path)
./build-ffmpeg.sh

# 3 — Ladybird (full engine — long build, needs deps)
./build-ladybird.sh

# 4 — Servo (Rust engine track)
./build-servo.sh
```

## Run — one exe, RTX goodies included

```bash
export NEXUS_INSTALL_ROOT="$(cd .. && pwd)"
./build.sh
./build/rtx/bin/Linux/queen-browser --queen --extended-field
```

No external host-browser UI — operators see **Queen Browser** only. AmmoOS panel loads **inside** the RTX engine (`FieldWebPanel` + `QueenBoot.comp` compshader boot). Threat panel API auto-starts on `:9477` if needed.

Binary names: `queen-browser`, `queen-field-engine`, `field-queen`.

**User guide:** `http://127.0.0.1:9481/world/queen-browser-guide.html`