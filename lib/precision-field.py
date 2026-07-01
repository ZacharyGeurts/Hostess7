#!/usr/bin/env pythong
"""Precision field — new map & spiderweb data with sub-micron detected GPS placement."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
REGISTRY_JSON = STATE / "precision-field-registry.json"
PLACEMENTS_JSON = STATE / "precision-placements.json"
PANEL_CACHE = STATE / "precision-field-panel.json"
HOST_ATTACKS = STATE / "host-attacks.json"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _collect_entities() -> list[dict[str, Any]]:
    gp = _mod("gps_precision", "gps-precision.py")
    anchor = gp._load_anchor([])
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any], section: str) -> None:
        eid = str(row.get("id") or row.get("ip") or f"{section}_{len(entities)}")
        if eid in seen:
            return
        seen.add(eid)
        enriched = gp.enrich_entity({**row, "section": section, "id": eid}, anchor)
        enriched["id"] = eid
        entities.append(enriched)

    reg = _load_json(STATE / "universal-field-registry.json", {})
    for section, key in (("homes", "home"), ("internet", "internet"), ("mobile", "mobile"), ("batteries", "battery")):
        for row in reg.get(section) or []:
            if isinstance(row, dict) and row.get("lat") is not None:
                add(row, key)

    sw = _load_json(STATE / "terror-spiderweb-panel.json", {})
    for n in sw.get("nodes") or []:
        if isinstance(n, dict) and n.get("lat") is not None:
            add(n, n.get("kind") or "node")

    thermal = _load_json(STATE / "thermal-earth-field.json", {})
    for b in thermal.get("bodies") or []:
        if isinstance(b, dict) and b.get("lat") is not None:
            add(b, "thermal")

    manual = _load_json(PLACEMENTS_JSON, {"placements": []})
    for p in manual.get("placements") or []:
        if isinstance(p, dict):
            add(p, p.get("section") or "manual")

    ha = _load_json(HOST_ATTACKS, {})
    for p in ha.get("points") or []:
        if not isinstance(p, dict) or p.get("lat") is None:
            continue
        killed = p.get("target_status") == "killed" or p.get("disabled_permanent")
        add({
            "id": p.get("id") or p.get("ip"),
            "ip": p.get("ip"),
            "label": p.get("label") or p.get("ip"),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
            "kind": "hostile" if killed else (p.get("kind") or "internet"),
            "section": "internet",
            "heat": p.get("heat"),
            "target_status": p.get("target_status"),
        }, "hostile" if killed else "internet")

    return entities


def _build_edges(entities: list[dict[str, Any]], anchor: dict[str, Any]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_id = {e["id"]: e for e in entities if e.get("id")}
    primary = next((e for e in entities if e.get("role") == "home" or e.get("section") == "home"), None)
    if not primary:
        primary = next((e for e in entities if e.get("anchor_id") == "operator"), entities[0] if entities else None)
    if not primary:
        return edges
    pid = primary.get("id")
    for e in entities:
        eid = e.get("id")
        if not eid or eid == pid:
            continue
        kind = "terror" if e.get("kind") in ("terror", "hostile") or e.get("section") == "internet" and e.get("kind") == "terror" else "link"
        if e.get("section") in ("home", "neighbor", "gov", "tagged") or e.get("role") in ("neighbor", "gov"):
            kind = "neighbor"
        edges.append({
            "id": f"pe:{pid}:{eid}",
            "from": pid,
            "to": eid,
            "kind": kind,
            "precision": "sub_micron",
        })
    return edges


def place_entity(body: dict[str, Any]) -> dict[str, Any]:
    gp = _mod("gps_precision", "gps-precision.py")
    anchor = gp._load_anchor()
    lat = body.get("lat")
    lon = body.get("lon")
    if lat is None and lon is None and body.get("enu_e_nm") is None:
        return {"ok": False, "error": "missing_coordinates"}
    use_enu = body.get("enu_e_nm") is not None and body.get("enu_n_nm") is not None
    row = gp.placement_from_detected(
        lat if lat is not None else anchor["lat"],
        lon if lon is not None else anchor["lon"],
        anchor=anchor if use_enu else None,
        east_nm=body.get("enu_e_nm") if use_enu else None,
        north_nm=body.get("enu_n_nm") if use_enu else None,
        up_nm=body.get("enu_u_nm") if use_enu else None,
        source=body.get("source") or "manual_place",
        label=str(body.get("label") or body.get("id") or "placed"),
    )
    row["id"] = str(body.get("id") or f"place_{row['lat_i'][:12]}")
    row["section"] = body.get("section") or "manual"
    row["kind"] = body.get("kind") or "placed"
    doc = _load_json(PLACEMENTS_JSON, {"placements": [], "updated": None})
    placements = [p for p in (doc.get("placements") or []) if p.get("id") != row["id"]]
    placements.append(row)
    doc["placements"] = placements[-500:]
    doc["updated"] = _now()
    _save_json(PLACEMENTS_JSON, doc)
    return {"ok": True, "placement": row}


def build_precision_field() -> dict[str, Any]:
    gp = _mod("gps_precision", "gps-precision.py")
    entities = _collect_entities()
    anchor = gp._load_anchor(entities)
    if anchor.get("id") != "operator":
        for ent in entities:
            gp.enrich_entity(ent, anchor)
    edges = _build_edges(entities, anchor)

    placed = [e for e in entities if e.get("placed")]
    doc = {
        "schema": "precision-field/v1",
        "updated": _now(),
        "motto": "Precision map & spiderweb — every detection placed at sub-micron GPS.",
        "tagline": "Detected coordinates to 15 decimal degrees · ENU nanometers · ~0.11 nm LSB.",
        "anchor": anchor,
        "gps": gp.panel_json(),
        "entities": entities,
        "edges": edges,
        "stats": {
            "total": len(entities),
            "placed": len(placed),
            "sub_micron": sum(1 for e in entities if e.get("precision") == "sub_micron"),
            "edges": len(edges),
            "manual_placements": len(_load_json(PLACEMENTS_JSON, {}).get("placements") or []),
        },
        "views": {
            "precision_map": {"engine": "leaflet-enu-nm", "max_zoom": 28, "crs": "enu_nanometer"},
            "precision_spiderweb": {"engine": "canvas-submicron", "edge_precision": "sub_micron"},
        },
    }
    _save_json(REGISTRY_JSON, doc)
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_CACHE.is_file():
        doc = _load_json(PANEL_CACHE, {})
        if doc.get("updated") and (doc.get("entities") or doc.get("stats", {}).get("total", 0) > 0):
            return doc
    return {
        "schema": "precision-field/v1",
        "mode": "idle",
        "entities": [],
        "edges": [],
        "stats": {"idle": True, "total": 0},
        "motto": "Rebuild precision field after spiderweb survey — operator-triggered only.",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_precision_field(), ensure_ascii=False))
        return 0
    if cmd == "place" and len(sys.argv) >= 2:
        body = json.loads(sys.argv[2] if sys.argv[2] != "-" else sys.stdin.read())
        print(json.dumps(place_entity(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: precision-field.py [json|build|place JSON]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())