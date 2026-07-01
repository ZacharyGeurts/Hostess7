#!/usr/bin/env pythong
"""CHIPS core — condense ironclad_chips + plate_stack into one core after Ironclad seals."""
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
DOCTRINE = INSTALL / "data" / "field-chips-core-doctrine.json"
PANEL = STATE / "field-chips-core-panel.json"
CORE = STATE / "field-chips-core.json"
IRONCLAD_CHIPS = STATE / "field-ironclad-chips-combinatorics.json"
PLATE_STACK = STATE / "field-chips-plate-stack.json"
ENABLED = os.environ.get("NEXUS_CHIPS_CORE", "1") == "1"
FACET = "chips_core"
IRONCLAD_CITE = "ironclad:chips:core"

_SOVEREIGN_CLOCK_MOD = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock_cc", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


def _load(path: Path, default: Any = None) -> Any:
    if os.environ.get("NEXUS_H7S_LANE", "1") == "1":
        lane = _import_py(INSTALL / "lib" / "field-h7s-lane.py", "field_h7s_lane_chips")
        if lane and hasattr(lane, "load_json"):
            doc = lane.load_json(path, default=None)
            if doc is not None:
                return doc
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def _ironclad_slice() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema"):
        return cached
    mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ic_cc")
    if mod and hasattr(mod, "immediate_slice"):
        try:
            return mod.immediate_slice()
        except Exception:
            pass
    return cached


def _ironclad_sealed(ironclad: dict[str, Any] | None = None) -> bool:
    doc = ironclad if ironclad is not None else _ironclad_slice()
    pts = doc.get("plate_to_sense") or {}
    return bool(doc.get("ironclad_sealed") or doc.get("realized") or pts.get("plate_sealed"))


def _ensure_ironclad_chips(*, refresh: bool = False) -> dict[str, Any]:
    cached = _load(IRONCLAD_CHIPS, {})
    if cached.get("chips") and not refresh:
        return cached
    mod = _import_py(INSTALL / "lib" / "field-ironclad-chips-combinatorics.py", "icc_src")
    if mod and hasattr(mod, "publish_panel"):
        pub = mod.publish_panel(write_combinatorics=True)
        return _load(IRONCLAD_CHIPS, {}) or pub.get("panel") or {}
    if mod and hasattr(mod, "build_ironclad_chips_combinatorics"):
        return mod.build_ironclad_chips_combinatorics()
    return cached


def _ensure_plate_stack(*, refresh: bool = False) -> dict[str, Any]:
    cached = _load(PLATE_STACK, {})
    if cached.get("modules") and not refresh:
        return cached
    mod = _import_py(INSTALL / "lib" / "field-chips-plate-stack.py", "cps_src")
    if mod and hasattr(mod, "publish_panel"):
        pub = mod.publish_panel(refresh=refresh, write_battery=True)
        return pub.get("battery") or cached
    if mod and hasattr(mod, "build_plate_stack"):
        return mod.build_plate_stack(refresh=refresh)
    return cached


def _core_leaf(chip: dict[str, Any], leaf: dict[str, Any] | None = None) -> dict[str, Any]:
    base = leaf or {}
    return {
        "id": base.get("id") or chip.get("combinatorics_leaf"),
        "chip_id": chip.get("id"),
        "label": chip.get("label"),
        "kind": chip.get("kind"),
        "family": chip.get("family"),
        "path_pct": chip.get("path_pct"),
        "sort_slot": chip.get("sort_slot", chip.get("slot")),
        "facet": FACET,
        "ironclad_cite": IRONCLAD_CITE,
        "source": chip.get("source"),
        "mame_device": chip.get("mame_device"),
        "core": True,
    }


def _core_module(mod: dict[str, Any], *, slot: int) -> dict[str, Any]:
    fam = str(mod.get("family") or "unknown")
    leaves = mod.get("leaves") or []
    return {
        "id": f"chips_core:{fam}",
        "core_id": f"chips_core:{fam}",
        "family": fam,
        "label": mod.get("label") or f"Core {fam}",
        "kind": "chips_core_family",
        "facet": FACET,
        "slot": slot,
        "chip_count": int(mod.get("chip_count") or mod.get("indexed_chips") or len(leaves) or 1),
        "path_pct": mod.get("path_pct"),
        "leaves": leaves[:64],
        "leaf_count": len(leaves) if leaves else int(mod.get("indexed_chips") or 1),
        "bsp_model": mod.get("bsp_model"),
        "neural_calc": mod.get("neural_calc"),
        "ironclad_grounded": mod.get("ironclad_grounded"),
        "steel_plate": mod.get("steel_plate"),
        "combinatorics_leaf": mod.get("combinatorics_leaf") or f"chips_core:{fam}",
        "condensed_from": ["chips_plate_stack", "ironclad_chips"],
    }


def condense_into_core(
    *,
    ironclad_chips: dict[str, Any] | None = None,
    plate_stack: dict[str, Any] | None = None,
    ironclad: dict[str, Any] | None = None,
    refresh_sources: bool = False,
) -> dict[str, Any]:
    """Fold scattered CHIP layers into one core when Ironclad is sealed."""
    t0 = time.perf_counter()
    doctrine = _load(DOCTRINE, {})
    iron = ironclad if ironclad is not None else _ironclad_slice()
    sealed = _ironclad_sealed(iron)
    truth = float(iron.get("truth_percent") or (iron.get("plate_to_sense") or {}).get("truth_percent") or 0)

    chip_doc = ironclad_chips if ironclad_chips is not None else _ensure_ironclad_chips(refresh=refresh_sources)
    stack_doc = plate_stack if plate_stack is not None else _ensure_plate_stack(refresh=refresh_sources)
    chips = list(chip_doc.get("chips") or [])
    leaves_src = list(chip_doc.get("combinatorics_leaves") or [])
    modules_src = list(stack_doc.get("modules") or [])
    pred = chip_doc.get("code_path_prediction") or {}

    if not sealed:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "schema": "field-chips-core/v1",
            "updated": _now(),
            "motto": doctrine.get("motto"),
            "ok": bool(chips),
            "enabled": ENABLED,
            "condensed": False,
            "pending": True,
            "ironclad_sealed": False,
            "facet": FACET,
            "ironclad_citation": IRONCLAD_CITE,
            "sources": {
                "ironclad_chips": {"chip_count": len(chips), "leaf_count": len(leaves_src)},
                "chips_plate_stack": {"module_count": len(modules_src)},
            },
            "counts": {
                "chips": len(chips),
                "leaves": len(leaves_src),
                "core_modules": 0,
            },
            "posture": "Awaiting Ironclad seal — CHIP layers remain scattered.",
            "elapsed_ms": elapsed_ms,
        }

    leaf_by_chip = {str(l.get("chip_id") or ""): l for l in leaves_src if l.get("chip_id")}
    core_leaves = [_core_leaf(c, leaf_by_chip.get(str(c.get("id") or ""))) for c in chips]
    core_leaves.sort(key=lambda row: (
        row.get("sort_slot") if row.get("sort_slot") is not None else 999,
        -float(row.get("path_pct") or 0),
        str(row.get("label") or ""),
    ))

    if modules_src:
        core_modules = [_core_module(m, slot=i) for i, m in enumerate(modules_src)]
    else:
        by_family: dict[str, list[dict[str, Any]]] = {}
        for chip in chips:
            fam = str(chip.get("family") or "unknown")
            by_family.setdefault(fam, []).append(chip)
        core_modules = []
        for slot, (fam, fam_chips) in enumerate(sorted(by_family.items())):
            core_modules.append({
                "id": f"chips_core:{fam}",
                "core_id": f"chips_core:{fam}",
                "family": fam,
                "label": f"Core {fam}",
                "kind": "chips_core_family",
                "facet": FACET,
                "slot": slot,
                "chip_count": len(fam_chips),
                "path_pct": round(sum(float(c.get("path_pct") or 0) for c in fam_chips), 2),
                "leaves": [_core_leaf(c) for c in fam_chips[:64]],
                "leaf_count": len(fam_chips),
                "condensed_from": ["ironclad_chips"],
            })

    indexed = sum(int(m.get("leaf_count") or m.get("chip_count") or 0) for m in core_modules)
    families = {str(m.get("family") or "unknown"): int(m.get("chip_count") or 1) for m in core_modules}
    stack_counts = stack_doc.get("counts") or {}
    chip_counts = chip_doc.get("counts") or {}

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "schema": "field-chips-core/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "ok": len(core_modules) > 0 and len(core_leaves) > 0,
        "enabled": ENABLED,
        "condensed": True,
        "pending": False,
        "ironclad_sealed": True,
        "facet": FACET,
        "ironclad_citation": IRONCLAD_CITE,
        "ironclad_chain": {
            "root": "ironclad-immediate",
            "citation": IRONCLAD_CITE,
            "truth_percent": truth,
            "grounded": True,
            "sources_condensed": ["ironclad_chips", "chips_plate_stack"],
            "layers": ["ironclad", "chips_core"],
        },
        "sources": {
            "ironclad_chips": {
                "schema": chip_doc.get("schema"),
                "chip_count": len(chips),
                "leaf_count": len(leaves_src),
                "counts": chip_counts,
            },
            "chips_plate_stack": {
                "schema": stack_doc.get("schema"),
                "module_count": len(modules_src),
                "counts": stack_counts,
                "steel_rewrite": bool(stack_doc.get("steel_rewrite")),
            },
        },
        "counts": {
            "chips": len(chips),
            "leaves": len(core_leaves),
            "core_modules": len(core_modules),
            "families": len(families),
            "indexed_chips": indexed,
            "compression_ratio": round(len(chips) / max(1, len(core_modules)), 2),
            "resolution_lossless": indexed >= len(chips) or bool(chip_doc.get("h7s_reconstructed")),
            "by_kind": chip_counts.get("by_kind") or {},
            "by_family": families,
        },
        "code_path_prediction": {
            "hard_percent": pred.get("hard_percent", True),
            "total_pct": pred.get("total_pct"),
            "path_count": pred.get("path_count"),
            "the_sort": pred.get("the_sort", True),
            "algorithm": pred.get("algorithm") or "composite_bsp",
        },
        "core_modules": core_modules,
        "core_leaves": core_leaves,
        "sample_modules": core_modules[:24],
        "sample_leaves": core_leaves[:48],
        "connection_policy": stack_doc.get("connection_policy") or {"sovereign_time_only": True},
        "plate_layers": stack_doc.get("layers"),
        "combinatronic": True,
        "all_data_combinatronic": True,
        "queen_surface": doctrine.get("queen_surface") or "/world/queen-chips-cores.html",
        "posture": (
            f"CHIPS core sealed — {len(chips)} dies → {len(core_modules)} core modules "
            f"({round(len(chips) / max(1, len(core_modules)), 1)}× condense)"
        ),
        "elapsed_ms": elapsed_ms,
    }


def build_chips_core(*, refresh: bool = False) -> dict[str, Any]:
    cached = _load(CORE, {})
    if cached.get("condensed") and cached.get("core_modules") and not refresh:
        return cached
    return condense_into_core(refresh_sources=refresh)


def publish_panel(*, refresh: bool = False, write_core: bool = True) -> dict[str, Any]:
    core = build_chips_core(refresh=refresh)
    panel = {
        "schema": "field-chips-core-panel/v1",
        "updated": core.get("updated"),
        "ok": core.get("ok"),
        "motto": core.get("motto"),
        "condensed": core.get("condensed"),
        "pending": core.get("pending"),
        "ironclad_sealed": core.get("ironclad_sealed"),
        "facet": FACET,
        "counts": core.get("counts"),
        "sources": core.get("sources"),
        "code_path_prediction": core.get("code_path_prediction"),
        "sample_modules": core.get("sample_modules"),
        "sample_leaves": core.get("sample_leaves"),
        "posture": core.get("posture"),
        "elapsed_ms": core.get("elapsed_ms"),
        "queen_surface": core.get("queen_surface"),
        "combinatronic": True,
    }
    _save(PANEL, panel)
    if write_core:
        _save(CORE, core)
        if os.environ.get("NEXUS_H7S_LANE", "1") == "1":
            lane = _import_py(INSTALL / "lib" / "field-h7s-lane.py", "field_h7s_lane_publish")
            if lane and hasattr(lane, "after_json_publish"):
                lane.after_json_publish(CORE)
                lane.after_json_publish(IRONCLAD_CHIPS)
    return {"ok": core.get("ok", True), "panel": panel, "core": core}


def chips_core_slice() -> dict[str, Any]:
    cached = _load(CORE, {})
    if cached.get("schema"):
        return {
            "schema": "field-chips-core-slice/v1",
            "condensed": cached.get("condensed"),
            "pending": cached.get("pending"),
            "ironclad_sealed": cached.get("ironclad_sealed"),
            "counts": cached.get("counts"),
            "facet": FACET,
            "sample_modules": cached.get("sample_modules"),
            "sample_leaves": cached.get("sample_leaves"),
            "posture": cached.get("posture"),
            "cached": True,
        }
    pub = publish_panel(refresh=False, write_core=True)
    core = pub.get("core") or {}
    return {
        "schema": "field-chips-core-slice/v1",
        "condensed": core.get("condensed"),
        "pending": core.get("pending"),
        "counts": core.get("counts"),
        "facet": FACET,
        "cached": False,
    }


def maybe_condense_after_ironclad(*, refresh: bool = False) -> dict[str, Any] | None:
    """Hook for ironclad publish — condense only when sealed."""
    if not ENABLED:
        return None
    if not _ironclad_sealed():
        return None
    return publish_panel(refresh=refresh, write_core=True)


def verify_core() -> dict[str, Any]:
    core = build_chips_core(refresh=False)
    counts = core.get("counts") or {}
    sealed = bool(core.get("ironclad_sealed"))
    condensed = bool(core.get("condensed"))
    chips_n = int(counts.get("chips") or 0)
    modules_n = int(counts.get("core_modules") or 0)
    leaves_n = int(counts.get("leaves") or 0)
    if not sealed:
        ok = chips_n >= 50 and bool(core.get("pending"))
    else:
        ok = (
            condensed
            and chips_n >= 50
            and modules_n >= 1
            and leaves_n >= 50
            and bool(counts.get("resolution_lossless"))
        )
    return {
        "ok": ok,
        "ironclad_sealed": sealed,
        "condensed": condensed,
        "chip_count": chips_n,
        "core_module_count": modules_n,
        "leaf_count": leaves_n,
        "compression_ratio": counts.get("compression_ratio"),
        "resolution_lossless": counts.get("resolution_lossless"),
        "facet": FACET,
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
    if cmd in ("build", "publish", "condense", "core"):
        print(json.dumps(publish_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(chips_core_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        doc = verify_core()
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "build", "publish", "condense", "core", "slice", "verify"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())