#!/usr/bin/env pythong
"""G16 Universal Combinatronic — every chip + every language in one optimal facet."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-g16-universal-combinatronic-doctrine.json"
PANEL = STATE / "field-g16-universal-combinatronic-panel.json"
BATTERY = STATE / "field-g16-universal-combinatronic.json"
LEAF_PREFIX = "g16"


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


def _import_mod(name: str, rel: str) -> Any | None:
    for base in (INSTALL / "lib", Path(__file__).resolve().parent):
        path = base / rel
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            continue
    return None


def _chip_panel(*, refresh: bool = False) -> dict[str, Any]:
    mod = _import_mod("ic_chips", "field-ironclad-chips-combinatorics.py")
    if mod and hasattr(mod, "combinatronic_panel"):
        return mod.combinatronic_panel(refresh=refresh, state_dir=STATE)
    return _load(STATE / "field-ironclad-chips-combinatorics.json", {})


def _program_panel(*, refresh: bool = False) -> dict[str, Any]:
    mod = _import_mod("fpc", "field-program-combinatronic.py")
    if mod and hasattr(mod, "combinatronic_panel"):
        return mod.combinatronic_panel(refresh=refresh, state_dir=STATE)
    return _load(STATE / "field-program-combinatronic.json", {})


def _sense_slice() -> dict[str, Any]:
    mod = _import_mod("fsp", "field-sense-package-meld.py")
    if mod and hasattr(mod, "sense_universal_slice"):
        try:
            return mod.sense_universal_slice(state_dir=STATE)
        except Exception:
            pass
    return {}


_ISA_LANG: dict[str, list[str]] = {
    "combinatronics": [
        "ammolang", "field", "python", "c", "cxx", "javascript", "typescript", "java", "shell", "sql",
    ],
    "x86": [
        "c", "cxx", "asm", "pascal", "turbo_pascal", "delphi", "modula2", "fortran", "basic", "qbasic",
        "quickbasic", "freebasic", "visual_basic", "vba", "ammolang", "field", "python", "javascript",
        "typescript", "java", "kotlin", "csharp", "rust", "go", "zig", "d", "ada", "objc", "ruby", "php",
        "perl", "lua", "shell", "haskell", "lisp", "scala", "cobol", "forth", "algol",
    ],
    "m6809": ["asm", "basic", "c", "forth"],
    "m6502": ["asm", "basic", "forth"],
    "z80": ["asm", "basic", "forth", "c"],
    "arm": ["c", "cxx", "rust", "go", "swift", "kotlin", "ammolang", "python"],
    "riscv": ["c", "cxx", "rust", "go", "zig", "ammolang", "python"],
    "mips": ["c", "cxx", "java"],
    "powerpc": ["c", "cxx", "fortran"],
    "sh4": ["c", "cxx"],
    "cyrix": ["asm", "c", "cxx", "turbo_pascal", "pascal", "delphi"],
    "coco": ["basic", "asm", "forth"],
}


def _chip_isa(chip: dict[str, Any]) -> str:
    fam = str(chip.get("family") or chip.get("vendor") or "").lower()
    kind = str(chip.get("kind") or "").lower()
    dev = str(chip.get("mame_device") or chip.get("id") or "").lower()
    if "cyrix" in fam or "cyrix" in dev:
        return "cyrix"
    if "coco" in fam or "coco" in str(chip.get("platforms") or []):
        return "coco"
    if "z80" in dev or "z180" in dev:
        return "z80"
    if "6502" in dev or "65c02" in dev:
        return "m6502"
    if "6809" in dev or "6800" in dev:
        return "m6809"
    if "arm" in dev:
        return "arm"
    if "riscv" in dev:
        return "riscv"
    if "sh" in dev:
        return "sh4"
    if kind in ("host_cpu", "guest_cpu", "mame_device"):
        if "8086" in dev or "8088" in dev or "386" in dev or "486" in dev or "pentium" in dev:
            return "x86"
    return "x86" if kind == "host_cpu" else fam or "unknown"


def _connect_graph(chips: list[dict[str, Any]], langs: dict[str, Any]) -> list[dict[str, Any]]:
    lang_ids = set((langs.get("languages") or {}).keys()) if isinstance(langs.get("languages"), dict) else set()
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chip in chips[:400]:
        isa = _chip_isa(chip)
        targets = _ISA_LANG.get(isa, ["c", "asm"])
        for lang in targets:
            if lang_ids and lang not in lang_ids:
                continue
            key = f"{chip.get('id')}:{lang}"
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "from": chip.get("id"),
                "from_label": chip.get("label"),
                "isa": isa,
                "to_lang": lang,
                "kind": "chip_lang",
                "weight": 1.0,
            })
    return edges[:512]


def _leaf_score(leaf: dict[str, Any], *, idx: int) -> float:
    base = 1000.0 - idx
    facet = str(leaf.get("facet") or "")
    if facet in ("ironclad_chips", "chips_battery"):
        base += float(leaf.get("path_pct") or 0) * 2
        if str(leaf.get("thermal_tier") or "") == "cool":
            base += 12
    elif facet == "program_combinatronic":
        if leaf.get("kind") == "single_combinatronic":
            base += 48
        base += 8
    if leaf.get("runner") == "native_bsp":
        base += 16
    return base


def rebalance_leaves(leaves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = [( _leaf_score(l, idx=i), i, l) for i, l in enumerate(leaves)]
    scored.sort(key=lambda x: (-x[0], x[1]))
    out: list[dict[str, Any]] = []
    for rank, (score, _i, leaf) in enumerate(scored):
        row = dict(leaf)
        row["rebalance_rank"] = rank + 1
        row["rebalance_score"] = round(score, 2)
        out.append(row)
    return out


def condense_bands(
    chip_leaves: list[dict[str, Any]],
    prog_leaves: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bands: dict[str, dict[str, Any]] = {}
    for leaf in chip_leaves:
        fam = str(leaf.get("family") or leaf.get("kind") or "chips")
        bands.setdefault(f"chip:{fam}", {"band": f"chip:{fam}", "kind": "chip_family", "members": [], "count": 0})
        bands[f"chip:{fam}"]["members"].append(leaf.get("id"))
        bands[f"chip:{fam}"]["count"] += 1
    for leaf in prog_leaves:
        if leaf.get("kind") == "single_combinatronic":
            key = "prog:canonical"
        else:
            key = f"prog:{leaf.get('lang') or 'lang'}"
        bands.setdefault(key, {"band": key, "kind": "language_band", "members": [], "count": 0})
        bands[key]["members"].append(leaf.get("id"))
        bands[key]["count"] += 1
    rows = sorted(bands.values(), key=lambda b: (-b["count"], b["band"]))
    for i, row in enumerate(rows):
        row["condense_slot"] = i
        row["members"] = row["members"][:12]
    return rows


def _balance_mod() -> Any | None:
    return _import_mod("g16_balance", "field-combinatronic-balance.py")


def build_g16_universal(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _balance_mod()
    gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh"):
        gate = bal.gate_refresh(refresh, force=force)
        if gate.get("skip_reorganize") and not force:
            cached = _load(BATTERY, {})
            if cached.get("combinatorics_leaves"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                if hasattr(bal, "record_cycle"):
                    bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
                cached = dict(cached)
                cached["balance_hold"] = True
                cached["fast_path"] = True
                cached["balance_gate"] = gate
                cached["elapsed_ms"] = elapsed_ms
                return cached
        refresh = bool(gate.get("effective_refresh", refresh))

    if refresh:
        chip_mod = _import_mod("ic_chips", "field-ironclad-chips-combinatorics.py")
        prog_mod = _import_mod("fpc", "field-program-combinatronic.py")
        if chip_mod and hasattr(chip_mod, "publish_panel"):
            chip_mod.publish_panel(write_combinatorics=True)
        if prog_mod and hasattr(prog_mod, "publish_panel"):
            prog_mod.publish_panel(write_battery=True)
    chips_doc = _load(STATE / "field-ironclad-chips-combinatorics.json", {}) or _chip_panel(refresh=False)
    prog_doc = _load(STATE / "field-program-combinatronic.json", {}) or _program_panel(refresh=False)
    sense = _sense_slice()

    chip_leaves_in = chips_doc.get("combinatorics_leaves") or []
    prog_leaves_in = prog_doc.get("combinatorics_leaves") or []

    unified: list[dict[str, Any]] = []
    for leaf in chip_leaves_in:
        lid = str(leaf.get("id") or "")
        unified.append({
            **leaf,
            "id": f"{LEAF_PREFIX}:chip:{lid}",
            "source_leaf": lid,
            "sub_facet": "ironclad_chips",
            "facet": "g16_universal",
        })
    for leaf in prog_leaves_in:
        lid = str(leaf.get("id") or "")
        unified.append({
            **leaf,
            "id": f"{LEAF_PREFIX}:prog:{lid}",
            "source_leaf": lid,
            "sub_facet": "program_combinatronic",
            "facet": "g16_universal",
        })

    state_bal = (bal.balance_state() if bal and hasattr(bal, "balance_state") else {}) or {}
    at_balance = bool(state_bal.get("balanced")) and not refresh
    if at_balance and _load(BATTERY, {}).get("combinatorics_leaves"):
        rebalanced = _load(BATTERY, {}).get("combinatorics_leaves") or unified
        incremental_added = 0
    else:
        rebalanced = rebalance_leaves(unified)
        incremental_added = 0
    if bal and hasattr(bal, "stamp_optimized"):
        rebalanced = bal.stamp_optimized(rebalanced, balanced=at_balance or bool(gate.get("balanced")))
    bands = condense_bands(chip_leaves_in, prog_leaves_in)
    chip_rows = chips_doc.get("counts") or {}
    prog_counts = prog_doc.get("counts") or {}
    chips_list = _load(STATE / "field-ironclad-chips-combinatorics.json", {}).get("chips") or []
    connections = _connect_graph(chips_list, _load(STATE / "field-program-combinatronic.json", {}))

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    reorganized = bool(refresh and not gate.get("skip_reorganize"))
    result = {
        "schema": "field-g16-universal-combinatronic/v1",
        "updated": _now(),
        "motto": "G16 does everything — every chip, every language, one combinatronic.",
        "ok": True,
        "facet": "g16_universal",
        "sub_facets": {
            "ironclad_chips": {
                "leaf_count": chips_doc.get("leaf_count") or len(chip_leaves_in),
                "counts": chip_rows,
            },
            "program_combinatronic": {
                "leaf_count": prog_doc.get("leaf_count") or len(prog_leaves_in),
                "counts": prog_counts,
                "boil_pct": prog_doc.get("boil_pct"),
                "boil_complete": prog_doc.get("boil_complete"),
            },
            "sense_universal": {
                "leaf_count": sense.get("leaf_count"),
                "universal_lock": sense.get("universal_lock"),
            },
        },
        "counts": {
            "chips": chip_rows.get("total") or chip_rows.get("leaves"),
            "chip_leaves": len(chip_leaves_in),
            "languages": prog_counts.get("languages"),
            "commands": prog_counts.get("commands"),
            "program_leaves": len(prog_leaves_in),
            "unified_leaves": len(rebalanced),
            "connections": len(connections),
            "condense_bands": len(bands),
        },
        "combinatorics_leaves": rebalanced,
        "condense_bands": bands,
        "connections": connections,
        "rebalance": {
            "optimal": True,
            "top_leaves": rebalanced[:16],
            "statement": "Composite score — native_bsp + cool thermals + path_pct + canonical ops",
        },
        "single_combinatronic": {
            "chips_and_programs": True,
            "boil_pct": prog_doc.get("boil_pct"),
            "terminal_runner": "native_bsp",
            "terminal_belt": "belt_2_0",
        },
        "elapsed_ms": elapsed_ms,
        "balance_gate": gate or None,
        "optimized_combinatronic": at_balance or bool(gate.get("balanced")),
        "all_data_combinatronic": True,
        "combinatronic": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(
            reorganized=reorganized,
            elapsed_ms=elapsed_ms,
            incremental_added=incremental_added,
        )
    return result


def publish_panel(*, refresh: bool = False, write_battery: bool = True) -> dict[str, Any]:
    battery = build_g16_universal(refresh=refresh)
    panel = {
        "schema": "field-g16-universal-combinatronic-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok", True),
        "motto": battery.get("motto"),
        "facet": "g16_universal",
        "counts": battery.get("counts"),
        "sub_facets": battery.get("sub_facets"),
        "combinatorics_facet": "g16_universal",
        "leaf_count": len(battery.get("combinatorics_leaves") or []),
        "sample_leaves": (battery.get("combinatorics_leaves") or [])[:20],
        "condense_bands": (battery.get("condense_bands") or [])[:24],
        "connections_sample": (battery.get("connections") or [])[:16],
        "rebalance": battery.get("rebalance"),
        "single_combinatronic": battery.get("single_combinatronic"),
        "elapsed_ms": battery.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    return {"ok": True, "panel": panel, "battery_path": str(BATTERY), "panel_path": str(PANEL)}


def g16_universal_slice(*, state_dir: Path | None = None) -> dict[str, Any]:
    state = state_dir or STATE
    cached = _load(state / "field-g16-universal-combinatronic.json", {})
    if cached.get("combinatorics_leaves"):
        return {
            "schema": "field-g16-universal-slice/v1",
            "facet": "g16_universal",
            "counts": cached.get("counts"),
            "leaf_count": len(cached.get("combinatorics_leaves") or []),
            "combinatorics_leaves": (cached.get("combinatorics_leaves") or [])[:48],
            "sub_facets": cached.get("sub_facets"),
            "boil_pct": (cached.get("single_combinatronic") or {}).get("boil_pct"),
            "connections": len(cached.get("connections") or []),
            "condense_bands": len(cached.get("condense_bands") or []),
            "cached": True,
        }
    old = STATE
    try:
        if state_dir:
            globals()["STATE"] = state  # noqa: PLW0603
        pub = publish_panel(refresh=False, write_battery=True)
    finally:
        globals()["STATE"] = old
    panel = pub.get("panel") or {}
    return {
        "schema": "field-g16-universal-slice/v1",
        "facet": "g16_universal",
        "counts": panel.get("counts"),
        "leaf_count": panel.get("leaf_count"),
        "combinatorics_leaves": panel.get("sample_leaves") or [],
        "sub_facets": panel.get("sub_facets"),
        "cached": False,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    refresh = "--refresh" in sys.argv[2:]
    if cmd in ("json", "panel", "status"):
        if PANEL.is_file() and not refresh:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel(refresh=refresh).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "battery"):
        print(json.dumps(publish_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("combinatronic", "universal"):
        print(json.dumps(build_g16_universal(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(g16_universal_slice(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-g16-universal-combinatronic.py [json|build|combinatronic|slice]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())