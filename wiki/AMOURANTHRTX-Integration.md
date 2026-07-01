# AMOURANTHRTX Integration

**Repo:** [ZacharyGeurts/AMOURANTHRTX](https://github.com/ZacharyGeurts/AMOURANTHRTX)  
**Canonical:** `NewLatest/AMOURANTHRTX` (symlink via `wire-stack.sh`)

Vulkan field die — RTX-DOS, games, `x86.comp` canvas. GPL v3 or commercial (separate from NEXUS MIT).

## Stack wiring

| Piece | Path |
|-------|------|
| Engine tree | `NewLatest/AMOURANTHRTX` |
| Queen RTX build | `Queen/scripts/g16-build.sh` → `queen-browser` |
| Native build | `AMOURANTHRTX/kilroy.sh` |
| SPIR-V pack | `make -C AMOURANTHRTX/Navigator/shaders` |
| Integrate | `scripts/integrate-amouranthrtx.sh` |
| Vulkan doctrine | `data/vulkan-os-doctrine.json` |

## Double-click `.spv` / `.comp`

```bash
./scripts/integrate-amouranthrtx.sh
# Registers MIME + desktop handlers under ~/.local/share/applications/
```

- **`.comp`** — `glslc` → SPIR-V → staged under `assets/shaders/compute/` → launches Field Die
- **`.spv`** — staged and launched with `AMOURANTHRTX_CANVAS=<basename>`

Manual:

```bash
./scripts/amouranthrtx-open.sh path/to/demo.comp
./scripts/amouranthrtx-open.sh path/to/demo.spv
```

## Build engine

```bash
./scripts/integrate-amouranthrtx.sh --build
# or: Queen/scripts/g16-build.sh
# or: AMOURANTHRTX/kilroy.sh run
```

## NEXUS corroboration

- **Whitelist:** `config/device-whitelist.conf`
- **Module:** `lib/device-whitelist.sh`

NEXUS-Shield remains MIT. Field Die runtime ships from AMOURANTHRTX repo.

→ **[Licensing](Licensing)**