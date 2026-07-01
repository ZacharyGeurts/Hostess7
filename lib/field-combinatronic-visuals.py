#!/usr/bin/env pythong
"""Combinatronic visuals — precise chip macro renders, Explaining X book covers, H7 manuals."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
QUEEN = INSTALL / "Queen"
CATALOG = INSTALL / "data" / "field-combinatronic-chip-catalog.json"
SEED = INSTALL / "data" / "field-program-combinatronic-seed.json"
DOCTRINE = INSTALL / "data" / "field-combinatronic-visuals-doctrine.json"
MANIFEST = INSTALL / "data" / "field-combinatronic-visuals-manifest.json"
REGISTRY = INSTALL / "data" / "field-combinatronic-visuals-registry.json"
ASSETS = INSTALL / "data" / "combinatronic-visuals"
CHIPS_DIR = ASSETS / "chips"
CHIPS_THUMBS_DIR = CHIPS_DIR / "thumbs"
CHIPS_DETAIL_DIR = CHIPS_DIR / "detail"
IRONCLAD_CHIPS = STATE / "field-ironclad-chips-combinatorics.json"
BOOKS_DIR = ASSETS / "books"
WORLD_ASSETS = QUEEN / "world" / "assets" / "combinatronic"
LIBRARY_SHELF = INSTALL / "library" / "dewey" / "000-computer-science"
PANEL = STATE / "field-combinatronic-visuals-panel.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
H7_MAGICS = (b"H7B\x01", b"H7B\x02")
H7C_MAGICS = (b"H7C\x01", b"H7C\x02", b"H7C\x03", b"H7C\x04")

LANG_LABELS: dict[str, str] = {
    "c": "C",
    "cxx": "C++",
    "python": "Python",
    "rust": "Rust",
    "go": "Go",
    "zig": "Zig",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "sql": "SQL",
    "shell": "Shell",
    "asm": "Assembly",
    "fortran": "Fortran",
    "haskell": "Haskell",
    "lisp": "Lisp",
    "ruby": "Ruby",
    "php": "PHP",
    "lua": "Lua",
    "csharp": "C#",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "cobol": "COBOL",
    "prolog": "Prolog",
    "verilog": "Verilog",
    "ada": "Ada",
    "objc": "Objective-C",
    "d": "D",
    "elixir": "Elixir",
    "erlang": "Erlang",
    "scala": "Scala",
    "perl": "Perl",
    "r": "R",
    "julia": "Julia",
    "ocaml": "OCaml",
    "clojure": "Clojure",
    "matlab": "MATLAB",
    "nim": "Nim",
    "dart": "Dart",
    "field": "Field",
    "ammolang": "AmmoLang",
    "basic": "BASIC",
    "qbasic": "QBasic",
    "quickbasic": "QuickBASIC",
    "freebasic": "FreeBASIC",
    "pascal": "Pascal",
    "turbo_pascal": "Turbo Pascal",
    "delphi": "Delphi",
    "modula2": "Modula-2",
    "smalltalk": "Smalltalk",
    "forth": "Forth",
    "apl": "APL",
    "visual_basic": "Visual Basic",
    "vba": "VBA",
    "algol": "Algol",
    "snobol": "SNOBOL",
    "cobol_copy": "COBOL COPY",
    "linux": "Linux",
    "economics": "Economics",
}

LANG_ACCENT: dict[str, tuple[int, int, int]] = {
    "python": (55, 118, 171),
    "rust": (222, 99, 52),
    "go": (0, 173, 216),
    "javascript": (247, 223, 30),
    "typescript": (49, 120, 198),
    "c": (85, 85, 85),
    "cxx": (0, 90, 156),
    "java": (237, 139, 0),
    "ruby": (204, 52, 45),
    "qbasic": (0, 128, 0),
    "pascal": (0, 64, 128),
    "turbo_pascal": (0, 48, 96),
    "basic": (0, 128, 128),
    "ammolang": (96, 32, 128),
    "linux": (252, 198, 45),
    "economics": (46, 139, 87),
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _chip_ids() -> list[str]:
    catalog = _load(CATALOG, {})
    return [str(c["id"]) for c in catalog.get("chips") or [] if c.get("id")]


def _ironclad_chip_ids() -> list[str]:
    doc = _load(IRONCLAD_CHIPS, {})
    return [str(c["id"]) for c in doc.get("chips") or [] if c.get("id")]


def _ironclad_chip_row(chip_id: str) -> dict[str, Any] | None:
    doc = _load(IRONCLAD_CHIPS, {})
    for row in doc.get("chips") or []:
        if str(row.get("id")) == chip_id:
            return dict(row)
    return None


def _catalog_chip(chip_id: str) -> dict[str, Any] | None:
    catalog = _load(CATALOG, {})
    for row in catalog.get("chips") or []:
        if str(row.get("id")) == chip_id:
            return dict(row)
    return None


_KIND_VISUAL_DEFAULTS: dict[str, dict[str, Any]] = {
    "host_cpu": {"package": "pga", "pins": 168, "body": "#1a1a1a", "socket": "CPU socket"},
    "guest_cpu": {"package": "dip", "pins": 40, "body": "#1c1c1c", "socket": "DIP-40"},
    "mame_device": {"package": "dip", "pins": 40, "body": "#222228", "socket": "DIP-40"},
    "chips_hot": {"package": "dip", "pins": 40, "body": "#1a1a1a", "socket": "DIP-40"},
    "soc": {"package": "qfp", "pins": 208, "body": "#252530", "socket": "BGA/QFP"},
    "gpu": {"package": "qfp", "pins": 256, "body": "#1a1a22", "socket": "BGA"},
    "logic": {"package": "dip", "pins": 14, "body": "#1a1a18", "socket": "DIP-14"},
    "memory": {"package": "dip", "pins": 32, "body": "#22221a", "socket": "DIP-32"},
    "analog": {"package": "dip", "pins": 16, "body": "#1c1c20", "socket": "DIP-16"},
    "sound": {"package": "dip", "pins": 28, "body": "#1a1a1a", "socket": "DIP-28"},
    "video": {"package": "dip", "pins": 40, "body": "#1a1a1a", "socket": "DIP-40"},
    "network": {"package": "plcc", "pins": 68, "body": "#252528", "socket": "PLCC-68"},
    "northbridge": {"package": "qfp", "pins": 304, "body": "#222228", "socket": "BGA"},
    "southbridge": {"package": "qfp", "pins": 208, "body": "#222228", "socket": "BGA"},
    "super_io": {"package": "qfp", "pins": 128, "body": "#282830", "socket": "QFP-128"},
    "chipset": {"package": "dip", "pins": 28, "body": "#222228", "socket": "DIP-28"},
    "fpga": {"package": "plcc", "pins": 84, "body": "#1a2028", "socket": "PLCC-84"},
    "dsp": {"package": "qfp", "pins": 144, "body": "#1c1c22", "socket": "QFP-144"},
    "coprocessor": {"package": "dip", "pins": 68, "body": "#1a1a1a", "socket": "DIP-68"},
    "fab": {"package": "qfp", "pins": 0, "body": "#303038", "socket": "wafer die"},
    "glue": {"package": "plcc", "pins": 84, "body": "#222228", "socket": "PLCC-84"},
    "pio": {"package": "dip", "pins": 24, "body": "#1c1c1c", "socket": "DIP-24"},
    "fdc": {"package": "dip", "pins": 40, "body": "#1a1a1a", "socket": "DIP-40"},
    "mmu": {"package": "dip", "pins": 40, "body": "#222228", "socket": "DIP-40"},
    "isa_platform": {"package": "dip", "pins": 40, "body": "#1a1a1a", "socket": "ISA"},
    "arcade_asic": {"package": "dip", "pins": 40, "body": "#1a1a1a", "socket": "DIP-40"},
}

_KIND_SCHEMATIC_DEFAULTS: dict[str, str] = {
    "host_cpu": "Fetch → decode → dispatch → ALU/FPU → L1 · bus · MMU · interrupt controller",
    "guest_cpu": "Opcode fetch · address latch · ALU · flags · IRQ/NMI acknowledge",
    "mame_device": "MAME device bus · clock domain · memory map hook · save-state leaf",
    "chips_hot": "Hot-path dispatch vector · register file · cycle-accurate timing band",
    "soc": "CPU cluster · GPU tile · NPU/ISP · memory controller · I/O PHY south",
    "gpu": "Command processor · shader cores · ROP · VRAM controller · display PHY",
    "logic": "Combinatorial gates · propagation delay · fan-in/out · truth table",
    "memory": "Address decode · row/column · sense amp · refresh · bus timing",
    "analog": "Op-amp stages · reference · comparator · filter network",
    "sound": "FM/PSG/wavetable channels · mixer · envelope · DAC output",
    "video": "Tile/sprite fetch · palette · scanline IRQ · composite/RGB encoder",
    "network": "MAC · PHY · DMA ring · packet buffer · IRQ coalesce",
    "northbridge": "CPU front-side bus · AGP/PCIe root · DRAM controller",
    "southbridge": "PCI/ISA bridge · ACPI · LPC · SATA/USB legacy",
    "super_io": "Floppy · parallel · serial · keyboard · RTC · ACPI SCI",
    "chipset": "Address decode · glue logic · wait-state generator · IRQ router",
    "fpga": "LUT fabric · routing · DSP slices · PLL · transceivers",
    "dsp": "MAC array · program/data memory · DMA · serial I/O",
    "coprocessor": "FPU/MMU extension · opcode decode · register file · bus master",
    "fab": "Wafer die · process node · reticle · yield bin",
    "glue": "Timer · IRQ · DMA glue · board-specific ASIC",
    "pio": "Parallel port latch · handshake · IRQ on strobe",
    "fdc": "MFM/FM decode · DMA · index pulse · drive select",
    "mmu": "TLB · page tables · protection bits · TLB shootdown",
    "isa_platform": "ISA slot decode · wait states · IRQ/DMA cascade",
    "arcade_asic": "Board timing · sprite priority · scanline counter · coin/IRQ glue",
}

_DESIGN_OVER_STANDARD = (
    "Field catalog: pink felt #d4899a macro on #080808 — exact imprint + pin geometry from seed, "
    "not stock clip art. Combinatronics assigns path_pct band; ironclad detail adds vendor/kind/era. "
    "Differs from datasheet photos: package type drives render (PGA/QFP/DIP/BGA), pin count is authoritative."
)

CPU_LIBRARY_SEED = INSTALL / "data" / "field-cpu-library-seed.json"


def _cpu_library_row(chip_id: str) -> dict[str, Any] | None:
    seed = _load(CPU_LIBRARY_SEED, {})
    for row in seed.get("detailed") or []:
        if str(row.get("id")) == chip_id:
            return dict(row)
    return None


def _kind_schematic(kind: str, label: str, *, pins: int = 0, package: str = "") -> str:
    base = _KIND_SCHEMATIC_DEFAULTS.get(kind) or _KIND_SCHEMATIC_DEFAULTS["mame_device"]
    pin_bit = f" · {pins}-pin {package.upper()}" if pins and package else ""
    return f"{label}{pin_bit} — {base}"


def _catalog_design_over_standard(chip_row: dict[str, Any]) -> str:
    custom = str(chip_row.get("design_over_standard") or "").strip()
    if custom:
        return custom
    pins = chip_row.get("pins")
    package = str(chip_row.get("package") or "dip")
    kind = str(chip_row.get("kind") or "mame_device").replace("_", " ")
    extra = ""
    cpu = _cpu_library_row(str(chip_row.get("id") or ""))
    if cpu and cpu.get("ai_detail"):
        extra = f" CPU library: {cpu['ai_detail']}"
    return f"{_DESIGN_OVER_STANDARD} This die: {kind}, {pins} pins, {package.upper()}.{extra}"


def enrich_chip_catalog(*, write: bool = False) -> dict[str, Any]:
    """Verify featured render overlay — schematic/design computed at render, not stored in catalog."""
    icc = _import_py(INSTALL / "lib" / "field-ironclad-chips-combinatorics.py", "icc_vis_enrich")
    if icc and hasattr(icc, "clean_catalog_render_layer") and write:
        icc.clean_catalog_render_layer(write=True)
    catalog = _load(CATALOG, {})
    iron_ids = set(_ironclad_chip_ids())
    chips = catalog.get("chips") or []
    missing: list[str] = []
    stripped = 0
    for row in chips:
        cid = str(row.get("id") or "")
        if cid and iron_ids and cid not in iron_ids:
            missing.append(cid)
        for drop in ("schematic_blueprint", "design_over_standard", "note", "source"):
            if drop in row:
                row.pop(drop, None)
                stripped += 1
    if write and stripped:
        catalog["role"] = "featured_render_overlay"
        catalog["truth_source"] = "field-ironclad-chips-combinatorics.json"
        _save(CATALOG, catalog)
    return {
        "ok": len(missing) == 0,
        "chip_count": len(chips),
        "role": catalog.get("role") or "featured_render_overlay",
        "missing_in_ironclad": missing[:24],
        "stripped_stored_truth": stripped,
        "note": "schematic/design_over_standard render-time only via _chip_visual_spec",
    }


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _parse_note_visuals(note: str | None) -> dict[str, Any]:
    if not note:
        return {}
    out: dict[str, Any] = {}
    pkg = re.search(r"package\s*=\s*(\w+)", note, re.I)
    pins = re.search(r"pins\s*=\s*(\d+)", note, re.I)
    if pkg:
        out["package"] = pkg.group(1).lower()
    if pins:
        out["pins"] = int(pins.group(1))
    return out


def _build_chip_imprint(chip_row: dict[str, Any], catalog_row: dict[str, Any] | None = None) -> list[str]:
    if catalog_row and catalog_row.get("imprint"):
        return [str(x) for x in catalog_row["imprint"]]
    lines: list[str] = []
    vendor = str(chip_row.get("vendor") or "").strip()
    label = str(chip_row.get("label") or chip_row.get("id") or "CHIP").strip()
    if vendor and vendor not in ("—", "-", "?"):
        lines.append(vendor.upper()[:18])
    if label:
        lines.append(label[:22])
    mhz = chip_row.get("mhz")
    bits = chip_row.get("bits")
    era = chip_row.get("era")
    if mhz:
        lines.append(f"{mhz}MHz")
    if bits:
        lines.append(f"{bits}-bit")
    if era:
        lines.append(f"©{era}")
    kind = str(chip_row.get("kind") or "")
    if kind and len(lines) < 4:
        lines.append(kind.replace("_", " ").upper()[:16])
    if not lines:
        lines.append(str(chip_row.get("id", "CHIP"))[:18])
    return lines[:5]


def _chip_visual_spec(chip_id: str, chip_row: dict[str, Any] | None = None) -> dict[str, Any]:
    """Derive package/pins/body/imprint from ironclad row, catalog, or kind defaults."""
    row = chip_row or _ironclad_chip_row(chip_id) or {}
    catalog_row = _catalog_chip(chip_id)
    kind = str(row.get("kind") or "mame_device")
    defaults = dict(_KIND_VISUAL_DEFAULTS.get(kind) or _KIND_VISUAL_DEFAULTS["mame_device"])
    note_vis = _parse_note_visuals(row.get("note"))
    spec: dict[str, Any] = {
        "id": chip_id,
        "label": row.get("label") or ((catalog_row or {}).get("label")) or chip_id,
        "vendor": row.get("vendor") or (catalog_row or {}).get("vendor") or "—",
        "kind": kind,
        "family": row.get("family"),
        "era": row.get("era"),
        "mhz": row.get("mhz"),
        "bits": row.get("bits"),
        "note": row.get("note"),
        "source": row.get("source"),
        "mame_device": row.get("mame_device"),
        "package": str((catalog_row or {}).get("package") or note_vis.get("package") or defaults.get("package") or "dip"),
        "pins": int((catalog_row or {}).get("pins") or note_vis.get("pins") or defaults.get("pins") or 40),
        "body": str((catalog_row or {}).get("body") or defaults.get("body") or "#1a1a1a"),
        "socket": str((catalog_row or {}).get("socket") or defaults.get("socket") or ""),
        "imprint": _build_chip_imprint(row, catalog_row),
    }
    if catalog_row:
        for key in ("schematic_blueprint", "design_over_standard", "kind", "family", "bits", "mhz", "era"):
            if catalog_row.get(key) is not None and spec.get(key) in (None, "", "—"):
                spec[key] = catalog_row[key]
    cpu = _cpu_library_row(chip_id)
    if cpu:
        if not spec.get("schematic_blueprint") and cpu.get("schematic_blueprint"):
            spec["schematic_blueprint"] = cpu["schematic_blueprint"]
        if not spec.get("design_over_standard") and cpu.get("ai_detail"):
            spec["design_over_standard"] = _catalog_design_over_standard({**spec, "design_over_standard": cpu["ai_detail"]})
    if not spec.get("schematic_blueprint"):
        spec["schematic_blueprint"] = _kind_schematic(
            str(spec.get("kind") or "mame_device"),
            str(spec.get("label") or chip_id),
            pins=int(spec.get("pins") or 0),
            package=str(spec.get("package") or "dip"),
        )
    if not spec.get("design_over_standard"):
        spec["design_over_standard"] = _catalog_design_over_standard(spec)
    if kind == "fab":
        spec["package"] = "die"
        spec["pins"] = 0
    return spec


def _lang_ids() -> list[str]:
    seed = _load(SEED, {})
    return sorted((seed.get("language_packs") or {}).keys())


def _expected_file_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chip_id in _chip_ids():
        rows.append(
            {
                "pattern": "chip_png",
                "chip_id": chip_id,
                "path": _rel(CHIPS_DIR / f"{chip_id}.png"),
                "repair_cmd": f"chip {chip_id}",
            }
        )
        rows.append(
            {
                "pattern": "chip_mirror",
                "chip_id": chip_id,
                "path": _rel(WORLD_ASSETS / "chips" / f"{chip_id}.png"),
                "repair_cmd": "repair mirror",
                "mirror_of": _rel(CHIPS_DIR / f"{chip_id}.png"),
            }
        )
    for chip_id in _ironclad_chip_ids():
        rows.append(
            {
                "pattern": "chip_thumb_png",
                "chip_id": chip_id,
                "path": _rel(CHIPS_THUMBS_DIR / f"{chip_id}.png"),
                "repair_cmd": f"ironclad-chip {chip_id}",
            }
        )
        rows.append(
            {
                "pattern": "chip_detail_png",
                "chip_id": chip_id,
                "path": _rel(CHIPS_DETAIL_DIR / f"{chip_id}.png"),
                "repair_cmd": f"ironclad-chip {chip_id}",
            }
        )
        rows.append(
            {
                "pattern": "chip_thumb_mirror",
                "chip_id": chip_id,
                "path": _rel(WORLD_ASSETS / "chips" / "thumbs" / f"{chip_id}.png"),
                "repair_cmd": "repair mirror ironclad",
                "mirror_of": _rel(CHIPS_THUMBS_DIR / f"{chip_id}.png"),
            }
        )
        rows.append(
            {
                "pattern": "chip_detail_mirror",
                "chip_id": chip_id,
                "path": _rel(WORLD_ASSETS / "chips" / "detail" / f"{chip_id}.png"),
                "repair_cmd": "repair mirror ironclad",
                "mirror_of": _rel(CHIPS_DETAIL_DIR / f"{chip_id}.png"),
            }
        )
    for lang_id in _lang_ids():
        book_id = f"explaining_{lang_id}"
        rows.append(
            {
                "pattern": "book_cover",
                "lang_id": lang_id,
                "path": _rel(BOOKS_DIR / f"{lang_id}.png"),
                "repair_cmd": f"book {lang_id}",
            }
        )
        rows.append(
            {
                "pattern": "book_mirror",
                "lang_id": lang_id,
                "path": _rel(WORLD_ASSETS / "books" / f"{lang_id}.png"),
                "repair_cmd": "repair mirror",
                "mirror_of": _rel(BOOKS_DIR / f"{lang_id}.png"),
            }
        )
        rows.append(
            {
                "pattern": "h7_manual",
                "lang_id": lang_id,
                "path": _rel(LIBRARY_SHELF / book_id / f"{book_id}.h7c"),
                "repair_cmd": f"book {lang_id}",
            }
        )
        rows.append(
            {
                "pattern": "book_json",
                "lang_id": lang_id,
                "path": _rel(LIBRARY_SHELF / book_id / "book.json"),
                "repair_cmd": f"book {lang_id}",
            }
        )
    rows.extend(
        [
            {"pattern": "manifest", "path": _rel(MANIFEST), "repair_cmd": "generate"},
            {"pattern": "registry", "path": _rel(REGISTRY), "repair_cmd": "registry"},
            {"pattern": "panel", "path": "field-combinatronic-visuals-panel.json", "root": "state", "repair_cmd": "manifest"},
            {"pattern": "chip_catalog", "path": _rel(CATALOG), "role": "source"},
            {"pattern": "ironclad_chips", "path": _rel(IRONCLAD_CHIPS), "role": "source", "root": "state"},
            {"pattern": "program_seed", "path": _rel(SEED), "role": "source"},
            {"pattern": "doctrine", "path": _rel(DOCTRINE), "role": "source"},
            {"pattern": "generator", "path": _rel(Path(__file__)), "role": "source"},
            {"pattern": "h7_packer", "path": "Hostess7/scripts/field_h7_book.py", "role": "source"},
        ]
    )
    return rows


def _resolve_row_path(row: dict[str, Any]) -> Path:
    if row.get("root") == "state":
        name = Path(row["path"]).name
        if name == "field-ironclad-chips-combinatorics.json":
            return IRONCLAD_CHIPS
        return STATE / name
    return INSTALL / row["path"]


def _classify_visual_storage(path: Path) -> dict[str, Any]:
    """Native PNG vs in-place H7s/H7 — magic + properties reveal true format."""
    vis = _import_mod("field_h7_visual", "field-h7-visual-adopt.py")
    if vis and hasattr(vis, "classify_visual_asset"):
        return vis.classify_visual_asset(path)
    if not path.is_file():
        return {"storage": "missing"}
    try:
        data = path.read_bytes()
    except OSError:
        return {"storage": "unreadable"}
    if len(data) >= 4:
        magic = data[:4]
        if magic == b"H7S\x01":
            return {"storage": "disguised_hostess7", "true_format": "h7s/1"}
        if magic == b"H7\x07\x01":
            return {"storage": "disguised_hostess7", "true_format": "h7/7"}
        if magic == b"H7E\x01":
            return {"storage": "disguised_hostess7", "true_format": "h7e/1"}
    h7 = _h7_module()
    if h7 and hasattr(h7, "classify_hostess7_blob"):
        cls = h7.classify_hostess7_blob(data)
        if cls.get("is_container"):
            return {"storage": "disguised_hostess7", "true_format": cls.get("format")}
    if data.startswith(PNG_MAGIC):
        return {"storage": "native_png", "true_format": "native"}
    return {"storage": "unknown"}


def _verify_png(path: Path, *, min_bytes: int = 3000) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "status": "missing"}
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"ok": False, "status": "unreadable", "error": str(exc)}
    if len(data) < 64:
        return {"ok": False, "status": "truncated", "bytes": len(data)}
    storage = _classify_visual_storage(path)
    if storage.get("storage") == "disguised_hostess7":
        fmt = storage.get("true_format") or "hostess7"
        return {
            "ok": True,
            "status": "ok",
            "storage": "disguised_hostess7",
            "true_format": fmt,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "face_format_id": storage.get("face_format_id"),
            "properties_only": True,
        }
    if len(data) < min_bytes:
        return {"ok": False, "status": "truncated", "bytes": len(data)}
    if not data.startswith(PNG_MAGIC):
        return {"ok": False, "status": "bad_magic", "bytes": len(data), "magic_hex": data[:4].hex()}
    return {
        "ok": True,
        "status": "ok",
        "storage": "native_png",
        "true_format": "native",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _h7c_module():
    path = INSTALL / "lib" / "field-h7c-compression.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7c_compression", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _verify_h7(path: Path) -> dict[str, Any]:
    """Verify Dewey manual — H7c primary; legacy H7 converts on open."""
    if not path.is_file():
        return {"ok": False, "status": "missing"}
    if path.suffix.lower() == ".h7":
        dewey = _import_mod("field_dewey_vis", "field-dewey-library.py")
        if dewey and hasattr(dewey, "ensure_h7c_path"):
            path = dewey.ensure_h7c_path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"ok": False, "status": "unreadable", "error": str(exc)}
    if os.environ.get("AML_INLINE") == "1" or os.environ.get("AML_TEST_DIRECT") == "1":
        if data[:4] in H7C_MAGICS and len(data) > 64:
            return {
                "ok": True,
                "status": "ok",
                "format": "h7c",
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "quick": True,
            }
    if data[:4] in H7C_MAGICS:
        mod = _h7c_module()
        if not mod:
            return {"ok": False, "status": "no_h7c_module", "bytes": len(data)}
        try:
            header, text, _stats = mod.decompress_h7c(data, verify=True)
        except Exception as exc:
            return {"ok": False, "status": "corrupt", "error": str(exc), "bytes": len(data)}
        return {
            "ok": True,
            "status": "ok",
            "format": "h7c",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "char_count": header.get("char_count") or len(text),
            "line_count": header.get("line_count"),
            "title": header.get("title"),
        }
    if data[:4] not in H7_MAGICS:
        return {"ok": False, "status": "bad_magic", "bytes": len(data)}
    mod = _h7_module()
    if not mod:
        return {"ok": False, "status": "no_h7_module", "bytes": len(data)}
    try:
        header, text = mod.unpack_h7(data, verify=True)
    except Exception as exc:
        return {"ok": False, "status": "corrupt", "error": str(exc), "bytes": len(data)}
    return {
        "ok": True,
        "status": "ok",
        "format": "h7",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "char_count": header.get("char_count"),
        "line_count": header.get("line_count"),
        "title": header.get("title"),
    }


def _verify_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "status": "missing"}
    try:
        doc = _load(path, default=None)
        if not isinstance(doc, dict):
            return {"ok": False, "status": "corrupt", "error": "unreadable"}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "corrupt", "error": str(exc)}
    return {"ok": True, "status": "ok", "bytes": path.stat().st_size, "sha256": _sha256_file(path), "schema": doc.get("schema")}


def _verify_row(row: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_row_path(row)
    pattern = row.get("pattern", "")
    if pattern in ("chip_png", "chip_thumb_png", "chip_detail_png", "book_cover", "chip_mirror", "book_mirror", "chip_thumb_mirror", "chip_detail_mirror"):
        if pattern == "chip_thumb_png":
            min_b = 1500
        elif pattern == "chip_detail_png":
            min_b = 12000
        elif "chip" in pattern:
            min_b = 8000
        else:
            min_b = 3000
        check = _verify_png(path, min_bytes=min_b)
    elif pattern == "h7_manual":
        check = _verify_h7(path)
    elif pattern in ("book_json", "manifest", "registry", "chip_catalog", "ironclad_chips", "program_seed", "doctrine"):
        check = _verify_json(path)
    elif pattern == "panel":
        check = _verify_json(path) if path.is_file() else {"ok": False, "status": "missing"}
    elif pattern == "generator":
        check = {"ok": path.is_file(), "status": "ok" if path.is_file() else "missing", "sha256": _sha256_file(path)}
    elif pattern == "h7_packer":
        p = INSTALL / row["path"]
        check = {"ok": p.is_file(), "status": "ok" if p.is_file() else "missing", "sha256": _sha256_file(p)}
    else:
        check = {"ok": path.is_file(), "status": "ok" if path.is_file() else "missing"}
    return {**row, "abs_path": str(path), "verify": check}


def inventory() -> dict[str, Any]:
    rows = [_verify_row(r) for r in _expected_file_rows()]
    required = [r for r in rows if r.get("pattern") != "panel"]
    ok = sum(1 for r in required if r.get("verify", {}).get("ok"))
    broken = [r for r in required if not r.get("verify", {}).get("ok")]
    return {
        "schema": "field-combinatronic-visuals-inventory/v1",
        "generated": _now(),
        "install_root": str(INSTALL),
        "state_dir": str(STATE),
        "total": len(rows),
        "required": len(required),
        "ok": ok,
        "broken": len(broken),
        "complete": len(broken) == 0,
        "rows": rows,
        "broken_rows": broken,
        "doctrine": _rel(DOCTRINE),
    }


def verify_all() -> dict[str, Any]:
    inv = inventory()
    return {
        "schema": "field-combinatronic-visuals-verify/v1",
        "ok": inv["complete"],
        "generated": inv["generated"],
        "total": inv["total"],
        "broken": inv["broken"],
        "broken_paths": [r["path"] for r in inv["broken_rows"]],
    }


def repair_mirror(*, ironclad: bool = False) -> dict[str, Any]:
    fixed: list[str] = []
    errors: list[dict[str, Any]] = []
    if not ironclad:
        for chip_id in _chip_ids():
            src = CHIPS_DIR / f"{chip_id}.png"
            if not src.is_file():
                errors.append({"path": _rel(src), "error": "source_missing"})
                continue
            _mirror_chip_asset(src)
            fixed.append(_rel(WORLD_ASSETS / "chips" / f"{chip_id}.png"))
    for chip_id in _ironclad_chip_ids():
        for variant, src_dir in (("thumbs", CHIPS_THUMBS_DIR), ("detail", CHIPS_DETAIL_DIR)):
            src = src_dir / f"{chip_id}.png"
            if not src.is_file():
                if ironclad:
                    errors.append({"path": _rel(src), "error": "source_missing"})
                continue
            _mirror_chip_asset(src, variant=variant)
            fixed.append(_rel(WORLD_ASSETS / "chips" / variant / f"{chip_id}.png"))
    for lang_id in _lang_ids():
        src = BOOKS_DIR / f"{lang_id}.png"
        if not src.is_file():
            errors.append({"path": _rel(src), "error": "source_missing"})
            continue
        _mirror_asset(src, "books")
        fixed.append(_rel(WORLD_ASSETS / "books" / f"{lang_id}.png"))
    return {"ok": not errors, "fixed": fixed, "errors": errors}


def repair_row(row: dict[str, Any]) -> dict[str, Any]:
    pattern = row.get("pattern", "")
    cmd = row.get("repair_cmd", "")
    try:
        if pattern in ("chip_png", "chip_mirror", "chip_thumb_png", "chip_detail_png", "chip_thumb_mirror", "chip_detail_mirror"):
            chip_id = row.get("chip_id")
            if not chip_id:
                return {"ok": False, "error": "no_chip_id"}
            if pattern in ("chip_thumb_png", "chip_detail_png", "chip_thumb_mirror", "chip_detail_mirror"):
                if pattern.endswith("_mirror"):
                    variant = "thumbs" if "thumb" in pattern else "detail"
                    src_dir = CHIPS_THUMBS_DIR if variant == "thumbs" else CHIPS_DETAIL_DIR
                    src = src_dir / f"{chip_id}.png"
                    if not src.is_file():
                        return generate_ironclad_chip(str(chip_id))
                    return {"ok": True, "mirrored": str(_mirror_chip_asset(src, variant=variant))}
                return generate_ironclad_chip(str(chip_id))
            if pattern == "chip_mirror":
                src = CHIPS_DIR / f"{chip_id}.png"
                if not src.is_file():
                    return generate_chip(chip_id)
                return {"ok": True, "mirrored": str(_mirror_chip_asset(src))}
            return generate_chip(chip_id)
        if pattern in ("book_cover", "book_mirror", "h7_manual", "book_json"):
            lang_id = row.get("lang_id")
            if not lang_id:
                return {"ok": False, "error": "no_lang_id"}
            if pattern == "book_mirror":
                src = BOOKS_DIR / f"{lang_id}.png"
                if not src.is_file():
                    return generate_book(lang_id)
                return {"ok": True, "mirrored": str(_mirror_asset(src, "books"))}
            return generate_book(lang_id)
        if pattern == "manifest":
            return generate_all()
        if pattern == "registry":
            return build_registry()
        if pattern == "panel":
            return visuals_panel()
        if cmd == "repair mirror":
            return repair_mirror()
    except Exception as exc:
        return {"ok": False, "path": row.get("path"), "error": str(exc)}
    return {"ok": False, "error": "unknown_pattern", "pattern": pattern}


def repair_all(*, only_broken: bool = True) -> dict[str, Any]:
    inv = inventory()
    targets = inv["broken_rows"] if only_broken else inv["rows"]
    results: list[dict[str, Any]] = []
    for row in targets:
        if row.get("role") == "source":
            continue
        results.append({**row, "repair": repair_row(row)})
    after = inventory()
    return {
        "schema": "field-combinatronic-visuals-repair/v1",
        "ok": after["complete"],
        "generated": _now(),
        "attempted": len(results),
        "before_broken": inv["broken"],
        "after_broken": after["broken"],
        "results": results,
        "inventory": after,
    }


def build_registry() -> dict[str, Any]:
    inv = inventory()
    patterns = (_load(DOCTRINE, {}) or {}).get("patterns") or {}
    files = []
    for row in inv["rows"]:
        v = row.get("verify") or {}
        files.append(
            {
                "pattern": row.get("pattern"),
                "path": row.get("path"),
                "chip_id": row.get("chip_id"),
                "lang_id": row.get("lang_id"),
                "status": v.get("status"),
                "bytes": v.get("bytes"),
                "sha256": v.get("sha256"),
                "repair_cmd": row.get("repair_cmd"),
            }
        )
    doc = {
        "schema": "field-combinatronic-visuals-registry/v1",
        "generated": _now(),
        "install_root": str(INSTALL),
        "chip_count": len(_chip_ids()),
        "lang_count": len(_lang_ids()),
        "file_count": len(files),
        "ok_count": inv["ok"],
        "broken_count": inv["broken"],
        "patterns": patterns,
        "sources": (_load(DOCTRINE, {}) or {}).get("sources") or {},
        "repair": (_load(DOCTRINE, {}) or {}).get("repair") or {},
        "files": files,
    }
    _save(REGISTRY, doc)
    reg_check = _verify_json(REGISTRY)
    for entry in doc["files"]:
        if entry.get("pattern") == "registry":
            entry["status"] = reg_check.get("status")
            entry["bytes"] = reg_check.get("bytes")
            entry["sha256"] = reg_check.get("sha256")
    doc["ok_count"] = sum(1 for f in doc["files"] if f.get("status") == "ok")
    doc["broken_count"] = sum(1 for f in doc["files"] if f.get("status") != "ok")
    _save(REGISTRY, doc)
    return doc


def explain_pattern(pattern_id: str) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    pat = (doctrine.get("patterns") or {}).get(pattern_id)
    if not pat:
        return {"ok": False, "error": "unknown_pattern", "pattern_id": pattern_id, "known": sorted((doctrine.get("patterns") or {}).keys())}
    examples = [r for r in _expected_file_rows() if r.get("pattern") == pattern_id][:5]
    return {
        "ok": True,
        "pattern_id": pattern_id,
        "pattern": pat,
        "examples": examples,
        "doctrine": _rel(DOCTRINE),
    }


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 30, 30, 30


def _figure_compress_mod():
    path = INSTALL / "lib" / "field-h7c-figure-compress.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("field_h7c_figure_compress_v", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _save_plate_figure(img, path: Path, *, plate_key: str, accent: tuple[int, int, int]) -> Path:
    mod = _figure_compress_mod()
    if mod and hasattr(mod, "save_plate_figure"):
        return mod.save_plate_figure(img, path, plate_key=plate_key, accent=accent)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True, compress_level=9)
    return path


def _font(size: int, *, bold: bool = False):
    from PIL import ImageFont  # noqa: WPS433

    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _felt_texture(w: int, h: int, felt: tuple[int, int, int], felt_dark: tuple[int, int, int], seed: int):
    from PIL import Image  # noqa: WPS433

    rng = random.Random(seed)
    img = Image.new("RGB", (w, h), felt)
    px = img.load()
    for y in range(h):
        for x in range(w):
            n = rng.randint(-18, 18)
            fib = ((x * 7 + y * 13) % 5) - 2
            r = max(0, min(255, felt[0] + n + fib))
            g = max(0, min(255, felt[1] + n + fib))
            b = max(0, min(255, felt[2] + n + fib))
            if (x + y) % 17 == 0:
                r, g, b = felt_dark[0], felt_dark[1], felt_dark[2]
            px[x, y] = (r, g, b)
    return img


def _vignette(img, strength: float = 0.55):
    from PIL import Image, ImageDraw  # noqa: WPS433

    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-w * 0.15, -h * 0.15, w * 1.15, h * 1.15), fill=(0, 0, 0, int(255 * strength)))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def _draw_dip_pins(draw, cx: int, cy: int, bw: int, bh: int, pins: int, pin_color: tuple[int, int, int]):
    per_side = pins // 2
    pitch_y = bh / (per_side + 1)
    pin_w, pin_h = 5, 14
    for i in range(per_side):
        py = int(cy - bh // 2 + pitch_y * (i + 1))
        draw.rectangle((cx - bw // 2 - pin_w, py - pin_h // 2, cx - bw // 2, py + pin_h // 2), fill=pin_color)
        draw.rectangle((cx + bw // 2, py - pin_h // 2, cx + bw // 2 + pin_w, py + pin_h // 2), fill=pin_color)


def _draw_qfp_pins(draw, cx: int, cy: int, bw: int, bh: int, pins: int, pin_color: tuple[int, int, int]):
    per_side = pins // 4
    pitch_x = bw / (per_side + 1)
    pitch_y = bh / (per_side + 1)
    pin_len = 10
    for i in range(per_side):
        px = int(cx - bw // 2 + pitch_x * (i + 1))
        py_top = cy - bh // 2 - pin_len
        py_bot = cy + bh // 2
        draw.rectangle((px - 2, py_top, px + 2, cy - bh // 2), fill=pin_color)
        draw.rectangle((px - 2, cy + bh // 2, px + 2, py_bot + pin_len), fill=pin_color)
    for i in range(per_side):
        py = int(cy - bh // 2 + pitch_y * (i + 1))
        draw.rectangle((cx - bw // 2 - pin_len, py - 2, cx - bw // 2, py + 2), fill=pin_color)
        draw.rectangle((cx + bw // 2, py - 2, cx + bw // 2 + pin_len, py + 2), fill=pin_color)


def _draw_plcc_pins(draw, cx: int, cy: int, bw: int, bh: int, pins: int, pin_color: tuple[int, int, int]):
    per_side = pins // 4
    pitch_x = bw / (per_side + 1)
    pitch_y = bh / (per_side + 1)
    for i in range(per_side):
        px = int(cx - bw // 2 + pitch_x * (i + 1))
        draw.rectangle((px - 3, cy - bh // 2 - 8, px + 3, cy - bh // 2), fill=pin_color)
        draw.rectangle((px - 3, cy + bh // 2, px + 3, cy + bh // 2 + 8), fill=pin_color)
    for i in range(per_side):
        py = int(cy - bh // 2 + pitch_y * (i + 1))
        draw.rectangle((cx - bw // 2 - 8, py - 3, cx - bw // 2, py + 3), fill=pin_color)
        draw.rectangle((cx + bw // 2, py - 3, cx + bw // 2 + 8, py + 3), fill=pin_color)


def _draw_pga_pins(draw, cx: int, cy: int, bw: int, bh: int, pins: int, pin_color: tuple[int, int, int]):
    cols = max(8, int(pins ** 0.5))
    rows = max(8, pins // cols)
    pad = 6
    gx0, gy0 = cx - bw // 2 + pad, cy - bh // 2 + pad
    gx1, gy1 = cx + bw // 2 - pad, cy + bh // 2 - pad
    step_x = (gx1 - gx0) / max(1, cols - 1)
    step_y = (gy1 - gy0) / max(1, rows - 1)
    drawn = 0
    for row in range(rows):
        for col in range(cols):
            if drawn >= pins:
                return
            px = int(gx0 + col * step_x)
            py = int(gy0 + row * step_y)
            draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=pin_color)
            drawn += 1


def _chip_body_scale(pins: int, package: str) -> float:
    if package == "die":
        return 0.9
    if pins > 200:
        return 1.35
    if pins > 100:
        return 1.15
    if pins <= 16:
        return 0.75
    return 1.0


def _draw_chip_package(
    draw,
    cx: int,
    cy: int,
    *,
    package: str,
    pins: int,
    body: tuple[int, int, int],
    bg: tuple[int, int, int],
    imprint: list[str],
    scale: float = 1.0,
    pin_color: tuple[int, int, int] = (192, 192, 200),
):
    bw = int(220 * scale)
    bh = int(180 * scale) if package == "dip" else int(200 * scale)
    if package == "die":
        bw, bh = int(180 * scale), int(180 * scale)
        draw.ellipse((cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2), fill=body, outline=(90, 90, 98), width=2)
        draw.ellipse((cx - bw // 4, cy - bh // 4, cx + bw // 4, cy + bh // 4), outline=(70, 70, 78), width=1)
    else:
        if package == "dip":
            _draw_dip_pins(draw, cx, cy, bw, bh, pins, pin_color)
        elif package == "qfp":
            _draw_qfp_pins(draw, cx, cy, bw, bh, pins, pin_color)
        elif package == "plcc":
            _draw_plcc_pins(draw, cx, cy, bw, bh, pins, pin_color)
        else:
            _draw_pga_pins(draw, cx, cy, bw + 40, bh + 40, pins, pin_color)
        draw.rounded_rectangle(
            (cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2),
            radius=max(4, int(8 * scale)),
            fill=body,
            outline=(60, 60, 68),
            width=max(1, int(2 * scale)),
        )
        notch_x = cx - bw // 2 + max(4, int(12 * scale))
        draw.polygon(
            [
                (notch_x, cy - bh // 2),
                (notch_x + max(8, int(18 * scale)), cy - bh // 2 + max(4, int(10 * scale))),
                (notch_x, cy - bh // 2 + max(8, int(20 * scale))),
            ],
            fill=bg,
        )
    line_font = _font(max(8, int(14 * scale)))
    line_h = max(12, int(18 * scale))
    y0 = cy - (len(imprint) * line_h) // 2
    for i, line in enumerate(imprint):
        tw = draw.textlength(str(line), font=line_font)
        draw.text((cx - tw / 2, y0 + i * line_h), str(line), fill=(210, 210, 218), font=line_font)


def render_chip_closeup(chip: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    catalog = _load(CATALOG, {})
    backdrop = catalog.get("backdrop") or {}
    felt = _hex_rgb(backdrop.get("felt", "#d4899a"))
    felt_dark = _hex_rgb(backdrop.get("felt_dark", "#b86b7f"))
    bg = _hex_rgb(backdrop.get("background", "#080808"))

    chip_id = str(chip.get("id", "chip"))
    w, h = 960, 720
    rng_seed = int(hashlib.md5(chip_id.encode()).hexdigest()[:8], 16)

    img = Image.new("RGB", (w, h), bg)
    felt_w, felt_h = int(w * 0.82), int(h * 0.62)
    fx, fy = (w - felt_w) // 2, (h - felt_h) // 2 + 30
    felt_img = _felt_texture(felt_w, felt_h, felt, felt_dark, rng_seed)
    img.paste(felt_img, (fx, fy))

    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 + 10
    package = str(chip.get("package", "dip"))
    pins = int(chip.get("pins", 40))
    body = _hex_rgb(str(chip.get("body", "#1a1a1a")))
    scale = _chip_body_scale(pins, package)
    imprint = chip.get("imprint") or [chip.get("label", chip_id)]
    _draw_chip_package(draw, cx, cy, package=package, pins=pins, body=body, bg=bg, imprint=imprint, scale=scale)

    badge = f"{pins} PINS" if package != "die" else "WAFER DIE"
    socket = chip.get("socket", "")
    badge_font = _font(18, bold=True)
    pin_font = _font(14)
    draw.text((24, 24), chip.get("label", chip_id), fill=(230, 230, 235), font=_font(22, bold=True))
    draw.text((24, 52), badge, fill=(94, 234, 212), font=badge_font)
    if socket:
        draw.text((24, 76), str(socket), fill=(180, 190, 200), font=pin_font)
    draw.text((24, h - 36), f"macro · pink felt · {package.upper()}", fill=(120, 130, 140), font=pin_font)

    img = _vignette(img, 0.42)
    out = out or CHIPS_DIR / f"{chip_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def render_chip_thumbnail(chip: dict[str, Any], *, out: Path | None = None) -> Path:
    """Small labeled ironclad chip thumb — 320×240 with name band."""
    from PIL import Image, ImageDraw  # noqa: WPS433

    catalog = _load(CATALOG, {})
    backdrop = catalog.get("backdrop") or {}
    felt = _hex_rgb(backdrop.get("felt", "#d4899a"))
    felt_dark = _hex_rgb(backdrop.get("felt_dark", "#b86b7f"))
    bg = _hex_rgb(backdrop.get("background", "#080808"))

    chip_id = str(chip.get("id", "chip"))
    label = str(chip.get("label", chip_id))
    w, h = 320, 240
    rng_seed = int(hashlib.md5((chip_id + ":thumb").encode()).hexdigest()[:8], 16)

    img = Image.new("RGB", (w, h), bg)
    felt_h = int(h * 0.68)
    felt_w = int(w * 0.88)
    fx, fy = (w - felt_w) // 2, 8
    felt_img = _felt_texture(felt_w, felt_h, felt, felt_dark, rng_seed)
    img.paste(felt_img, (fx, fy))

    draw = ImageDraw.Draw(img)
    package = str(chip.get("package", "dip"))
    pins = int(chip.get("pins", 40))
    body = _hex_rgb(str(chip.get("body", "#1a1a1a")))
    scale = _chip_body_scale(pins, package) * 0.42
    imprint = chip.get("imprint") or [label]
    cx, cy = w // 2, fy + felt_h // 2 + 4
    _draw_chip_package(draw, cx, cy, package=package, pins=pins, body=body, bg=bg, imprint=imprint[:3], scale=scale)

    band_y = h - 44
    draw.rectangle((0, band_y, w, h), fill=(16, 18, 24))
    draw.rectangle((0, band_y, w, band_y + 2), fill=(94, 234, 212))
    title_font = _font(14, bold=True)
    sub_font = _font(10)
    title = label if len(label) <= 28 else label[:25] + "…"
    tw = draw.textlength(title, font=title_font)
    draw.text(((w - tw) / 2, band_y + 8), title, fill=(235, 238, 245), font=title_font)
    meta = f"{chip.get('vendor', '—')} · {chip.get('kind', 'chip').replace('_', ' ')}"
    mw = draw.textlength(meta, font=sub_font)
    draw.text(((w - mw) / 2, band_y + 26), meta, fill=(140, 150, 165), font=sub_font)

    img = _vignette(img, 0.28)
    out = out or CHIPS_THUMBS_DIR / f"{chip_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def render_chip_detail_page(chip: dict[str, Any], *, out: Path | None = None) -> Path:
    """Big ironclad catalog page — 1200×900 with imprint, vendor, kind, dates, note."""
    from PIL import Image, ImageDraw  # noqa: WPS433

    catalog = _load(CATALOG, {})
    backdrop = catalog.get("backdrop") or {}
    felt = _hex_rgb(backdrop.get("felt", "#d4899a"))
    felt_dark = _hex_rgb(backdrop.get("felt_dark", "#b86b7f"))
    bg = _hex_rgb(backdrop.get("background", "#080808"))

    chip_id = str(chip.get("id", "chip"))
    w, h = 1200, 900
    rng_seed = int(hashlib.md5((chip_id + ":detail").encode()).hexdigest()[:8], 16)

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    panel_w = 380
    draw.rectangle((0, 0, panel_w, h), fill=(14, 16, 22))
    draw.rectangle((panel_w - 2, 0, panel_w, h), fill=(94, 234, 212))

    title_font = _font(30, bold=True)
    head_font = _font(13, bold=True)
    body_font = _font(13)
    small_font = _font(11)

    label = str(chip.get("label", chip_id))
    vendor = str(chip.get("vendor", "—"))
    kind = str(chip.get("kind", "chip")).replace("_", " ")
    family = str(chip.get("family") or "—")
    era = chip.get("era")
    mhz = chip.get("mhz")
    bits = chip.get("bits")
    note = str(chip.get("note") or "").strip()
    schematic = str(chip.get("schematic_blueprint") or "").strip()
    design_over = str(chip.get("design_over_standard") or "").strip()
    source = str(chip.get("source") or "—")
    mame_device = chip.get("mame_device")
    package = str(chip.get("package", "dip"))
    pins = int(chip.get("pins", 40))
    socket = str(chip.get("socket") or "")

    y = 28
    draw.text((24, y), label, fill=(240, 242, 248), font=title_font)
    y += 44
    draw.text((24, y), vendor, fill=(94, 234, 212), font=head_font)
    y += 30

    def _line(key: str, val: str) -> None:
        nonlocal y
        if not val or val in ("—", "None"):
            return
        draw.text((24, y), key, fill=(110, 120, 135), font=small_font)
        draw.text((24, y + 14), val[:72], fill=(200, 205, 215), font=body_font)
        y += 38

    _line("Kind", kind.title())
    _line("Family", family.replace("_", " "))
    if era:
        _line("Era / date", str(era))
    if mhz:
        _line("Clock", f"{mhz} MHz")
    if bits:
        _line("Width", f"{bits}-bit")
    pin_line = f"{pins} pins · {package.upper()}" if package != "die" else "wafer die"
    if socket:
        pin_line += f" · {socket}"
    _line("Package", pin_line)
    _line("Source", source.replace("_", " "))
    if mame_device:
        _line("MAME device", str(mame_device))
    if note:
        wrapped = note
        if len(note) > 120:
            wrapped = note[:117] + "…"
        _line("Note", wrapped)
    if schematic:
        wrapped = schematic
        if len(schematic) > 120:
            wrapped = schematic[:117] + "…"
        _line("Schematic", wrapped)
    if design_over:
        wrapped = design_over
        if len(design_over) > 120:
            wrapped = design_over[:117] + "…"
        _line("Design vs standard", wrapped)

    draw.text((24, h - 52), "Ironclad CHIPS · combinatorics catalog", fill=(90, 100, 115), font=small_font)
    draw.text((24, h - 34), chip_id, fill=(70, 80, 95), font=small_font)

    macro_x0 = panel_w + 24
    felt_w, felt_h = w - macro_x0 - 24, int(h * 0.72)
    fx, fy = macro_x0, 48
    felt_img = _felt_texture(felt_w, felt_h, felt, felt_dark, rng_seed)
    img.paste(felt_img, (fx, fy))

    body = _hex_rgb(str(chip.get("body", "#1a1a1a")))
    scale = _chip_body_scale(pins, package) * 1.25
    imprint = chip.get("imprint") or [label]
    cx = fx + felt_w // 2
    cy = fy + felt_h // 2 + 10
    _draw_chip_package(draw, cx, cy, package=package, pins=pins, body=body, bg=bg, imprint=imprint, scale=scale)

    badge_font = _font(18, bold=True)
    pin_font = _font(14)
    draw.text((macro_x0, 16), label, fill=(230, 230, 235), font=_font(22, bold=True))
    badge = f"{pins} PINS · {package.upper()}" if package != "die" else "WAFER DIE"
    draw.text((macro_x0, 44), badge, fill=(94, 234, 212), font=badge_font)
    if socket:
        draw.text((macro_x0, 68), socket, fill=(180, 190, 200), font=pin_font)
    draw.text((macro_x0, h - 36), f"ironclad detail · {kind}", fill=(120, 130, 140), font=pin_font)

    img = _vignette(img, 0.38)
    out = out or CHIPS_DETAIL_DIR / f"{chip_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def render_book_cover(lang_id: str, *, label: str | None = None, command_count: int = 0, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    title_label = label or LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    accent = LANG_ACCENT.get(lang_id, (94, 234, 212))
    w, h = 400, 600

    img = Image.new("RGB", (w, h), (12, 14, 18))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 8), fill=accent)
    draw.rectangle((0, h - 48, w, h), fill=(20, 24, 30))

    title_font = _font(28, bold=True)
    sub_font = _font(16)
    small_font = _font(12)

    draw.text((28, 80), "Explaining", fill=(200, 205, 215), font=_font(20))
    draw.text((28, 108), title_label, fill=accent, font=title_font)
    draw.text((28, 160), "Hostess 7 · H7 Manual", fill=(140, 150, 165), font=sub_font)
    draw.text((28, 190), f"{command_count} commands · g16 combinatronic", fill=(110, 120, 135), font=small_font)

    draw.rectangle((28, 240, w - 28, 420), outline=accent, width=2)
    lines = [
        "Distilled from the language reference",
        "Boiled to canonical ops",
        "What · Why · How · Pitfalls",
        "Field program combinatronic facet",
    ]
    y = 260
    for line in lines:
        draw.text((44, y), line, fill=(175, 180, 190), font=small_font)
        y += 28

    draw.text((28, h - 36), "NEXUS-Shield · Dewey 000", fill=(90, 100, 115), font=small_font)

    out = out or BOOKS_DIR / f"{lang_id}.png"
    return _save_plate_figure(img, out, plate_key="cover", accent=accent)


def _resolve_language_pack(seed: dict[str, Any], lang_id: str) -> dict[str, Any]:
    packs = seed.get("language_packs") or {}
    pack = dict(packs.get(lang_id) or {})
    if pack.get("extends"):
        base = dict(packs.get(pack["extends"]) or {})
        merged_cmds = dict(base.get("commands") or {})
        merged_cmds.update(pack.get("commands") or {})
        pack["commands"] = merged_cmds
    return pack


def _canonical_labels(seed: dict[str, Any]) -> dict[str, str]:
    return {op["id"]: op.get("label", op["id"]) for op in seed.get("canonical_ops") or []}


_LANG_PROFILE_ALIASES = {
    "cxx": "cpp",
    "asm": "assembly",
    "ammolang": "ammoasm",
    "visual_basic": "vb",
    "qbasic": "basic",
    "quickbasic": "basic",
    "freebasic": "basic",
    "turbo_pascal": "pascal",
    "delphi": "pascal",
    "modula2": "pascal",
    "objc": "objc",
    "csharp": "csharp",
    "cobol_copy": "cobol",
    "linux": "linux",
    "economics": "economics",
}


def _lang_profile(lang_id: str) -> dict[str, Any]:
    """Best-effort language metadata from Hostess7 langs catalog."""
    for base in (INSTALL / "Hostess7" / "scripts", INSTALL.parent / "Hostess7" / "scripts"):
        path = base / "field_langs_data.py"
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("field_langs_data_v", path)
            if not spec or not spec.loader:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            lookup = _LANG_PROFILE_ALIASES.get(lang_id, lang_id)
            for entry in getattr(mod, "LANG_ENTRIES", ()) or ():
                eid = str(entry.get("id") or "").lower()
                tags = tuple(str(t).lower() for t in (entry.get("tags") or ()))
                if eid == lookup or lang_id in tags or lookup in tags:
                    return dict(entry)
        except Exception:
            pass
    return {}


def render_syntax_diagram(
    lang_id: str,
    *,
    label: str | None = None,
    commands: dict[str, str] | None = None,
    out: Path | None = None,
) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    title_label = label or LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    accent = LANG_ACCENT.get(lang_id, (94, 234, 212))
    w, h = 720, 420
    img = Image.new("RGB", (w, h), (14, 16, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 44), fill=accent)
    draw.text((16, 10), f"{title_label} — syntax surface", fill=(12, 14, 18), font=_font(18, bold=True))
    sample = sorted((commands or {}).keys(), key=str.lower)[:14]
    y = 64
    for cmd in sample:
        canon = (commands or {}).get(cmd, "?")
        draw.text((24, y), f"{cmd}", fill=accent, font=_font(14, bold=True))
        draw.text((200, y), f"→ {canon}", fill=(190, 195, 205), font=_font(13))
        y += 24
    if not sample:
        draw.text((24, 80), "No commands in seed pack.", fill=(140, 150, 165), font=_font(14))
    draw.text((16, h - 28), "Hostess 7 · H7c embedded figure · syntax", fill=(100, 110, 125), font=_font(11))
    out = out or BOOKS_DIR / f"{lang_id}_syntax.png"
    return _save_plate_figure(img, out, plate_key="syntax", accent=accent)


def render_op_map_diagram(
    lang_id: str,
    *,
    label: str | None = None,
    commands: dict[str, str] | None = None,
    seed: dict[str, Any] | None = None,
    out: Path | None = None,
) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    title_label = label or LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    accent = LANG_ACCENT.get(lang_id, (94, 234, 212))
    used: dict[str, int] = {}
    for canon in (commands or {}).values():
        used[str(canon)] = used.get(str(canon), 0) + 1
    w, h = 720, 480
    img = Image.new("RGB", (w, h), (14, 16, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 44), fill=accent)
    draw.text((16, 10), f"{title_label} — canonical op map", fill=(12, 14, 18), font=_font(18, bold=True))
    cols, rows = 4, 9
    cell_w, cell_h = (w - 32) // cols, 44
    ops = seed.get("canonical_ops") if seed else []
    op_ids = [str(op.get("id")) for op in ops]
    for i, op_id in enumerate(op_ids[: cols * rows]):
        col, row = i % cols, i // cols
        x0 = 16 + col * cell_w
        y0 = 56 + row * cell_h
        count = used.get(op_id, 0)
        fill = (32, 48, 42) if count else (28, 30, 38)
        draw.rectangle((x0 + 2, y0 + 2, x0 + cell_w - 4, y0 + cell_h - 6), fill=fill, outline=accent if count else (50, 55, 65))
        draw.text((x0 + 8, y0 + 8), op_id[:10], fill=(220, 225, 235) if count else (120, 125, 135), font=_font(11, bold=True))
        if count:
            draw.text((x0 + 8, y0 + 24), f"{count} cmd", fill=accent, font=_font(10))
    draw.text((16, h - 28), "36 canonical atoms · shaded = used by this language", fill=(100, 110, 125), font=_font(11))
    out = out or BOOKS_DIR / f"{lang_id}_opmap.png"
    return _save_plate_figure(img, out, plate_key="op_map", accent=accent)


def render_memory_diagram(
    lang_id: str,
    *,
    label: str | None = None,
    profile: dict[str, Any] | None = None,
    out: Path | None = None,
) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    title_label = label or LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    accent = LANG_ACCENT.get(lang_id, (94, 234, 212))
    memory = str((profile or {}).get("memory") or "runtime-managed")
    w, h = 720, 360
    img = Image.new("RGB", (w, h), (14, 16, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 44), fill=accent)
    draw.text((16, 10), f"{title_label} — memory & objects", fill=(12, 14, 18), font=_font(18, bold=True))
    rows = [
        ("Stack", "call frames · locals · fast path"),
        ("Heap", "objects · containers · shared state"),
        ("Model", memory),
        ("GC / reclaim", "language runtime policy"),
        ("Interop", "FFI · g16 belt · NEXUS-Shield"),
    ]
    y = 64
    for title, detail in rows:
        draw.rectangle((24, y, w - 24, y + 44), fill=(24, 28, 36), outline=(50, 55, 65))
        draw.text((36, y + 6), title, fill=accent, font=_font(13, bold=True))
        draw.text((36, y + 24), detail, fill=(185, 190, 200), font=_font(11))
        y += 52
    draw.text((16, h - 28), "Hostess 7 · H7c plate · memory facet", fill=(100, 110, 125), font=_font(11))
    out = out or BOOKS_DIR / f"{lang_id}_memory.png"
    return _save_plate_figure(img, out, plate_key="memory", accent=accent)


def render_compile_path_diagram(
    lang_id: str,
    *,
    label: str | None = None,
    out: Path | None = None,
) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    title_label = label or LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    accent = LANG_ACCENT.get(lang_id, (94, 234, 212))
    w, h = 720, 400
    img = Image.new("RGB", (w, h), (14, 16, 22))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 44), fill=accent)
    draw.text((16, 10), f"{title_label} — g16 compile path", fill=(12, 14, 18), font=_font(18, bold=True))
    steps = [
        "source → token surface",
        "boil → 36 canonical ops",
        "belt runner → native_bsp / python",
        "g16-compile-combinatronics.py gate",
        "link · field combinatronic verify",
    ]
    x0, y0 = 32, 70
    for i, step in enumerate(steps):
        yy = y0 + i * 58
        draw.rectangle((x0, yy, w - 32, yy + 46), fill=(28, 32, 42), outline=accent if i == 2 else (55, 60, 72))
        draw.text((x0 + 14, yy + 14), f"{i + 1}. {step}", fill=(210, 215, 225), font=_font(13, bold=(i == 2)))
        if i < len(steps) - 1:
            draw.line((w // 2, yy + 46, w // 2, yy + 58), fill=accent, width=2)
    draw.text((16, h - 28), "Field program facet · belt_2_0 default", fill=(100, 110, 125), font=_font(11))
    out = out or BOOKS_DIR / f"{lang_id}_compile.png"
    return _save_plate_figure(img, out, plate_key="compile", accent=accent)


def _explaining_body_sections(
    lang_id: str,
    label: str,
    cmds: dict[str, str],
    by_canon: dict[str, list[str]],
    profile: dict[str, Any],
    seed: dict[str, Any],
) -> list[str]:
    """Information-manual sections — target ~1 figure per 1,100 words."""
    lines: list[str] = []
    parad = profile.get("paradigm") or "multi-paradigm"
    typing = profile.get("typing") or "see language reference"
    memory = profile.get("memory") or "runtime-managed"

    lines.extend([
        "## Execution model",
        "",
        f"{label} programs execute through the Field program combinatronic facet. Surface syntax",
        "maps to 36 canonical ops; each op selects a belt runner (native_bsp on belt_2_0 or",
        "python on belt_1_0). The explaining manual documents semantics — not a tutorial walkthrough.",
        "",
        f"- **Paradigm:** {parad}",
        f"- **Typing discipline:** {typing}",
        f"- **Memory:** {memory}",
        f"- **Commands in seed:** {len(cmds)}",
        f"- **Canonical ops exercised:** {len(by_canon)}",
        "",
        "![Memory and objects](h7fig:memory)",
        "",
        "## Lexical structure",
        "",
        "Tokens partition into identifiers, literals, operators, and significant whitespace",
        f"per {label} reference rules. Hostess7 boil heuristics treat unknown tokens as exec",
        "unless a seed keyword maps them. Extended packs inherit parent commands.",
        "",
    ])
    sample_cmds = sorted(cmds.keys(), key=str.lower)[:24]
    for cmd in sample_cmds:
        lines.append(f"- `{cmd}` → `{cmds[cmd]}`")
    lines.extend(["", "## Type and value space", ""])
    if profile.get("body"):
        for para in str(profile["body"]).split("\n\n"):
            para = para.strip()
            if para:
                lines.extend([para, ""])
    else:
        lines.extend([
            f"The {label} value space follows the language reference: primitives, aggregates,",
            "and callables compose through assign, call, and return canonical ops.",
            "",
        ])
    lines.extend([
        "## Control flow",
        "",
        "branch · loop · break · continue · return — all languages converge on these atoms.",
        f"In {label}, control constructs in the seed pack boil as follows:",
        "",
    ])
    for cop in ("branch", "loop", "return", "throw"):
        hits = by_canon.get(cop) or []
        if hits:
            lines.append(f"- **{cop}:** {', '.join(f'`{c}`' for c in hits[:8])}")
    lines.extend([
        "",
        "## Modules and boundaries",
        "",
        "import · export · module · package — boundary ops isolate compilation units.",
        "NEXUS-Shield indexes each manual under Dewey 000; combinatronic rebalance may extend packs.",
        "",
        "![G16 compile path](h7fig:compile)",
        "",
        "## Standard library surface",
        "",
        f"Where the seed lists I/O or runtime commands, they map to the io and call ops.",
        f"Verify any keyword with `field-program-combinatronic.py boil {lang_id} \"<cmd>\"`.",
        "",
    ])
    io_cmds = [c for c, k in cmds.items() if k in ("io", "call", "import")]
    for cmd in sorted(io_cmds, key=str.lower)[:16]:
        lines.append(f"- `{cmd}`")
    lines.extend(["", "## Interop and embedding", ""])
    lines.extend([
        f"{label} may embed in Queen Code, Grok16 belt builds, or NEXUS panel scripts.",
        "G16 unified driver (`g16`) compiles C/C++ neighbors; python runner hosts dynamic facets.",
        "Use `g16-compile-combinatronics.py` when program facet gates must pass at compile time.",
        "",
        "## Secure compile & run chamber",
        "",
        f"Every {label} compile and run path is sealed — **no bare host exec**. User code passes",
        "`g16-code-security.py` first, then executes inside `g16-secure-chamber.py` with scrubbed",
        "env (`HOME`, `TMPDIR`, `PATH` limited) so AmmoOS, Hostess 7, and Grok16/bin stay protected.",
        "",
        f"- **Check:** `g16-secure-chamber.py compile` (stdin JSON: content, lang)",
        f"- **Run:** `g16-secure-chamber.py run <path> --lang {lang_id}`",
        f"- **Posture:** `/api/g16/secure-chamber` · `nexus-g16-bridge.py json` → `secure_chamber`",
        f"- **Queen launch:** `runner_policy.{lang_id}` = `chamber` in `.launch` manifests",
        "- **Forbidden:** Hostess7, AmmoCode, Grok16/bin, /usr/bin — cannot execute in place",
        "",
        "## Performance notes",
        "",
        "belt_2_0 native_bsp is the default for hot paths; belt_1_0 python runner applies",
        "when combinatorics bridge degrades the gate. Always-optimal panel pins the best belt",
        "from bench receipts — not guessed from language family alone.",
        "",
        "## Research references",
        "",
        "Training manuals (school-style textbooks) complement this explaining manual.",
        f"See `training_{lang_id}` on the Dewey shelf when published.",
        "Field Research book and g16-power-sort plates inform algorithm choices in tooling.",
        "",
    ])
    return lines


def _grok15_mod() -> Any | None:
    path = INSTALL / "Grok16" / "lib" / "grok15-language-core.py"
    if not path.is_file():
        path = INSTALL.parent / "Grok16" / "lib" / "grok15-language-core.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("grok15_language_core", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_explaining_manual(lang_id: str, *, seed: dict[str, Any] | None = None) -> str:
    seed = seed or _load(SEED, {})
    g15 = _grok15_mod()
    if g15 and hasattr(g15, "condensed_explaining_manual"):
        if os.environ.get("GROK15_FULL_MANUAL", "").strip().lower() not in ("1", "true", "yes"):
            return g15.condensed_explaining_manual(lang_id, seed=seed)
    pack = _resolve_language_pack(seed, lang_id)
    cmds: dict[str, str] = pack.get("commands") or {}
    canon = _canonical_labels(seed)
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    profile = _lang_profile(lang_id)
    by_canon: dict[str, list[str]] = {}
    for cmd, cop in cmds.items():
        by_canon.setdefault(str(cop), []).append(cmd)

    lines = [
        f"# Explaining {label}",
        "",
        "![Cover — Explaining " + label + "](h7fig:cover)",
        "",
        f"Hostess 7 programming language manual — complete reference distilled from the",
        f"{label} combinatronic pack and boiled to the g16 program facet (36 canonical ops).",
        "",
        f"- **Language id:** `{lang_id}`",
        f"- **Command entries:** {len(cmds)}",
        f"- **Canonical ops used:** {len(by_canon)}",
        f"- **Generated:** {_now()}",
        f"- **Format:** H7c v3 with embedded figures",
        "",
        "## At a glance",
        "",
    ]
    if profile:
        lines.extend([
            f"- **Paradigm:** {profile.get('paradigm', '—')}",
            f"- **Typing:** {profile.get('typing', '—')}",
            f"- **Memory:** {profile.get('memory', '—')}",
            f"- **Year originated:** {profile.get('year', '—')}",
            "",
            str(profile.get("body") or ""),
            "",
        ])
    else:
        lines.extend([
            f"{label} is catalogued in the Field program combinatronic seed.",
            "Profile metadata fills in when Hostess7 langs corpus matches this id.",
            "",
        ])

    lines.extend([
        "![Syntax overview](h7fig:syntax)",
        "",
        "![Canonical op map](h7fig:op_map)",
        "",
        "## Introduction",
        "",
        f"This manual explains every seeded {label} construct: surface syntax, semantic role,",
        "canonical combinatronic op, belt runner, and NEXUS-Shield integration paths.",
        "Use the GUI reader (`/field-lang-manuals`) or text mode (`field-lang-manual-reader.py text`).",
        "",
        "## Reading guide",
        "",
        "1. **At a glance** — paradigm, typing, memory model.",
        "2. **Canonical atoms** — the 36 ops all languages boil to.",
        "3. **Commands by op** — every keyword grouped by canonical target.",
        "4. **Full command index** — alphabetical reference.",
        "5. **G16 & NEXUS** — compile, belt, API, pitfalls.",
        "",
        "## Canonical combinatronic atoms",
        "",
    ])
    for op in seed.get("canonical_ops") or []:
        used = len(by_canon.get(str(op.get("id")), []))
        mark = "✓" if used else "·"
        lines.append(
            f"- {mark} **{op['id']}** — {op.get('label', '')} "
            f"(runner: {op.get('runner', 'native_bsp')}, belt: {op.get('belt', 'belt_2_0')})"
        )
    lines.extend(["", f"## {label} commands by canonical op", ""])
    for cop in sorted(by_canon.keys()):
        desc = canon.get(cop, cop)
        lines.extend([f"### `{cop}` — {desc}", ""])
        for cmd in sorted(by_canon[cop], key=str.lower):
            lines.append(f"- `{cmd}`")
        lines.append("")

    lines.extend([f"## {label} full command reference", ""])
    for cmd in sorted(cmds.keys(), key=lambda s: (cmds[s], s.lower())):
        canonical = cmds[cmd]
        desc = canon.get(canonical, canonical)
        lines.extend([
            f"### `{cmd}`",
            f"- **Boils to:** `{canonical}` — {desc}",
            f"- **Runner:** from canonical op belt map",
            f"- **Verify:** `field-program-combinatronic.py boil {lang_id} \"{cmd}\"`",
            "",
        ])

    lines.extend(_explaining_body_sections(lang_id, label, cmds, by_canon, profile or {}, seed))

    lines.extend([
        "## G16 compile path",
        "",
        f"- **Boil:** `field-program-combinatronic.py boil {lang_id}`",
        "- **Universal facet:** `field-g16-universal-combinatronic.json`",
        "- **Grok16 compile:** `g16-compile-combinatronics.py` with program facet profile",
        "- **Belt runners:** native_bsp (belt_2_0) and python (belt_1_0) per canonical op",
        "- **Secure chamber:** `lib/g16-secure-chamber.py` — mandatory for all 57 Grok16 languages",
        f"- **Filetype actions:** `run` / `compile` → `secure_chamber` in field-programming-filetypes.json",
        "",
        "## Code patterns",
        "",
        f"Representative {label} patterns map to canonical ops as follows:",
        "",
        "- **Declaration + assign** → declare, assign",
        "- **Conditional** → branch",
        "- **Iteration** → loop, break, continue",
        "- **Procedure call** → call, return",
        "- **Module boundary** → import, export, module",
        "- **I/O** → io",
        "- **Error handling** → throw, catch",
        "",
        "## Pitfalls",
        "",
        f"- Case sensitivity varies — {label} keywords may not match heuristic boil.",
        "- Extended packs inherit parent commands; check `extends` in the seed.",
        "- Unknown tokens fall through to heuristic_keywords before defaulting to exec.",
        "- CDN and macro expansion are advisory until combinatronic rebalance runs.",
        f"- **Never run {label} on the bare host** — shell escapes, `eval`, `system`, and JVM/Node",
        "  subprocess calls are blocked transparently; use the sealed chamber lane.",
        "- Missing host toolchains (javac, node, cobc, fpc) return clear errors inside the chamber.",
        "",
        "## Where in NEXUS-Shield",
        "",
        "- Seed: `data/field-program-combinatronic-seed.json`",
        "- Battery: `field-program-combinatronic.json` (STATE)",
        "- Manual: `library/dewey/000-computer-science/explaining_" + lang_id + "/`",
        "- Reader API: `/api/lang-manuals` · `/api/lang-manuals/" + lang_id + "`",
        "- H7c figures: cover, syntax, op_map, memory, compile (field plate + meld)",
        "",
    ])
    if pack.get("extends"):
        lines.extend([f"- **Extends pack:** `{pack['extends']}`", ""])
    return "\n".join(lines) + "\n"


def _h7_module():
    for base in (INSTALL / "Hostess7" / "scripts", INSTALL.parent / "Hostess7" / "scripts"):
        path = base / "field_h7_book.py"
        if path.is_file():
            spec = importlib.util.spec_from_file_location("field_h7_book", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
    return None


def pack_explaining_h7(lang_id: str, text: str) -> Path:
    h7c_mod = _h7c_module()
    if not h7c_mod:
        raise RuntimeError("field-h7c-compression.py missing")
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    book_id = f"explaining_{lang_id}"
    dest = LIBRARY_SHELF / book_id
    dest.mkdir(parents=True, exist_ok=True)
    h7c_path = dest / f"{book_id}.h7c"
    meta = {
        "id": book_id,
        "title": f"Explaining {label}",
        "author": "Hostess 7",
        "license": "Field",
        "subject": "programming languages",
        "category": "computer science",
        "dewey": "000",
        "combinatronic_lang": lang_id,
        "uploaded": _now(),
        "reader": "NEXUS_H7C",
    }
    figures_dir = dest / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    cover_path = BOOKS_DIR / f"{lang_id}.png"
    pack = _resolve_language_pack(_load(SEED, {}), lang_id)
    profile = _lang_profile(lang_id)
    accent = LANG_ACCENT.get(lang_id, (94, 234, 212))
    syntax_path = render_syntax_diagram(lang_id, label=label, commands=pack.get("commands") or {})
    opmap_path = render_op_map_diagram(
        lang_id,
        label=label,
        commands=pack.get("commands") or {},
        seed=_load(SEED, {}),
    )
    memory_path = render_memory_diagram(lang_id, label=label, profile=profile)
    compile_path = render_compile_path_diagram(lang_id, label=label)
    figures = {
        "cover": {
            "path": cover_path if cover_path.is_file() else syntax_path,
            "alt": f"Explaining {label} cover",
            "mime": "image/png",
            "plate_key": "cover",
            "accent": accent,
        },
        "syntax": {"path": syntax_path, "alt": f"{label} syntax overview", "mime": "image/png", "plate_key": "syntax", "accent": accent},
        "op_map": {"path": opmap_path, "alt": f"{label} canonical op map", "mime": "image/png", "plate_key": "op_map", "accent": accent},
        "memory": {"path": memory_path, "alt": f"{label} memory model", "mime": "image/png", "plate_key": "memory", "accent": accent},
        "compile": {"path": compile_path, "alt": f"{label} g16 compile path", "mime": "image/png", "plate_key": "compile", "accent": accent},
    }
    packed = h7c_mod.pack_h7c(text, meta, use_optimizer=True, format_version=3, figures=figures)
    h7c_path.write_bytes(packed)
    ein = "H7C-FIELD-" + hashlib.sha256(text.encode()).hexdigest()[:12]
    book_json = {
        "id": book_id,
        "title": f"Explaining {label}",
        "author": "Hostess 7",
        "dewey": "000",
        "dewey_label": "Computer science, information & general works",
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "embedded_figures": ["cover", "syntax", "op_map", "memory", "compile"],
        "manual_reader": "/field-lang-manuals",
        "h7c": _rel(h7c_path),
        "h7": None,
        "field_path": _rel(h7c_path),
        "github_shelf": "000-computer-science",
        "combinatronic_lang": lang_id,
        "cover": f"/world/assets/combinatronic/books/{lang_id}.png",
        "updated": _now(),
    }
    (dest / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return h7c_path


def _mirror_asset(src: Path, sub: str) -> Path:
    dest = WORLD_ASSETS / sub / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return dest


def _mirror_chip_asset(src: Path, *, variant: str = "") -> Path:
    if variant:
        dest = WORLD_ASSETS / "chips" / variant / src.name
    else:
        dest = WORLD_ASSETS / "chips" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return dest


def generate_ironclad_chip(chip_id: str, *, thumbs_only: bool = False, detail_only: bool = False) -> dict[str, Any]:
    row = _ironclad_chip_row(chip_id)
    if not row:
        return {"ok": False, "error": "chip_not_in_ironclad", "chip_id": chip_id}
    spec = _chip_visual_spec(chip_id, row)
    result: dict[str, Any] = {
        "ok": True,
        "chip_id": chip_id,
        "label": spec.get("label"),
        "vendor": spec.get("vendor"),
        "kind": spec.get("kind"),
        "package": spec.get("package"),
        "pins": spec.get("pins"),
    }
    if not detail_only:
        thumb = render_chip_thumbnail(spec)
        thumb_mirror = _mirror_chip_asset(thumb, variant="thumbs")
        result["thumb"] = str(thumb)
        result["thumb_mirror"] = str(thumb_mirror)
        result["thumb_url"] = f"/world/assets/combinatronic/chips/thumbs/{chip_id}.png"
    if not thumbs_only:
        detail = render_chip_detail_page(spec)
        detail_mirror = _mirror_chip_asset(detail, variant="detail")
        result["detail"] = str(detail)
        result["detail_mirror"] = str(detail_mirror)
        result["detail_url"] = f"/world/assets/combinatronic/chips/detail/{chip_id}.png"
    return result


def generate_ironclad_all(*, thumbs_only: bool = False, limit: int | None = None) -> dict[str, Any]:
    chip_ids = _ironclad_chip_ids()
    if limit is not None and limit > 0:
        chip_ids = chip_ids[:limit]
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for chip_id in chip_ids:
        try:
            row = generate_ironclad_chip(chip_id, thumbs_only=thumbs_only)
            if row.get("ok"):
                results.append(row)
            else:
                errors.append(row)
        except Exception as exc:
            errors.append({"ok": False, "chip_id": chip_id, "error": str(exc)})
    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "ok": len(errors) == 0,
        "schema": "field-combinatronic-visuals-ironclad/v1",
        "generated": _now(),
        "ironclad_source": str(IRONCLAD_CHIPS),
        "total": len(chip_ids),
        "ok_count": ok_count,
        "error_count": len(errors),
        "thumbs_only": thumbs_only,
        "thumb_dir": _rel(CHIPS_THUMBS_DIR),
        "detail_dir": _rel(CHIPS_DETAIL_DIR) if not thumbs_only else None,
        "sample": results[:8],
        "errors": errors[:12],
    }


def generate_chip(chip_id: str) -> dict[str, Any]:
    catalog = _load(CATALOG, {})
    chip = next((c for c in catalog.get("chips") or [] if c.get("id") == chip_id), None)
    if not chip:
        return {"ok": False, "error": "chip_not_in_catalog", "chip_id": chip_id}
    png_path = CHIPS_DIR / f"{chip_id}.png"
    if (os.environ.get("AML_INLINE") == "1" or os.environ.get("AML_TEST_DIRECT") == "1") and png_path.is_file():
        mirrored = WORLD_ASSETS / "chips" / f"{chip_id}.png"
        return {
            "ok": True,
            "chip_id": chip_id,
            "path": str(png_path),
            "world_url": f"/world/assets/combinatronic/chips/{chip_id}.png",
            "mirrored": str(mirrored),
            "pins": chip.get("pins"),
            "package": chip.get("package"),
            "cached": True,
        }
    png = render_chip_closeup(chip)
    mirrored = _mirror_chip_asset(png)
    return {
        "ok": True,
        "chip_id": chip_id,
        "path": str(png),
        "world_url": f"/world/assets/combinatronic/chips/{chip_id}.png",
        "mirrored": str(mirrored),
        "pins": chip.get("pins"),
        "package": chip.get("package"),
    }


def write_exploring_manual(lang_id: str, *, seed: dict[str, Any] | None = None) -> str:
    """Hands-on Exploring book — labs, hello sample, G16 compile path, CHIPs notes."""
    seed = seed or _load(SEED, {})
    pack = _resolve_language_pack(seed, lang_id) if lang_id in (seed.get("language_packs") or {}) else {
        "commands": {"print": "io", "run": "exec", "compile": "exec"},
    }
    cmds: dict[str, str] = pack.get("commands") or {}
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    profile = _lang_profile(lang_id)
    g16_root = Path(os.environ.get("GROK16_ROOT", INSTALL / "Grok16"))
    g16_doc = _load(g16_root / "data" / "grok16-languages.json", {}) if g16_root.is_dir() else {}
    g16_row = (g16_doc.get("languages") or {}).get(lang_id) or {}
    hello = g16_root / "examples" / "languages" / lang_id
    hello_file = ""
    if hello.is_dir():
        for p in sorted(hello.glob("hello.*")):
            hello_file = p.name
            break
    lines = [
        f"# Exploring {label}",
        "",
        "![Cover — Exploring " + label + "](h7fig:cover)",
        "",
        f"Grok16 **Exploring** manual — learn by doing. No host JDK, no third-party toolchains.",
        f"Every exercise compiles through **bin/g16** inside the secure chamber.",
        "",
        f"- **Language id:** `{lang_id}`",
        f"- **G16 driver:** `{g16_row.get('driver', 'g16-interp')}`",
        f"- **Hello sample:** `{hello_file or 'examples/languages/' + lang_id + '/hello.*'}`",
        f"- **Generated:** {_now()}",
        "",
        "## Lab 0 — Prerequisites",
        "",
        "1. `GROK16_ROOT` points at your Grok16 tree.",
        "2. `bin/g16` exists — Grok16 compiles everything itself.",
        "3. Secure chamber: `lib/g16-secure-chamber.py`.",
        "4. Test harness: `lib/g16-compiler-test-harness.py`.",
        "",
        "## Lab 1 — Hello world",
        "",
        f"Open `Grok16/examples/languages/{lang_id}/{hello_file or 'hello.*'}` and run:",
        "",
        "```bash",
        f"python3 lib/g16-compiler-test-harness.py --lang {lang_id} --no-halt --json",
        "```",
        "",
        "## Lab 2 — Compile lane",
        "",
        "```bash",
        f"python3 Grok16/lib/g16-native-compile.py compile --lang {lang_id} \\",
        f"  Grok16/examples/languages/{lang_id}/{hello_file or 'hello.*'}",
        "```",
        "",
        "## Lab 3 — Interpreter lane",
        "",
        "If driver is `g16-interp` or `gpy-16`, benchmark the interpreter path:",
        "",
        "```bash",
        f"python3 Grok16/lib/g16-native-compile.py run \\",
        f"  Grok16/examples/languages/{lang_id}/{hello_file or 'hello.*'} --lang {lang_id}",
        "```",
        "",
        "## Lab 4 — CHIPs compatibility",
        "",
        "CHIPs silicon uses Grok16 `field_opt` (`-DCHIPS_G16_ACCURATE=1`). Languages on",
        "`native_bsp` runners share the same toolchain. Check health:",
        "",
        "```bash",
        "cat .nexus-state/g16-chips-lang-health.json",
        "```",
        "",
        "![Syntax overview](h7fig:syntax)",
        "![Canonical op map](h7fig:op_map)",
        "",
    ]
    if profile:
        lines.extend([
            f"- **Paradigm:** {profile.get('paradigm', '—')}",
            f"- **Typing:** {profile.get('typing', '—')}",
            f"- **Memory:** {profile.get('memory', '—')}",
            "",
        ])
    lines.extend([
        "## Canonical atoms (quick reference)",
        "",
    ])
    for op in (seed.get("canonical_ops") or [])[:12]:
        lines.append(f"- **{op['id']}** — {op.get('label', '')}")
    lines.extend([
        "",
        f"## {label} command sampler",
        "",
    ])
    for cmd in sorted(cmds.keys(), key=str.lower)[:24]:
        lines.append(f"- `{cmd}` → `{cmds[cmd]}`")
    lines.extend([
        "",
        "## Issue detection",
        "",
        "The compiler test harness reports: `security_block`, `compile_fail`, `interp_fail`,",
        "`missing_exploring_book`, `chips_gate_fail`. Halt severity stops the suite on critical gates.",
        "",
        "## Pair with Explaining",
        "",
        f"Read **Explaining {label}** (`explaining_{lang_id}/`) for the full command reference.",
        "",
        f"- Manual shelf: `library/dewey/000-computer-science/exploring_{lang_id}/`",
        f"- GUI: `/field-lang-manuals` (Exploring tab when available)",
        "",
    ])
    return "\n".join(lines) + "\n"


def pack_exploring_h7(lang_id: str, text: str) -> Path:
    h7c_mod = _h7c_module()
    if not h7c_mod:
        raise RuntimeError("field-h7c-compression.py missing")
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    book_id = f"exploring_{lang_id}"
    dest = LIBRARY_SHELF / book_id
    dest.mkdir(parents=True, exist_ok=True)
    h7c_path = dest / f"{book_id}.h7c"
    meta = {
        "id": book_id,
        "title": f"Exploring {label}",
        "author": "Grok16 Field",
        "license": "Field",
        "subject": "programming languages — hands-on",
        "category": "computer science",
        "dewey": "000",
        "combinatronic_lang": lang_id,
        "book_kind": "exploring",
        "uploaded": _now(),
        "reader": "NEXUS_H7C",
    }
    seed = _load(SEED, {})
    pack = _resolve_language_pack(seed, lang_id) if lang_id in (seed.get("language_packs") or {}) else {"commands": {}}
    profile = _lang_profile(lang_id)
    accent = LANG_ACCENT.get(lang_id, (168, 85, 247))
    cover_path = BOOKS_DIR / f"{lang_id}.png"
    syntax_path = render_syntax_diagram(lang_id, label=label, commands=pack.get("commands") or {})
    opmap_path = render_op_map_diagram(lang_id, label=label, commands=pack.get("commands") or {}, seed=seed)
    memory_path = render_memory_diagram(lang_id, label=label, profile=profile)
    compile_path = render_compile_path_diagram(lang_id, label=label)
    figures = {
        "cover": {"path": cover_path if cover_path.is_file() else syntax_path, "alt": f"Exploring {label}", "mime": "image/png", "plate_key": "cover", "accent": accent},
        "syntax": {"path": syntax_path, "alt": f"{label} syntax", "mime": "image/png", "plate_key": "syntax", "accent": accent},
        "op_map": {"path": opmap_path, "alt": f"{label} op map", "mime": "image/png", "plate_key": "op_map", "accent": accent},
        "memory": {"path": memory_path, "alt": f"{label} memory", "mime": "image/png", "plate_key": "memory", "accent": accent},
        "compile": {"path": compile_path, "alt": f"{label} g16 path", "mime": "image/png", "plate_key": "compile", "accent": accent},
    }
    packed = h7c_mod.pack_h7c(text, meta, use_optimizer=True, format_version=3, figures=figures)
    h7c_path.write_bytes(packed)
    ein = "H7C-EXPLORE-" + hashlib.sha256(text.encode()).hexdigest()[:12]
    book_json = {
        "id": book_id,
        "title": f"Exploring {label}",
        "author": "Grok16 Field",
        "dewey": "000",
        "dewey_label": "Computer science, information & general works",
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "book_kind": "exploring",
        "embedded_figures": ["cover", "syntax", "op_map", "memory", "compile"],
        "manual_reader": "/field-lang-manuals",
        "h7c": _rel(h7c_path),
        "field_path": _rel(h7c_path),
        "github_shelf": "000-computer-science",
        "combinatronic_lang": lang_id,
        "cover": f"/world/assets/combinatronic/books/{lang_id}.png",
        "updated": _now(),
    }
    (dest / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return h7c_path


def generate_exploring_book(lang_id: str) -> dict[str, Any]:
    seed = _load(SEED, {})
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    cover = render_book_cover(lang_id, label=f"Exploring {label}", command_count=0)
    mirrored = _mirror_asset(cover, "books")
    text = write_exploring_manual(lang_id, seed=seed)
    h7c_path = pack_exploring_h7(lang_id, text)
    return {
        "ok": True,
        "lang_id": lang_id,
        "kind": "exploring",
        "label": label,
        "cover": str(cover),
        "world_url": f"/world/assets/combinatronic/books/{lang_id}_exploring.png",
        "mirrored": str(mirrored),
        "h7c_path": str(h7c_path),
        "char_count": len(text),
    }


def ensure_exploring_books(*, limit: int | None = None) -> dict[str, Any]:
    g16 = _load(Path(os.environ.get("GROK16_ROOT", INSTALL / "Grok16")) / "data" / "grok16-languages.json", {})
    langs = sorted((g16.get("languages") or {}).keys())
    if limit:
        langs = langs[:limit]
    created, skipped, errors = [], [], []
    for lang_id in langs:
        if (LIBRARY_SHELF / f"exploring_{lang_id}" / "book.json").is_file():
            skipped.append(lang_id)
            continue
        try:
            rep = generate_exploring_book(lang_id)
            if rep.get("ok"):
                created.append(lang_id)
            else:
                errors.append({"lang": lang_id, "error": rep.get("error")})
        except Exception as exc:
            errors.append({"lang": lang_id, "error": type(exc).__name__})
    return {"ok": not errors, "created": created, "skipped": skipped, "errors": errors}


def generate_book(lang_id: str) -> dict[str, Any]:
    seed = _load(SEED, {})
    packs = seed.get("language_packs") or {}
    if lang_id not in packs:
        return {"ok": False, "error": "language_not_in_seed", "lang_id": lang_id}
    book_id = f"explaining_{lang_id}"
    h7c_path = LIBRARY_SHELF / book_id / f"{book_id}.h7c"
    cover_path = BOOKS_DIR / f"{lang_id}.png"
    if (os.environ.get("AML_INLINE") == "1" or os.environ.get("AML_TEST_DIRECT") == "1") and h7c_path.is_file() and cover_path.is_file():
        label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
        return {
            "ok": True,
            "lang_id": lang_id,
            "label": label,
            "cover": str(cover_path),
            "world_url": f"/world/assets/combinatronic/books/{lang_id}.png",
            "h7c_path": str(h7c_path),
            "h7_path": str(h7c_path),
            "cached": True,
        }
    pack = _resolve_language_pack(seed, lang_id)
    cmds = pack.get("commands") or {}
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    cover = render_book_cover(lang_id, label=label, command_count=len(cmds))
    mirrored = _mirror_asset(cover, "books")
    text = write_explaining_manual(lang_id, seed=seed)
    h7c_path = pack_explaining_h7(lang_id, text)
    return {
        "ok": True,
        "lang_id": lang_id,
        "label": label,
        "cover": str(cover),
        "world_url": f"/world/assets/combinatronic/books/{lang_id}.png",
        "mirrored": str(mirrored),
        "h7c_path": str(h7c_path),
        "h7_path": str(h7c_path),
        "command_count": len(cmds),
        "char_count": len(text),
    }


def build_manifest(*, chips: list[dict[str, Any]] | None = None, books: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    catalog = _load(CATALOG, {})
    seed = _load(SEED, {})
    chip_rows = chips or []
    book_rows = books or []
    return {
        "schema": "field-combinatronic-visuals-manifest/v1",
        "generated": _now(),
        "chips": {
            "count": len(chip_rows),
            "catalog_count": len(catalog.get("chips") or []),
            "items": chip_rows,
        },
        "books": {
            "count": len(book_rows),
            "language_count": len(seed.get("language_packs") or {}),
            "items": book_rows,
        },
        "assets_root": str(ASSETS),
        "world_root": "/world/assets/combinatronic",
    }


def _balance_mod() -> Any | None:
    path = INSTALL / "lib" / "field-combinatronic-balance.py"
    if not path.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("vis_bal", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def publish_panel(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    """Synchronous combinatoric entry — manifest/registry without full regen at balance."""
    import time
    t0 = time.perf_counter()
    bal = _balance_mod()
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("visuals", refresh=refresh, force=force, battery_path=PANEL)
        if entry.get("skip_build") and entry.get("cached_doc"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if hasattr(bal, "record_cycle"):
                bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
            panel = dict(entry["cached_doc"])
            panel["fast_path"] = True
            panel["balance_hold"] = True
            panel["balance_gate"] = entry.get("gate")
            panel["elapsed_ms"] = elapsed_ms
            panel["combinatronic"] = True
            return {"ok": True, "panel": panel, "skipped": True}
    if refresh:
        return generate_all()
    panel = _load(PANEL, {})
    if panel:
        registry = build_registry()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        gate = entry.get("gate") or {}
        if bal and hasattr(bal, "record_cycle"):
            bal.record_cycle(reorganized=not gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
        return {
            "ok": True,
            "panel": {**panel, "combinatronic": True, "entry_synchronous": True, "balance_gate": gate},
            "registry": {"path": _rel(REGISTRY), "file_count": registry.get("file_count")},
        }
    return generate_all()


def generate_all(*, chips_only: bool = False, books_only: bool = False) -> dict[str, Any]:
    catalog = _load(CATALOG, {})
    seed = _load(SEED, {})
    chip_results: list[dict[str, Any]] = []
    book_results: list[dict[str, Any]] = []

    if not books_only:
        for chip in catalog.get("chips") or []:
            cid = chip.get("id")
            if not cid:
                continue
            try:
                chip_results.append(generate_chip(str(cid)))
            except Exception as exc:
                chip_results.append({"ok": False, "chip_id": cid, "error": str(exc)})

    if not chips_only:
        for lang_id in sorted((seed.get("language_packs") or {}).keys()):
            try:
                book_results.append(generate_book(lang_id))
            except Exception as exc:
                book_results.append({"ok": False, "lang_id": lang_id, "error": str(exc)})

    manifest = build_manifest(chips=chip_results, books=book_results)
    _save(MANIFEST, manifest)
    panel = {
        "schema": "field-combinatronic-visuals-panel/v1",
        "generated": manifest["generated"],
        "chip_ok": sum(1 for r in chip_results if r.get("ok")),
        "book_ok": sum(1 for r in book_results if r.get("ok")),
        "manifest": str(MANIFEST),
        "world_root": manifest["world_root"],
    }
    _save(PANEL, panel)
    registry = build_registry()
    return {
        "ok": True,
        "manifest": manifest,
        "panel": panel,
        "registry": {"path": _rel(REGISTRY), "file_count": registry.get("file_count")},
    }


def visuals_panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    manifest = _load(MANIFEST, {})
    if manifest:
        if cached:
            return {**cached, "manifest": manifest, "ok": True}
        if os.environ.get("AML_INLINE") == "1" or os.environ.get("AML_TEST_DIRECT") == "1":
            return {
                "schema": "field-combinatronic-visuals-panel/v1",
                "generated": manifest.get("generated") or _now(),
                "manifest": manifest,
                "ok": True,
                "cold_cache": True,
            }
    if cached:
        return {**cached, "manifest": manifest, "ok": True}
    return generate_all()


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    if cmd == "generate":
        chips_only = "--chips" in sys.argv
        books_only = "--books" in sys.argv
        doc = generate_all(chips_only=chips_only, books_only=books_only)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "chip" and len(sys.argv) > 2:
        print(json.dumps(generate_chip(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "book" and len(sys.argv) > 2:
        print(json.dumps(generate_book(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "exploring" and len(sys.argv) > 2:
        print(json.dumps(generate_exploring_book(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "exploring-all":
        limit = None
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(ensure_exploring_books(limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "inventory":
        print(json.dumps(inventory(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "registry":
        print(json.dumps(build_registry(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ironclad-chip" and len(sys.argv) > 2:
        print(json.dumps(generate_ironclad_chip(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ironclad-all":
        limit = None
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(generate_ironclad_all(limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ironclad-thumbs":
        limit = None
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(generate_ironclad_all(thumbs_only=True, limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "repair":
        if len(sys.argv) > 2 and sys.argv[2] == "mirror":
            ironclad = len(sys.argv) > 3 and sys.argv[3] == "ironclad"
            print(json.dumps(repair_mirror(ironclad=ironclad), ensure_ascii=False, indent=2))
            return 0
        only_broken = "--all" not in sys.argv
        print(json.dumps(repair_all(only_broken=only_broken), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pattern" and len(sys.argv) > 2:
        print(json.dumps(explain_pattern(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "manifest":
        print(json.dumps(visuals_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(visuals_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("h7-audit", "h7_audit", "storage-audit"):
        vis = _import_mod("field_h7_visual", "field-h7-visual-adopt.py")
        if not vis:
            print(json.dumps({"ok": False, "error": "field-h7-visual-adopt missing"}, indent=2))
            return 1
        print(json.dumps(vis.audit_visuals(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("h7-adopt", "h7_adopt", "storage-adopt"):
        apply = "--apply" in sys.argv
        vis = _import_mod("field_h7_visual", "field-h7-visual-adopt.py")
        if not vis:
            print(json.dumps({"ok": False, "error": "field-h7-visual-adopt missing"}, indent=2))
            return 1
        print(json.dumps(vis.adopt_all_visuals(apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "enrich-catalog":
        print(json.dumps(enrich_chip_catalog(), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage",
                "hint": (
                    "field-combinatronic-visuals.py "
                    "[generate|manifest|inventory|verify|registry|repair|repair mirror|"
                    "enrich-catalog|ironclad-chip <id>|ironclad-all|ironclad-thumbs|"
                    "pattern <id>|chip <id>|book <lang>]"
                ),
                "doctrine": _rel(DOCTRINE),
            },
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())