#!/usr/bin/env pythong
"""Steel plate optimal — equations, algorithms, brute-force / assignment-optimal ordering."""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))

EQUATIONS: dict[str, str] = {
    "plate_score": (
        "S(p,s) = path_pct(p) * rank(s) * steel_boost(p) * bsp_boost(p)"
    ),
    "rank": "rank(s) = 1 + max(0, (500 - s) / 500)",
    "steel_boost": "steel_boost(p) = 1.12 if steel_member else 1.0",
    "bsp_boost": "bsp_boost(p) = 1.08 if bsp_model == direct_neural_calculator else 1.0",
    "stack_objective": "O(π) = Σᵢ S(plate_π(i), i)",
    "organize_gain": "G = (truth_percent/100) * composite_bsp_weight * bridge_weight",
    "organize_gain_deriv": (
        "dG/ds = (truth/100) * d(composite_bsp_weight)/ds * bridge_weight + ..."
    ),
    "rearrangement": (
        "O maximal when plate weights wᵢ = path_pct·steel_boost·bsp_boost "
        "and slot ranks rank(s) are similarly sorted (rearrangement inequality)"
    ),
}

BRUTE_FORCE_MAX = int(os.environ.get("NEXUS_STEEL_BRUTE_FORCE_MAX", "11"))


def _import_deriv() -> Any | None:
    path = INSTALL / "lib" / "field-plate-rebalance-derivatives.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("steel_plate_deriv", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def rank_factor(slot: int) -> float:
    return 1.0 + max(0.0, (500.0 - float(slot)) / 500.0)


def plate_weight(plate: dict[str, Any]) -> float:
    """wᵢ — path mass × boosts (slot-independent part of S)."""
    pct = float(plate.get("path_pct") or 0)
    steel_boost = 1.12 if plate.get("steel_member") else 1.0
    bsp_boost = 1.08 if str(plate.get("bsp_model") or "") == "direct_neural_calculator" else 1.0
    return pct * steel_boost * bsp_boost


def plate_score_at_slot(plate: dict[str, Any], slot: int) -> float:
    """S(p,s) — full plate score at assigned slot."""
    return plate_weight(plate) * rank_factor(slot)


def stack_objective(plates: list[dict[str, Any]], order: list[int]) -> float:
    """O(π) = Σᵢ S(plate[order[i]], i)."""
    total = 0.0
    for slot, idx in enumerate(order):
        if 0 <= idx < len(plates):
            total += plate_score_at_slot(plates[idx], slot)
    return total


def _brute_force_permutation(plates: list[dict[str, Any]]) -> tuple[list[int], dict[str, Any]]:
    """Exhaustive permutation — globally optimal for n ≤ BRUTE_FORCE_MAX."""
    n = len(plates)
    t0 = time.perf_counter()
    best_order = list(range(n))
    best_score = stack_objective(plates, best_order)
    perm_count = 0
    for perm in itertools.permutations(range(n)):
        perm_count += 1
        score = stack_objective(plates, list(perm))
        if score > best_score:
            best_score = score
            best_order = list(perm)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    return best_order, {
        "algorithm": "brute_force_permutation",
        "optimal": True,
        "exhaustive": True,
        "permutations_tried": perm_count,
        "objective_score": round(best_score, 6),
        "elapsed_ms": elapsed_ms,
        "n": n,
    }


def _assignment_optimal(plates: list[dict[str, Any]]) -> tuple[list[int], dict[str, Any]]:
    """Assignment-optimal via rearrangement inequality — O(n log n), globally optimal for separable S."""
    t0 = time.perf_counter()
    n = len(plates)
    indexed = [(plate_weight(p), i) for i, p in enumerate(plates)]
    indexed.sort(key=lambda t: (-t[0], t[1]))
    order = [0] * n
    for slot, (_, plate_idx) in enumerate(indexed):
        order[slot] = plate_idx
    inv_order = [0] * n
    for slot, plate_idx in enumerate(order):
        inv_order[plate_idx] = slot
    score = stack_objective(plates, order)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    return order, {
        "algorithm": "assignment_rearrangement",
        "optimal": True,
        "exhaustive": False,
        "objective_score": round(score, 6),
        "elapsed_ms": elapsed_ms,
        "n": n,
        "proof": "rearrangement_inequality",
    }


def _brute_force_pairwise(plates: list[dict[str, Any]], *, max_rounds: int = 64) -> tuple[list[int], dict[str, Any]]:
    """Exhaustive pairwise-swap local search — brute force until stable."""
    t0 = time.perf_counter()
    n = len(plates)
    order = list(range(n))
    score = stack_objective(plates, order)
    swaps = 0
    rounds = 0
    improved = True
    while improved and rounds < max_rounds:
        improved = False
        rounds += 1
        for i in range(n):
            for j in range(i + 1, n):
                trial = list(order)
                trial[i], trial[j] = trial[j], trial[i]
                trial_score = stack_objective(plates, trial)
                if trial_score > score + 1e-12:
                    order = trial
                    score = trial_score
                    swaps += 1
                    improved = True
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    return order, {
        "algorithm": "brute_force_pairwise_swap",
        "optimal": swaps == 0 or n <= BRUTE_FORCE_MAX,
        "exhaustive": False,
        "pairwise_swaps": swaps,
        "rounds": rounds,
        "objective_score": round(score, 6),
        "elapsed_ms": elapsed_ms,
        "n": n,
    }


def optimal_family_order(
    plates: list[dict[str, Any]],
    *,
    brute_force_max: int | None = None,
) -> tuple[list[int], dict[str, Any]]:
    """Pick globally optimal family plate order — brute perm if small, else assignment + pairwise polish."""
    n = len(plates)
    if n <= 1:
        return list(range(n)), {
            "algorithm": "trivial",
            "optimal": True,
            "objective_score": stack_objective(plates, [0]) if n == 1 else 0.0,
            "n": n,
        }
    cap = brute_force_max if brute_force_max is not None else BRUTE_FORCE_MAX
    if n <= cap:
        return _brute_force_permutation(plates)
    order, meta = _assignment_optimal(plates)
    pairwise_order, pairwise_meta = _brute_force_pairwise(plates)
    if float(pairwise_meta.get("objective_score") or 0) > float(meta.get("objective_score") or 0) + 1e-9:
        pairwise_meta["assignment_score"] = meta.get("objective_score")
        pairwise_meta["algorithm"] = "assignment_rearrangement+pairwise_polish"
        return pairwise_order, pairwise_meta
    meta["pairwise_polish"] = pairwise_meta
    return order, meta


def apply_optimal_order(
    modules: list[dict[str, Any]],
    order: list[int],
    *,
    sort_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    """Reorder steel family modules; order[slot] = source index at that slot."""
    n = len(modules)
    reordered = [dict(modules[order[slot]]) for slot in range(n) if 0 <= order[slot] < n]
    for slot, mod in enumerate(reordered):
        mod["slot"] = slot
        mod["sort_slot"] = slot
        mod["steel_slot"] = slot
        mod["plate_score"] = round(plate_score_at_slot(mod, slot), 6)
        mod["optimal_order"] = True
        mod["sort_algorithm"] = sort_meta.get("algorithm")
        leaves = mod.get("leaves") or []
        for leaf in leaves:
            if isinstance(leaf, dict):
                leaf["steel_family_slot"] = slot
    return reordered


def algorithms_doc() -> dict[str, Any]:
    deriv = _import_deriv()
    seal = {}
    if deriv and hasattr(deriv, "symbolic_organize_gain_seal"):
        try:
            seal = deriv.symbolic_organize_gain_seal()
        except Exception:
            pass
    return {
        "schema": "field-steel-plate-optimal/v1",
        "equations": EQUATIONS,
        "algorithms": {
            "brute_force_permutation": f"exhaustive n! for n ≤ {BRUTE_FORCE_MAX}",
            "assignment_rearrangement": "O(n log n) global optimal for separable S(p,s)",
            "brute_force_pairwise_swap": "exhaustive pairwise swap until stable",
            "composite_bsp": "iron plate THE sort on chip_paths",
            "central_difference": "d(score)/d(slot) on stamped stack",
        },
        "symbolic_seal": seal,
        "brute_force_max": BRUTE_FORCE_MAX,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "equations").strip().lower()
    if cmd in ("equations", "algorithms", "doc"):
        print(json.dumps(algorithms_doc(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        sample = [
            {"path_pct": 40.0, "steel_member": True, "bsp_model": "direct_neural_calculator"},
            {"path_pct": 25.0, "steel_member": True, "bsp_model": "composite_bsp"},
            {"path_pct": 15.0, "steel_member": False, "bsp_model": "composite_bsp"},
        ]
        order, meta = optimal_family_order(sample)
        score = stack_objective(sample, order)
        ok = bool(meta.get("optimal")) and score > 0 and len(order) == 3
        print(json.dumps({"ok": ok, "order": order, "meta": meta, "score": round(score, 4)}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["equations", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())