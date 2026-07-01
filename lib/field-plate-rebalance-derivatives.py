#!/usr/bin/env pythong
"""Plate rebalance derivatives — super-quick marginal gain for iron+steel stack."""
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
CACHE = STATE / "field-plate-rebalance-derivatives.json"
FAST_PATH_MS = 8
IRONCLAD_CITE = "ironclad:chips:3"
_SYMBOLIC_SEAL: dict[str, Any] | None = None


def _ironclad_truth() -> dict[str, Any]:
    imm = _load(STATE / "ironclad-immediate.json", {})
    pts = imm.get("plate_to_sense") or {}
    return {
        "ironclad_citation": IRONCLAD_CITE,
        "truth_percent": imm.get("truth_percent") or pts.get("truth_percent"),
        "ironclad_grounded": bool(imm.get("ironclad_sealed") or pts.get("ironclad_grounded")),
        "connected": True,
    }


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


def _fingerprint(modules: list[dict[str, Any]]) -> str:
    parts = [str(len(modules))]
    for m in modules[:48]:
        parts.append(f"{m.get('chip_id') or m.get('id')}:{m.get('path_pct')}:{m.get('band')}:{m.get('slot')}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def module_plate_score(module: dict[str, Any]) -> float:
    """Marginal plate score — path_pct × band coolness × steel membership."""
    pct = float(module.get("path_pct") or 0)
    slot = float(module.get("sort_slot") if module.get("sort_slot") is not None else module.get("slot") or 999)
    steel_boost = 1.12 if module.get("steel_member") else 1.0
    bsp_boost = 1.08 if str(module.get("bsp_model") or "") == "direct_neural_calculator" else 1.0
    rank_factor = 1.0 + max(0.0, (500.0 - slot) / 500.0)
    return pct * rank_factor * steel_boost * bsp_boost


def fast_derivatives(modules: list[dict[str, Any]]) -> tuple[list[float], dict[str, Any]]:
    """O(n) central-difference derivatives of plate score w.r.t. slot — super quick."""
    t0 = time.perf_counter()
    n = len(modules)
    scores = [module_plate_score(m) for m in modules]
    derivs = [0.0] * n
    if n == 0:
        return derivs, {"count": 0, "elapsed_ms": 0.0, "method": "central_difference"}
    if n == 1:
        derivs[0] = 0.0
    else:
        derivs[0] = scores[1] - scores[0]
        derivs[-1] = scores[-1] - scores[-2]
        for i in range(1, n - 1):
            derivs[i] = (scores[i + 1] - scores[i - 1]) / 2.0
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    return derivs, {
        "method": "central_difference",
        "count": n,
        "elapsed_ms": elapsed_ms,
        "fast_path": elapsed_ms <= FAST_PATH_MS,
        "fast_path_ms_target": FAST_PATH_MS,
    }


def symbolic_organize_gain_seal() -> dict[str, Any]:
    """Locked direct-neural-calculator witness — organize_gain partial w.r.t. slot."""
    global _SYMBOLIC_SEAL
    if _SYMBOLIC_SEAL is not None:
        return _SYMBOLIC_SEAL
    cached = _load(CACHE, {}).get("symbolic_seal")
    if cached:
        _SYMBOLIC_SEAL = cached
        return cached
    out: dict[str, Any] = {
        "equation": "organize_gain = truth_percent * composite_bsp_weight * bridge_weight",
        "variable": "slot",
        "method": "product_rule",
        "result": "d(organize_gain)/d(slot) = truth_percent * d(composite_bsp_weight)/d(slot) * bridge_weight + truth_percent * composite_bsp_weight * d(bridge_weight)/d(slot) + d(truth_percent)/d(slot) * composite_bsp_weight * bridge_weight",
        "locked": True,
        "calculator": "lib/hostess7-calculator.py",
    }
    calc_py = INSTALL / "lib" / "hostess7-calculator.py"
    if calc_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_calc_deriv", calc_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "compute"):
                    witness = mod.compute("diff t*b*w wrt s")
                    if witness.get("ok"):
                        out["calculator_witness"] = witness.get("result")
                        out["calculator_method"] = witness.get("method")
        except Exception as exc:
            out["calculator_warn"] = str(exc)[:120]
    _SYMBOLIC_SEAL = out
    return out


def apply_derivative_stamp(
    modules: list[dict[str, Any]],
    *,
    rebalance_within_band: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stamp d(score)/d(slot) on every module; optional within-band micro-rebalance."""
    t0 = time.perf_counter()
    fp = _fingerprint(modules)
    cached = _load(CACHE, {})
    if cached.get("fingerprint") == fp and cached.get("derivatives") and len(cached["derivatives"]) == len(modules):
        derivs = list(cached["derivatives"])
        meta = dict(cached.get("meta") or {})
        meta["cache_hit"] = True
        meta["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 3)
        meta["fast_path"] = meta["elapsed_ms"] <= FAST_PATH_MS
    else:
        derivs, meta = fast_derivatives(modules)
        meta["cache_hit"] = False
        _save(CACHE, {
            "schema": "field-plate-rebalance-derivatives/v1",
            "fingerprint": fp,
            "derivatives": derivs,
            "meta": meta,
            "symbolic_seal": symbolic_organize_gain_seal(),
        })

    stamped: list[dict[str, Any]] = []
    for i, mod in enumerate(modules):
        row = dict(mod)
        row["plate_score"] = round(module_plate_score(mod), 6)
        row["d_score_d_slot"] = round(derivs[i], 6)
        row["marginal_gain"] = round(derivs[i] * float(mod.get("path_pct") or 1.0), 6)
        stamped.append(row)

    if rebalance_within_band and len(stamped) > 1:
        stamped = sorted(
            stamped,
            key=lambda r: (-float(r.get("d_score_d_slot") or 0), -float(r.get("plate_score") or 0)),
        )
        meta["the_sort_rebalance"] = True

    symbolic = symbolic_organize_gain_seal()
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    meta.update({
        "fingerprint": fp,
        "symbolic_seal": symbolic,
        "elapsed_ms_total": elapsed_ms,
        "fast_path": elapsed_ms <= FAST_PATH_MS,
        "top_marginal": [
            {"chip_id": r.get("chip_id"), "d_score_d_slot": r.get("d_score_d_slot"), "plate_score": r.get("plate_score")}
            for r in sorted(stamped, key=lambda x: -float(x.get("d_score_d_slot") or 0))[:8]
        ],
    })
    return stamped, meta


def rebalance_plate_stack(
    modules: list[dict[str, Any]],
    *,
    iron_meta: dict[str, Any] | None = None,
    truth_percent: float | None = None,
) -> dict[str, Any]:
    """Full derivative rebalance slice — for g16 rebalance and plate stack publish."""
    t0 = time.perf_counter()
    stamped, meta = apply_derivative_stamp(modules, rebalance_within_band=True)
    truth = float(truth_percent if truth_percent is not None else 0)
    if truth <= 0 and iron_meta:
        truth = float(iron_meta.get("truth_percent") or 0)
    organize_gain_deriv = round(
        truth / 100.0 * float(meta.get("top_marginal", [{}])[0].get("d_score_d_slot") or 0) if truth else 0,
        6,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    return {
        "schema": "field-plate-rebalance-derivatives/v1",
        "ok": len(stamped) > 0,
        "module_count": len(stamped),
        "derivatives": meta,
        "organize_gain_derivative": organize_gain_deriv,
        "symbolic_seal": meta.get("symbolic_seal"),
        "modules_sample": stamped[:12],
        "elapsed_ms": elapsed_ms,
        "super_quick": elapsed_ms <= FAST_PATH_MS,
        "motto": "Plate rebalance derivatives — marginal gain in one pass.",
        "ironclad": _ironclad_truth(),
        "ironclad_citation": IRONCLAD_CITE,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    stack = _load(STATE / "field-chips-plate-stack.json", {})
    modules = list(stack.get("modules") or [])
    if cmd in ("json", "derivatives", "deriv"):
        if not modules:
            print(json.dumps({"ok": False, "error": "no_plate_stack"}, ensure_ascii=False, indent=2))
            return 1
        doc = rebalance_plate_stack(modules, iron_meta=(stack.get("layers") or {}).get("iron_plate"))
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "verify":
        if not modules:
            print(json.dumps({"ok": False, "error": "no_plate_stack"}, ensure_ascii=False))
            return 1
        _, meta = fast_derivatives(modules)
        doc = rebalance_plate_stack(modules)
        numeric_quick = bool(meta.get("fast_path"))
        ok = bool(doc.get("ok")) and numeric_quick and int(doc.get("module_count") or 0) >= 50
        print(json.dumps({
            "ok": ok,
            "module_count": doc.get("module_count"),
            "numeric_elapsed_ms": meta.get("elapsed_ms"),
            "elapsed_ms": doc.get("elapsed_ms"),
            "super_quick": numeric_quick,
            "derivative_method": meta.get("method"),
            "cache_hit": meta.get("cache_hit"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if cmd == "seal":
        print(json.dumps(symbolic_organize_gain_seal(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["json", "derivatives", "verify", "seal"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())