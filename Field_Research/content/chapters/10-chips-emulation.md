## Field-native silicon emulation

Compatibility layer 4 (**CHIPS / emu**) exposes retro cores behind gates — not as desktop shader toys, but as **FieldChip BSP** routed through Queen Webbrowser.

## Manifest and registry

`Queen/data/chips-g16-manifest.json` — hot paths:

- 6502, 68000, Z80, YM2612, …
- Built with `CHIPS_G16_ACCURATE=1` + g16 `field_opt`

`queen-game-room.json` platform registry:

- **Active:** NES, SNES, Genesis, SMS, Atari 2600
- **Scaffold:** C64, Apple II, Amiga, PS1, N64, …

`queen-chips.py` orchestrates; engine lives under `AMOURANTHRTX/Navigator/engine/CHIPS/`.

## Why CHIPS is layer 4, not layer 1

Research ordering:

1. Substrate must pin linux/KILROY first
2. Exec must know belt/runner posture
3. Program interop must wire toolchain
4. Web compat must cage legacy HTML
5. **Then** emulation — because emu **rides** exec posture and GPU fabric

Putting CHIPS at layer 1 inverted dependencies and broke gatekeeper assumptions.

## G16 accurate path

CHIPS compiles through Grok16 field_opt profile — same forge as native belt, different runner facet. Combinatorics `runner: emulator` selects this path.

## Queen browser only

`field-host-desktop-doctrine.json`: NEXUS host desktop — programs as windows, **Queen browser only** for web surface. CHIPS renders inside browser gates when `QUEEN_READY`.

## BSP rewrite note

Inventory shows CHIPS BSP rewrite planned — manifest scaffolds exist. Label scaffolds <span class="tag impl">Implemented</span> registry; not every core <span class="tag meta">Metaphor</span> "shippable game parity."

## Research conclusion

CHIPS is how **Grok's heart meets silicon memory** — childhood machines as field citizens, not orphans. Layer 4 honors that without skipping substrate or exec.

**Next:** Chapter 11 — NEXUS perimeter and diagnostic mode.