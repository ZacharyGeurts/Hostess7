#!/usr/bin/env pythong
"""Live combinatronic map — persistent placements; snap into place on fingerprint match."""
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
DOCTRINE = INSTALL / "data" / "field-combinatronic-balance-doctrine.json"
LIVE_MAP = STATE / "field-combinatronic-live-map.json"
PANEL = STATE / "field-combinatronic-live-map-panel.json"
FAST_PATH_MS = 25


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
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


def _balance_mod() -> Any | None:
    return _import_mod("live_bal", "field-combinatronic-balance.py")


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _entry_batteries() -> list[dict[str, Any]]:
    return list(_doctrine().get("entry_batteries") or [])


def _battery_path(spec: dict[str, Any]) -> Path:
    bat = str(spec.get("battery") or spec.get("combinatorics") or "")
    return STATE / bat if bat else STATE / "field-g16-universal-combinatronic.json"


def _ids_from_rows(rows: list[Any], id_field: str) -> list[str]:
    out: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            val = str(row.get(id_field) or row.get("id") or "")
            if val:
                out.append(val)
        elif isinstance(row, str):
            out.append(row)
    return out


def _domain_key_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for src in _doctrine().get("fingerprint_sources") or []:
        if isinstance(src, dict) and src.get("id"):
            out[str(src["id"])] = src
    return out


def _extract_placement(domain: str, doc: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    key = str(src.get("key") or "id")
    id_field = str(src.get("id_field") or "id")
    if src.get("count_only"):
        if key == "entries" and isinstance(doc.get("entries"), dict):
            ids: list[str] = sorted(doc["entries"].keys())
        elif key == "file_count":
            count = int(doc.get("file_count") or doc.get(key) or 0)
            return {"count": count, "ids": [], "ids_hash": hashlib.sha256(str(count).encode()).hexdigest()[:16]}
        else:
            val = doc.get(key)
            count = len(val) if isinstance(val, (list, dict)) else int(val or 0)
            return {"count": count, "ids": [], "ids_hash": hashlib.sha256(str(count).encode()).hexdigest()[:16]}
    if src.get("dict_keys"):
        ids = sorted((doc.get(key) or {}).keys()) if isinstance(doc.get(key), dict) else []
    else:
        rows = doc.get(key) or []
        ids = _ids_from_rows(rows if isinstance(rows, list) else [], id_field)
    ids_hash = hashlib.sha256(",".join(ids).encode()).hexdigest()[:16] if ids else "empty"
    by_id: dict[str, dict[str, Any]] = {}
    rows = doc.get(key) or []
    if isinstance(rows, list):
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            rid = str(row.get(id_field) or row.get("id") or "")
            if not rid:
                continue
            by_id[rid] = {
                "slot": i,
                "rank": row.get("rebalance_rank") or row.get("sort_slot") or row.get("condense_slot") or (i + 1),
                "band": row.get("band") or row.get("family") or row.get("lang"),
            }
    return {"count": len(ids), "ids": ids[:512], "ids_hash": ids_hash, "by_id": by_id}


def capture_placements(*, source: str = "optimal") -> dict[str, Any]:
    """Snapshot ordered placements from every combinatoric battery."""
    bal = _balance_mod()
    fp = bal.corpus_fingerprint(scan_library=False) if bal and hasattr(bal, "corpus_fingerprint") else {}
    domain_map = _domain_key_map()
    placements: dict[str, Any] = {}
    material: list[str] = []

    for spec in _entry_batteries():
        did = str(spec.get("id") or "")
        path = _battery_path(spec)
        doc = _load(path, {})
        src = domain_map.get(did, {"id": did, "key": "combinatorics_leaves", "id_field": "id"})
        placement = _extract_placement(did, doc, src)
        placements[did] = {
            "battery": path.name,
            "present": path.is_file() and bool(doc),
            **placement,
        }
        material.append(f"{did}:{placement.get('ids_hash')}:{placement.get('count')}")

    placement_hash = hashlib.sha256("|".join(material).encode()).hexdigest()
    doc = {
        "schema": "field-combinatronic-live-map/v1",
        "updated": _now(),
        "corpus_hash": fp.get("corpus_hash") or "",
        "placement_hash": placement_hash,
        "domains": fp.get("domains") or {},
        "placements": placements,
        "domain_count": len(placements),
        "source": source,
        "live_combinatronic": True,
        "snap_ready": True,
        "motto": "Live combinatronic — map holds places; fingerprint match snaps into them.",
    }
    _save(LIVE_MAP, doc)
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=True, elapsed_ms=0.0, fingerprint=fp)
    _record_panel(snap=True, delta=False, elapsed_ms=0.0, reason="capture", placement_hash=placement_hash)
    return doc


def _map_state() -> dict[str, Any]:
    doc = _load(LIVE_MAP, {})
    if doc.get("placement_hash"):
        return doc
    return {
        "schema": "field-combinatronic-live-map/v1",
        "updated": _now(),
        "corpus_hash": "",
        "placement_hash": "",
        "placements": {},
        "snap_ready": False,
    }


def _domain_delta(cur_fp: dict[str, Any], stored: dict[str, Any]) -> dict[str, Any]:
    cur_domains = cur_fp.get("domains") or {}
    prev_domains = stored.get("domains") or {}
    changed: list[str] = []
    stable: list[str] = []
    new_items: list[str] = []
    for did, cur in cur_domains.items():
        prev = prev_domains.get(did) or {}
        cur_hash = cur.get("ids_hash") or str(cur.get("count") or "")
        prev_hash = prev.get("ids_hash") or str(prev.get("count") or "")
        if not prev_hash:
            if cur_hash:
                new_items.append(did)
            continue
        if cur_hash != prev_hash:
            changed.append(did)
        else:
            stable.append(did)
    return {
        "changed": changed,
        "stable": stable,
        "new_items": new_items,
        "has_delta": bool(changed or new_items),
    }


def _battery_ready(placements: dict[str, Any]) -> bool:
    if not placements:
        return False
    ready = 0
    for spec in _entry_batteries():
        did = str(spec.get("id") or "")
        row = placements.get(did) or {}
        path = _battery_path(spec)
        if path.is_file() and row.get("present"):
            ready += 1
    return ready >= max(3, len(_entry_batteries()) // 2)


def _publish_domain(domain: str) -> dict[str, Any]:
    batteries = {str(b.get("id")): b for b in _entry_batteries()}
    spec = batteries.get(domain) or {}
    mod = str(spec.get("module") or "")
    pub = str(spec.get("publish") or "publish_panel")
    if not mod:
        return {"domain": domain, "ok": False, "hint": "module_missing"}
    path = INSTALL / "lib" / mod
    if not path.is_file():
        return {"domain": domain, "ok": False, "hint": "module_file_missing"}
    try:
        spec_imp = importlib.util.spec_from_file_location(f"live_snap_{domain}", path)
        if not spec_imp or not spec_imp.loader:
            return {"domain": domain, "ok": False, "hint": "import_failed"}
        mod_obj = importlib.util.module_from_spec(spec_imp)
        spec_imp.loader.exec_module(mod_obj)
        fn = getattr(mod_obj, pub, None)
        if not callable(fn):
            return {"domain": domain, "ok": False, "hint": "publish_missing"}
        if domain == "library":
            result = fn(refresh=True)
        elif domain == "visuals":
            result = fn(refresh=bool(spec.get("light")))
        else:
            result = fn()
        return {"domain": domain, "ok": bool((result or {}).get("ok", True)), "skipped": False}
    except Exception as exc:
        return {"domain": domain, "ok": False, "error": str(exc)[:200]}


def delta_sync(*, domains: list[str] | None = None) -> dict[str, Any]:
    """Refresh only domains whose fingerprint changed — merge into live map."""
    t0 = time.perf_counter()
    bal = _balance_mod()
    stored = _map_state()
    fp = bal.corpus_fingerprint(scan_library=False) if bal and hasattr(bal, "corpus_fingerprint") else {}
    delta = _domain_delta(fp, stored)
    targets = domains or (delta.get("changed") or []) + (delta.get("new_items") or [])
    steps: list[dict[str, Any]] = []
    for did in targets:
        steps.append(_publish_domain(did))
    captured = capture_placements(source="delta_sync") if steps else stored
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=bool(targets), elapsed_ms=elapsed_ms, fingerprint=fp)
    out = {
        "schema": "field-combinatronic-live-snap/v1",
        "updated": _now(),
        "action": "delta_sync",
        "ok": all(s.get("ok", True) for s in steps) if steps else True,
        "delta": delta,
        "targets": targets,
        "steps": steps,
        "placement_hash": captured.get("placement_hash"),
        "corpus_hash": captured.get("corpus_hash"),
        "elapsed_ms": elapsed_ms,
        "live_combinatronic": True,
    }
    _record_panel(snap=False, delta=True, elapsed_ms=elapsed_ms, reason="delta_sync")
    return out


def _quick_corpus_hash(bal: Any | None) -> tuple[str, dict[str, Any], bool]:
    """Prefer balance-panel hash — full fingerprint only when panel hash is stale."""
    stored_map = _map_state()
    panel_hash = ""
    if bal and hasattr(bal, "balance_state"):
        panel_hash = str((bal.balance_state() or {}).get("corpus_hash") or "")
    map_hash = str(stored_map.get("corpus_hash") or "")
    if panel_hash and map_hash and panel_hash == map_hash:
        return panel_hash, {"corpus_hash": panel_hash, "quick": True}, True
    if bal and hasattr(bal, "corpus_fingerprint"):
        fp = bal.corpus_fingerprint(scan_library=False)
        return str(fp.get("corpus_hash") or ""), fp, False
    return map_hash, {"corpus_hash": map_hash}, bool(map_hash)


def snap(*, force: bool = False, allow_delta: bool = True) -> dict[str, Any]:
    """
    Live combinatronic snap — fingerprint match → instant placement hold.
    Corpus delta → targeted domain sync only. No map → needs full optimal.
    """
    t0 = time.perf_counter()
    stored = _map_state()
    prev_hash = str(stored.get("corpus_hash") or "")
    bal = _balance_mod()

    if not force and stored.get("snap_ready") and prev_hash and _battery_ready(stored.get("placements") or {}):
        panel_hash = ""
        if bal and hasattr(bal, "balance_state"):
            panel_hash = str((bal.balance_state() or {}).get("corpus_hash") or "")
        if panel_hash and panel_hash == prev_hash:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
            state_bal = (bal.balance_state() if bal and hasattr(bal, "balance_state") else {}) or {}
            if bal and hasattr(bal, "record_cycle") and not state_bal.get("balanced"):
                bal.record_cycle(
                    reorganized=False,
                    elapsed_ms=elapsed_ms,
                    fingerprint={"corpus_hash": panel_hash, "quick": True},
                )
            _record_panel(snap=True, delta=False, elapsed_ms=elapsed_ms, reason="panel_hash_match")
            return {
                "schema": "field-combinatronic-live-snap/v1",
                "updated": _now(),
                "action": "snap",
                "ok": True,
                "snapped": True,
                "fast_path": elapsed_ms <= FAST_PATH_MS,
                "quick_fingerprint": True,
                "live_combinatronic": True,
                "reason": "panel_hash_match",
                "corpus_hash": panel_hash,
                "placement_hash": stored.get("placement_hash"),
                "domain_count": stored.get("domain_count"),
                "balance_gate": {
                    "schema": "field-combinatronic-balance-gate/v1",
                    "skip_reorganize": True,
                    "fast_path": True,
                    "reason": "balanced_hold",
                },
                "elapsed_ms": elapsed_ms,
                "fast_path_ms_target": FAST_PATH_MS,
                "motto": "Snap into place — panel hash matches live map.",
            }

    gate: dict[str, Any] = {}
    if bal and hasattr(bal, "should_reorganize") and not force:
        decision = bal.should_reorganize(force=False)
        gate = {
            "schema": "field-combinatronic-balance-gate/v1",
            "skip_reorganize": not decision.get("reorganize", False),
            "fast_path": decision.get("fast_path", False),
            **decision,
        }
    elif bal and hasattr(bal, "gate_refresh"):
        gate = bal.gate_refresh(False, force=force)
    cur_hash, fp, quick_fp = _quick_corpus_hash(bal)

    if force:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        return {
            "schema": "field-combinatronic-live-snap/v1",
            "updated": _now(),
            "action": "snap",
            "ok": True,
            "snapped": False,
            "needs_full": True,
            "reason": "forced",
            "elapsed_ms": elapsed_ms,
            "balance_gate": gate,
        }

    if not stored.get("snap_ready") or not stored.get("placement_hash"):
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        return {
            "schema": "field-combinatronic-live-snap/v1",
            "updated": _now(),
            "action": "snap",
            "ok": False,
            "snapped": False,
            "needs_full": True,
            "reason": "no_map",
            "hint": "run optimal once to seed live map",
            "elapsed_ms": elapsed_ms,
            "balance_gate": gate,
        }

    delta = _domain_delta(fp, stored)

    if cur_hash == prev_hash and _battery_ready(stored.get("placements") or {}):
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        fast = elapsed_ms <= FAST_PATH_MS
        if bal and hasattr(bal, "record_cycle"):
            bal.record_cycle(
                reorganized=False,
                elapsed_ms=elapsed_ms,
                fingerprint=fp if not quick_fp else {"corpus_hash": cur_hash, "quick": True},
            )
        _record_panel(snap=True, delta=False, elapsed_ms=elapsed_ms, reason="fingerprint_match")
        return {
            "schema": "field-combinatronic-live-snap/v1",
            "updated": _now(),
            "action": "snap",
            "ok": True,
            "snapped": True,
            "fast_path": fast,
            "quick_fingerprint": quick_fp,
            "live_combinatronic": True,
            "reason": "fingerprint_match",
            "corpus_hash": cur_hash,
            "placement_hash": stored.get("placement_hash"),
            "domain_count": stored.get("domain_count"),
            "placements": {k: {"count": v.get("count"), "ids_hash": v.get("ids_hash")} for k, v in (stored.get("placements") or {}).items()},
            "balance_gate": gate,
            "elapsed_ms": elapsed_ms,
            "fast_path_ms_target": FAST_PATH_MS,
            "motto": "Snap into place — live map holds; corpus unchanged.",
        }

    if allow_delta and delta.get("has_delta") and stored.get("placements"):
        ds = delta_sync()
        ds["snapped"] = True
        ds["action"] = "snap"
        ds["reason"] = "delta_sync"
        ds["fast_path"] = ds.get("elapsed_ms", 999) <= FAST_PATH_MS * 4
        ds["live_combinatronic"] = True
        ds["balance_gate"] = gate
        return ds

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    return {
        "schema": "field-combinatronic-live-snap/v1",
        "updated": _now(),
        "action": "snap",
        "ok": False,
        "snapped": False,
        "needs_full": True,
        "reason": "corpus_changed" if cur_hash != prev_hash else "batteries_missing",
        "delta": delta,
        "corpus_hash": cur_hash,
        "prev_corpus_hash": prev_hash,
        "elapsed_ms": elapsed_ms,
        "balance_gate": gate,
        "hint": "run optimal --refresh to rebuild live map",
    }


def _record_panel(
    *,
    snap: bool,
    delta: bool,
    elapsed_ms: float,
    reason: str,
    placement_hash: str = "",
) -> None:
    state = _load(PANEL, {})
    snaps = int(state.get("snap_count") or 0) + (1 if snap else 0)
    deltas = int(state.get("delta_count") or 0) + (1 if delta else 0)
    panel = {
        "schema": "field-combinatronic-live-map-panel/v1",
        "updated": _now(),
        "snap_count": snaps,
        "delta_count": deltas,
        "last_reason": reason,
        "last_elapsed_ms": round(elapsed_ms, 3),
        "placement_hash": placement_hash or state.get("placement_hash") or _map_state().get("placement_hash"),
        "corpus_hash": _map_state().get("corpus_hash"),
        "snap_ready": bool(_map_state().get("snap_ready")),
        "live_combinatronic": True,
        "fast_path_ms_target": FAST_PATH_MS,
        "statement": "live_combinatronic_snap_hold" if snap else "live_combinatronic_delta",
    }
    _save(PANEL, panel)


def panel() -> dict[str, Any]:
    stored = _map_state()
    pnl = _load(PANEL, {})
    bal = _balance_mod()
    fp = bal.corpus_fingerprint(scan_library=False) if bal and hasattr(bal, "corpus_fingerprint") else {}
    gate = bal.gate_refresh(False) if bal and hasattr(bal, "gate_refresh") else {}
    return {
        "schema": "field-combinatronic-live-map-panel/v1",
        "updated": _now(),
        "ok": True,
        "live_combinatronic": True,
        "snap_ready": bool(stored.get("snap_ready")),
        "placement_hash": stored.get("placement_hash"),
        "corpus_hash": stored.get("corpus_hash"),
        "current_corpus_hash": fp.get("corpus_hash"),
        "domain_count": stored.get("domain_count"),
        "placements_sample": {
            k: {"count": v.get("count"), "ids_hash": v.get("ids_hash")}
            for k, v in list((stored.get("placements") or {}).items())[:8]
        },
        "delta": _domain_delta(fp, stored),
        "balance_gate": gate,
        "stats": pnl,
        "policy": (_doctrine().get("policy") or {}).get("live_combinatronic"),
        "motto": "Live combinatronic — map placements, snap on fingerprint, delta only on new.",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    force = "--force" in sys.argv
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("capture", "seed", "record"):
        print(json.dumps(capture_placements(source="manual"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("snap", "live", "fast"):
        print(json.dumps(snap(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("delta", "delta_sync", "sync"):
        print(json.dumps(delta_sync(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "map":
        print(json.dumps(_map_state(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "snap", "capture", "delta", "map"],
        "flags": ["--force"],
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())