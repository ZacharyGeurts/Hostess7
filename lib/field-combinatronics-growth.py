#!/usr/bin/env pythong
"""Combinatronics growth — scan every file, surface-collapse tree, optimal compute width."""
from __future__ import annotations

import hashlib
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
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-combinatronics-growth-doctrine.json"
PANEL = STATE / "field-combinatronics-growth-panel.json"
BATTERY = STATE / "field-combinatronics-growth.json"
SKIP_DIRS = {
    ".git", ".nexus-state", "node_modules", "__pycache__", ".cache", "build", "dist",
    "target", ".venv", "venv", "zac", "fieldstorage",
}
WIDTH_CANDIDATES = (8, 12, 16, 20, 24, 32, 48)
NARROW_WIDTH = 16
DEFAULT_NARROW_WIDTH = 16


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


def _scan_roots() -> list[Path]:
    roots: list[Path] = [INSTALL]
    for rel in ("Grok16", "Queen", "Hostess7", "panel", "lib", "data", "library"):
        p = INSTALL / rel
        if p.is_dir() and p not in roots:
            roots.append(p)
    if SG.is_dir() and SG != INSTALL.parent:
        for name in ("Grok16", "Final_Eye", "Final_Ear", "ZOCR", "Spiderweb"):
            p = SG / name
            if p.is_dir() and p not in roots:
                roots.append(p)
    return roots


def scan_system_files(*, max_files: int = 12000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in _scan_roots():
        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if any(part in SKIP_DIRS for part in path.parts):
                    continue
                rel = str(path)
                if rel in seen:
                    continue
                seen.add(rel)
                try:
                    rel_install = str(path.relative_to(INSTALL))
                except ValueError:
                    try:
                        rel_install = str(path.relative_to(SG))
                    except ValueError:
                        rel_install = rel
                ext = path.suffix.lower().lstrip(".") or "none"
                rows.append({
                    "path": rel_install,
                    "ext": ext,
                    "bytes": path.stat().st_size,
                    "depth": len(Path(rel_install).parts),
                })
                if len(rows) >= max_files:
                    return rows
        except OSError:
            continue
    return rows


def _facet_for(ext: str, path: str) -> str:
    if ext in ("py", "pyx"):
        return "program"
    if ext in ("json", "jsonl"):
        return "data"
    if ext in ("png", "svg", "jpg", "webp"):
        return "visual"
    if ext in ("html", "js", "css"):
        return "queen_surface"
    if ext in ("sh", "bash"):
        return "shell"
    if ext in ("h7",):
        return "h7_manual"
    if "combinatronic" in path or "combinatorics" in path:
        return "combinatronics"
    if ext in ("cpp", "c", "h", "hpp", "rs", "go"):
        return "native"
    return "plate"


def _build_tree(files: list[dict[str, Any]]) -> dict[str, Any]:
    root: dict[str, Any] = {"name": "AmmoOS", "children": {}, "files": 0, "depth": 0}
    for row in files:
        node = root
        parts = Path(row["path"]).parts
        for i, part in enumerate(parts[:-1]):
            ch = node["children"].setdefault(part, {"name": part, "children": {}, "files": 0, "depth": i + 1})
            node = ch
        node["files"] = int(node.get("files", 0)) + 1
        node.setdefault("ext_counts", Counter())
        if isinstance(node["ext_counts"], Counter):
            node["ext_counts"][row["ext"]] += 1
        else:
            node["ext_counts"] = Counter({row["ext"]: 1})
    return root


def _collapse_surface(tree: dict[str, Any], *, surface_depth: int) -> dict[str, Any]:
    """Merge deep nodes toward surface — growth iteration collapses inward."""
    def walk(node: dict[str, Any], depth: int) -> dict[str, Any]:
        out = {"name": node.get("name"), "depth": depth, "files": node.get("files", 0), "children": {}}
        ext_c: Counter[str] = Counter()
        if isinstance(node.get("ext_counts"), Counter):
            ext_c.update(node["ext_counts"])
        for child_name, child in (node.get("children") or {}).items():
            if depth >= surface_depth:
                out["files"] += child.get("files", 0)
                if isinstance(child.get("ext_counts"), Counter):
                    ext_c.update(child["ext_counts"])
                for gc in (child.get("children") or {}).values():
                    out["files"] += _count_files(gc)
            else:
                out["children"][child_name] = walk(child, depth + 1)
        if ext_c:
            out["ext_top"] = ext_c.most_common(3)
        return out

    return walk(tree, 0)


def _count_files(node: dict[str, Any]) -> int:
    n = int(node.get("files", 0))
    for ch in (node.get("children") or {}).values():
        n += _count_files(ch)
    return n


def _van_emde_bois_sort(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket by path prefix length — surface-first ordering."""
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in files:
        buckets[min(4, row["depth"])].append(row)
    out: list[dict[str, Any]] = []
    for d in sorted(buckets.keys()):
        out.extend(sorted(buckets[d], key=lambda r: (r["path"], -r["bytes"])))
    return out


def _surface_score(collapsed: dict[str, Any]) -> float:
    """Higher = closer to surface (fewer deep children, more file mass near root)."""
    def mass(node: dict[str, Any], depth: int) -> tuple[int, int]:
        f = int(node.get("files", 0))
        deep = f * depth
        for ch in (node.get("children") or {}).values():
            cf, cd = mass(ch, depth + 1)
            f += cf
            deep += cd
        return f, deep

    total, weighted = mass(collapsed, 0)
    if total <= 0:
        return 0.0
    return round(1.0 - (weighted / (total * max(1, _tree_depth(collapsed)))), 4)


def _tree_depth(node: dict[str, Any]) -> int:
    kids = node.get("children") or {}
    if not kids:
        return int(node.get("depth", 0))
    return max(_tree_depth(ch) for ch in kids.values())


def _optimal_width(
    files: list[dict[str, Any]],
    facet_counts: Counter[str],
    *,
    surface_score: float = 0.0,
) -> dict[str, Any]:
    """Find narrow_band width minimizing simulated band overflow."""
    n = len(files) or 1
    best_w = DEFAULT_NARROW_WIDTH
    best_score = -1.0
    receipts: list[dict[str, Any]] = []
    depth_mass = sum(r.get("depth", 1) for r in files) / n
    for w in WIDTH_CANDIDATES:
        bands = max(1, math.ceil(n / w))
        overflow = max(0, n - bands * w)
        facet_spread = len(facet_counts) / bands
        collapse_bonus = surface_score * (1.0 - abs(w - 16) / 32.0)
        depth_fit = 1.0 / (1.0 + abs(w - depth_mass * 4))
        score = facet_spread + collapse_bonus + depth_fit * 0.15 - overflow * 0.02 - abs(w - 16) * 0.001
        receipts.append({
            "width": w,
            "bands": bands,
            "overflow": overflow,
            "collapse_bonus": round(collapse_bonus, 4),
            "score": round(score, 4),
        })
        if score > best_score:
            best_score = score
            best_w = w
    return {"optimal_width": best_w, "score": round(best_score, 4), "receipts": receipts}


def _sync_narrow_width(width: int) -> dict[str, Any]:
    """Push growth optimal width into spider wire narrow bands."""
    width = max(min(WIDTH_CANDIDATES), min(max(WIDTH_CANDIDATES), int(width)))
    sync_path = STATE / "field-combinatronics-narrow-width.json"
    receipt: dict[str, Any] = {
        "schema": "field-combinatronics-narrow-width/v1",
        "updated": _now(),
        "narrow_width": width,
        "source": "growth_optimal_width",
    }
    _save(sync_path, receipt)
    spider = INSTALL / "lib" / "field-combinatronic-spider-wire.py"
    if spider.is_file():
        try:
            spec = importlib.util.spec_from_file_location("sw_sync", spider)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "apply_narrow_width"):
                    mod.apply_narrow_width(width)
                elif hasattr(mod, "NARROW_WIDTH"):
                    mod.NARROW_WIDTH = width
                receipt["spider_wire"] = "synced"
        except Exception as exc:
            receipt["spider_wire"] = f"error:{exc}"[:120]
    return receipt


def _balance_mod() -> Any | None:
    path = INSTALL / "lib" / "field-combinatronic-balance.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("growth_bal", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def grow_combinatronics(*, generations: int = 8, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _balance_mod()
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("growth", refresh=False, force=force, battery_path=BATTERY)
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
    files = scan_system_files()
    tree = _build_tree(files)
    facet_counts: Counter[str] = Counter()
    for row in files:
        facet_counts[_facet_for(row["ext"], row["path"])] += 1

    growth_curve: list[dict[str, Any]] = []
    best_surface = 0.0
    best_depth = max(1, _tree_depth(tree))
    for gen in range(generations, 0, -1):
        collapsed = _collapse_surface(tree, surface_depth=gen)
        score = _surface_score(collapsed)
        depth = _tree_depth(collapsed)
        growth_curve.append({
            "generation": generations - gen + 1,
            "surface_depth": gen,
            "surface_score": score,
            "tree_depth": depth,
            "root_files": collapsed.get("files", 0),
        })
        if score >= best_surface:
            best_surface = score
            best_depth = depth

    sorted_files = _van_emde_bois_sort(files)
    width_doc = _optimal_width(files, facet_counts, surface_score=best_surface)
    leaves = []
    for i, row in enumerate(sorted_files[:512]):
        facet = _facet_for(row["ext"], row["path"])
        leaves.append({
            "id": f"growth:{i:04d}",
            "path": row["path"],
            "facet": facet,
            "ext": row["ext"],
            "depth": row["depth"],
            "surface_rank": i + 1,
        })

    gate = entry.get("gate") or {}
    if bal and hasattr(bal, "stamp_optimized"):
        leaves = bal.stamp_optimized(leaves[:256], balanced=bool(gate.get("balanced")))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-combinatronics-growth/v1",
        "updated": _now(),
        "product": "AmmoOS",
        "motto": "Scan every file — grow inward, collapse to surface, find optimal compute width.",
        "ok": True,
        "file_count": len(files),
        "facet_counts": dict(facet_counts),
        "generations": generations,
        "growth_curve": growth_curve,
        "best_surface_score": best_surface,
        "best_surface_depth": best_depth,
        "optimal_width": width_doc,
        "sort_method": "van_emde_bois_surface_first",
        "tree_method": "surface_collapse",
        "combinatorics_leaves": leaves,
        "leaf_count": len(leaves),
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


def publish_panel(*, write_battery: bool = True) -> dict[str, Any]:
    battery = grow_combinatronics()
    ow = (battery.get("optimal_width") or {}).get("optimal_width", DEFAULT_NARROW_WIDTH)
    panel = {
        "schema": "field-combinatronics-growth-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok"),
        "file_count": battery.get("file_count"),
        "optimal_width": ow,
        "optimal_width_score": (battery.get("optimal_width") or {}).get("score"),
        "best_surface_score": battery.get("best_surface_score"),
        "best_surface_depth": battery.get("best_surface_depth"),
        "growth_curve": (battery.get("growth_curve") or [])[-4:],
        "facet_counts": battery.get("facet_counts"),
        "sort_method": battery.get("sort_method"),
        "tree_method": battery.get("tree_method"),
        "elapsed_ms": battery.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    panel["narrow_width_sync"] = _sync_narrow_width(ow)
    return {"ok": True, "panel": panel, "battery": battery}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json"):
        if PANEL.is_file() and "--refresh" not in sys.argv:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("grow", "build", "scan"):
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "hint": "field-combinatronics-growth.py [panel|grow|scan] [--refresh]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())