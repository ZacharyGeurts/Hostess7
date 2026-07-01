#!/usr/bin/env python3
"""Enrich field-chips-catalog-curation.json with chips_hot and missing combinatronic featured dies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURATION_PATH = ROOT / "data" / "field-chips-catalog-curation.json"
COMBINATRONIC_PATH = ROOT / "data" / "field-combinatronic-chip-catalog.json"

CHIPS_HOT_IDS: tuple[str, ...] = (
    "chips_6502",
    "chips_2c02",
    "chips_68000",
    "chips_z80",
    "chips_ym2612",
    "chips_sn76489",
    "chips_tia",
    "chips_2a03",
    "chips_6507",
    "chips_65816",
    "chips_8080",
    "chips_fieldchips",
    "chips_sid",
    "chips_sm83",
    "chips_spc700",
)

CHIPS_HOT_ENTRIES: dict[str, dict[str, Any]] = {
    "chips_6502": {
        "mfg_date_start": "1975-09",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — MOS 6502 opcode dispatch; Apple II, C64, Atari, NES heart of 8-bit era.",
    },
    "chips_2c02": {
        "mfg_date_start": "1983-07",
        "mfg_date_end": "1995-08",
        "discontinued": "1995-08",
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "Japan",
        "featured": True,
        "curator_note": "CHIPS hot path — Ricoh 2C02 PPU scanline SIMD tile fetch for NES.",
    },
    "chips_68000": {
        "mfg_date_start": "1979-09",
        "mfg_date_end": "2005-12",
        "discontinued": "2005-12",
        "socket": "DIP-64",
        "package": "DIP-64",
        "pins": 64,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — Motorola 68000 effective-address calc for Genesis, Mac, Amiga.",
    },
    "chips_z80": {
        "mfg_date_start": "1976-03",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — Zilog Z80 flag-table LTO for SMS, MSX, and arcade sound CPUs.",
    },
    "chips_ym2612": {
        "mfg_date_start": "1988-01",
        "mfg_date_end": "2005-12",
        "discontinued": "2005-12",
        "socket": "DIP-24",
        "package": "DIP-24",
        "pins": 24,
        "country": "Japan",
        "featured": True,
        "curator_note": "CHIPS hot path — Yamaha YM2612 OPN2 FM envelope fast-math for Mega Drive.",
    },
    "chips_sn76489": {
        "mfg_date_start": "1978-12",
        "mfg_date_end": "1995-08",
        "discontinued": "1995-08",
        "socket": "DIP-16",
        "package": "DIP-16",
        "pins": 16,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — TI SN76489 PSG square-wave period unroll for ColecoVision and SMS.",
    },
    "chips_tia": {
        "mfg_date_start": "1977-09",
        "mfg_date_end": "1992-06",
        "discontinued": "1992-06",
        "socket": "DIP-48",
        "package": "DIP-48",
        "pins": 48,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — MOS TIA television interface adaptor with entropy-scheduled Atari 2600 raster.",
    },
    "chips_2a03": {
        "mfg_date_start": "1983-07",
        "mfg_date_end": "1995-08",
        "discontinued": "1995-08",
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "Japan",
        "featured": True,
        "curator_note": "CHIPS hot path — Ricoh 2A03 NES CPU (6502 derivative) with on-die APU integrated tick.",
    },
    "chips_6507": {
        "mfg_date_start": "1977-09",
        "mfg_date_end": "1992-06",
        "discontinued": "1992-06",
        "socket": "DIP-28",
        "package": "DIP-28",
        "pins": 28,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — MOS 6507 Atari 2600 CPU with 13-bit address bus and on-chip clock.",
    },
    "chips_65816": {
        "mfg_date_start": "1983-03",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — WDC 65C816 SNES main CPU with HDMA and 24-bit banked addressing.",
    },
    "chips_8080": {
        "mfg_date_start": "1974-04",
        "mfg_date_end": "1998-06",
        "discontinued": "1998-06",
        "socket": "DIP-40",
        "package": "Ceramic DIP",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — Intel 8080 arcade and CP/M emulation core; Altair/IMSAI lineage.",
    },
    "chips_fieldchips": {
        "mfg_date_start": "2024-06",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "Software",
        "package": "g++16 field_opt",
        "pins": 0,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — FieldChips.hpp aggregator; rebuild with g++16 field_opt vectorization.",
    },
    "chips_sid": {
        "mfg_date_start": "1982-08",
        "mfg_date_end": "1994-06",
        "discontinued": "1994-06",
        "socket": "DIP-28",
        "package": "DIP-28",
        "pins": 28,
        "country": "USA",
        "featured": True,
        "curator_note": "CHIPS hot path — MOS 6581/8580 SID three-voice analog synthesis for Commodore 64.",
    },
    "chips_sm83": {
        "mfg_date_start": "1989-04",
        "mfg_date_end": "2003-12",
        "discontinued": "2003-12",
        "socket": "QFP-80",
        "package": "QFP-80",
        "pins": 80,
        "country": "Japan",
        "featured": True,
        "curator_note": "CHIPS hot path — Sharp SM83/LR35902 Game Boy CPU with LCD STAT interrupt path.",
    },
    "chips_spc700": {
        "mfg_date_start": "1990-11",
        "mfg_date_end": "1998-12",
        "discontinued": "1998-12",
        "socket": "QFP-80",
        "package": "QFP-80",
        "pins": 80,
        "country": "Japan",
        "featured": True,
        "curator_note": "CHIPS hot path — Sony SPC700 SNES audio sub-CPU with 64KB SRAM and BRR decode.",
    },
}

FEATURED_MISSING_ENTRIES: dict[str, dict[str, Any]] = {
    "mame_i80386": {
        "mfg_date_start": "1985-10",
        "mfg_date_end": "2007-09",
        "discontinued": "2007-09",
        "socket": "Socket 2/3",
        "package": "PGA-132",
        "pins": 132,
        "country": "USA",
        "featured": True,
        "curator_note": "MAME imprint die — Intel 80386DX 32-bit protected-mode multitasking era.",
    },
    "mame_pentium_mmx": {
        "mfg_date_start": "1997-01",
        "mfg_date_end": "1999-06",
        "discontinued": "1999-06",
        "socket": "Socket 7",
        "package": "PGA-321",
        "pins": 321,
        "country": "USA",
        "featured": True,
        "curator_note": "MAME imprint die — Pentium MMX P55C; SIMD debut on Socket 7 desktop.",
    },
    "mame_wdc65816": {
        "mfg_date_start": "1983-03",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "MAME WDC 65C816 — CMOS 16-bit 6502 lineage for SNES and Apple IIGS.",
    },
    "mame_r3000": {
        "mfg_date_start": "1988-06",
        "mfg_date_end": "2005-12",
        "discontinued": "2005-12",
        "socket": "PGA-179",
        "package": "PGA-179",
        "pins": 179,
        "country": "USA",
        "featured": True,
        "curator_note": "MIPS R3000A — PlayStation and early RISC workstation CPU, 33MHz class.",
    },
    "mame_arm7": {
        "mfg_date_start": "1994-09",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "LQFP-64",
        "package": "LQFP-64",
        "pins": 64,
        "country": "UK",
        "featured": True,
        "curator_note": "ARM7TDMI — 32-bit RISC macrocell for Game Boy Advance and embedded SoCs.",
    },
    "mame_sh4": {
        "mfg_date_start": "1997-09",
        "mfg_date_end": "2005-12",
        "discontinued": "2005-12",
        "socket": "QFP-120",
        "package": "QFP-120",
        "pins": 120,
        "country": "Japan",
        "featured": True,
        "curator_note": "Hitachi SH-4 SH7750 — Dreamcast main CPU, superscalar RISC with FPU.",
    },
    "mame_huc6280": {
        "mfg_date_start": "1987-10",
        "mfg_date_end": "1995-12",
        "discontinued": "1995-12",
        "socket": "QFP-80",
        "package": "QFP-80",
        "pins": 80,
        "country": "Japan",
        "featured": True,
        "curator_note": "Hudson HuC6280 — PC Engine/TurboGrafx-16 CPU with on-die PSG and timer block.",
    },
    "mame_i8086": {
        "mfg_date_start": "1978-06",
        "mfg_date_end": "1998-09",
        "discontinued": "1998-09",
        "socket": "DIP-40",
        "package": "Ceramic DIP",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "MAME imprint die — Intel 8086 16-bit ISA origin for IBM PC architecture.",
    },
    "mame_i8088": {
        "mfg_date_start": "1979-06",
        "mfg_date_end": "1998-09",
        "discontinued": "1998-09",
        "socket": "DIP-40",
        "package": "Ceramic DIP",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "MAME imprint die — Intel 8088 8-bit external bus variant in original IBM PC.",
    },
    "coco_sn76489": {
        "mfg_date_start": "1978-12",
        "mfg_date_end": "1995-08",
        "discontinued": "1995-08",
        "socket": "DIP-16",
        "package": "DIP-16",
        "pins": 16,
        "country": "USA",
        "featured": True,
        "curator_note": "TI SN76489N on Tandy Color Computer — three square-wave PSG channels.",
    },
    "mame_sid6526": {
        "mfg_date_start": "1982-08",
        "mfg_date_end": "1994-06",
        "discontinued": "1994-06",
        "socket": "DIP-28",
        "package": "DIP-28",
        "pins": 28,
        "country": "USA",
        "featured": True,
        "curator_note": "MOS 6581 SID — Commodore 64 sound interface device with analog filter.",
    },
    "amd_am486dx4": {
        "mfg_date_start": "1994-03",
        "mfg_date_end": "1999-06",
        "discontinued": "1999-06",
        "socket": "Socket 3",
        "package": "PGA-168",
        "pins": 168,
        "country": "USA",
        "featured": True,
        "curator_note": "AMD Am486DX4 — 3× clock 486 on Socket 3; write-back cache on later steppings.",
    },
    "intel_80387dx": {
        "mfg_date_start": "1987-04",
        "mfg_date_end": "1998-06",
        "discontinued": "1998-06",
        "socket": "PGA-68",
        "package": "PGA-68",
        "pins": 68,
        "country": "USA",
        "featured": True,
        "curator_note": "Intel 80387DX — external x87 FPU companion for 386DX systems.",
    },
    "nec_v30": {
        "mfg_date_start": "1983-06",
        "mfg_date_end": "1998-06",
        "discontinued": "1998-06",
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "Japan",
        "featured": True,
        "curator_note": "NEC V30 μPD70116 — 8086-compatible CPU popular in Japanese PC-9800 line.",
    },
    "wdc_65c02": {
        "mfg_date_start": "1983-03",
        "mfg_date_end": None,
        "discontinued": None,
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "WDC 65C02 — CMOS 6502 with extra opcodes; Apple IIc/IIe and NES clone cores.",
    },
    "intel_i960": {
        "mfg_date_start": "1988-07",
        "mfg_date_end": "2007-03",
        "discontinued": "2007-03",
        "socket": "BGA-304",
        "package": "BGA-304",
        "pins": 304,
        "country": "USA",
        "featured": True,
        "curator_note": "Intel i960CA — 32-bit RISC for embedded RAID and I/O processor boards.",
    },
    "intel_i860": {
        "mfg_date_start": "1989-02",
        "mfg_date_end": "2002-08",
        "discontinued": "2002-08",
        "socket": "PGA-168",
        "package": "PGA-168",
        "pins": 168,
        "country": "USA",
        "featured": True,
        "curator_note": "Intel i860XR — VLIW numeric processor; early 3D graphics and HPC experiments.",
    },
    "weitek_1167": {
        "mfg_date_start": "1988-06",
        "mfg_date_end": "1995-12",
        "discontinued": "1995-12",
        "socket": "PGA-121",
        "package": "PGA-121",
        "pins": 121,
        "country": "USA",
        "featured": True,
        "curator_note": "Weitek 1167 — IEEE-754 floating-point accelerator for 386/486 workstations.",
    },
    "ti_tms9918a": {
        "mfg_date_start": "1979-06",
        "mfg_date_end": "1995-12",
        "discontinued": "1995-12",
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "USA",
        "featured": True,
        "curator_note": "TI TMS9918A VDP — MSX, ColecoVision, and TI-99/4A tile/sprite video chip.",
    },
    "yamaha_v9938": {
        "mfg_date_start": "1988-06",
        "mfg_date_end": "1995-12",
        "discontinued": "1995-12",
        "socket": "QFP-64",
        "package": "QFP-64",
        "pins": 64,
        "country": "Japan",
        "featured": True,
        "curator_note": "Yamaha V9938 VDP — MSX2 80-column and bitmap graphics upgrade over TMS9918.",
    },
    "yamaha_ym2149": {
        "mfg_date_start": "1978-06",
        "mfg_date_end": "1998-12",
        "discontinued": "1998-12",
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "Japan",
        "featured": True,
        "curator_note": "Yamaha YM2149F PSG — Atari ST and MSX square/noise/envelope sound chip.",
    },
    "oki_m6295": {
        "mfg_date_start": "1989-06",
        "mfg_date_end": "2005-12",
        "discontinued": "2005-12",
        "socket": "QFP-44",
        "package": "QFP-44",
        "pins": 44,
        "country": "Japan",
        "featured": True,
        "curator_note": "OKI M6295 — four-channel ADPCM playback for Neo Geo and arcade boards.",
    },
    "konami_052001": {
        "mfg_date_start": "1988-06",
        "mfg_date_end": "1998-12",
        "discontinued": "1998-12",
        "socket": "DIP-64",
        "package": "DIP-64",
        "pins": 64,
        "country": "Japan",
        "featured": True,
        "curator_note": "Konami 052001 SCC — sound chip with wavetable extension for MSX and arcade.",
    },
    "capcom_cps_b_a": {
        "mfg_date_start": "1989-05",
        "mfg_date_end": "1995-12",
        "discontinued": "1995-12",
        "socket": "DIP-40",
        "package": "DIP-40",
        "pins": 40,
        "country": "Japan",
        "featured": True,
        "curator_note": "Capcom CPS-B-A — CPS-1 board I/O and protection glue ASIC.",
    },
    "taito_tc0100scn": {
        "mfg_date_start": "1992-06",
        "mfg_date_end": "2004-06",
        "discontinued": "2004-06",
        "socket": "QFP-160",
        "package": "QFP-160",
        "pins": 160,
        "country": "Japan",
        "featured": True,
        "curator_note": "Taito TC0100SCN — F3 system tilemap and scroll engine ASIC.",
    },
    "mitsubishi_m37702": {
        "mfg_date_start": "1993-06",
        "mfg_date_end": "2003-12",
        "discontinued": "2003-12",
        "socket": "QFP-128",
        "package": "QFP-128",
        "pins": 128,
        "country": "Japan",
        "featured": True,
        "curator_note": "Mitsubishi M37702 — Capcom CPS-2 main CPU with on-chip QSound DMA path.",
    },
    "ensoniq_esp_r2": {
        "mfg_date_start": "1994-08",
        "mfg_date_end": "2002-08",
        "discontinued": "2002-08",
        "socket": "QFP-100",
        "package": "QFP-100",
        "pins": 100,
        "country": "USA",
        "featured": True,
        "curator_note": "Ensoniq ESP-R2 OTIS — ADPCM wavetable engine for arcade and PCI sound cards.",
    },
    "ti_tms34010": {
        "mfg_date_start": "1986-06",
        "mfg_date_end": "1998-12",
        "discontinued": "1998-12",
        "socket": "PGA-179",
        "package": "PGA-179",
        "pins": 179,
        "country": "USA",
        "featured": True,
        "curator_note": "TI TMS34010 GSP — graphics system processor for NCR and arcade framebuffer boards.",
    },
    "xilinx_xc2064": {
        "mfg_date_start": "1985-06",
        "mfg_date_end": "1995-12",
        "discontinued": "1995-12",
        "socket": "PLCC-68",
        "package": "PLCC-68",
        "pins": 68,
        "country": "USA",
        "featured": True,
        "curator_note": "Xilinx XC2064 — world's first commercial SRAM FPGA, 64 configurable logic blocks.",
    },
    "altera_ep300": {
        "mfg_date_start": "1984-08",
        "mfg_date_end": "1992-12",
        "discontinued": "1992-12",
        "socket": "DIP-24",
        "package": "DIP-24",
        "pins": 24,
        "country": "USA",
        "featured": True,
        "curator_note": "Altera EP300 — first reprogrammable EPLD; DIP-24 fuse-era logic array.",
    },
    "lattice_isp1016": {
        "mfg_date_start": "1990-06",
        "mfg_date_end": "2005-12",
        "discontinued": "2005-12",
        "socket": "PLCC-44",
        "package": "PLCC-44",
        "pins": 44,
        "country": "USA",
        "featured": True,
        "curator_note": "Lattice ispLSI1016 — first in-system programmable CPLD with JTAG boundary scan.",
    },
    "actel_a1020b": {
        "mfg_date_start": "1990-03",
        "mfg_date_end": "2002-08",
        "discontinued": "2002-08",
        "socket": "PLCC-84",
        "package": "PLCC-84",
        "pins": 84,
        "country": "USA",
        "featured": True,
        "curator_note": "Actel A1020B — antifuse FPGA for rad-hard and one-time-programmed designs.",
    },
    "xilinx_virtex_ii_pro": {
        "mfg_date_start": "2002-01",
        "mfg_date_end": "2012-08",
        "discontinued": "2012-08",
        "socket": "BGA-1156",
        "package": "BGA-1156",
        "pins": 1156,
        "country": "USA",
        "featured": True,
        "curator_note": "Xilinx Virtex-II Pro XC2VP50 — embedded PowerPC 405 and RocketIO transceivers.",
    },
    "yamaha_ym2610": {
        "mfg_date_start": "1990-04",
        "mfg_date_end": "2004-06",
        "discontinued": "2004-06",
        "socket": "DIP-64",
        "package": "DIP-64",
        "pins": 64,
        "country": "Japan",
        "featured": True,
        "curator_note": "Yamaha YM2610 OPNB — Neo Geo FM+ADPCM sound with four FM and three PCM channels.",
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _combinatronic_index() -> dict[str, dict[str, Any]]:
    doc = _load_json(COMBINATRONIC_PATH)
    return {str(chip["id"]): chip for chip in doc.get("chips", []) if chip.get("id")}


def _package_label(chip: dict[str, Any]) -> str | None:
    package = str(chip.get("package") or "").strip().lower()
    pins = chip.get("pins")
    if not package:
        return None
    if package == "dip" and pins:
        return f"DIP-{pins}"
    if package == "pga" and pins:
        return f"PGA-{pins}"
    if package == "qfp" and pins:
        return f"QFP-{pins}"
    if package == "plcc" and pins:
        return f"PLCC-{pins}"
    if package == "bga" and pins:
        return f"BGA-{pins}"
    if package == "slot":
        return "Slot 1 cartridge"
    return package.upper()


def _apply_catalog_overrides(entry: dict[str, Any], chip: dict[str, Any] | None) -> dict[str, Any]:
    if not chip:
        return entry
    out = dict(entry)
    if chip.get("socket"):
        out["socket"] = chip["socket"]
    pkg = _package_label(chip)
    if pkg:
        out["package"] = pkg
    if chip.get("pins") is not None:
        out["pins"] = chip["pins"]
    return out


def _featured_missing_ids(combinatronic: dict[str, dict[str, Any]], entries: dict[str, Any]) -> list[str]:
    return sorted(
        chip_id
        for chip_id, chip in combinatronic.items()
        if chip.get("featured") and chip_id not in entries
    )


def enrich_curation(*, dry_run: bool = False) -> dict[str, Any]:
    doc = _load_json(CURATION_PATH)
    entries: dict[str, Any] = dict(doc.get("entries") or {})
    before_count = len(entries)
    combinatronic = _combinatronic_index()

    added: list[str] = []
    for chip_id, payload in {**CHIPS_HOT_ENTRIES, **FEATURED_MISSING_ENTRIES}.items():
        if chip_id in entries:
            continue
        entry = _apply_catalog_overrides(payload, combinatronic.get(chip_id))
        entries[chip_id] = entry
        added.append(chip_id)

    doc["entries"] = dict(sorted(entries.items()))
    if not dry_run:
        _save_json(CURATION_PATH, doc)

    still_missing = _featured_missing_ids(combinatronic, entries)
    return {
        "added_count": len(added),
        "added_ids": added,
        "final_count": len(entries),
        "before_count": before_count,
        "still_missing_featured": still_missing,
        "chips_hot_added": [cid for cid in added if cid in CHIPS_HOT_IDS],
        "featured_added": [cid for cid in added if cid in FEATURED_MISSING_ENTRIES],
        "dry_run": dry_run,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Compute changes without writing JSON")
    args = parser.parse_args()

    result = enrich_curation(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())