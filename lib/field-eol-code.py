#!/usr/bin/env python3
"""EOL Code — Layer 0 BSP tree generator; pending (−4) → every path/dead end → EOL at 0."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-eol-code-doctrine.json"
PANEL = STATE / "field-eol-code-panel.json"
RUNTIME = STATE / "field-eol-code-runtime.json"
LEDGER = STATE / "field-eol-code-ledger.jsonl"
TREE_CACHE = STATE / "field-eol-code-tree.json"

_IMPORT_RE = re.compile(
    r"(?:from\s+[\w.]+\s+import|import\s+[\w.]+|require\s*\(\s*['\"]([^'\"]+)['\"]|"
    r"import\s+.*?from\s+['\"]([^'\"]+)['\"])",
    re.MULTILINE,
)
_EOL_MARKERS = (
    "ironclad",
    "eol",
    "plate_meld",
    "field-gnu-terminal",
    "field-eol-code",
    "truth_percent",
    "meld_citation",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


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


def doctrine_doc() -> dict[str, Any]:
    return _load(DOCTRINE, {"schema": "field-eol-code/v1", "policy": {}})


def _composite_bsp_sort(rows: list[dict[str, Any]], *, key: str = "truth_percent") -> list[dict[str, Any]]:
    best = _import_py(INSTALL / "lib" / "field-best-sort.py", "field_best_sort")
    if best and hasattr(best, "apply_best"):
        try:
            sorted_rows, _ = best.apply_best(rows, context="eol_code_tree", n=len(rows))
            return sorted_rows
        except Exception:
            pass
    if len(rows) <= 1:
        return list(rows)

    def score(row: dict[str, Any], idx: int) -> float:
        raw = row.get(key)
        if raw is None:
            raw = row.get("priority")
        if raw is None:
            raw = len(rows) - idx
        return float(raw)

    scored = [(score(r, i), r) for i, r in enumerate(rows)]
    scored.sort(key=lambda t: t[0], reverse=True)
    mid = len(scored) // 2
    left = _composite_bsp_sort([r for _, r in scored[:mid]], key=key)
    right = _composite_bsp_sort([r for _, r in scored[mid:]], key=key)
    return left + right


def _layer_for_path(rel: str, policy: dict[str, Any]) -> int:
    r = rel.replace("\\", "/").lower()
    if "eol-code" in r or r.startswith("panel/eol") or r == "lib/field-eol-code.py":
        return 0
    if r.startswith("panel/") or r.startswith("lib/field-") or r.startswith("lib/hostess7"):
        return 0
    if r.startswith("data/field-host-desktop") or "ammoos" in r:
        return -1
    if r.startswith("lib/field-dns") or "kilroy" in r or "botnet" in r:
        return -2
    if r.startswith("lib/threat-panel") or "nexus-c2" in r or "command" in r:
        return -3
    if r.startswith("queen/"):
        return 1
    if r.startswith("data/"):
        return -1
    if r.startswith("scripts/"):
        return -2
    return -4


def _scan_files(policy: dict[str, Any]) -> list[dict[str, Any]]:
    roots = policy.get("scan_roots") or ["lib", "panel", "data", "scripts"]
    exts = set(policy.get("code_extensions") or [".py", ".js", ".html", ".json", ".sh"])
    exclude = set(policy.get("exclude_dirs") or [])
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()

    for root_name in roots:
        root = INSTALL / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(INSTALL).as_posix()
            if any(part in exclude for part in path.parts):
                continue
            if path.suffix.lower() not in exts and path.suffix:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            nodes.append({
                "id": rel,
                "path": rel,
                "kind": "file",
                "layer": _layer_for_path(rel, policy),
                "size": size,
                "ext": path.suffix.lower(),
            })
    return nodes


def _edges_for(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:120000]
    except OSError:
        return []
    edges: list[str] = []
    for m in _IMPORT_RE.finditer(text):
        g = m.group(1) or m.group(2) or ""
        if g and not g.startswith("."):
            edges.append(g.split("/")[-1].split(".")[0])
    return edges[:24]


def _eol_markers_in(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:8000].lower()
    except OSError:
        return False
    return sum(1 for mk in _EOL_MARKERS if mk in head) >= 2


def _truth_for_node(node: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    path = INSTALL / str(node.get("path") or "")
    eol_thr = float(policy.get("truth_eol_threshold") or 100.0)
    active_thr = float(policy.get("truth_active_threshold") or 85.0)
    has_markers = _eol_markers_in(path) if path.is_file() else False
    edges = _edges_for(path) if path.is_file() else []
    base = 72.0
    if has_markers:
        base += 18.0
    if node.get("layer", -4) >= 0:
        base += 6.0
    if not edges:
        base -= 8.0
    truth = min(100.0, max(0.0, base))
    if has_markers and node.get("layer", -4) >= 0:
        truth = eol_thr
    status = "pending"
    if truth >= eol_thr:
        status = "eol"
    elif truth >= active_thr:
        status = "active"
    elif not edges:
        status = "dead_end"
    else:
        status = "leaf" if len(edges) <= 2 else "active"
    return {
        "truth_percent": round(truth, 2),
        "eol_status": status,
        "edges": len(edges),
        "eol_markers": has_markers,
        "ironclad_cite": "ironclad:field_sanity:2 — classify, strip, dedupe, flatten, cool_sort",
    }


def _ironclad_extend_batch(nodes: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    truth_mod = _import_py(INSTALL / "lib" / "field-ironclad-truth.py", "field_ironclad_truth")
    ic = _load(STATE / "ironclad-immediate.json", {})
    sealed = bool(ic.get("ironclad_sealed"))
    out: list[dict[str, Any]] = []
    for node in nodes:
        t = _truth_for_node(node, policy)
        query = str(node.get("path") or "")
        if truth_mod and hasattr(truth_mod, "ironclad_truth") and sealed:
            try:
                doc = truth_mod.ironclad_truth(query, mode="information")
                if doc.get("ok"):
                    imm = doc.get("ironclad") or {}
                    t["truth_percent"] = float(imm.get("truth_percent") or t["truth_percent"])
                    t["verdict"] = imm.get("verdict")
                    t["ironclad_extended"] = True
            except Exception:
                t["ironclad_extended"] = False
        else:
            t["ironclad_extended"] = False
            if sealed:
                t["truth_percent"] = min(100.0, t["truth_percent"] + 5.0)
        merged = {**node, **t}
        if merged.get("truth_percent", 0) >= float(policy.get("truth_eol_threshold") or 100):
            merged["eol_status"] = "eol"
        out.append(merged)
    return out


def _build_bsp_tree(nodes: list[dict[str, Any]], doctrine: dict[str, Any]) -> dict[str, Any]:
    layers = {row["z"]: row for row in (doctrine.get("layers") or []) if "z" in row}
    by_layer: dict[int, list[dict[str, Any]]] = {}
    for n in nodes:
        z = int(n.get("layer", -4))
        by_layer.setdefault(z, []).append(n)

    def branch(layer_z: int, label: str) -> dict[str, Any]:
        kids = _composite_bsp_sort(by_layer.get(layer_z, []), key="truth_percent")
        child_branches = []
        for row in kids:
            child_branches.append({
                "id": row.get("id"),
                "path": row.get("path"),
                "eol_status": row.get("eol_status", "pending"),
                "truth_percent": row.get("truth_percent", 0),
                "edges": row.get("edges", 0),
                "dead_end": row.get("eol_status") == "dead_end",
                "leaf": row.get("eol_status") in ("leaf", "dead_end", "eol"),
                "children": [],
            })
        not_eol = [c for c in child_branches if c.get("eol_status") != "eol"]
        dead = [c for c in child_branches if c.get("dead_end")]
        return {
            "layer": layer_z,
            "label": label,
            "node_count": len(child_branches),
            "eol_count": sum(1 for c in child_branches if c.get("eol_status") == "eol"),
            "pending_count": sum(1 for c in child_branches if c.get("eol_status") == "pending"),
            "dead_end_count": len(dead),
            "not_eol_count": len(not_eol),
            "children": child_branches,
        }

    layer_order = sorted(layers.keys())
    root_label = layers.get(min(layer_order), {}).get("label", "Pending")
    tree_children = []
    for z in layer_order:
        meta = layers.get(z, {})
        tree_children.append(branch(z, str(meta.get("label") or z)))

    all_nodes = nodes
    summary = {
        "total_paths": len(all_nodes),
        "eol": sum(1 for n in all_nodes if n.get("eol_status") == "eol"),
        "pending": sum(1 for n in all_nodes if n.get("eol_status") == "pending"),
        "active": sum(1 for n in all_nodes if n.get("eol_status") == "active"),
        "dead_end": sum(1 for n in all_nodes if n.get("eol_status") == "dead_end"),
        "leaf": sum(1 for n in all_nodes if n.get("eol_status") == "leaf"),
        "not_eol_yet": sum(1 for n in all_nodes if n.get("eol_status") not in ("eol",)),
        "cut_candidates": sum(
            1 for n in all_nodes if n.get("eol_status") in ("dead_end", "leaf") and n.get("truth_percent", 0) < 90
        ),
    }
    return {
        "schema": "field-eol-code-tree/v1",
        "root": {
            "id": "pending-root",
            "layer": min(layer_order) if layer_order else -4,
            "label": root_label,
            "children": tree_children,
        },
        "summary": summary,
        "bsp": {"algorithm": "composite_bsp", "sort_key": "truth_percent"},
    }


def _runtime() -> dict[str, Any]:
    return _load(RUNTIME, {
        "schema": "field-eol-code-runtime/v1",
        "generation": 0,
        "cursor": 0,
        "nodes": {},
        "log": [],
        "running": False,
    })


def _save_runtime(rt: dict[str, Any]) -> None:
    _save(RUNTIME, rt)


def generator_tick(*, batch: int | None = None, write: bool = True) -> dict[str, Any]:
    """Self-run EOL generator — process next batch, Ironclad extend, BSP refresh."""
    doctrine = doctrine_doc()
    policy = doctrine.get("policy") or {}
    batch_n = int(batch or policy.get("generator_batch") or 48)
    rt = _runtime()
    all_files = _scan_files(policy)
    node_map: dict[str, dict[str, Any]] = dict(rt.get("nodes") or {})
    for f in all_files:
        fid = str(f.get("id") or "")
        if fid not in node_map:
            node_map[fid] = {**f, "eol_status": "pending", "truth_percent": 0.0}

    ids = sorted(node_map.keys())
    cursor = int(rt.get("cursor") or 0)
    if cursor >= len(ids):
        cursor = 0
    slice_ids = ids[cursor : cursor + batch_n]
    if not slice_ids:
        slice_ids = ids[:batch_n]
    batch_nodes = [node_map[i] for i in slice_ids]
    extended = _ironclad_extend_batch(batch_nodes, policy)
    log_lines: list[str] = []
    for row in extended:
        node_map[str(row["id"])] = row
        log_lines.append(
            f"{row.get('path')}: {row.get('eol_status')} truth={row.get('truth_percent')}% "
            f"edges={row.get('edges', 0)}"
        )
    cursor = (cursor + len(slice_ids)) % max(len(ids), 1)
    gen = int(rt.get("generation") or 0) + 1
    nodes_list = list(node_map.values())
    tree = _build_bsp_tree(nodes_list, doctrine)
    rt.update({
        "generation": gen,
        "cursor": cursor,
        "nodes": node_map,
        "log": (list(rt.get("log") or []) + log_lines)[-120:],
        "running": True,
        "updated": _now(),
        "last_batch": len(slice_ids),
        "tree_summary": tree.get("summary"),
    })
    if write:
        _save_runtime(rt)
        _save(TREE_CACHE, tree)
        for line in log_lines[:12]:
            _append_ledger({"op": "tick", "generation": gen, "line": line})
    return {
        "ok": True,
        "schema": "field-eol-code-tick/v1",
        "generation": gen,
        "processed": len(slice_ids),
        "cursor": cursor,
        "total": len(ids),
        "log": log_lines,
        "tree_summary": tree.get("summary"),
        "ironclad_extended": sum(1 for r in extended if r.get("ironclad_extended")),
    }


def generator_run(*, ticks: int = 5) -> dict[str, Any]:
    results = []
    for _ in range(max(1, min(int(ticks), 32))):
        results.append(generator_tick(write=True))
    last = results[-1] if results else {}
    return {
        "ok": True,
        "schema": "field-eol-code-run/v1",
        "ticks": len(results),
        "generation": last.get("generation"),
        "tree_summary": last.get("tree_summary"),
        "log_tail": (last.get("log") or [])[-8:],
    }


def build_panel(*, refresh: bool = False, write: bool = True) -> dict[str, Any]:
    doctrine = doctrine_doc()
    policy = doctrine.get("policy") or {}
    rt = _runtime()
    if refresh or not rt.get("nodes"):
        generator_tick(batch=int(policy.get("generator_batch") or 48), write=True)
        rt = _runtime()
    nodes_list = list((rt.get("nodes") or {}).values())
    if not nodes_list:
        nodes_list = _ironclad_extend_batch(_scan_files(policy), policy)
    tree = _load(TREE_CACHE, None) or _build_bsp_tree(nodes_list, doctrine)
    ic = _load(STATE / "ironclad-immediate.json", {})
    doc = {
        "ok": True,
        "schema": "field-eol-code-panel/v1",
        "at": _now(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "os_layer": policy.get("os_layer", 0),
        "self_run": policy.get("self_run", True),
        "generation": rt.get("generation", 0),
        "runtime": {
            "cursor": rt.get("cursor", 0),
            "running": rt.get("running", False),
            "log": rt.get("log", [])[-40:],
            "last_batch": rt.get("last_batch", 0),
        },
        "tree": tree,
        "layers": doctrine.get("layers") or [],
        "ironclad": {
            "sealed": ic.get("ironclad_sealed"),
            "truth_percent": ic.get("truth_percent"),
            "verdict": ic.get("verdict"),
            "cite": (doctrine.get("ironclad") or {}).get("field_sanity_cite"),
        },
        "api": (doctrine.get("surface") or {}).get("api", "/api/field-eol-code"),
        "panel": (doctrine.get("surface") or {}).get("panel", "/eol-code"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def handle_api(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").lower().replace("-", "_")
    if action in ("panel", "json", "status"):
        return build_panel(refresh=bool(body.get("refresh")))
    if action == "tree":
        rt = _runtime()
        nodes = list((rt.get("nodes") or {}).values())
        if not nodes:
            nodes = _ironclad_extend_batch(_scan_files(doctrine_doc().get("policy") or {}), doctrine_doc().get("policy") or {})
        return _build_bsp_tree(nodes, doctrine_doc())
    if action in ("tick", "step"):
        return generator_tick(batch=body.get("batch"))
    if action == "run":
        return generator_run(ticks=int(body.get("ticks") or 5))
    if action == "reset":
        for p in (RUNTIME, TREE_CACHE):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        return {"ok": True, "reset": True}
    return {"ok": False, "error": f"unknown_action:{action}"}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(refresh="--refresh" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "tick":
        print(json.dumps(generator_tick(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(json.dumps(generator_run(ticks=n), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(handle_api(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-eol-code.py [panel|tick|run N|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())