#!/usr/bin/env python3
"""Field Chips Catalog — library book: Ironclad truth, universal chipset, every die by kind."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-chips-catalog-doctrine.json"
CURATION = INSTALL / "data" / "field-chips-catalog-curation.json"
COMPANION_SEED = INSTALL / "data" / "field-cpu-companion-seed.json"
COMBINATRONIC_CATALOG = INSTALL / "data" / "field-combinatronic-chip-catalog.json"
IRONCLAD_PY = INSTALL / "lib" / "field-ironclad-chips-combinatorics.py"
IRONCLAD_JSON = STATE / "field-ironclad-chips-combinatorics.json"
PANEL = STATE / "field-chips-catalog-panel.json"
CATALOG = STATE / "field-chips-catalog.json"

CHAPTERS: tuple[dict[str, Any], ...] = (
    {"page": 1, "id": "ironclad_truth", "title": "Ironclad Truth", "layout": "index"},
    {"page": 2, "id": "universal_chipset", "title": "Universal Chipset", "layout": "featured",
     "filter": {"source": "cpu_companion", "family": "cpu_companion_universal"}},
    {"page": 3, "id": "host_cpu", "title": "Host CPUs", "layout": "grid", "filter": {"kind": "host_cpu"}},
    {"page": 4, "id": "guest_cpu", "title": "Guest CPUs", "layout": "grid", "filter": {"kind": "guest_cpu"}},
    {"page": 5, "id": "soc", "title": "SoCs", "layout": "grid", "filter": {"kind": "soc"}},
    {"page": 6, "id": "northbridge", "title": "Northbridges", "layout": "grid", "filter": {"kind": "northbridge"}},
    {"page": 7, "id": "southbridge", "title": "Southbridges", "layout": "grid", "filter": {"kind": "southbridge"}},
    {"page": 8, "id": "chipset", "title": "Chipsets", "layout": "grid", "filter": {"kind": "chipset"}},
    {"page": 9, "id": "super_io", "title": "Super I/O", "layout": "grid", "filter": {"kind": "super_io"}},
    {"page": 10, "id": "mame_device", "title": "MAME Devices", "layout": "grid", "filter": {"kind": "mame_device"}},
    {"page": 11, "id": "video", "title": "Video", "layout": "grid", "filter": {"kind": "video"}},
    {"page": 12, "id": "sound", "title": "Sound", "layout": "grid", "filter": {"kind": "sound"}},
    {"page": 13, "id": "gpu", "title": "GPUs", "layout": "grid", "filter": {"kind": "gpu"}},
    {"page": 14, "id": "memory", "title": "Memory", "layout": "grid", "filter": {"kind": "memory"}},
    {"page": 15, "id": "logic", "title": "Logic", "layout": "grid", "filter": {"kind": "logic"}},
    {"page": 16, "id": "network", "title": "Network", "layout": "grid", "filter": {"kind": "network"}},
    {"page": 17, "id": "dsp", "title": "DSP", "layout": "grid", "filter": {"kind": "dsp"}},
    {"page": 18, "id": "fpga", "title": "FPGA", "layout": "grid", "filter": {"kind": "fpga"}},
    {"page": 19, "id": "analog", "title": "Analog", "layout": "grid", "filter": {"kind": "analog"}},
    {"page": 20, "id": "fab", "title": "Fab", "layout": "grid", "filter": {"kind": "fab"}},
    {"page": 21, "id": "chips_hot", "title": "CHIPS Hot Paths", "layout": "grid", "filter": {"kind": "chips_hot"}},
    {"page": 22, "id": "isa_platform", "title": "ISA Platforms", "layout": "grid", "filter": {"kind": "isa_platform"}},
    {"page": 23, "id": "coprocessor", "title": "Coprocessors", "layout": "grid", "filter": {"kind": "coprocessor"}},
    {"page": 24, "id": "arcade_asic", "title": "Arcade ASICs", "layout": "grid", "filter": {"kind": "arcade_asic"}},
    {"page": 25, "id": "glue", "title": "Glue Logic", "layout": "grid", "filter": {"kind": "glue"}},
    {"page": 26, "id": "pio", "title": "PIO", "layout": "grid", "filter": {"kind": "pio"}},
    {"page": 27, "id": "fdc", "title": "FDC", "layout": "grid", "filter": {"kind": "fdc"}},
    {"page": 28, "id": "mmu", "title": "MMU", "layout": "grid", "filter": {"kind": "mmu"}},
    {"page": 29, "id": "console_snes", "title": "SNES Platform Stack", "layout": "grid",
     "filter": {"platform_stack": "console_snes"}},
    {"page": 30, "id": "console_ps1", "title": "PlayStation Platform Stack", "layout": "grid",
     "filter": {"platform_stack": "console_ps1"}},
    {"page": 31, "id": "zhaoxin", "title": "Zhaoxin / VIA KX Stack", "layout": "grid",
     "filter": {"platform_stack": "pc_zhaoxin_kx"}},
    {"page": 32, "id": "loongson", "title": "Loongson Platform Stack", "layout": "grid",
     "filter": {"platform_stack": "pc_loongson"}},
    {"page": 33, "id": "elbrus", "title": "Elbrus MCST Stack", "layout": "grid",
     "filter": {"platform_stack": "pc_elbrus"}},
    {"page": 34, "id": "arm_soc", "title": "ARM SoC Stack", "layout": "grid",
     "filter": {"platform_stack": "arm_soc_template"}},
)

COMPANION_STACK_CHAPTERS: frozenset[str] = frozenset({
    "console_snes", "console_ps1", "zhaoxin", "loongson", "elbrus", "arm_soc",
})

COMPANION_STACK_BY_PLATFORM: dict[str, tuple[int, str]] = {
    "console_snes": (29, "console_snes"),
    "console_ps1": (30, "console_ps1"),
    "pc_zhaoxin_kx": (31, "zhaoxin"),
    "pc_loongson": (32, "loongson"),
    "pc_elbrus": (33, "elbrus"),
    "arm_soc_template": (34, "arm_soc"),
}

SEARCH_BLOB_FIELDS: tuple[str, ...] = (
    "id", "label", "vendor", "kind", "family", "source", "era", "status",
    "note", "curator_note", "socket", "package", "country", "imprint",
    "companion_role", "platform_stack", "mame_device", "chapter",
)

THUMB_PATTERN = "/world/assets/combinatronic/chips/thumbs/{chip_id}.png"
DETAIL_PATTERN = "/world/assets/combinatronic/chips/detail/{chip_id}.png"
CLOSEUP_PATTERN = "/world/assets/combinatronic/chips/{chip_id}.png"
THUMB_FALLBACK = "/world/assets/combinatronic/chips/generic_die.png"
THUMBS_ASSETS = INSTALL / "Queen" / "world" / "assets" / "combinatronic" / "chips" / "thumbs"
DETAIL_ASSETS = INSTALL / "Queen" / "world" / "assets" / "combinatronic" / "chips" / "detail"
DEWEY_SHELF_DIR = INSTALL / "library" / "dewey" / "621-computer-engineering" / "chips-catalog"
DEWEY_BOOK_DIR = DEWEY_SHELF_DIR / "ironclad-chips-catalog"
DEWEY_PAGES_DIR = DEWEY_BOOK_DIR / "pages"
DEWEY_BOOK_COVER = "/world/assets/combinatronic/chips/cyrix_6x86.png"
DEWEY_BOOK_THUMB = "/panel/assets/queen-prog-chips.png"
IRONCLAD_PAGE_COVER = "/panel/assets/ironclad/ironclad-01-bounds.jpg"
IRONCLAD_PAGE_THUMB = "/panel/assets/ironclad/ironclad-03-knowledge-source.jpg"
COMBINATRONIC_ASSETS = INSTALL / "Queen" / "world" / "assets" / "combinatronic" / "chips"

PAGE_IRONCLAD_BODY = """# Ironclad — Truth Plate & Combinatorics Root

Every die in this catalog hangs from a single sealed root: **Ironclad**, the melded plate of truth (`ironclad:chips:3`). Sealed **2026-06-27** under sovereign clock, this plate replaced the battery — combinatorics is now the only admission gate. No chip enters without a combinatorics leaf, a hard path percent from `field-chip-path-predict.py`, and a receipt stamped back to the truth plate.

## Doctrine

Ironclad declares the epistemic floor and ceiling for all field knowledge. Chips are not a loose parts bin — they are **leaves** on the `ironclad_chips` facet, each stamped `chip:<family>:<slug>` and sorted by `composite_bsp` through `field-best-sort.py`. Truth percent from `ironclad-immediate` grounds every ingest; `field-sanity.py` must pass before publish. Manufacturing eras span **1971** (Intel 4004) through **2026** (Raptor Lake, AM5, LoongArch 3A, KX-7000) — but era is metadata, not permission. Permission flows only from Ironclad.

The doctrine file (`data/field-chips-catalog-doctrine.json`) mandates library fields: `mfg_date_start`, `mfg_date_end`, `discontinued`, `vendor`, `platform_stack`, `always_with`, `companion_role`. Every Dewey page in this book carries `chip_ids[]`, cover/thumb refs, and body prose with mfg-era notes.

## Combinatorics root

The combinatorics tree fans out from Ironclad into families: host CPUs, guest dies, north/south bridges, Super I/O, SoCs, GPUs, MAME devices, world-national dies, console platform stacks, and the full semiconductor atlas. Sources merge from seed, Queen game room, CPU library, ISA platforms, libretro cores, MAME cache, combinatronic catalog, world seeds (`field-world-chips-seed.json`), and CPU companion stacks (`field-cpu-companion-seed.json`) — then dedupe by id. `_cpu_companion_chips` emits universal dies plus every `platform_stacks` companion row; `_enrich_always_with_companions` stamps `always_with` on matching host and guest CPUs.

## Plate stack

Above Ironclad sits the chips plate stack (`field-chips-plate-stack.py`):

1. **Iron** — truth plate (`ironclad:chips:3`); facet root, citation seal.
2. **Steel** — combinatorics merge layer; dedupe, normalize, count by kind.
3. **Brass** — path prediction; hard percent per active system from `field-chip-path-predict-seed.json`.
4. **Glass** — combinatronic imprint; thumb/detail/closeup asset resolution.

Sovereign time only — no wall-clock drift in `updated` stamps. Code path prediction assigns every leaf a **hard percent**; the sort is THE sort — one best ever, no guesswork without receipts.

## Reading this book

- **Page 1** (here): Ironclad root, doctrine, plate stack, combinatorics admission.
- **Page 2**: Universal chipset — north bridge, south bridge, Super I/O, PIC/DMA/RTC companions stamped free on every host CPU (8088 → Core i + PCH).
- **Pages 3–30**: One page per major chip kind — host CPU, guest CPU, northbridge, SoC, MAME device, world CHIPS, and the full kind atlas.
- **Pages 31+**: Platform stacks — Genesis, SNES, PS1, Saturn, N64, Zhaoxin/VIA, Loongson, Elbrus, ARM SoC PMIC.

*Citation: ironclad:chips:3 · facet ironclad_chips · module field-ironclad-chips-combinatorics.py · built 2026-06-27*
"""

PAGE_UNIVERSAL_CHIPSET_BODY = """# Universal Chipset — North Bridge, South Bridge, Super I/O

A host CPU never ships alone. The **universal chipset** layer stamps platform companions for free: north bridge (memory controller hub), south bridge (I/O controller hub), Super I/O (floppy, serial, parallel, keyboard), and the AT-era glue — PIC, DMA, PIT, RTC — that every PC-class stack still carries in spirit. This page is the companion atlas for PC and retro glue; platform-specific console and domestic stacks have dedicated pages from 31 onward.

## Manufacturing eras — PC north/south timeline

| Era | North bridge | South bridge | Notes |
|-----|-------------|--------------|-------|
| **1981–1985** | PC/XT glue | PC/XT I/O channel | 8088/8086 — 8284 clock, 82288 bus |
| **1984–1989** | 82284 clock | 82288 AT bus | 80286 AT — 8259A/8237A universal |
| **1989–1993** | 420TX Saturn | PIIX / 82378 SIO | 486 PCI transition |
| **1993–1997** | 430FX/VX Triton | PIIX3 | Pentium SDRAM path |
| **1997–2001** | 440BX / AMD 751 Irongate | PIIX4E / AMD 756 Viper | AGP era — K6, Pentium II/III |
| **2000–2006** | 82845/865PE MCH | ICH5/ICH7 | Pentium 4 NetBurst — SATA USB2 |
| **2006–2011** | P35/X48 MCH | ICH9/ICH10 | Core 2 Penryn — DDR3 |
| **2011–2026** | CPU-integrated MCH | Z790/B660/H610 PCH, AMD PROM21 | Core i + PCH, Ryzen AM5 |

## North bridge

The north bridge owns the fast path: CPU ↔ RAM ↔ AGP/PCIe graphics. From Intel **420TX (1989)** and **440BX (1998)** through AMD **Irongate (1999)** and modern MCH integrations (north logic absorbed into CPU die from Nehalem onward), each entry is matched to host CPU era, bit width, and vendor. Leaves read `northbridge` kind with `companion_role: northbridge`.

## South bridge

The south bridge carries the slow path: PCI/ISA bridges, IDE/SATA, USB, ACPI, LPC. **PIIX (1993)**, **ICH generations (1999–2024)**, VIA **VT82C586B**, AMD **Viper/SB850/FCH** — each south die is paired to its `platform_stacks` entry in `field-cpu-companion-seed.json` and merged into combinatorics on publish.

## Super I/O

Winbond **W83627 (1990s)**, National **PC87309**, ITE **IT8712/IT8708 (2000s–2020s)** — floppy, COM, LPT, KBC, hardware monitor. Kind `super_io`, role `super_io`. These sit below the south bridge on LPC and persist long after the north bridge moved into the CPU package.

## Free populate doctrine

`cpu_companion` source runs at combinatorics build: for every host CPU, `_enrich_always_with_companions` detects the best-matching `platform_stacks` rule set, stamps `always_with` ids, sets `platform_stack`, and emits platform-specific NB/SB rows. No manual wiring — the catalog receives the full stack automatically. Universal dies (8259A, 8237A, 8254, MC146818) attach to every PC stack from **8088 through Core i + PCH**.

## Universal dies

The `universal` array holds cross-platform parts referenced by every matching `platform_stacks` entry. These twelve ids are the AT backbone: interrupt, DMA, timer, clock, RTC, and Super I/O templates that outlived individual north bridge generations.

*Seed: data/field-cpu-companion-seed.json · populate: free · citation: ironclad:chips:3 · plate: steel merge layer*
"""

DEWEY_PLATFORM_PAGES: tuple[dict[str, Any], ...] = (
    {"slug": "stack-genesis", "stack_id": "console_genesis", "title": "Sega Genesis Platform Stack",
     "family": "console", "era": "1988–1997", "vendor": "Sega",
     "intro": "Motorola 68000 main CPU with Z80 sound sub-CPU, Yamaha FM, and Sega VDP — the 16-bit cartridge platform launched **October 1988** in Japan (Mega Drive)."},
    {"slug": "stack-snes", "stack_id": "console_snes", "title": "Super Nintendo Platform Stack",
     "family": "console", "era": "1990–1996", "vendor": "Nintendo",
     "intro": "Ricoh **5A22** (65C816 @ 3.58 MHz), dual PPU, Sony **SPC700** audio sub-system — launched **November 1990** in Japan."},
    {"slug": "stack-ps1", "stack_id": "console_ps1", "title": "PlayStation Platform Stack",
     "family": "console", "era": "1994–2006", "vendor": "Sony",
     "intro": "LSI **R3000A** @ 33.8 MHz with CXD8530 glue, GPU, SPU, and CD-ROM controller — launched **December 1994** in Japan."},
    {"slug": "stack-saturn", "stack_id": "console_saturn", "title": "Sega Saturn Platform Stack",
     "family": "console", "era": "1994–1998", "vendor": "Sega",
     "intro": "Dual Hitachi **SH-2** CPUs with SCU system control, VDP1/VDP2 graphics, and SMPC peripheral hub — launched **November 1994** in Japan."},
    {"slug": "stack-n64", "stack_id": "console_n64", "title": "Nintendo 64 Platform Stack",
     "family": "console", "era": "1996–2002", "vendor": "Nintendo",
     "intro": "NEC VR4300 @ 93.75 MHz with Reality Co-Processor (RSP + RDP) — launched **June 1996** in Japan."},
    {"slug": "stack-zhaoxin-via", "stack_id": "pc_zhaoxin_kx", "title": "Zhaoxin / VIA x86 Platform Stack",
     "family": "domestic", "era": "1999–2026", "vendor": "Zhaoxin / VIA",
     "intro": "Centaur/VIA C3/C7 lineage (**1999–2013**) through Zhaoxin **KX-6000 (16nm, 2018)** and **KX-7000 (DDR5/PCIe5, 2022+)** — domestic x86 with CHX003 I/O hub."},
    {"slug": "stack-loongson", "stack_id": "pc_loongson", "title": "Loongson Platform Stack",
     "family": "domestic", "era": "2002–2026", "vendor": "Loongson",
     "intro": "MIPS (**2K, 2002**) through LoongArch **3A5000 (2020)** and **7A1000 bridge** — sovereign Chinese CPU with IOMMU, LPC, and PCIe root."},
    {"slug": "stack-elbrus", "stack_id": "pc_elbrus", "title": "Elbrus MCST Platform Stack",
     "family": "domestic", "era": "2001–2026", "vendor": "MCST",
     "intro": "E2K VLIW architecture with **Elbrus-8CB (2018)** eight-core server die, DDR4 MC, PCIe switch, and x86 binary translation layer."},
    {"slug": "stack-arm-soc-pmic", "stack_id": "arm_soc_template", "title": "ARM SoC PMIC Platform Stack",
     "family": "mobile", "era": "2007–2026", "vendor": "ARM ecosystem",
     "intro": "Mobile SoC companion template — DDRC, PMIC rail sequencing, GIC interrupt, clock/reset, pin controller, USB PHY — paired with Apple/Snapdragon/Exynos/MediaTek host dies."},
    {"slug": "stack-retro-c64", "stack_id": "retro_c64", "title": "Commodore 64 Classic Platform Stack",
     "family": "retro", "era": "1982–1994", "vendor": "Commodore",
     "intro": "Classic **breadbin C64** — MOS **6510**, **VIC-II**, **SID** (6581/8580), dual **CIA** 6526. Queen CHIPS scaffold; **not** the 2025 FPGA C64 Ultimate."},
    {"slug": "stack-c64-ultimate", "stack_id": "c64_ultimate_fpga", "title": "Commodore 64 Ultimate (FPGA)",
     "family": "hardware_pair", "era": "2025–2026", "vendor": "Commodore International Corporation",
     "intro": "**C64U / C64CU** — AMD Xilinx **Artix-7** FPGA, cycle-accurate recreation. Pairs with Grok16 on the host; **g16 does not run on classic 6510 silicon**."},
    {"slug": "stack-retro-6502", "stack_id": "retro_6502", "title": "6502 Family Platform Stack",
     "family": "retro", "era": "1975–1990", "vendor": "MOS / Ricoh",
     "intro": "6502 / 65C02 guest dies — NES, Atari 2600, Apple II, PC Engine, and other 8-bit systems sharing MOS glue."},
    {"slug": "stack-retro-z80", "stack_id": "retro_z80", "title": "Z80 Family Platform Stack",
     "family": "retro", "era": "1976–1995", "vendor": "Zilog",
     "intro": "Z80 / Z180 systems — SMS, MSX, Spectrum, Game Boy, Game Gear."},
    {"slug": "stack-retro-m68k", "stack_id": "retro_m68k", "title": "Motorola 68000 Platform Stack",
     "family": "retro", "era": "1979–1996", "vendor": "Motorola",
     "intro": "68000-line guests — Genesis, Neo Geo, CoCo, and other m68k arcade/home systems."},
    {"slug": "stack-amiga", "stack_id": "amiga_chipset", "title": "Commodore Amiga Chipset Stack",
     "family": "retro", "era": "1985–1996", "vendor": "Commodore",
     "intro": "Agnus, Denise, Paula — OCS/ECS/AGA chipset for Amiga 500/1200/4000 class machines."},
    {"slug": "stack-pc-pentium", "stack_id": "pc_pentium", "title": "PC / DOS Pentium Stack",
     "family": "pc", "era": "1993–2006", "vendor": "Intel",
     "intro": "DOS / early Windows guest — Pentium MMX class north/south companions for Queen Game Room PC lane."},
)

DEWEY_PLATFORM_TEMPLATE = """# {title}

**Platform stack:** `{stack_id}` · **Era:** {era} · **Vendor:** {vendor} · **Count:** {count}

{intro}

## Stack doctrine

This page lists every combinatorics leaf stamped `platform_stack: {stack_id}` plus companion dies emitted from `field-cpu-companion-seed.json`. Host and guest CPUs matching the stack's `match` rules receive `always_with` linkage at combinatorics build — no manual wiring.

## Manufacturing notes — companion dies

{companion_notes}

## Catalog ids

The `chip_ids` array holds all **{count}** entries for this platform stack, sorted alphabetically. Run `field-ironclad-chips-combinatorics.py combinatronic` for path percents and imprint renders.

*Stack: {stack_id} · seed: data/field-cpu-companion-seed.json · citation: ironclad:chips:3*
"""

DEWEY_KIND_PAGES: tuple[dict[str, Any], ...] = (
    {"slug": "host-cpu", "kind": "host_cpu", "title": "Host CPUs", "family": "execution"},
    {"slug": "guest-cpu", "kind": "guest_cpu", "title": "Guest CPUs", "family": "emulation"},
    {"slug": "northbridge", "kind": "northbridge", "title": "North Bridges", "family": "chipset"},
    {"slug": "southbridge", "kind": "southbridge", "title": "South Bridges", "family": "chipset"},
    {"slug": "super-io", "kind": "super_io", "title": "Super I/O", "family": "chipset"},
    {"slug": "chipset", "kind": "chipset", "title": "Chipsets & Glue", "family": "chipset"},
    {"slug": "soc", "kind": "soc", "title": "Systems on Chip", "family": "integration"},
    {"slug": "gpu", "kind": "gpu", "title": "GPUs & Graphics", "family": "graphics"},
    {"slug": "mame-device", "kind": "mame_device", "title": "MAME Devices", "family": "mame"},
    {"slug": "world", "source": "world_chips", "title": "World CHIPS", "family": "world"},
    {"slug": "semiconductor-world", "source": "semiconductor_world", "title": "Semiconductor World", "family": "semiconductor"},
    {"slug": "chips-hot", "kind": "chips_hot", "title": "CHIPS Hot Paths", "family": "queen"},
    {"slug": "video", "kind": "video", "title": "Video & Display", "family": "peripheral"},
    {"slug": "sound", "kind": "sound", "title": "Sound & Audio", "family": "peripheral"},
    {"slug": "isa-platform", "kind": "isa_platform", "title": "ISA Platforms", "family": "platform"},
    {"slug": "memory", "kind": "memory", "title": "Memory", "family": "semiconductor"},
    {"slug": "logic", "kind": "logic", "title": "Logic", "family": "semiconductor"},
    {"slug": "network", "kind": "network", "title": "Network", "family": "peripheral"},
    {"slug": "fpga", "kind": "fpga", "title": "FPGA", "family": "programmable"},
    {"slug": "dsp", "kind": "dsp", "title": "DSP", "family": "signal"},
    {"slug": "analog", "kind": "analog", "title": "Analog", "family": "semiconductor"},
    {"slug": "fab", "kind": "fab", "title": "Fab & Process", "family": "semiconductor"},
    {"slug": "pio", "kind": "pio", "title": "Parallel I/O", "family": "peripheral"},
    {"slug": "fdc", "kind": "fdc", "title": "Floppy Controllers", "family": "peripheral"},
    {"slug": "mmu", "kind": "mmu", "title": "MMU", "family": "system"},
    {"slug": "arcade-asic", "kind": "arcade_asic", "title": "Arcade ASICs", "family": "arcade"},
    {"slug": "coprocessor", "kind": "coprocessor", "title": "Coprocessors", "family": "execution"},
    {"slug": "glue", "kind": "glue", "title": "Glue Logic", "family": "chipset"},
)

DEWEY_KIND_TEMPLATE = """# {title}

**Kind:** `{kind_label}` · **Count:** {count} · **Family:** {family}

This page lists every `{kind_label}` die in the Ironclad CHIPS combinatorics catalog. Each id is a combinatorics leaf off the truth plate (`ironclad:chips:3`), merged from seed, Queen, MAME, CPU library, world seeds, and companion populate.

## Catalog ids

The `chip_ids` array on this page holds all **{count}** entries for this kind, sorted alphabetically. Open Queen CHIPS Combinatronic or run `field-ironclad-chips-combinatorics.py combinatronic` for path percents, bands, and imprint renders.

*Regenerated from live combinatorics · facet ironclad_chips*
"""


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, path: str | Path) -> Any | None:
    path = Path(path)
    if not path.is_file():
        path = INSTALL / "lib" / path.name
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _thumb_ids_on_disk() -> set[str]:
    if not THUMBS_ASSETS.is_dir():
        return set()
    return {p.stem for p in THUMBS_ASSETS.glob("*.png") if p.is_file()}


def _closeup_ids_on_disk() -> set[str]:
    if not COMBINATRONIC_ASSETS.is_dir():
        return set()
    return {p.stem for p in COMBINATRONIC_ASSETS.glob("*.png") if p.is_file()}


def _thumb_url(
    chip_id: str,
    *,
    thumb_ids: set[str] | None = None,
    closeup_ids: set[str] | None = None,
) -> tuple[str, bool]:
    """Return (url, thumb_available). thumb_available only when thumbs/{id}.png exists."""
    thumbs = thumb_ids if thumb_ids is not None else _thumb_ids_on_disk()
    closeups = closeup_ids if closeup_ids is not None else _closeup_ids_on_disk()
    if chip_id in thumbs:
        return THUMB_PATTERN.format(chip_id=chip_id), True
    if chip_id in closeups:
        return CLOSEUP_PATTERN.format(chip_id=chip_id), False
    return THUMB_FALLBACK, False


def _is_active(*sources: dict[str, Any]) -> bool:
    for src in sources:
        disc = src.get("discontinued")
        if disc is None:
            continue
        text = str(disc).strip()
        if text and text.lower() not in ("null", "none", "—", "-"):
            return False
    return True


def _search_blob(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in SEARCH_BLOB_FIELDS:
        val = entry.get(key)
        if val is not None and val != "":
            parts.append(str(val))
    for key in ("platforms", "always_with"):
        for item in entry.get(key) or []:
            parts.append(str(item))
    return " ".join(parts).lower()


def _html_esc(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _highlight_text(text: str, query: str) -> str:
    raw = str(text or "")
    if not raw or not query.strip():
        return _html_esc(raw)
    q = query.strip().lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 0]
    if not tokens:
        return _html_esc(raw)
    lower = raw.lower()
    spans: list[tuple[int, int]] = []
    for tok in sorted(tokens, key=len, reverse=True):
        start = 0
        while True:
            idx = lower.find(tok, start)
            if idx < 0:
                break
            spans.append((idx, idx + len(tok)))
            start = idx + len(tok)
    if not spans:
        return _html_esc(raw)
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    out: list[str] = []
    cursor = 0
    for start, end in merged:
        if start > cursor:
            out.append(_html_esc(raw[cursor:start]))
        out.append(f"<mark>{_html_esc(raw[start:end])}</mark>")
        cursor = end
    if cursor < len(raw):
        out.append(_html_esc(raw[cursor:]))
    return "".join(out)


def _score_entry(row: dict[str, Any], query: str) -> int:
    q = query.strip().lower()
    if not q:
        score = 0
        if row.get("featured"):
            score += 3
        if row.get("thumb_available"):
            score += 1
        return score
    blob = row.get("search_blob") or _search_blob(row)
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 0]
    score = 0
    if q in blob:
        score += 24
    cid = str(row.get("id") or "").lower()
    label = str(row.get("label") or "").lower()
    vendor = str(row.get("vendor") or "").lower()
    if q in cid:
        score += 20
    if q in label:
        score += 16
    if q in vendor:
        score += 12
    for tok in tokens:
        if tok in cid:
            score += 10
        if tok in label:
            score += 8
        if tok in vendor:
            score += 6
        if tok in str(row.get("kind") or "").lower():
            score += 5
        if tok in str(row.get("family") or "").lower():
            score += 4
        if tok in blob:
            score += 3
    if row.get("featured"):
        score += 2
    if row.get("active") is False:
        score -= 4
    return score


def _detail_url(chip_id: str) -> str | None:
    if (DETAIL_ASSETS / f"{chip_id}.png").is_file():
        return DETAIL_PATTERN.format(chip_id=chip_id)
    return None


def _ironclad_batch(*, refresh: bool = False) -> dict[str, Any]:
    if not refresh and IRONCLAD_JSON.is_file():
        cached = _load(IRONCLAD_JSON, {})
        if cached.get("chips"):
            return cached
    mod = _import_mod("field_ironclad_chips_lib", IRONCLAD_PY)
    if mod and hasattr(mod, "build_ironclad_chips_combinatorics"):
        return mod.build_ironclad_chips_combinatorics(force=refresh)
    return _load(IRONCLAD_JSON, {})


def _companion_universal_index() -> dict[str, dict[str, Any]]:
    seed = _load(COMPANION_SEED, {})
    out: dict[str, dict[str, Any]] = {}
    for row in seed.get("universal") or []:
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def _curation_map() -> dict[str, dict[str, Any]]:
    doc = _load(CURATION, {})
    entries = doc.get("entries") or {}
    if isinstance(entries, dict):
        return {str(k): v for k, v in entries.items() if isinstance(v, dict)}
    if isinstance(entries, list):
        return {
            str(row["id"]): row
            for row in entries
            if isinstance(row, dict) and row.get("id")
        }
    return {}


def _combinatronic_index() -> dict[str, dict[str, Any]]:
    doc = _load(COMBINATRONIC_CATALOG, {})
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("chips") or []:
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def _matches_filter(row: dict[str, Any], filt: dict[str, Any]) -> bool:
    for key, expected in filt.items():
        val = row.get(key)
        if isinstance(expected, list):
            if val not in expected:
                return False
        elif str(val or "") != str(expected):
            return False
    return True


def _catalog_entry(
    chip: dict[str, Any],
    *,
    curation: dict[str, dict[str, Any]],
    companion_uni: dict[str, dict[str, Any]],
    combinatronic: dict[str, dict[str, Any]],
    thumb_ids: set[str],
    closeup_ids: set[str],
    page: int,
    chapter: str,
) -> dict[str, Any]:
    cid = str(chip.get("id") or "")
    cur = dict(curation.get(cid) or {})
    comp = companion_uni.get(cid) or {}
    combo = combinatronic.get(cid) or {}
    thumb, thumb_ok = _thumb_url(cid, thumb_ids=thumb_ids, closeup_ids=closeup_ids)

    entry: dict[str, Any] = {
        "id": cid,
        "label": chip.get("label") or cid,
        "vendor": chip.get("vendor") or "—",
        "kind": chip.get("kind") or "unknown",
        "family": chip.get("family") or "",
        "source": chip.get("source") or "",
        "bits": chip.get("bits"),
        "mhz": chip.get("mhz"),
        "era": chip.get("era"),
        "status": chip.get("status"),
        "combinatorics_leaf": chip.get("combinatorics_leaf"),
        "companion_role": chip.get("companion_role") or comp.get("companion_role"),
        "platform_stack": chip.get("platform_stack"),
        "always_with": list(chip.get("always_with") or []),
        "mame_device": chip.get("mame_device"),
        "platforms": list(chip.get("platforms") or []),
        "note": chip.get("note") or comp.get("note"),
        "path_pct": chip.get("path_pct"),
        "band": chip.get("band"),
        "country": chip.get("country") or cur.get("country"),
        "page": page,
        "chapter": chapter,
        "thumb_url": thumb,
        "thumb_available": thumb_ok,
        "detail_image_url": _detail_url(cid),
        "curated": bool(cur),
        "featured": bool(cur.get("featured") or combo.get("featured")),
    }

    for field in (
        "mfg_date_start", "mfg_date_end", "discontinued",
        "socket", "package", "pins", "curator_note",
    ):
        if cur.get(field) is not None:
            entry[field] = cur[field]
        elif combo.get(field) is not None:
            entry[field] = combo[field]
        elif comp.get(field) is not None:
            entry[field] = comp[field]

    if combo.get("imprint"):
        entry["imprint"] = list(combo["imprint"])
    if combo.get("body"):
        entry["body_color"] = combo["body"]
    if combo.get("label") and entry.get("label") == cid:
        entry["label"] = combo["label"]

    if not entry.get("mfg_date_start") and entry.get("era"):
        entry["mfg_date_start"] = str(entry["era"])

    entry["active"] = _is_active(cur, chip, entry)
    entry["search_blob"] = _search_blob(entry)
    return entry


def _chapter_page(chapter: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    page_no = int(chapter["page"])
    chap_id = str(chapter["id"])
    filt = chapter.get("filter") or {}

    if chap_id == "ironclad_truth":
        chip_ids = [e["id"] for e in entries]
        featured = [e["id"] for e in entries if e.get("featured")][:24]
    elif filt:
        matched = [e for e in entries if _matches_filter(e, filt)]
        chip_ids = [e["id"] for e in matched]
        featured = [e["id"] for e in matched if e.get("featured")][:12]
    else:
        chip_ids = []
        featured = []

    return {
        "page": page_no,
        "chapter": chap_id,
        "title": chapter.get("title") or chap_id,
        "layout": chapter.get("layout") or "grid",
        "count": len(chip_ids),
        "chip_ids": chip_ids,
        "featured_ids": featured,
        "thumbnails": [
            {"id": e["id"], "label": e["label"], "thumb_url": e["thumb_url"]}
            for e in entries
            if e["id"] in chip_ids and e.get("thumb_available")
        ][:48],
    }


def build_catalog(*, refresh: bool = False) -> dict[str, Any]:
    import time
    t0 = time.perf_counter()

    iron = _ironclad_batch(refresh=refresh)
    chips = iron.get("chips") or []
    curation = _curation_map()
    companion_uni = _companion_universal_index()
    combinatronic = _combinatronic_index()
    thumb_ids = _thumb_ids_on_disk()
    closeup_ids = _closeup_ids_on_disk()

    by_chapter: dict[str, int] = {}
    entries: list[dict[str, Any]] = []
    page_lookup: dict[str, int] = {}

    for chip in chips:
        if not isinstance(chip, dict) or not chip.get("id"):
            continue
        cid = str(chip["id"])
        kind = str(chip.get("kind") or "unknown")
        source = str(chip.get("source") or "")
        family = str(chip.get("family") or "")
        platform_stack = str(chip.get("platform_stack") or "")

        if source == "cpu_companion" and family == "cpu_companion_universal":
            page, chapter = 2, "universal_chipset"
        elif source == "cpu_companion" and platform_stack in COMPANION_STACK_BY_PLATFORM:
            page, chapter = COMPANION_STACK_BY_PLATFORM[platform_stack]
        else:
            page, chapter = 1, "ironclad_truth"
            for ch in CHAPTERS[2:]:
                if str(ch.get("id") or "") in COMPANION_STACK_CHAPTERS:
                    continue
                filt = ch.get("filter") or {}
                probe = {**chip, "kind": kind, "source": source, "family": family}
                if _matches_filter(probe, filt):
                    page = int(ch["page"])
                    chapter = str(ch["id"])
                    break

        page_lookup[cid] = page
        by_chapter[chapter] = by_chapter.get(chapter, 0) + 1
        entries.append(_catalog_entry(
            chip,
            curation=curation,
            companion_uni=companion_uni,
            combinatronic=combinatronic,
            thumb_ids=thumb_ids,
            closeup_ids=closeup_ids,
            page=page,
            chapter=chapter,
        ))

    api = _import_mod("ironclad_api", "ironclad-secure-api.py")
    if api and hasattr(api, "sort_index"):
        try:
            entries, sort_meta = api.sort_index(entries, context="chip_catalog")
            for i, e in enumerate(entries):
                e.setdefault("ironclad_index", i)
        except Exception:
            entries.sort(key=lambda e: (e.get("page", 99), str(e.get("kind") or ""), str(e.get("label") or "")))
            sort_meta = {}
    else:
        entries.sort(key=lambda e: (e.get("page", 99), str(e.get("kind") or ""), str(e.get("label") or "")))
        sort_meta = {}

    by_kind: dict[str, int] = {}
    for e in entries:
        k = str(e.get("kind") or "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1

    pages = [_chapter_page(ch, entries) for ch in CHAPTERS]
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "schema": "field-chips-catalog/v1",
        "updated": _now(),
        "motto": "Library book of every die — Page 1 Ironclad, Page 2 universal chipset, chapters by kind.",
        "ok": True,
        "ironclad_root": iron.get("ironclad_root") or iron.get("ironclad"),
        "ironclad_citation": iron.get("ironclad_citation"),
        "counts": {
            "total": len(entries),
            "curated": sum(1 for e in entries if e.get("curated")),
            "combinatronic_overlay": len(combinatronic),
            "featured": sum(1 for e in entries if e.get("featured")),
            "active": sum(1 for e in entries if e.get("active") is not False),
            "thumb_available": sum(1 for e in entries if e.get("thumb_available")),
            "thumbs_on_disk": len(thumb_ids),
            "closeup_on_disk": len(closeup_ids),
            "pages": len(pages),
            "by_kind": by_kind,
            "by_chapter": by_chapter,
        },
        "chapters": list(CHAPTERS),
        "pages": pages,
        "entries": entries,
        "page_lookup": page_lookup,
        "elapsed_ms": elapsed_ms,
        "combinatronic": True,
        "ironclad_sort": sort_meta or None,
        "ironclad_citation": "ironclad:api:1",
        "sources": {
            "ironclad": str(IRONCLAD_JSON),
            "curation": str(CURATION.relative_to(INSTALL)) if CURATION.is_relative_to(INSTALL) else str(CURATION),
            "companion_seed": str(COMPANION_SEED.relative_to(INSTALL)) if COMPANION_SEED.is_relative_to(INSTALL) else str(COMPANION_SEED),
            "visual_catalog": len(thumb_ids),
        },
    }


def catalog_json(*, refresh: bool = False) -> dict[str, Any]:
    if refresh or not CATALOG.is_file():
        return build_catalog(refresh=refresh)
    doc = _load(CATALOG, {})
    if doc.get("entries"):
        return doc
    return build_catalog(refresh=refresh)


def _autocomplete_hit(row: dict[str, Any], *, score: int, query: str) -> dict[str, Any]:
    cid = str(row.get("id") or "")
    label = str(row.get("label") or cid)
    vendor = str(row.get("vendor") or "—")
    return {
        "id": cid,
        "label": label,
        "vendor": vendor,
        "kind": row.get("kind") or "unknown",
        "thumb_url": row.get("thumb_url") or THUMB_FALLBACK,
        "active": row.get("active", True),
        "score": score,
        "highlight": {
            "id": _highlight_text(cid, query),
            "label": _highlight_text(label, query),
            "vendor": _highlight_text(vendor, query),
        },
    }


def search_autocomplete(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    doc = catalog_json()
    q = query.strip()
    ql = q.lower()
    entries = list(doc.get("entries") or [])

    if not ql:
        pool = [e for e in entries if e.get("featured")]
        pool.extend(entries)
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for row in pool:
            cid = str(row.get("id") or "")
            if cid in seen:
                continue
            seen.add(cid)
            out.append(_autocomplete_hit(row, score=_score_entry(row, q), query=q))
            if len(out) >= limit:
                break
        return out

    hits: list[tuple[int, dict[str, Any]]] = []
    for row in entries:
        score = _score_entry(row, q)
        if score > 0:
            hits.append((score, row))
    hits.sort(key=lambda x: (-x[0], str(x[1].get("label") or "").lower()))
    rows = [row for _, row in hits[: max(limit, len(hits))]]
    acc = _import_mod("ironclad_access_chips", "ironclad-access.py")
    if acc and hasattr(acc, "sort_rows") and rows:
        try:
            rows, _ = acc.sort_rows(rows, context="chip_catalog", n=limit)
        except Exception:
            rows = rows[:limit]
    elif rows:
        api = _import_mod("ironclad_api", "ironclad-secure-api.py")
        if api and hasattr(api, "sort_index"):
            try:
                rows, _ = api.ironclad_secure_api().sort_index(rows, context="chip_catalog", n=limit)
            except Exception:
                rows = rows[:limit]
        else:
            rows = rows[:limit]
    score_by_id = {str(row.get("id")): sc for sc, row in hits}
    return [_autocomplete_hit(row, score=score_by_id.get(str(row.get("id")), 0), query=q) for row in rows]


def entry_detail(chip_id: str) -> dict[str, Any] | None:
    doc = catalog_json()
    for row in doc.get("entries") or []:
        if str(row.get("id")) == chip_id:
            detail = dict(row)
            detail["detail_url"] = f"/world/queen-chips-detail.html?id={chip_id}"
            detail["ironclad_root"] = doc.get("ironclad_root")
            return detail
    return None


def build_pages() -> list[dict[str, Any]]:
    doc = catalog_json()
    return list(doc.get("pages") or [])


def _rel_install(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _dewey_page_filename(page_num: int, slug: str) -> str:
    return f"page-{page_num:03d}-{slug}.json"


def _dewey_chip_png(chip_id: str) -> str | None:
    if (COMBINATRONIC_ASSETS / f"{chip_id}.png").is_file():
        return THUMB_PATTERN.format(chip_id=chip_id)
    return None


def _dewey_page_assets(chip_ids: list[str], *, fallback_cover: str = DEWEY_BOOK_COVER, fallback_thumb: str = DEWEY_BOOK_THUMB) -> dict[str, str]:
    for cid in chip_ids:
        png = _dewey_chip_png(cid)
        if png:
            return {"cover": png, "thumb": png}
    return {"cover": fallback_cover, "thumb": fallback_thumb}


def _dewey_chips_for_spec(chips: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    if spec.get("source") == "world_chips":
        return [c for c in chips if c.get("source") == "world_chips" or c.get("country")]
    if spec.get("source") == "semiconductor_world":
        return [c for c in chips if c.get("source") == "semiconductor_world"]
    kind = spec.get("kind")
    if kind:
        return [c for c in chips if str(c.get("kind") or "") == kind]
    return []


def _dewey_stack_seed_ids(stack_id: str) -> set[str]:
    companion_doc = _load(COMPANION_SEED, {})
    stack = (companion_doc.get("platform_stacks") or {}).get(stack_id) or {}
    ids: set[str] = set()
    for row in stack.get("companions") or []:
        if isinstance(row, dict) and row.get("id"):
            ids.add(str(row["id"]))
    for cid in stack.get("always_with") or []:
        if cid:
            ids.add(str(cid))
    return ids


def _dewey_chips_for_platform_stack(chips: list[dict[str, Any]], stack_id: str) -> list[str]:
    seed_ids = _dewey_stack_seed_ids(stack_id)
    fam = f"cpu_companion_{stack_id}"
    matched: set[str] = set()
    for chip in chips:
        cid = str(chip.get("id") or "").strip()
        if not cid:
            continue
        if chip.get("platform_stack") == stack_id:
            matched.add(cid)
        if cid in seed_ids:
            matched.add(cid)
        if chip.get("family") == fam:
            matched.add(cid)
        if stack_id in str(chip.get("source") or ""):
            matched.add(cid)
    return sorted(matched)


def _dewey_platform_body(spec: dict[str, Any], count: int) -> str:
    companion_doc = _load(COMPANION_SEED, {})
    stack = (companion_doc.get("platform_stacks") or {}).get(spec["stack_id"]) or {}
    notes: list[str] = []
    for row in stack.get("companions") or []:
        if not isinstance(row, dict):
            continue
        label = row.get("label") or row.get("id") or "companion"
        vendor = row.get("vendor") or spec.get("vendor") or ""
        bits = row.get("bits")
        note = row.get("note") or ""
        bit_s = f"{bits}-bit" if bits else ""
        notes.append(f"- **{label}** ({vendor}{', ' + bit_s if bit_s else ''}) — {note}")
    companion_notes = "\n".join(notes) if notes else "- Companion rows pending in companion seed."
    return DEWEY_PLATFORM_TEMPLATE.format(
        title=spec["title"],
        stack_id=spec["stack_id"],
        era=spec.get("era") or "—",
        vendor=spec.get("vendor") or "—",
        count=count,
        intro=spec.get("intro") or stack.get("label") or "",
        companion_notes=companion_notes,
    ).strip()


def build_dewey_library_book(*, refresh: bool = False) -> dict[str, Any]:
    """Regenerate Dewey library book page JSON from live combinatorics counts."""
    iron = _ironclad_batch(refresh=refresh)
    chips: list[dict[str, Any]] = list(iron.get("chips") or [])
    counts = iron.get("counts") or {}
    pages_meta: list[dict[str, Any]] = []
    page_num = 0

    page_num = 1
    featured = [
        c["id"] for c in chips
        if c.get("kind") in ("host_cpu", "chips_hot") or "cyrix" in str(c.get("id", "")).lower()
    ][:24]
    assets = {"cover": IRONCLAD_PAGE_COVER, "thumb": IRONCLAD_PAGE_THUMB}
    p1 = {
        "schema": "field-chips-catalog-page/v1",
        "page_num": page_num,
        "slug": "ironclad",
        "title": "Ironclad — Truth Plate & Combinatorics Root",
        "body": PAGE_IRONCLAD_BODY.strip(),
        "chip_ids": featured,
        "chip_count": len(featured),
        "kind": None,
        "family": "ironclad",
        "combinatorics_total": counts.get("total", len(chips)),
        "cover": assets["cover"],
        "thumb": assets["thumb"],
        "updated": _now(),
    }
    p1_path = DEWEY_PAGES_DIR / _dewey_page_filename(page_num, "ironclad")
    _save(p1_path, p1)
    pages_meta.append({"page_num": page_num, "slug": "ironclad", "title": p1["title"], "file": _rel_install(p1_path), "chip_count": p1["chip_count"]})

    page_num = 2
    companion_ids = sorted({
        c["id"] for c in chips
        if c.get("kind") in ("northbridge", "southbridge", "super_io", "chipset")
        or c.get("source") == "cpu_companion"
        or c.get("companion_role")
    })
    assets = _dewey_page_assets(companion_ids)
    p2 = {
        "schema": "field-chips-catalog-page/v1",
        "page_num": page_num,
        "slug": "universal-chipset",
        "title": "Universal Chipset — North Bridge, South Bridge, Super I/O",
        "body": PAGE_UNIVERSAL_CHIPSET_BODY.strip(),
        "chip_ids": companion_ids,
        "chip_count": len(companion_ids),
        "kind": "chipset_companion",
        "family": "chipset",
        "combinatorics_total": counts.get("total", len(chips)),
        "cover": assets["cover"],
        "thumb": assets["thumb"],
        "updated": _now(),
    }
    p2_path = DEWEY_PAGES_DIR / _dewey_page_filename(page_num, "universal-chipset")
    _save(p2_path, p2)
    pages_meta.append({"page_num": page_num, "slug": "universal-chipset", "title": p2["title"], "file": _rel_install(p2_path), "chip_count": p2["chip_count"]})

    for spec in DEWEY_KIND_PAGES:
        page_num += 1
        rows = _dewey_chips_for_spec(chips, spec)
        chip_ids = sorted({str(c["id"]) for c in rows if c.get("id")})
        kind_label = spec.get("kind") or spec.get("source") or spec["slug"]
        body = DEWEY_KIND_TEMPLATE.format(
            title=spec["title"],
            kind_label=kind_label,
            count=len(chip_ids),
            family=spec.get("family", "catalog"),
        ).strip()
        assets = _dewey_page_assets(chip_ids)
        page = {
            "schema": "field-chips-catalog-page/v1",
            "page_num": page_num,
            "slug": spec["slug"],
            "title": spec["title"],
            "body": body,
            "chip_ids": chip_ids,
            "chip_count": len(chip_ids),
            "kind": spec.get("kind") or spec.get("source"),
            "family": spec.get("family"),
            "combinatorics_total": counts.get("total", len(chips)),
            "cover": assets["cover"],
            "thumb": assets["thumb"],
            "updated": _now(),
        }
        page_path = DEWEY_PAGES_DIR / _dewey_page_filename(page_num, spec["slug"])
        _save(page_path, page)
        pages_meta.append({
            "page_num": page_num,
            "slug": spec["slug"],
            "title": spec["title"],
            "file": _rel_install(page_path),
            "chip_count": len(chip_ids),
            "kind": page["kind"],
        })

    for spec in DEWEY_PLATFORM_PAGES:
        page_num += 1
        chip_ids = _dewey_chips_for_platform_stack(chips, spec["stack_id"])
        body = _dewey_platform_body(spec, len(chip_ids))
        assets = _dewey_page_assets(chip_ids)
        page = {
            "schema": "field-chips-catalog-page/v1",
            "page_num": page_num,
            "slug": spec["slug"],
            "title": spec["title"],
            "body": body,
            "chip_ids": chip_ids,
            "chip_count": len(chip_ids),
            "kind": "platform_stack",
            "family": spec.get("family"),
            "platform_stack": spec["stack_id"],
            "era": spec.get("era"),
            "combinatorics_total": counts.get("total", len(chips)),
            "cover": assets["cover"],
            "thumb": assets["thumb"],
            "updated": _now(),
        }
        page_path = DEWEY_PAGES_DIR / _dewey_page_filename(page_num, spec["slug"])
        _save(page_path, page)
        pages_meta.append({
            "page_num": page_num,
            "slug": spec["slug"],
            "title": spec["title"],
            "file": _rel_install(page_path),
            "chip_count": len(chip_ids),
            "kind": "platform_stack",
            "platform_stack": spec["stack_id"],
        })

    book = {
        "id": "ironclad-chips-catalog",
        "title": "Ironclad CHIPS Catalog",
        "author": "Hostess 7",
        "dewey": "621",
        "dewey_label": "Computer engineering",
        "ein": "H7C-FIELD-chips-catalog",
        "format": "chips-catalog",
        "format_version": 1,
        "schema": "field-chips-catalog-book/v1",
        "pages_dir": "pages/",
        "page_count": page_num,
        "combinatorics_facet": "ironclad_chips",
        "ironclad_citation": iron.get("ironclad_citation") or "ironclad:chips:3",
        "combinatorics_total": counts.get("total", len(chips)),
        "combinatorics_by_kind": counts.get("by_kind") or {},
        "pages": pages_meta,
        "manual_reader": "/world/queen-chips-cores.html",
        "combinatronic_api": "/api/chips/combinatronic",
        "cover": DEWEY_BOOK_COVER,
        "thumb": DEWEY_BOOK_THUMB,
        "cover_asset": "Queen/world/assets/combinatronic/chips/cyrix_6x86.png",
        "github_shelf": "621-computer-engineering/chips-catalog",
        "updated": _now(),
    }
    _save(DEWEY_BOOK_DIR / "book.json", book)

    shelf = {
        "schema": "dewey-shelf/v1",
        "shelf": "621-computer-engineering/chips-catalog",
        "code": "621",
        "title": "Computer Engineering — CHIPS Catalog",
        "updated": _now(),
        "format_primary": "chips-catalog",
        "book_count": 1,
        "books": [
            {
                "id": "ironclad-chips-catalog",
                "title": book["title"],
                "author": book["author"],
                "dewey": "621",
                "format": "chips-catalog",
                "page_count": page_num,
                "cover": DEWEY_BOOK_COVER,
                "thumb": DEWEY_BOOK_THUMB,
                "ready": True,
            }
        ],
    }
    _save(DEWEY_SHELF_DIR / "shelf.json", shelf)

    return {
        "ok": True,
        "schema": "field-chips-catalog-build/v1",
        "shelf": _rel_install(DEWEY_SHELF_DIR / "shelf.json"),
        "book": _rel_install(DEWEY_BOOK_DIR / "book.json"),
        "page_count": page_num,
        "combinatorics_total": counts.get("total", len(chips)),
        "pages": pages_meta,
        "updated": _now(),
    }


def library_book() -> dict[str, Any]:
    doc = catalog_json()
    return {
        "schema": "field-chips-library-book/v1",
        "title": "Field Chips Catalog",
        "updated": doc.get("updated"),
        "motto": doc.get("motto"),
        "page_count": len(doc.get("pages") or []),
        "counts": doc.get("counts"),
        "ironclad_root": doc.get("ironclad_root"),
        "pages": doc.get("pages") or [],
        "chapters": doc.get("chapters") or list(CHAPTERS),
    }


def publish_catalog(*, refresh: bool = False) -> dict[str, Any]:
    cat = build_catalog(refresh=refresh)
    _save(CATALOG, cat)
    panel = {
        "schema": "field-chips-catalog-panel/v1",
        "updated": cat.get("updated"),
        "ok": True,
        "counts": cat.get("counts"),
        "page_count": len(cat.get("pages") or []),
        "chapters": [c.get("id") for c in (cat.get("chapters") or [])],
        "sample": (cat.get("entries") or [])[:24],
        "featured": [e for e in (cat.get("entries") or []) if e.get("featured")][:16],
        "ironclad_citation": cat.get("ironclad_citation"),
    }
    _save(PANEL, panel)
    return {
        "ok": True,
        "panel": panel,
        "catalog_path": str(CATALOG),
        "panel_path": str(PANEL),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    refresh = "--refresh" in sys.argv or os.environ.get("NEXUS_CHIPS_CATALOG_REFRESH", "0") == "1"

    if cmd in ("json", "panel", "status"):
        if PANEL.is_file() and not refresh:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_catalog(refresh=refresh).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish"):
        print(json.dumps(publish_catalog(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(catalog_json(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("search", "autocomplete"):
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = 20
        if len(sys.argv) > 3 and str(sys.argv[3]).isdigit():
            limit = int(sys.argv[3])
        for i, arg in enumerate(sys.argv):
            if arg == "--limit" and i + 1 < len(sys.argv):
                try:
                    limit = int(sys.argv[i + 1])
                except ValueError:
                    pass
        hits = search_autocomplete(q, limit=limit)
        print(json.dumps({
            "query": q,
            "hits": hits,
            "count": len(hits),
            "search_engine": "field-chips-catalog/v1-search-blob",
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "detail":
        cid = sys.argv[2] if len(sys.argv) > 2 else ""
        row = entry_detail(cid)
        print(json.dumps(row or {"ok": False, "error": "not_found", "id": cid}, ensure_ascii=False, indent=2))
        return 0 if row else 1
    if cmd == "pages":
        print(json.dumps({"pages": build_pages(), "page_count": len(build_pages())}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("library-book", "library_book", "book"):
        dewey = build_dewey_library_book(refresh=refresh)
        summary = library_book()
        summary["dewey"] = dewey
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("library-book-build", "dewey-book"):
        print(json.dumps(build_dewey_library_book(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pub = publish_catalog(refresh=refresh)
        cat = _load(CATALOG, {})
        counts = cat.get("counts") or (pub.get("panel") or {}).get("counts") or {}
        entries = cat.get("entries") or []
        fields_ok = bool(entries) and all(
            {"active", "search_blob", "thumb_url"}.issubset(e.keys()) for e in entries
        )
        ok = (
            counts.get("total", 0) >= 900
            and counts.get("pages", 0) >= 34
            and counts.get("thumb_available", 0) >= 900
            and fields_ok
        )
        print(json.dumps({"ok": ok, "counts": counts, "fields_ok": fields_ok}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["build", "publish", "catalog", "search", "autocomplete", "detail", "pages", "library-book", "library-book-build", "verify", "panel"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())