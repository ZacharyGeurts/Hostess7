#!/usr/bin/env pythong
"""Combinatronic Spider Wire — Ironclad outward view, neural lane priority, zero bottlenecks."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-combinatronic-spider-wire-doctrine.json"
PANEL = STATE / "field-combinatronic-spider-wire-panel.json"
BATTERY = STATE / "field-combinatronic-spider-wire.json"
NARROW_WIDTH = 16
GROWTH_PANEL = STATE / "field-combinatronics-growth-panel.json"
GROWTH_BATTERY = STATE / "field-combinatronics-growth.json"
NARROW_WIDTH_SYNC = STATE / "field-combinatronics-narrow-width.json"


def apply_narrow_width(width: int) -> int:
    """Apply growth-derived optimal compute width to spider wire bands."""
    global NARROW_WIDTH
    w = max(8, min(48, int(width)))
    NARROW_WIDTH = w
    return NARROW_WIDTH


def _resolve_narrow_width() -> int:
    """Prefer growth scan optimal width; fall back to sync receipt or default."""
    for path in (NARROW_WIDTH_SYNC, GROWTH_PANEL, GROWTH_BATTERY):
        doc = _load(path, {})
        if not doc:
            continue
        ow = doc.get("narrow_width") if path == NARROW_WIDTH_SYNC else doc.get("optimal_width")
        if isinstance(ow, dict):
            ow = ow.get("optimal_width")
        if isinstance(ow, (int, float)) and 4 <= int(ow) <= 128:
            return apply_narrow_width(int(ow))
    return NARROW_WIDTH


NEURAL_WEIGHTS = {
    "repetition": 0.35,
    "coolness": 0.30,
    "separation": 0.25,
    "fan_in_penalty": 0.40,
    "sovereign_phase": 0.05,
}


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
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sovereign_phase() -> float:
    """Sole external cadence — linear_ns phase 0..1 for tie-break only."""
    try:
        sc = INSTALL / "lib" / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sc", sc)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "ns_linear"):
                ns = int(mod.ns_linear())
                return (ns % 1_000_000) / 1_000_000.0
    except Exception:
        pass
    return (time.time_ns() % 1_000_000) / 1_000_000.0


def _ironclad_outward_root() -> dict[str, Any]:
    meld = _load(STATE / "field-plate-meld.json", {})
    sanity = _load(STATE / "ironclad-field-sanity-panel.json", {})
    organize = _load(STATE / "iron-plate-organize-panel.json", {})
    return {
        "id": "ironclad:capstone",
        "layer": 1,
        "kind": "ironclad",
        "citation": "ironclad:meld:2",
        "meld_generation": meld.get("generation"),
        "sanity_ok": sanity.get("ok", True),
        "organize_ok": organize.get("ok", True),
        "children": ["meld:plate", "sanity:cool_sort", "power_sort:plate", "combinatorics:bridge"],
    }


def _collect_sources() -> dict[str, Any]:
    uni = _load(STATE / "field-g16-universal-combinatronic.json", {})
    chips = _load(STATE / "field-ironclad-chips-combinatorics.json", {})
    prog = _load(STATE / "field-program-combinatronic.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    if not uni.get("combinatorics_leaves"):
        uni_mod = _import_mod("g16_uni", "field-g16-universal-combinatronic.py")
        if uni_mod and hasattr(uni_mod, "publish_panel"):
            pub = uni_mod.publish_panel(refresh=not chips.get("combinatorics_leaves"), write_battery=True)
            uni = pub.get("panel") or _load(STATE / "field-g16-universal-combinatronic.json", {})
            if not uni.get("combinatorics_leaves"):
                bat = _load(STATE / "field-g16-universal-combinatronic.json", {})
                if bat.get("combinatorics_leaves"):
                    uni = bat
    if not chips.get("combinatorics_leaves"):
        cm = _import_mod("ic_chips", "field-ironclad-chips-combinatorics.py")
        if cm and hasattr(cm, "combinatronic_panel"):
            chips = cm.combinatronic_panel(refresh=True)
    if not prog.get("combinatorics_leaves"):
        pm = _import_mod("fpc", "field-program-combinatronic.py")
        if pm and hasattr(pm, "combinatronic_panel"):
            prog = pm.combinatronic_panel(refresh=True)
    return {"uni": uni, "chips": chips, "prog": prog, "bridge": bridge}


def _instruction_key(leaf: dict[str, Any]) -> str:
    if leaf.get("canonical"):
        return str(leaf["canonical"])
    if leaf.get("kind") == "single_combinatronic":
        return str(leaf.get("canonical_op") or leaf.get("id") or "exec")
    if leaf.get("runner"):
        return f"runner:{leaf['runner']}"
    return str(leaf.get("id") or leaf.get("chip_id") or leaf.get("lang") or "leaf")


def _cool_score(leaf: dict[str, Any]) -> float:
    tier = str(leaf.get("thermal_tier") or leaf.get("pipe_width") or "").lower()
    band = int(leaf.get("band") or 2)
    if tier == "cool" or tier == "cold":
        return 1.0
    if tier == "warm":
        return 0.55
    if tier == "narrow":
        return 0.35
    if band >= 2:
        return 0.85
    if band == 1:
        return 0.5
    return 0.25


def _neural_priority(
    *,
    repetition: float,
    coolness: float,
    separation: float,
    fan_in: int,
    phase: float,
) -> float:
    w = NEURAL_WEIGHTS
    fan_pen = min(1.0, fan_in / 12.0)
    return round(
        w["repetition"] * repetition
        + w["coolness"] * coolness
        + w["separation"] * separation
        - w["fan_in_penalty"] * fan_pen
        + w["sovereign_phase"] * phase,
        4,
    )


def _build_wire_graph(sources: dict[str, Any]) -> list[dict[str, Any]]:
    root = _ironclad_outward_root()
    wires: list[dict[str, Any]] = [root]
    layer1 = {
        "id": "meld:plate",
        "layer": 1,
        "parent": root["id"],
        "kind": "meld_plate",
        "pattern": (sources["bridge"].get("exec_posture") or {}).get("pattern_id"),
    }
    wires.append(layer1)
    for facet_id, label in (
        ("ironclad_chips", "chips"),
        ("program_combinatronic", "program"),
        ("sense_universal", "sense"),
    ):
        sub = (sources["uni"].get("sub_facets") or {}).get(facet_id) or {}
        wires.append(
            {
                "id": f"g16:{facet_id}",
                "layer": 2,
                "parent": layer1["id"],
                "kind": "g16_facet",
                "facet": facet_id,
                "leaf_count": sub.get("leaf_count"),
            }
        )
    for band in sources["uni"].get("condense_bands") or []:
        wires.append(
            {
                "id": f"band:{band.get('band')}",
                "layer": 3,
                "parent": "g16:universal",
                "kind": "condense_band",
                "band": band.get("band"),
                "count": band.get("count"),
                "slot": band.get("condense_slot"),
            }
        )
    return wires


def _cool_band_count(leaves: list[dict[str, Any]], condense_bands: list[dict[str, Any]]) -> int:
    n = len(leaves) or 1
    base = max(NARROW_WIDTH, int(math.ceil(n / NARROW_WIDTH)))
    return min(max(base, len(condense_bands) or NARROW_WIDTH), 128)


def _lane_assignments(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], Counter[str]]:
    leaves = sources["uni"].get("combinatorics_leaves") or []
    condense = sources["uni"].get("condense_bands") or []
    chip_paths = (sources["chips"].get("path_prediction") or {}).get("bands") or []
    cool_bands = _cool_band_count(leaves, condense)
    path_by_chip: dict[str, dict[str, Any]] = {}
    for band in chip_paths:
        for slot in band.get("slots") or []:
            cid = str(slot.get("chip_id") or "")
            if cid:
                path_by_chip[cid] = {
                    "band": band.get("band"),
                    "pipe_width": band.get("pipe_width"),
                    "path_pct": slot.get("path_pct"),
                    "slot": slot.get("slot"),
                }

    op_counts: Counter[str] = Counter()
    for leaf in leaves:
        op_counts[_instruction_key(leaf)] += 1
    max_rep = max(op_counts.values()) if op_counts else 1

    lanes: list[dict[str, Any]] = []
    band_load: Counter[str] = Counter()
    phase = _sovereign_phase()

    for idx, leaf in enumerate(leaves):
        op = _instruction_key(leaf)
        chip_id = str(leaf.get("chip_id") or leaf.get("source_leaf") or "")
        path = path_by_chip.get(chip_id, {})
        pipe_raw = str(path.get("pipe_width") or leaf.get("pipe_width") or "cold")
        # Ironclad outward: round-robin cool bands — even separation, no hot piles
        if pipe_raw == "narrow":
            band_key = f"band:narrow:{idx % NARROW_WIDTH}"
            pipe = "narrow"
            spread = idx % NARROW_WIDTH
        elif pipe_raw == "warm":
            warm_slots = max(8, cool_bands // 4)
            band_key = f"band:warm:{idx % warm_slots}"
            pipe = "warm"
            spread = idx % warm_slots
        else:
            spread = idx % cool_bands
            band_key = f"band:cool:{spread}"
            pipe = "cold"
        cool = _cool_score({**leaf, "pipe_width": pipe, "band": spread})
        repetition = op_counts[op] / max_rep
        band_load[band_key] += 1
        expected = max(1, len(leaves) / cool_bands)
        separation = 1.0 / (1.0 + max(0, band_load[band_key] - expected) * 0.08)
        fan_in = band_load[band_key]
        priority = _neural_priority(
            repetition=repetition,
            coolness=cool,
            separation=separation,
            fan_in=max(0, fan_in - int(expected)),
            phase=phase,
        )
        lanes.append(
            {
                "lane_id": f"lane:{idx:04d}",
                "leaf_id": leaf.get("id"),
                "instruction": op,
                "facet": leaf.get("facet") or leaf.get("sub_facet"),
                "band": band_key,
                "pipe_width": pipe,
                "repetition": op_counts[op],
                "repetition_norm": round(repetition, 3),
                "coolness": round(cool, 3),
                "separation": round(separation, 3),
                "fan_in": fan_in,
                "neural_priority": priority,
                "thermal_tier": "cool" if cool >= 0.8 else ("warm" if cool >= 0.5 else "hot"),
            }
        )

    lanes.sort(key=lambda r: (-r["neural_priority"], r["lane_id"]))
    for rank, row in enumerate(lanes):
        row["priority_rank"] = rank + 1
    return lanes, band_load


def _detect_bottlenecks(lanes: list[dict[str, Any]], band_load: Counter[str]) -> list[dict[str, Any]]:
    bottlenecks: list[dict[str, Any]] = []
    if not lanes:
        return bottlenecks
    op_band: Counter[tuple[str, str]] = Counter()
    for row in lanes:
        op_band[(row["instruction"], row["band"])] += 1

    n = len(lanes)
    band_n = max(1, len(band_load))
    expected = n / band_n
    fan_threshold = max(NARROW_WIDTH, int(expected * 1.35))
    narrow_cap = NARROW_WIDTH if "narrow" in "".join(band_load.keys()) else int(expected * 1.5)

    for band, load in band_load.items():
        cap = narrow_cap if "narrow" in band else fan_threshold
        if load > cap:
            kind = "narrow_overflow" if "narrow" in band else "fan_in"
            bottlenecks.append(
                {
                    "id": f"{kind}:{band}",
                    "kind": kind,
                    "band": band,
                    "load": load,
                    "threshold": cap,
                    "fix": "promote_to_warm" if "narrow" in band else "split_lane",
                }
            )

    repeat_threshold = max(4, int(expected * 0.6))
    for (op, band), cnt in op_band.items():
        if cnt >= repeat_threshold:
            bottlenecks.append(
                {
                    "id": f"hot_repeat:{op}:{band}",
                    "kind": "hot_repeat",
                    "instruction": op,
                    "band": band,
                    "count": cnt,
                    "threshold": repeat_threshold,
                    "fix": "cool_sort_spread",
                }
            )

    narrow_hot = [r for r in lanes if r.get("pipe_width") == "narrow" and r.get("thermal_tier") == "hot"]
    if len(narrow_hot) >= max(6, int(n * 0.02)):
        bottlenecks.append(
            {
                "id": "adjacent_choke:narrow",
                "kind": "adjacent_choke",
                "count": len(narrow_hot),
                "threshold": max(6, int(n * 0.02)),
                "fix": "separate_band",
            }
        )
    return bottlenecks


def _optimize_lanes(lanes: list[dict[str, Any]], bottlenecks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-spill overloaded bands into least-loaded cool slots."""
    if not bottlenecks or not lanes:
        return lanes
    n = len(lanes)
    cool_slots = max(NARROW_WIDTH, int(math.ceil(n / NARROW_WIDTH)))
    overloaded = {b["band"] for b in bottlenecks if b.get("kind") in ("fan_in", "narrow_overflow", "hot_repeat")}
    band_counts: Counter[str] = Counter()
    cool_keys = [f"band:cool:{i}" for i in range(cool_slots)]
    spill_idx = 0
    optimized: list[dict[str, Any]] = []

    for row in lanes:
        r = dict(row)
        if r["band"] in overloaded or r.get("thermal_tier") == "hot":
            target = min(cool_keys, key=lambda k: band_counts[k])
            r["band"] = target
            r["pipe_width"] = "cold"
            r["optimized"] = True
            r["coolness"] = min(1.0, r.get("coolness", 0.5) + 0.25)
            spill_idx += 1
        band_counts[r["band"]] += 1
        r["fan_in_after"] = band_counts[r["band"]]
        optimized.append(r)

    optimized.sort(key=lambda r: (-r["neural_priority"], r.get("priority_rank", 0)))
    for rank, row in enumerate(optimized):
        row["priority_rank"] = rank + 1
    return optimized


def build_spider_wire(*, optimize: bool = True, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _import_mod("sw_bal", "field-combinatronic-balance.py")
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("spider", refresh=False, force=force, battery_path=BATTERY)
        if entry.get("skip_build") and entry.get("cached_doc"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if hasattr(bal, "record_cycle"):
                bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
            out = dict(entry["cached_doc"])
            out["fast_path"] = True
            out["balance_hold"] = True
            out["balance_gate"] = entry.get("gate")
            out["elapsed_ms"] = elapsed_ms
            return out
    narrow_w = _resolve_narrow_width()
    sources = _collect_sources()
    wires = _build_wire_graph(sources)
    lanes, band_load = _lane_assignments(sources)
    bottlenecks = _detect_bottlenecks(lanes, band_load)
    optimized_lanes = lanes
    if optimize and bottlenecks:
        for _ in range(3):
            optimized_lanes = _optimize_lanes(optimized_lanes, bottlenecks)
            after_load: Counter[str] = Counter(r["band"] for r in optimized_lanes)
            bottlenecks = _detect_bottlenecks(optimized_lanes, after_load)
            if not bottlenecks:
                break
    after_load = Counter(r["band"] for r in optimized_lanes)
    after_bn = _detect_bottlenecks(optimized_lanes, after_load)

    gate = entry.get("gate") or {}
    if bal and hasattr(bal, "stamp_optimized"):
        optimized_lanes = bal.stamp_optimized(optimized_lanes[:256], balanced=bool(gate.get("balanced")))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-combinatronic-spider-wire/v1",
        "updated": _now(),
        "motto": "Ironclad outward — spider wire, neural priority, cool separation, zero bottlenecks.",
        "view": "ironclad_outward",
        "ok": len(after_bn) == 0,
        "ironclad_root": wires[0] if wires else _ironclad_outward_root(),
        "wire_layers": wires,
        "wire_count": len(wires),
        "lane_count": len(optimized_lanes),
        "instruction_count": len({r["instruction"] for r in optimized_lanes}),
        "bottleneck_count": len(bottlenecks),
        "bottleneck_count_after": len(after_bn),
        "bottlenecks_before": bottlenecks[:24],
        "bottlenecks_after": after_bn[:12],
        "neural": {
            "kind": "simple_weighted",
            "weights": NEURAL_WEIGHTS,
            "sovereign_phase": round(_sovereign_phase(), 6),
            "outside_input": False,
        },
        "top_priorities": optimized_lanes[:32],
        "lanes": optimized_lanes,
        "band_load": dict(after_load),
        "optimized": optimize and bool(bottlenecks),
        "narrow_width": narrow_w,
        "elapsed_ms": elapsed_ms,
        "balance_gate": gate or None,
        "combinatronic": True,
        "all_data_combinatronic": True,
        "optimized_combinatronic": bool(gate.get("balanced")),
        "entry_synchronous": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    return result


def publish_panel(*, optimize: bool = True, write_battery: bool = True) -> dict[str, Any]:
    battery = build_spider_wire(optimize=optimize)
    panel = {
        "schema": "field-combinatronic-spider-wire-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok"),
        "view": "ironclad_outward",
        "wire_count": battery.get("wire_count"),
        "lane_count": battery.get("lane_count"),
        "bottleneck_count": battery.get("bottleneck_count_after"),
        "top_priorities": battery.get("top_priorities"),
        "ironclad_root": battery.get("ironclad_root"),
        "neural": battery.get("neural"),
        "optimized": battery.get("optimized"),
        "elapsed_ms": battery.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    return {"ok": battery.get("ok"), "panel": panel, "battery": battery}


def spider_wire_slice() -> dict[str, Any]:
    cached = _load(BATTERY, {})
    if cached.get("lanes"):
        return {
            "schema": "field-combinatronic-spider-wire-slice/v1",
            "view": "ironclad_outward",
            "ok": cached.get("ok"),
            "lane_count": cached.get("lane_count"),
            "bottleneck_count": cached.get("bottleneck_count_after"),
            "top_priorities": (cached.get("top_priorities") or [])[:16],
            "cached": True,
        }
    pub = publish_panel(optimize=True)
    bat = pub.get("battery") or {}
    return {
        "schema": "field-combinatronic-spider-wire-slice/v1",
        "view": "ironclad_outward",
        "ok": bat.get("ok"),
        "lane_count": bat.get("lane_count"),
        "bottleneck_count": bat.get("bottleneck_count_after"),
        "top_priorities": (bat.get("top_priorities") or [])[:16],
        "cached": False,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    optimize = "--no-optimize" not in sys.argv
    if cmd in ("panel", "json", "status"):
        if PANEL.is_file() and "--refresh" not in sys.argv:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel(optimize=optimize).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "wire", "spider"):
        print(json.dumps(publish_panel(optimize=optimize), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(spider_wire_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "bottlenecks":
        bat = build_spider_wire(optimize=False)
        print(json.dumps({"bottlenecks": bat.get("bottlenecks_before"), "count": bat.get("bottleneck_count")}, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage",
                "hint": "field-combinatronic-spider-wire.py [panel|build|slice|bottlenecks] [--refresh] [--no-optimize]",
                "doctrine": str(DOCTRINE),
            },
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())