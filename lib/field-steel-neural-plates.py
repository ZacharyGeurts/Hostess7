#!/usr/bin/env pythong
"""Steel Neural Plates — manage combinatorics with deep cross-domain neural connections."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-steel-neural-plates-doctrine.json"
PANEL = STATE / "field-steel-neural-plates-panel.json"
BATTERY = STATE / "field-steel-neural-plates.json"


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
    pio = _import_mod("plate_sealed_io", "plate-sealed-io.py")
    if pio and hasattr(pio, "sealed_write_json"):
        pio.sealed_write_json(path, doc)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        return None
    return None


def _balance_mod() -> Any | None:
    return _import_mod("snp_balance", "field-combinatronic-balance.py")


def _norm_tokens(row: dict[str, Any], keys: list[str]) -> set[str]:
    out: set[str] = set()
    for key in keys:
        val = row.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            for item in val:
                tok = str(item).strip().lower()
                if tok:
                    out.add(tok)
        else:
            tok = str(val).strip().lower()
            if tok:
                out.add(tok)
    return out


def _source_state_path(src: dict[str, Any]) -> str:
    """Resolve state file — combinatorics, battery, or panel."""
    for key in ("combinatorics", "battery", "panel"):
        val = str(src.get(key) or "").strip()
        if val:
            return val
    return ""


def _plate_members(doc: dict[str, Any], leaf_key: str, bridge_keys: list[str], *, limit: int = 0) -> list[dict[str, Any]]:
    rows = doc.get(leaf_key) or []
    if not isinstance(rows, list):
        return []
    members: list[dict[str, Any]] = []
    cap = len(rows) if limit <= 0 else min(len(rows), limit)
    for i, row in enumerate(rows[:cap]):
        if not isinstance(row, dict):
            continue
        mid = str(row.get("id") or row.get("chip_id") or row.get("instruction") or f"m:{i}")
        members.append({
            "id": mid,
            "label": row.get("label") or row.get("path") or mid,
            "tokens": sorted(_norm_tokens(row, bridge_keys)),
            "facet": row.get("facet"),
            "activation": float(row.get("activation") or row.get("path_pct") or row.get("rebalance_score") or 0) / 100.0,
        })
    return members


def _build_plates(doctrine: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    plates: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for src in doctrine.get("plate_sources") or []:
        pid = str(src.get("id") or "")
        bat = _source_state_path(src)
        doc = _load(STATE / bat, {}) if bat else {}
        members = _plate_members(
            doc,
            str(src.get("leaf_key") or "combinatorics_leaves"),
            list(src.get("bridge_keys") or ["id"]),
        )
        mean_act = sum(m.get("activation", 0) for m in members) / max(1, len(members))
        plate = {
            "id": f"steel:{pid}",
            "domain": pid,
            "facet": src.get("facet") or pid,
            "member_count": len(members),
            "members": members[:24],
            "mean_activation": round(mean_act, 4),
            "steel_weight": round(float(doctrine.get("steel_weight_base") or 1.0) * (1.0 + mean_act * 0.5), 4),
            "depth_layer": 1,
            "combinatronic": True,
        }
        plates.append(plate)
        by_id[pid] = {"plate": plate, "members": members, "tokens_by_member": {m["id"]: set(m.get("tokens") or []) for m in members}}
    return plates, by_id


def _wire_same_plate(members: list[dict[str, Any]], *, max_edges: int = 48) -> list[dict[str, Any]]:
    wires: list[dict[str, Any]] = []
    for i, a in enumerate(members):
        ta = set(a.get("tokens") or [])
        if not ta:
            continue
        for b in members[i + 1 : i + 9]:
            tb = set(b.get("tokens") or [])
            shared = ta & tb
            if not shared:
                continue
            w = round(min(1.0, len(shared) / max(1, min(len(ta), len(tb)))), 4)
            wires.append({
                "from": a["id"],
                "to": b["id"],
                "depth": 1,
                "kind": "intra_plate",
                "weight": w,
                "shared": sorted(shared)[:6],
            })
            if len(wires) >= max_edges:
                return wires
    return wires


def _cross_wire(
    src_id: str,
    dst_id: str,
    src_data: dict[str, Any],
    dst_data: dict[str, Any],
    bridge: dict[str, Any],
    weights: dict[str, float],
    *,
    universal_edges: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    wires: list[dict[str, Any]] = []
    via = [str(v).lower() for v in (bridge.get("via") or [])]
    kind = str(bridge.get("kind") or "cross")
    sm = src_data.get("members") or []
    dm = dst_data.get("members") or []
    if bridge.get("use_universal") and universal_edges:
        edge_map: dict[str, set[str]] = defaultdict(set)
        for edge in universal_edges[:512]:
            chip = str(edge.get("from") or "")
            lang = str(edge.get("to_lang") or "")
            if chip and lang:
                edge_map[chip].add(lang)
        for a in sm[:32]:
            chip = str(a.get("id") or "").split(":")[-1]
            for langs in edge_map.get(chip, set()):
                for b in dm[:32]:
                    if str(b.get("id") or "").endswith(lang) or langs in str(b.get("tokens") or []):
                        wires.append({
                            "from_plate": src_id,
                            "to_plate": dst_id,
                            "from": a["id"],
                            "to": b["id"],
                            "depth": 2,
                            "kind": kind,
                            "weight": round(weights.get("universal_edge", 0.25), 4),
                            "via": "universal_graph",
                        })
        return wires[:64]

    for a in sm[:24]:
        ta = set(a.get("tokens") or [])
        for b in dm[:24]:
            tb = set(b.get("tokens") or [])
            shared = {t for t in ta & tb if not via or any(v in t for v in via) or t in via}
            if not shared:
                continue
            w = round(weights.get("cross_domain", 0.18) * min(1.0, len(shared) / 3.0), 4)
            wires.append({
                "from_plate": src_id,
                "to_plate": dst_id,
                "from": a["id"],
                "to": b["id"],
                "depth": 2,
                "kind": kind,
                "weight": w,
                "shared": sorted(shared)[:4],
            })
            if len(wires) >= 48:
                return wires
    return wires


def _deep_paths(
    plate_wires: list[dict[str, Any]],
    cross_wires: list[dict[str, Any]],
    *,
    max_depth: int = 4,
    limit: int = 128,
) -> list[dict[str, Any]]:
    """Compose multi-hop steel paths across plates (depth 3–4)."""
    adj: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
    for w in plate_wires + cross_wires:
        a = str(w.get("from") or "")
        b = str(w.get("to") or "")
        wt = float(w.get("weight") or 0)
        kind = str(w.get("kind") or "wire")
        if a and b:
            adj[a].append((b, wt, kind))

    starts = [w.get("from") for w in cross_wires[:16] if w.get("from")]
    paths: list[dict[str, Any]] = []
    seen: set[str] = set()

    for start in starts:
        if not start:
            continue
        stack: list[tuple[str, list[str], float, int]] = [(str(start), [str(start)], 1.0, 0)]
        while stack and len(paths) < limit:
            node, chain, score, depth = stack.pop()
            if depth >= max_depth:
                if len(chain) >= 3:
                    key = "→".join(chain)
                    if key not in seen:
                        seen.add(key)
                        paths.append({
                            "path": chain,
                            "hops": len(chain) - 1,
                            "depth": len(chain) - 1,
                            "score": round(score, 4),
                            "kind": "deep_steel",
                        })
                continue
            for nb, wt, kind in adj.get(node, [])[:8]:
                if nb in chain:
                    continue
                stack.append((nb, chain + [nb], score * wt, depth + 1))

    paths.sort(key=lambda p: (-p.get("score", 0), -p.get("hops", 0)))
    return paths[:limit]


def _matrix_deep_wires(weights: dict[str, float]) -> list[dict[str, Any]]:
    matrix = _load(STATE / "field-combinamatrix.json", {})
    cells = matrix.get("cells") or []
    wires: list[dict[str, Any]] = []
    for cell in cells:
        for w in cell.get("wires") or []:
            wires.append({
                "from": cell.get("id"),
                "to": w.get("to"),
                "depth": 1,
                "kind": "matrix_adjacency",
                "weight": round(float(w.get("weight") or weights.get("matrix_adjacency", 0.15)), 4),
                "from_plate": "matrix",
                "to_plate": "matrix",
            })
    return wires[:256]


def build_steel_plates(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    doctrine = _load(DOCTRINE, {})
    bal = _balance_mod()
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("steel_plates", refresh=refresh, force=force, battery_path=BATTERY)
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

    weights = doctrine.get("neural_weights") or {}
    max_depth = int(doctrine.get("connection_depth_max") or 4)
    plates, by_domain = _build_plates(doctrine)

    intra_wires: list[dict[str, Any]] = []
    for pid, data in by_domain.items():
        for w in _wire_same_plate(data.get("members") or []):
            intra_wires.append({**w, "plate": pid})

    uni = _load(STATE / "field-g16-universal-combinatronic.json", {})
    universal_edges = uni.get("connections") or []

    cross_wires: list[dict[str, Any]] = []
    for bridge in doctrine.get("cross_bridges") or []:
        src = str(bridge.get("from") or "")
        dst = str(bridge.get("to") or "")
        if src not in by_domain or dst not in by_domain:
            continue
        cross_wires.extend(
            _cross_wire(src, dst, by_domain[src], by_domain[dst], bridge, weights, universal_edges=universal_edges)
        )

    matrix_wires = _matrix_deep_wires(weights)
    deep_paths = _deep_paths(intra_wires, cross_wires + matrix_wires, max_depth=max_depth)

    for plate in plates:
        pid = plate.get("domain")
        plate["intra_wire_count"] = sum(1 for w in intra_wires if w.get("plate") == pid)
        plate["cross_wire_count"] = sum(
            1 for w in cross_wires if w.get("from_plate") == pid or w.get("to_plate") == pid
        )
        plate["depth_layer"] = 2 if plate["cross_wire_count"] else 1

    max_hops = max((p.get("hops") or 0) for p in deep_paths) if deep_paths else 0
    mean_depth = round(sum(p.get("hops") or 0 for p in deep_paths) / max(1, len(deep_paths)), 2) if deep_paths else 0.0

    gate = entry.get("gate") or {}
    if bal and hasattr(bal, "stamp_optimized"):
        at_balance = bool(gate.get("balanced")) or gate.get("reason") == "balanced_hold"
        plates = bal.stamp_optimized(plates, balanced=at_balance)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    stack_witness: dict[str, Any] = {}
    pio = _import_mod("plate_sealed_io_sn", "plate-sealed-io.py")
    if pio and hasattr(pio, "stack_fabric_witness"):
        stack_witness = pio.stack_fabric_witness()

    result = {
        "schema": "field-steel-neural-plates/v1",
        "updated": _now(),
        "stack_fabric": stack_witness,
        "meld_citation": "ironclad:meld:2",
        "motto": doctrine.get("motto"),
        "ok": len(plates) > 0,
        "plate_count": len(plates),
        "plates": plates,
        "connection_depth": {
            "max": max_depth,
            "achieved": max_hops,
            "mean_hops": mean_depth,
            "deep_path_count": len(deep_paths),
        },
        "wires": {
            "intra": len(intra_wires),
            "cross": len(cross_wires),
            "matrix": len(matrix_wires),
            "total": len(intra_wires) + len(cross_wires) + len(matrix_wires),
        },
        "intra_wires_sample": intra_wires[:32],
        "cross_wires_sample": cross_wires[:48],
        "deep_paths": deep_paths[:64],
        "top_deep_paths": deep_paths[:12],
        "neural_weights": weights,
        "combinatronic": True,
        "all_data_combinatronic": True,
        "optimized_combinatronic": bool(gate.get("balanced")),
        "entry_synchronous": True,
        "balance_gate": gate or None,
        "elapsed_ms": elapsed_ms,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    return result


def publish_panel(*, refresh: bool = False, write_battery: bool = True, force: bool = False) -> dict[str, Any]:
    battery = build_steel_plates(refresh=refresh, force=force)
    panel = {
        "schema": "field-steel-neural-plates-panel/v1",
        "updated": _now(),
        "stack_fabric": battery.get("stack_fabric"),
        "meld_citation": battery.get("meld_citation") or "ironclad:meld:2",
        "ok": battery.get("ok"),
        "motto": battery.get("motto"),
        "plate_count": battery.get("plate_count"),
        "connection_depth": battery.get("connection_depth"),
        "wires": battery.get("wires"),
        "top_plates": (battery.get("plates") or [])[:8],
        "top_deep_paths": battery.get("top_deep_paths") or [],
        "elapsed_ms": battery.get("elapsed_ms"),
        "combinatronic": True,
        "fast_path": battery.get("fast_path", False),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    return {"ok": True, "panel": panel, "battery": battery}


def steel_plates_slice() -> dict[str, Any]:
    cached = _load(BATTERY, {})
    if cached.get("plates"):
        return {
            "schema": "field-steel-neural-plates-slice/v1",
            "plate_count": cached.get("plate_count"),
            "connection_depth": cached.get("connection_depth"),
            "wires": cached.get("wires"),
            "plates": (cached.get("plates") or [])[:12],
            "deep_paths": (cached.get("deep_paths") or [])[:16],
            "cached": True,
        }
    pub = publish_panel(refresh=False, write_battery=True)
    bat = pub.get("battery") or {}
    return {
        "schema": "field-steel-neural-plates-slice/v1",
        "plate_count": bat.get("plate_count"),
        "connection_depth": bat.get("connection_depth"),
        "wires": bat.get("wires"),
        "plates": (bat.get("plates") or [])[:12],
        "cached": False,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    refresh = "--refresh" in sys.argv[2:]
    force = "--force" in sys.argv[2:]
    if cmd in ("panel", "json", "status"):
        if PANEL.is_file() and not refresh:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel(refresh=refresh, force=force).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "battery"):
        print(json.dumps(publish_panel(refresh=refresh, force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(steel_plates_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        doc = build_steel_plates(refresh=False)
        depth = doc.get("connection_depth") or {}
        ok = bool(doc.get("ok")) and int(doc.get("plate_count") or 0) >= 5
        print(json.dumps({
            "ok": ok,
            "plate_count": doc.get("plate_count"),
            "connection_depth": depth,
            "wires": doc.get("wires"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["panel", "build", "slice", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())