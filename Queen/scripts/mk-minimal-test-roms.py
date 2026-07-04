#!/usr/bin/env python3
"""Generate minimal legal homebrew QA ROM stubs for CHIPS load tests."""
from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
RTX = Path(os.environ.get("AMOURANTHRTX_ROOT", NEXUS.parent / ".pages-hub-AMOURANTHRTX"))
MANIFEST = QUEEN / "data" / "queen-test-roms.json"


def _incoming_roots() -> list[Path]:
    return [
        NEXUS / "assets" / "dos" / "incoming",
        RTX / "assets" / "dos" / "incoming",
        QUEEN / "build" / "rtx" / "bin" / "Kilroy" / "assets" / "dos" / "incoming",
    ]


def mk_snes() -> bytes:
    rom = bytearray(32768)
    rom[0x7FC0:0x7FC0 + 21] = b"Queen SNES QA ROM  "
    rom[0x7FDC] = 0x20
    rom[0x7FDD] = 0x80
    rom[0x7FDE] = 0x00
    rom[0x7FDF] = 0x80
    return bytes(rom)


def mk_genesis() -> bytes:
    rom = bytearray(4096)
    rom[0x100:0x104] = b"SEGA"
    rom[0x180:0x190] = b"QUEEN GEN QA      "
    return bytes(rom)


def mk_sms() -> bytes:
    rom = bytearray(32768)
    rom[0:8] = b"Tmr Sega"
    rom[8:0x4000] = bytes([0xFF] * (0x4000 - 8))
    return bytes(rom)


def mk_a2600() -> bytes:
    rom = bytearray(4096)
    rom[0xFFC] = 0x00
    rom[0xFFD] = 0xF0
    rom[0xF0] = 0x4C
    rom[0xF1] = 0xF0
    rom[0xF2] = 0xFF
    return bytes(rom)


BUILDERS = {
    "snes": ("snes-test.smc", mk_snes),
    "genesis": ("genesis-test.bin", mk_genesis),
    "sms": ("sms-test.sms", mk_sms),
    "a2600": ("a2600-test.a26", mk_a2600),
}


def main() -> int:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for sys_id, (fname, fn) in BUILDERS.items():
        spec = (doc.get("systems") or {}).get(sys_id) or {}
        fname = str(spec.get("filename") or fname)
        blob = fn()
        written = []
        for root in _incoming_roots():
            d = root / sys_id
            d.mkdir(parents=True, exist_ok=True)
            out = d / fname
            out.write_bytes(blob)
            written.append(str(out))
        rows.append({"system": sys_id, "ok": True, "filename": fname, "bytes": len(blob), "written": written})
        print(json.dumps(rows[-1]))
    print(json.dumps({"schema": "queen-minimal-test-roms/v1", "ok": True, "built": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())