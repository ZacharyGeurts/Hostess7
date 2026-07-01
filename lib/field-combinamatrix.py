#!/usr/bin/env pythong
"""Combinamatrix — pack universal combinatoric leaves into width × length matrix cells."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-combinamatrix-doctrine.json"
PANEL = STATE / "field-combinamatrix-panel.json"
BATTERY = STATE / "field-combinamatrix.json"


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


def _matrix_dimensions() -> tuple[int, int]:
    doctrine = _load(DOCTRINE, {})
    dim = doctrine.get("dimensions") or {}
    growth = _load(STATE / "field-combinatronics-growth-panel.json", {})
    plate_dim = _load(STATE / "field-plate-dimensions-panel.json", {})
    width = int(growth.get("optimal_width") or dim.get("fallback_width") or 16)
    length = int((plate_dim.get("dimensions") or {}).get("length") or 0)
    if length <= 0:
        length = max(1, math.ceil(64 / max(1, width)))
    return max(8, min(48, width)), max(1, length)


def _normalize_cell(row: dict[str, Any], *, source: str, idx: int) -> dict[str, Any]:
    lid = str(row.get("id") or row.get("leaf_id") or f"cm:{source}:{idx:05d}")
    return {
        "id": lid,
        "source": source,
        "facet": str(row.get("facet") or row.get("sub_facet") or source),
        "label": row.get("label") or row.get("instruction") or row.get("path") or lid,
        "path_pct": float(row.get("path_pct") or row.get("rebalance_score") or 0),
        "depth": int(row.get("depth") or row.get("surface_rank") or 0),
        "canonical": row.get("canonical"),
        "runner": row.get("runner"),
        "belt": row.get("belt"),
        "thermal_tier": row.get("thermal_tier"),
        "band": row.get("band"),
    }


def _balance_mod() -> Any | None:
    return _import_mod("cm_balance", "field-combinatronic-balance.py")


def collect_leaves(*, refresh: bool = False, force: bool = False) -> tuple[list[dict[str, Any]], dict[str, int]]:
    doctrine = _load(DOCTRINE, {})
    bal = _balance_mod()
    if bal and hasattr(bal, "gate_refresh"):
        gate = bal.gate_refresh(refresh, force=force)
        if gate.get("skip_reorganize") and not force:
            refresh = False
    if refresh:
        uni = _import_mod("cm_uni", "field-g16-universal-combinatronic.py")
        if uni and hasattr(uni, "publish_panel"):
            uni.publish_panel(refresh=True, write_battery=True)
    leaves: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen: set[str] = set()
    for src in doctrine.get("sources") or []:
        sid = str(src.get("id") or "")
        doc = _load(STATE / str(src.get("panel") or ""), {})
        rows = doc.get(str(src.get("key") or "combinatorics_leaves")) or []
        if sid == "spider" and not rows:
            rows = doc.get("top_priorities") or doc.get("lanes") or []
        weight = float(src.get("weight") or 1.0)
        n = 0
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            cell = _normalize_cell(row, source=sid, idx=i)
            if cell["id"] in seen:
                continue
            seen.add(cell["id"])
            cell["source_weight"] = weight
            leaves.append(cell)
            n += 1
        counts[sid] = n
    leaves.sort(key=lambda r: (-float(r.get("source_weight") or 0), -r.get("path_pct", 0), r.get("id", "")))
    return leaves, counts


def _cell_activation(cell: dict[str, Any], weights: dict[str, float]) -> float:
    score = 0.0
    score += min(1.0, float(cell.get("path_pct") or 0) / 50.0) * float(weights.get("path_pct") or 0.2)
    if str(cell.get("thermal_tier") or "").lower() == "cool":
        score += float(weights.get("coolness") or 0.18)
    score += min(1.0, 1.0 / (1.0 + int(cell.get("depth") or 0))) * float(weights.get("surface_depth") or 0.12)
    if cell.get("canonical"):
        score += float(weights.get("canonical_bonus") or 0.1)
    score += float(cell.get("source_weight") or 0) * float(weights.get("facet_spread") or 0.25) * 0.2
    return round(min(1.0, score), 4)


def _wire_cells(cells: list[dict[str, Any]], *, width: int) -> list[dict[str, Any]]:
    by_rc = {(int(c.get("row") or 0), int(c.get("col") or 0)): c for c in cells}
    weights = (_load(DOCTRINE, {}).get("neural_weights") or {})
    w_adj = float(weights.get("wire_adjacency") or 0.15)
    for c in cells:
        r, col = int(c.get("row") or 0), int(c.get("col") or 0)
        wires: list[dict[str, Any]] = []
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = by_rc.get((r + dr, col + dc))
            if nb:
                wires.append({
                    "to": nb.get("id"),
                    "row": r + dr,
                    "col": col + dc,
                    "weight": round(w_adj * (float(c.get("activation") or 0) + float(nb.get("activation") or 0)) / 2, 4),
                })
        c["wires"] = wires
        c["wire_count"] = len(wires)
    return cells


def build_matrix(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _balance_mod()
    balance_gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh"):
        balance_gate = bal.gate_refresh(refresh, force=force)
        if balance_gate.get("skip_reorganize") and not force:
            cached = _load(BATTERY, {})
            if cached.get("cells"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                if hasattr(bal, "record_cycle"):
                    bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
                out = dict(cached)
                out["balance_hold"] = True
                out["fast_path"] = True
                out["balance_gate"] = balance_gate
                out["elapsed_ms"] = elapsed_ms
                out["optimized_combinatronic"] = True
                out["combinatronic"] = True
                return out
    doctrine = _load(DOCTRINE, {})
    width, length = _matrix_dimensions()
    leaves, source_counts = collect_leaves(refresh=refresh, force=force)
    weights = doctrine.get("neural_weights") or {}
    cells: list[dict[str, Any]] = []
    facets: set[str] = set()
    for i, leaf in enumerate(leaves[: width * length]):
        row, col = i // width, i % width
        activation = _cell_activation(leaf, weights)
        facets.add(str(leaf.get("facet") or ""))
        cells.append({
            **leaf,
            "row": row,
            "col": col,
            "cell_index": i,
            "activation": activation,
            "wires": [],
            "wire_count": 0,
        })
    cells = _wire_cells(cells, width=width)
    traversal = sorted(cells, key=lambda c: (-float(c.get("activation") or 0), c.get("row", 0), c.get("col", 0)))
    if bal and hasattr(bal, "stamp_optimized"):
        at_balance = bool(balance_gate.get("balanced")) or balance_gate.get("reason") == "balanced_hold"
        cells = bal.stamp_optimized(cells, balanced=at_balance)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-combinamatrix/v1",
        "updated": _now(),
        "product": "AmmoOS",
        "motto": doctrine.get("motto"),
        "ok": len(cells) > 0,
        "dimensions": {"width": width, "length": length, "cells": width * length, "filled": len(cells)},
        "source_counts": source_counts,
        "facet_count": len(facets),
        "cells": cells,
        "traversal": [{"id": c.get("id"), "row": c.get("row"), "col": c.get("col"), "activation": c.get("activation")} for c in traversal[:256]],
        "traverse_method": doctrine.get("traverse") or "van_emde_bois_row_major",
        "neural_weights": weights,
        "elapsed_ms": elapsed_ms,
        "balance_gate": balance_gate or None,
        "optimized_combinatronic": bool(balance_gate.get("balanced")),
        "combinatronic": True,
        "all_data_combinatronic": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not balance_gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    aml_boot = INSTALL / "library" / "dewey" / "000-computer-science" / "ammolang" / "combinamatrix_boot.aml"
    aml = _import_mod("aml", "field-ammolang.py")
    if aml and aml_boot.is_file():
        try:
            compiled = aml.compile_file(aml_boot)
            result["ammolang_curriculum"] = {
                "path": str(aml_boot.relative_to(INSTALL)),
                "ok": compiled.get("ok"),
                "step_count": compiled.get("step_count"),
                "combinators": [
                    s.get("name") for s in (compiled.get("ast") or {}).get("steps") or []
                    if s.get("op") == "COMBINATOR"
                ],
            }
        except Exception:
            pass
    return result


def publish_panel(*, refresh: bool = False, write_battery: bool = True) -> dict[str, Any]:
    battery = build_matrix(refresh=refresh)
    panel = {
        "schema": "field-combinamatrix-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok"),
        "dimensions": battery.get("dimensions"),
        "source_counts": battery.get("source_counts"),
        "facet_count": battery.get("facet_count"),
        "cell_count": len(battery.get("cells") or []),
        "top_cells": (battery.get("traversal") or [])[:16],
        "traverse_method": battery.get("traverse_method"),
        "elapsed_ms": battery.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    return {"ok": True, "panel": panel, "battery": battery}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    refresh = "--refresh" in sys.argv[2:]
    if cmd in ("panel", "json", "status"):
        print(json.dumps(publish_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "matrix", "cycle"):
        print(json.dumps(publish_panel(refresh=True, write_battery=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-combinamatrix.py [panel|build|matrix] [--refresh]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())