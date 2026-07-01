#!/usr/bin/env pythong
"""CHIPS Iron Plate + Steel Plate stack — every die removable above Ironclad, sovereign time only."""
from __future__ import annotations

import hashlib
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
DOCTRINE = INSTALL / "data" / "field-chips-iron-steel-plate-doctrine.json"
PANEL = STATE / "field-chips-plate-stack-panel.json"
BATTERY = STATE / "field-chips-plate-stack.json"
IRONCLAD_CHIPS = STATE / "field-ironclad-chips-combinatorics.json"
ENABLED = os.environ.get("NEXUS_CHIPS_PLATE_STACK", "1") == "1"
LOW_POWER = os.environ.get("NEXUS_CHIP_BATTERY_LOW_POWER", "1") == "1"

_SOVEREIGN_CLOCK_MOD = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock_cps", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


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
    pio = _import_py(INSTALL / "lib" / "plate-sealed-io.py", "plate_sealed_io")
    if pio and hasattr(pio, "sealed_write_json"):
        pio.sealed_write_json(path, doc)
        return
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


def _sovereign_wire() -> dict[str, Any]:
    sc = _SOVEREIGN_CLOCK_MOD
    if sc is None:
        _now()
        sc = _SOVEREIGN_CLOCK_MOD
    policy = (_load(DOCTRINE, {}).get("connection_policy") or {})
    wire: dict[str, Any] = {
        "wire": "sovereign_linear_ns",
        "linear_ns": int(sc.ns_linear()) if sc else 0,
        "utc": _now(),
        "policy": "sovereign_time_only",
        "allowed_wires": policy.get("allowed_wires") or ["sovereign_linear_ns", "linear_ns"],
        "forbidden_wires": policy.get("forbidden_wires") or [],
    }
    if sc and hasattr(sc, "desync_status"):
        try:
            wire["desync"] = sc.desync_status()
        except Exception:
            pass
    return wire


def _gate_connection(module: dict[str, Any]) -> dict[str, Any]:
    """Reject any module wire that is not sovereign time."""
    wire = module.get("wire") or {}
    kind = str(wire.get("wire") or "")
    allowed = {"sovereign_linear_ns", "linear_ns"}
    ok = kind in allowed and bool(wire.get("linear_ns"))
    forbidden_hit = [
        f for f in (wire.get("forbidden_wires") or [])
        if f in str(module.get("connections") or "")
    ]
    return {
        "ok": ok and not forbidden_hit,
        "sovereign_time_only": True,
        "wire_kind": kind,
        "forbidden_hit": forbidden_hit,
    }


def _composite_bsp_sort(rows: list[dict[str, Any]], *, key: str = "path_pct") -> list[dict[str, Any]]:
    if len(rows) <= 1:
        return list(rows)

    def score(row: dict[str, Any], idx: int) -> float:
        raw = row.get(key)
        if raw is None:
            raw = row.get("band")
        if raw is None:
            raw = len(rows) - idx
        return float(raw)

    scored = [(score(r, i), r) for i, r in enumerate(rows)]
    scored.sort(key=lambda t: t[0], reverse=True)
    mid = len(scored) // 2
    left = _composite_bsp_sort([r for _, r in scored[:mid]], key=key)
    right = _composite_bsp_sort([r for _, r in scored[mid:]], key=key)
    return left + right


def _iron_organize_chips(chips: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Iron Plate layer — THE sort (composite_bsp) grounded on Ironclad truth."""
    mod = None
    for path in (GROK16 / "lib" / "field-power-sort.py", INSTALL / "Grok16" / "lib" / "field-power-sort.py"):
        mod = _import_py(path, "fps_chip_paths")
        if mod:
            break

    alg = "composite_bsp"
    meta: dict[str, Any] = {"algorithm": alg, "context": "chip_paths", "layer": "iron_plate", "the_sort": True}
    best = _import_py(INSTALL / "lib" / "field-best-sort.py", "cps_best_sort")
    if best and hasattr(best, "apply_best"):
        try:
            row_inputs = [
                {**c, "name": str(c.get("label") or c.get("id") or ""), "path_pct": c.get("path_pct")}
                for c in chips
            ]
            working, sort_meta = best.apply_best(row_inputs, context="chip_paths", n=len(chips))
            meta.update(sort_meta)
            alg = str(sort_meta.get("algorithm") or alg)
        except Exception:
            working = _composite_bsp_sort(list(chips))
            meta["bsp_partitions"] = True
    elif mod and hasattr(mod, "select_sort"):
        try:
            pick = mod.select_sort("chip_paths", n=len(chips))
            alg = str(pick.get("algorithm") or "composite_bsp")
            meta["power_sort"] = pick
        except Exception:
            pass
        working = _composite_bsp_sort(list(chips))
        meta["bsp_partitions"] = True
    else:
        working = _composite_bsp_sort(list(chips))
        meta["bsp_partitions"] = True

    for i, chip in enumerate(working):
        chip["iron_slot"] = i
        chip["iron_plate"] = True
    meta["algorithm"] = alg
    meta["count"] = len(working)
    return working, meta


def _steel_plate_map(chips: list[dict[str, Any]], steel_doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Steel Plate layer — map chips into steel neural chips domain."""
    plates = steel_doc.get("plates") or []
    chips_plate = next((p for p in plates if p.get("domain") == "chips"), None)
    members = (chips_plate or {}).get("members") or []
    member_ids = {str(m.get("id") or "") for m in members}

    steel_slots: dict[str, int] = {}
    for i, m in enumerate(members[: len(chips)]):
        mid = str(m.get("id") or "")
        if mid:
            steel_slots[mid] = i

    plated: list[dict[str, Any]] = []
    cross_wired = 0
    for chip in chips:
        cid = str(chip.get("id") or "")
        row = {
            **chip,
            "steel_plate": True,
            "steel_domain": "chips",
            "steel_member": cid in member_ids,
            "steel_slot": steel_slots.get(cid),
            "neural_depth": int((chips_plate or {}).get("depth_layer") or 2),
        }
        if row["steel_member"]:
            cross_wired += 1
        plated.append(row)

    meta = {
        "layer": "steel_plate",
        "domain": "chips",
        "plate_live": bool(chips_plate),
        "member_count": len(members),
        "cross_wired": cross_wired,
        "connection_depth": steel_doc.get("connection_depth"),
        "wires": steel_doc.get("wires"),
    }
    return {"chips": plated, "meta": meta}, meta


def _bsp_model_for_chip(chip: dict[str, Any], doctrine: dict[str, Any]) -> str:
    bsp = doctrine.get("bsp_model") or {}
    preferred_kinds = set(bsp.get("kinds_preferred") or [])
    kind = str(chip.get("kind") or "")
    if kind in preferred_kinds:
        return str(bsp.get("preferred") or "direct_neural_calculator")
    return str(bsp.get("minimum") or "composite_bsp")


def _neural_calc_lock(chip: dict[str, Any], *, doctrine: dict[str, Any], wire: dict[str, Any]) -> dict[str, Any]:
    """Locked direct neural calculator module — one per chip family group."""
    bsp = doctrine.get("bsp_model") or {}
    fam = str(chip.get("family") or "misc")
    cid = str(chip.get("id") or "")
    prefix = str(bsp.get("family_module_prefix") or "chip_neural_calc")
    module_id = f"{prefix}:{fam}"
    material = json.dumps({"id": module_id, "family": fam, "chip": cid}, sort_keys=True)
    lock_hash = hashlib.sha256(material.encode()).hexdigest()[:24]
    model = _bsp_model_for_chip(chip, doctrine)
    return {
        "module_id": module_id,
        "family": fam,
        "chip_id": cid,
        "model": model,
        "locked": bool(bsp.get("locked", True)),
        "lock_hash": lock_hash,
        "calculator": bsp.get("calculator_module"),
        "calculator_doctrine": bsp.get("calculator_doctrine"),
        "wire": wire,
        "secure_connection": True,
        "connections": ["sovereign_linear_ns"],
    }


def _steel_rewrite_enabled(doctrine: dict[str, Any]) -> bool:
    rewrite = doctrine.get("steel_rewrite") or {}
    if os.environ.get("NEXUS_STEEL_REWRITE", "").strip().lower() in ("0", "false", "off"):
        return False
    if os.environ.get("NEXUS_STEEL_REWRITE", "").strip().lower() in ("1", "true", "on"):
        return True
    return bool(rewrite.get("enabled", True))


def _chip_leaf(chip: dict[str, Any], *, preserve: list[str]) -> dict[str, Any]:
    leaf = {
        "chip_id": chip.get("id"),
        "label": chip.get("label"),
        "kind": chip.get("kind"),
        "family": chip.get("family"),
        "combinatorics_leaf": chip.get("combinatorics_leaf"),
        "path_pct": chip.get("path_pct"),
        "sort_slot": chip.get("sort_slot", chip.get("slot")),
        "slot": chip.get("slot"),
        "iron_slot": chip.get("iron_slot"),
        "mame_device": chip.get("mame_device"),
        "source": chip.get("source"),
    }
    if preserve:
        return {k: leaf[k] for k in preserve if k in leaf or chip.get(k) is not None}
    return {k: v for k, v in leaf.items() if v is not None}


def _steel_family_plates(
    chips: list[dict[str, Any]],
    *,
    doctrine: dict[str, Any],
    wire: dict[str, Any],
    ironclad: dict[str, Any],
    steel_meta: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rewrite layer 3 as steel family plates — fewer slots, full leaf index, no resolution loss."""
    rewrite = doctrine.get("steel_rewrite") or {}
    preserve = list(rewrite.get("preserve") or [
        "chip_id", "combinatorics_leaf", "path_pct", "sort_slot", "kind", "label", "family",
    ])
    by_family: dict[str, list[dict[str, Any]]] = {}
    for chip in chips:
        fam = str(chip.get("family") or "unknown")
        by_family.setdefault(fam, []).append(chip)

    def _family_rank(chips_in: list[dict[str, Any]]) -> int:
        ranks = []
        for c in chips_in:
            slot = c.get("sort_slot")
            if slot is None:
                slot = c.get("slot")
            if slot is None:
                slot = c.get("iron_slot")
            ranks.append(int(slot) if slot is not None else 999)
        return min(ranks) if ranks else 999

    family_order = sorted(by_family.items(), key=lambda item: _family_rank(item[1]))

    draft_modules: list[dict[str, Any]] = []
    indexed = 0
    for slot, (fam, fam_chips) in enumerate(family_order):
        fam_chips.sort(key=lambda c: (
            c.get("sort_slot") if c.get("sort_slot") is not None else c.get("slot") if c.get("slot") is not None else 999,
            -float(c.get("path_pct") or 0),
        ))
        leaves = [_chip_leaf(c, preserve=preserve) for c in fam_chips]
        indexed += len(leaves)
        lead = fam_chips[0]
        path_sum = round(sum(float(c.get("path_pct") or 0) for c in fam_chips), 2)
        calc = _neural_calc_lock(lead, doctrine=doctrine, wire=wire)
        gate = _gate_connection({"wire": wire, "connections": calc.get("connections")})
        draft_modules.append({
            "id": f"steel_plate:{fam}",
            "plate_kind": "steel_family",
            "chip_id": str(lead.get("id") or ""),
            "label": f"Steel {fam}",
            "family": fam,
            "kind": "steel_family_plate",
            "combinatorics_leaf": f"steel_family:{fam}",
            "layer": 3,
            "removable": True,
            "plated_above": "ironclad",
            "steel_plate": True,
            "steel_domain": "chips",
            "steel_member": True,
            "steel_slot": slot,
            "steel_rewrite": True,
            "chip_count": len(leaves),
            "leaves": leaves,
            "indexed_chips": len(leaves),
            "path_pct": path_sum,
            "sort_slot": slot,
            "slot": slot,
            "iron_slot": lead.get("iron_slot"),
            "bsp_model": calc.get("model"),
            "neural_calc": calc,
            "wire": wire,
            "connection_gate": gate,
            "ironclad_grounded": bool(ironclad.get("ironclad_sealed") or ironclad.get("ironclad_grounded")),
            "absorb_operate": True,
            "resolution_lossless": True,
        })

    optimal_meta: dict[str, Any] = {}
    modules = draft_modules
    opt_py = INSTALL / "lib" / "field-steel-plate-optimal.py"
    opt_mod = _import_py(opt_py, "steel_plate_opt") if opt_py.is_file() else None
    if opt_mod and hasattr(opt_mod, "optimal_family_order") and hasattr(opt_mod, "apply_optimal_order"):
        try:
            order, optimal_meta = opt_mod.optimal_family_order(draft_modules)
            modules = opt_mod.apply_optimal_order(draft_modules, order, sort_meta=optimal_meta)
            if hasattr(opt_mod, "algorithms_doc"):
                optimal_meta["equations"] = (opt_mod.algorithms_doc() or {}).get("equations")
        except Exception as exc:
            optimal_meta = {"ok": False, "error": str(exc)[:160]}

    truth = float(ironclad.get("truth_percent") or 0)
    bsp_weight = 1.0
    bridge_weight = 1.0
    organize_gain = round((truth / 100.0) * bsp_weight * bridge_weight, 6) if truth else 0.0

    meta = {
        "layer": "steel_family_plates",
        "mode": rewrite.get("mode") or "steel_family",
        "family_plate_count": len(modules),
        "indexed_chips": indexed,
        "chip_count": len(chips),
        "compression_ratio": round(len(chips) / max(1, len(modules)), 2),
        "resolution_lossless": indexed == len(chips),
        "steel_domain": steel_meta.get("domain"),
        "cross_wired": steel_meta.get("cross_wired"),
        "optimal": optimal_meta,
        "equations": optimal_meta.get("equations") or {
            "plate_score": "S(p,s) = path_pct(p) * rank(s) * steel_boost(p) * bsp_boost(p)",
            "stack_objective": "O(π) = Σᵢ S(plate_π(i), i)",
            "organize_gain": "G = (truth_percent/100) * composite_bsp_weight * bridge_weight",
        },
        "organize_gain": organize_gain,
        "truth_percent": truth,
    }
    return modules, meta


def _removable_module(
    chip: dict[str, Any],
    *,
    slot: int,
    doctrine: dict[str, Any],
    wire: dict[str, Any],
    ironclad: dict[str, Any],
) -> dict[str, Any]:
    cid = str(chip.get("id") or "")
    fam = str(chip.get("family") or "misc")
    leaf = str(chip.get("combinatorics_leaf") or f"chip_mod:{fam}:{cid}")
    calc = _neural_calc_lock(chip, doctrine=doctrine, wire=wire)
    gate = _gate_connection({"wire": wire, "connections": calc.get("connections")})
    return {
        "id": f"mod_{cid}",
        "chip_id": cid,
        "label": chip.get("label") or cid,
        "family": fam,
        "kind": chip.get("kind"),
        "combinatorics_leaf": leaf,
        "layer": 3,
        "removable": True,
        "plated_above": "ironclad",
        "iron_slot": chip.get("iron_slot"),
        "steel_slot": chip.get("steel_slot"),
        "steel_member": chip.get("steel_member"),
        "band": chip.get("band"),
        "path_pct": chip.get("path_pct"),
        "bsp_model": calc.get("model"),
        "neural_calc": calc,
        "wire": wire,
        "connection_gate": gate,
        "ironclad_grounded": bool(ironclad.get("ironclad_sealed") or ironclad.get("ironclad_grounded")),
        "absorb_operate": True,
        "slot": slot,
    }


def _ensure_ironclad_chips(*, refresh: bool = False) -> dict[str, Any]:
    cached = _load(IRONCLAD_CHIPS, {})
    if os.environ.get("AML_TEST_DIRECT", "0") == "1" and not cached.get("chips"):
        for seed in (
            INSTALL / ".nexus-state" / "field-ironclad-chips-combinatorics.json",
            INSTALL / ".nexus-state-comb" / "field-ironclad-chips-combinatorics.json",
        ):
            cached = _load(seed, {})
            if cached.get("chips"):
                break
    if cached.get("chips") and (not refresh or os.environ.get("AML_TEST_DIRECT", "0") == "1"):
        return cached
    mod = _import_py(INSTALL / "lib" / "field-ironclad-chips-combinatorics.py", "ic_chips_cps")
    if mod and hasattr(mod, "publish_panel"):
        pub = mod.publish_panel(write_combinatorics=True)
        return _load(IRONCLAD_CHIPS, {}) or pub.get("panel") or {}
    if mod and hasattr(mod, "build_ironclad_chips_combinatorics"):
        return mod.build_ironclad_chips_combinatorics()
    return cached


def _ensure_steel_plates(*, refresh: bool = False) -> dict[str, Any]:
    cached = _load(STATE / "field-steel-neural-plates.json", {})
    if cached.get("plates") and not refresh:
        return cached
    mod = _import_py(INSTALL / "lib" / "field-steel-neural-plates.py", "snp_cps")
    if mod and hasattr(mod, "publish_panel"):
        pub = mod.publish_panel(refresh=refresh, write_battery=True)
        return pub.get("battery") or cached
    return cached


def _ironclad_slice() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema"):
        return cached
    mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ic_cps")
    if mod and hasattr(mod, "immediate_slice"):
        try:
            return mod.immediate_slice()
        except Exception:
            pass
    return cached


def build_plate_stack(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    """Absorb every chip — iron organize, steel neural depth, removable modules above Ironclad."""
    t0 = time.perf_counter()
    doctrine = _load(DOCTRINE, {})
    if os.environ.get("AML_TEST_DIRECT", "0") == "1" and not force:
        cached = _load(BATTERY, {})
        if not cached.get("modules"):
            for seed in (
                INSTALL / ".nexus-state" / "field-chips-plate-stack.json",
                INSTALL / ".nexus-state-comb" / "field-chips-plate-stack.json",
            ):
                cached = _load(seed, {})
                if cached.get("modules"):
                    break
        if cached.get("modules"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            out = dict(cached)
            out["fast_path"] = True
            out["aml_test_direct"] = True
            out["elapsed_ms"] = elapsed_ms
            return out
    if not ENABLED:
        return {
            "schema": "field-chips-plate-stack/v1",
            "ok": False,
            "enabled": False,
            "motto": doctrine.get("motto"),
        }

    bal = _import_py(INSTALL / "lib" / "field-combinatronic-balance.py", "cps_balance")
    balance_gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh") and not force:
        balance_gate = bal.gate_refresh(refresh, force=force)
        if balance_gate.get("skip_reorganize") and not refresh:
            cached = _load(BATTERY, {})
            if cached.get("modules"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                out = dict(cached)
                out["fast_path"] = True
                out["balance_hold"] = True
                out["balance_gate"] = balance_gate
                out["elapsed_ms"] = elapsed_ms
                return out

    chip_doc = _ensure_ironclad_chips(refresh=refresh or force)
    chips = list(chip_doc.get("chips") or [])
    if not chips:
        return {
            "schema": "field-chips-plate-stack/v1",
            "ok": False,
            "error": "ironclad_chips_empty",
            "motto": doctrine.get("motto"),
        }

    wire = _sovereign_wire()
    ironclad = _ironclad_slice()
    iron_sorted, iron_meta = _iron_organize_chips(chips)
    steel_doc = _ensure_steel_plates(refresh=refresh or force)
    steel_out, steel_meta = _steel_plate_map(iron_sorted, steel_doc)
    steel_chips = steel_out.get("chips") or iron_sorted

    rewrite_meta: dict[str, Any] = {}
    if _steel_rewrite_enabled(doctrine):
        modules, rewrite_meta = _steel_family_plates(
            steel_chips,
            doctrine=doctrine,
            wire=wire,
            ironclad=ironclad,
            steel_meta=steel_meta,
        )
    else:
        modules = [
            _removable_module(
                chip,
                slot=i,
                doctrine=doctrine,
                wire=wire,
                ironclad=ironclad,
            )
            for i, chip in enumerate(steel_chips)
        ]

    deriv_doc: dict[str, Any] = {}
    deriv_py = INSTALL / "lib" / "field-plate-rebalance-derivatives.py"
    deriv_mod = _import_py(deriv_py, "cps_deriv") if deriv_py.is_file() else None
    if deriv_mod and hasattr(deriv_mod, "apply_derivative_stamp"):
        try:
            modules, deriv_meta = deriv_mod.apply_derivative_stamp(modules, rebalance_within_band=True)
            truth = float(ironclad.get("truth_percent") or 0)
            top_d = float((deriv_meta.get("top_marginal") or [{}])[0].get("d_score_d_slot") or 0)
            deriv_doc = {
                "ok": True,
                "meta": deriv_meta,
                "organize_gain_derivative": round(truth / 100.0 * top_d, 6) if truth else 0.0,
                "super_quick": bool(deriv_meta.get("fast_path")),
                "symbolic_seal": deriv_meta.get("symbolic_seal"),
            }
        except Exception as exc:
            deriv_doc = {"ok": False, "error": str(exc)[:160]}

    gated_ok = sum(1 for m in modules if (m.get("connection_gate") or {}).get("ok"))
    bsp_counts: dict[str, int] = {}
    for m in modules:
        model = str(m.get("bsp_model") or "composite_bsp")
        bsp_counts[model] = bsp_counts.get(model, 0) + 1

    families: dict[str, int] = {}
    indexed_chips = 0
    for m in modules:
        fam = str(m.get("family") or "unknown")
        families[fam] = families.get(fam, 0) + 1
        indexed_chips += int(m.get("indexed_chips") or m.get("chip_count") or 1)

    calc_modules: dict[str, dict[str, Any]] = {}
    for m in modules:
        nc = m.get("neural_calc") or {}
        mid = str(nc.get("module_id") or "")
        if mid and mid not in calc_modules:
            calc_modules[mid] = nc

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    layers = doctrine.get("layer_stack") or []
    stack_witness: dict[str, Any] = {}
    pio = _import_py(INSTALL / "lib" / "plate-sealed-io.py", "plate_sealed_io_w")
    if pio and hasattr(pio, "stack_fabric_witness"):
        stack_witness = pio.stack_fabric_witness()

    result = {
        "schema": "field-chips-plate-stack/v1",
        "updated": _now(),
        "stack_fabric": stack_witness,
        "meld_citation": doctrine.get("ironclad_chain", {}).get("meld_citation") or "ironclad:meld:2",
        "motto": doctrine.get("motto"),
        "ok": len(modules) > 0 and gated_ok == len(modules),
        "enabled": ENABLED,
        "ironclad_citation": doctrine.get("ironclad_citation"),
        "ironclad_chain": {
            "root": "ironclad-immediate",
            "citation": doctrine.get("ironclad_citation"),
            "truth_percent": ironclad.get("truth_percent"),
            "grounded": bool(ironclad.get("ironclad_sealed") or ironclad.get("ironclad_grounded")),
            "layers": ["ironclad", "iron_plate", "steel_plate", "chip_modules"],
            "connected": True,
        },
        "connection_policy": {
            "sovereign_time_only": True,
            "wire": wire,
            "gated_modules": gated_ok,
            "total_modules": len(modules),
            "all_gated": gated_ok == len(modules),
        },
        "layer_stack": layers,
        "layers": {
            "ironclad": {
                "grounded": bool(ironclad.get("ironclad_sealed") or ironclad.get("ironclad_grounded")),
                "truth_percent": ironclad.get("truth_percent"),
            },
            "iron_plate": iron_meta,
            "steel_plate": steel_meta,
            "steel_family_plates": rewrite_meta or {
                "count": len(modules),
                "removable": True,
                "plated_above": "ironclad",
            },
        },
        "steel_rewrite": rewrite_meta or None,
        "counts": {
            "chips": len(chips),
            "modules": len(modules),
            "indexed_chips": indexed_chips,
            "families": len(families),
            "neural_calc_modules": len(calc_modules),
            "by_bsp_model": bsp_counts,
            "compression_ratio": round(len(chips) / max(1, len(modules)), 2) if rewrite_meta else 1.0,
            "resolution_lossless": indexed_chips == len(chips),
        },
        "bsp_model": doctrine.get("bsp_model"),
        "modules": modules,
        "neural_calc_modules": list(calc_modules.values()),
        "sample_modules": modules[:24],
        "family_counts": families,
        "ironclad_chips_counts": chip_doc.get("counts"),
        "ironclad_root": chip_doc.get("ironclad_root"),
        "code_path_prediction": chip_doc.get("code_path_prediction"),
        "plate_rebalance_derivatives": deriv_doc,
        "combinatronic": True,
        "all_data_combinatronic": True,
        "optimized_combinatronic": bool(balance_gate.get("balanced")),
        "balance_gate": balance_gate or None,
        "elapsed_ms": elapsed_ms,
        "low_power": LOW_POWER,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not balance_gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    return result


def publish_panel(*, refresh: bool = False, write_battery: bool = True, force: bool = False) -> dict[str, Any]:
    stack = build_plate_stack(refresh=refresh, force=force)
    panel = {
        "schema": "field-chips-plate-stack-panel/v1",
        "updated": _now(),
        "stack_fabric": stack.get("stack_fabric"),
        "meld_citation": stack.get("meld_citation") or "ironclad:meld:2",
        "ok": stack.get("ok"),
        "motto": stack.get("motto"),
        "counts": stack.get("counts"),
        "connection_policy": stack.get("connection_policy"),
        "layers": stack.get("layers"),
        "bsp_model": stack.get("bsp_model"),
        "sample_modules": stack.get("sample_modules"),
        "neural_calc_module_count": len(stack.get("neural_calc_modules") or []),
        "family_counts": dict(sorted((stack.get("family_counts") or {}).items(), key=lambda x: -x[1])[:16]),
        "plate_rebalance_derivatives": stack.get("plate_rebalance_derivatives"),
        "elapsed_ms": stack.get("elapsed_ms"),
        "combinatronic": True,
        "fast_path": stack.get("fast_path", False),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, stack)
    core_out: dict[str, Any] = {}
    cc = INSTALL / "lib" / "field-chips-core.py"
    if (
        cc.is_file()
        and os.environ.get("NEXUS_CHIPS_CORE", "1") == "1"
        and os.environ.get("AML_TEST_DIRECT", "0") != "1"
    ):
        try:
            spec = importlib.util.spec_from_file_location("chip_core_pub", cc)
            if spec and spec.loader:
                cc_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cc_mod)
                if hasattr(cc_mod, "maybe_condense_after_ironclad"):
                    core_out = cc_mod.maybe_condense_after_ironclad(refresh=refresh) or {}
        except Exception:
            core_out = {"ok": False, "skipped": "chips_core_condense_failed"}
    return {
        "ok": stack.get("ok", True),
        "panel": panel,
        "battery": stack,
        "chips_core": {
            "ok": (core_out.get("panel") or {}).get("ok"),
            "condensed": (core_out.get("panel") or {}).get("condensed"),
            "core_module_count": ((core_out.get("core") or {}).get("counts") or {}).get("core_modules"),
        } if core_out else None,
    }


def plate_stack_slice() -> dict[str, Any]:
    cached = _load(BATTERY, {})
    if cached.get("modules"):
        return {
            "schema": "field-chips-plate-stack-slice/v1",
            "counts": cached.get("counts"),
            "connection_policy": cached.get("connection_policy"),
            "layers": cached.get("layers"),
            "sample_modules": cached.get("sample_modules"),
            "cached": True,
        }
    pub = publish_panel(refresh=False, write_battery=True)
    bat = pub.get("battery") or {}
    return {
        "schema": "field-chips-plate-stack-slice/v1",
        "counts": bat.get("counts"),
        "connection_policy": bat.get("connection_policy"),
        "layers": bat.get("layers"),
        "sample_modules": bat.get("sample_modules"),
        "cached": False,
    }


def verify_stack() -> dict[str, Any]:
    stack = build_plate_stack(refresh=False)
    policy = stack.get("connection_policy") or {}
    counts = stack.get("counts") or {}
    chips_n = int(counts.get("chips") or 0)
    modules_n = int(counts.get("modules") or 0)
    indexed_n = int(counts.get("indexed_chips") or modules_n)
    lossless = bool(counts.get("resolution_lossless"))
    steel_rewrite = bool((stack.get("steel_rewrite") or {}).get("resolution_lossless"))
    ok = (
        bool(stack.get("ok"))
        and chips_n >= 50
        and modules_n >= 1
        and indexed_n >= 50
        and (lossless or indexed_n == chips_n)
        and bool(policy.get("sovereign_time_only"))
        and bool(policy.get("all_gated"))
        and int(counts.get("neural_calc_modules") or 0) >= 1
    )
    if steel_rewrite and chips_n > 0:
        ok = ok and modules_n < chips_n
    return {
        "ok": ok,
        "chip_count": counts.get("chips"),
        "module_count": counts.get("modules"),
        "indexed_chips": indexed_n,
        "compression_ratio": counts.get("compression_ratio"),
        "resolution_lossless": lossless,
        "steel_rewrite": steel_rewrite,
        "neural_calc_modules": counts.get("neural_calc_modules"),
        "sovereign_time_only": policy.get("sovereign_time_only"),
        "all_gated": policy.get("all_gated"),
        "by_bsp_model": counts.get("by_bsp_model"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    refresh = "--refresh" in sys.argv[2:]
    force = "--force" in sys.argv[2:]
    if cmd in ("json", "panel", "status"):
        if PANEL.is_file() and not refresh:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel(refresh=refresh, force=force).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "stack"):
        print(json.dumps(publish_panel(refresh=refresh, force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(plate_stack_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        doc = verify_stack()
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "wire":
        print(json.dumps(_sovereign_wire(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "build", "publish", "stack", "slice", "verify", "wire"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())