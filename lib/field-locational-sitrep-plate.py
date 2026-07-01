#!/usr/bin/env pythong
"""Locational sitrep plate — operator place, spatial existence, field lattice, threat geometry."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "NewLatest" else INSTALL.parent)))
DOCTRINE = INSTALL / "data" / "field-locational-sitrep-doctrine.json"
PLATE = STATE / "field-locational-sitrep-plate.json"
LEDGER = STATE / "field-locational-sitrep-ledger.jsonl"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _chain_hash(material: Any, prev: str = "") -> str:
    blob = json.dumps(material, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{prev}|{blob}".encode()).hexdigest()


def _import_call(script: Path, name: str, fn: str, *args: Any, **kwargs: Any) -> Any:
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        call = getattr(mod, fn, None)
        if not callable(call):
            return None
        return call(*args, **kwargs)
    except Exception:
        return None


def _operator_slice() -> dict[str, Any]:
    doc = _import_call(INSTALL / "lib" / "operator-location.py", "op_loc", "panel_json") or _load(
        STATE / "operator-location.json", {}
    )
    lat, lon = doc.get("lat"), doc.get("lon")
    ready = lat is not None and lon is not None and not (float(lat or 0) == 0 and float(lon or 0) == 0)
    return {
        "available": True,
        "gps_ready": ready,
        "lat": lat,
        "lon": lon,
        "label": doc.get("label") or "",
        "address": doc.get("address") or "",
        "source": doc.get("source") or "unset",
        "wireless": bool(doc.get("wireless")),
        "iface": doc.get("iface"),
        "kind": "this_one" if ready else "unset",
        "census_geographies": doc.get("census_geographies") or [],
        "country_code": doc.get("country_code") or "",
    }


def _spatial_existence_slice() -> dict[str, Any]:
    result = _import_call(
        INSTALL / "lib" / "ironclad-spatial-existence.py",
        "spatial_existence",
        "correlate_this_that",
    )
    if not result:
        panel = _load(STATE / "ironclad-spatial-existence-panel.json", {})
        result = panel.get("correlate") or panel.get("slice") or {}
    return {
        "available": bool(result),
        "pass_ok": bool(result.get("pass_ok")),
        "this_one": (result.get("this_one") or {}).get("kind"),
        "that_one": (result.get("that_one") or {}).get("kind"),
        "existence_correlation": result.get("existence_correlation"),
        "citation": result.get("citation") or "ironclad:spatial_existence:1",
        "meld_citation": result.get("meld_citation") or "ironclad:meld:2",
    }


def _field_lattice_slice(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        _import_call(INSTALL / "lib" / "field-spatial-cognition.py", "field_spatial", "build_spatial", write=True)
    doc = _load(STATE / "field-spatial-panel.json", {}) or _load(STATE / "field-spatial-runtime.json", {})
    mv = doc.get("movement_vector") or {}
    return {
        "available": bool(doc),
        "dimensions": doc.get("dimensions") or "3D+T",
        "total_energy": doc.get("total_energy"),
        "delta_t": doc.get("delta_t"),
        "geometry": mv.get("geometry") or "stable",
        "approach": bool(mv.get("approach")),
        "recede": bool(mv.get("recede")),
        "bearing_deg": mv.get("bearing_deg"),
        "trespass": bool(mv.get("trespass")),
        "target_count": doc.get("target_count") or 0,
        "nearest_threat": doc.get("nearest_threat"),
        "operator": doc.get("operator") or {},
        "eye_live": doc.get("eye_live"),
        "ear_live": doc.get("ear_live"),
    }


def _threat_geometry_slice() -> dict[str, Any]:
    panel = _load(STATE / "threat-panel.json", {})
    ha = panel.get("host_attacks") or {}
    pins = ha.get("pins") or ha.get("active") or []
    hot = int((panel.get("field_command") or {}).get("pulse", {}).get("host_hot") or 0)
    rf = panel.get("field_rf") or {}
    return {
        "available": bool(panel),
        "host_hot": hot,
        "pin_count": len(pins) if isinstance(pins, list) else int(ha.get("count") or 0),
        "rf_bursts": len(rf.get("recent_bursts") or []),
        "field_rf_level": rf.get("level"),
    }


def _physics_slice() -> dict[str, Any]:
    doc = _load(STATE / "field-physics-witness.json", {})
    if not doc.get("thermal"):
        doc = _import_call(INSTALL / "lib" / "field-physics-witness.py", "fpw", "witness", sections=False) or {}
    th = doc.get("thermal") or {}
    return {
        "available": bool(th),
        "cool_ok": th.get("cool_ok"),
        "headroom_pct": th.get("headroom_pct"),
        "level": th.get("level"),
    }


def _sitrep_summary(
    operator: dict[str, Any],
    spatial: dict[str, Any],
    lattice: dict[str, Any],
    threat: dict[str, Any],
) -> str:
    if not operator.get("gps_ready"):
        return "Locational sitrep: operator place unset — set GPS or address before trusting motion posture."
    label = operator.get("label") or f"{operator.get('lat')}, {operator.get('lon')}"
    place = f"This one at {label}"
    if not spatial.get("pass_ok"):
        place += " — spatial existence gate watch (correlate before that one influences trust)."
    else:
        place += " — this one witnessed."
    geom = lattice.get("geometry") or "stable"
    if lattice.get("approach"):
        place += f" Nearest threat geometry {geom} — approach bearing {lattice.get('bearing_deg', '—')}°."
    elif lattice.get("trespass"):
        place += f" Trespass flagged — geometry {geom}."
    else:
        place += f" Field lattice stable ({geom})."
    if threat.get("host_hot", 0) > 0:
        place += f" Host heat {threat['host_hot']}."
    return place


def gather_sitrep(*, refresh_spatial: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    operator = _operator_slice()
    spatial = _spatial_existence_slice()
    lattice = _field_lattice_slice(refresh=refresh_spatial and bool(
        (doctrine.get("policy") or {}).get("refresh_spatial_on_cycle", True)
    ))
    threat = _threat_geometry_slice()
    physics = _physics_slice()
    census = {
        "available": bool(operator.get("census_geographies")),
        "geographies": operator.get("census_geographies") or [],
        "country_code": operator.get("country_code") or "",
    }
    sections = {
        "operator": {**operator, "consumer": "operator_location"},
        "spatial_existence": {**spatial, "consumer": "ironclad_spatial_existence"},
        "field_lattice": {**lattice, "consumer": "field_spatial_cognition"},
        "threat_geometry": {**threat, "consumer": "threat_panel"},
        "census": {**census, "consumer": "census_field_populate"},
        "physics_thermal": {**physics, "consumer": "field_physics_witness"},
        "compat_layers": {
            "available": operator.get("gps_ready") and spatial.get("pass_ok"),
            "consumer": "field_compatibility_layers",
        },
        "panel": {"available": True, "manifest_api": "/api/locational-sitrep"},
    }
    for sid, row in sections.items():
        if "available" not in row:
            row["available"] = True
    summary = _sitrep_summary(operator, spatial, lattice, threat)
    return {
        "schema": "field-locational-sitrep/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "meld_citation": doctrine.get("meld_citation") or "ironclad:meld:2",
        "ironclad_ref": doctrine.get("ironclad_ref") or "ironclad:spatial_existence:1",
        "summary": summary,
        "operator": operator,
        "spatial_existence": spatial,
        "field_lattice": lattice,
        "threat_geometry": threat,
        "physics_thermal": physics,
        "census": census,
        "sections": sections,
        "this_one": {
            "kind": "this_one" if operator.get("gps_ready") and spatial.get("pass_ok") else "watch",
            "lat": operator.get("lat"),
            "lon": operator.get("lon"),
            "label": operator.get("label"),
        },
        "movement": {
            "geometry": lattice.get("geometry"),
            "approach": lattice.get("approach"),
            "bearing_deg": lattice.get("bearing_deg"),
            "trespass": lattice.get("trespass"),
        },
    }


def build_plate(*, write: bool = True, refresh_spatial: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    sitrep = gather_sitrep(refresh_spatial=refresh_spatial)
    prev = str(_load(PLATE, {}).get("chain_hash") or "")
    operator = sitrep.get("operator") or {}
    spatial = sitrep.get("spatial_existence") or {}
    lattice = sitrep.get("field_lattice") or {}

    plated = bool(operator.get("gps_ready")) and bool(spatial.get("available"))
    if plated and spatial.get("pass_ok") and not lattice.get("trespass"):
        verdict = "GREEN"
    elif operator.get("gps_ready"):
        verdict = "WATCH"
    else:
        verdict = "HOLD"

    material = {
        "summary": sitrep.get("summary"),
        "this_one": sitrep.get("this_one"),
        "movement": sitrep.get("movement"),
        "sections_live": sum(1 for s in (sitrep.get("sections") or {}).values() if s.get("available")),
        "pass_ok": spatial.get("pass_ok"),
    }
    chain = _chain_hash(material, prev)

    doc = {
        "schema": "field-locational-sitrep-plate/v1",
        "updated": sitrep.get("updated"),
        "title": doctrine.get("title") or "Locational sitrep plate",
        "motto": doctrine.get("motto") or "",
        "meld_citation": doctrine.get("meld_citation") or "ironclad:meld:2",
        "ironclad_ref": doctrine.get("ironclad_ref") or "ironclad:spatial_existence:1",
        "plate_not_wire": True,
        "ok": plated,
        "plated": plated,
        "verdict": verdict,
        "chain_hash": chain,
        "sitrep": sitrep,
        "summary": sitrep.get("summary"),
        "sections": sitrep.get("sections") or {},
        "this_one": sitrep.get("this_one"),
        "movement": sitrep.get("movement"),
        "spatial_pass_ok": spatial.get("pass_ok"),
        "gps_ready": operator.get("gps_ready"),
    }
    if write:
        _save(PLATE, doc)
        _append_ledger({
            "ts": doc["updated"],
            "ok": doc.get("ok"),
            "verdict": verdict,
            "chain_hash": chain,
            "gps_ready": operator.get("gps_ready"),
            "pass_ok": spatial.get("pass_ok"),
            "geometry": (sitrep.get("movement") or {}).get("geometry"),
        })
    return doc


def cycle() -> dict[str, Any]:
    return build_plate(write=True, refresh_spatial=True)


def attach_to_sections(sections: dict[str, Any], *, plate: dict[str, Any] | None = None) -> dict[str, Any]:
    plate = plate or _load(PLATE, {}) or build_plate(write=False, refresh_spatial=False)
    sitrep = plate.get("sitrep") or plate
    loc = {
        "summary": plate.get("summary") or sitrep.get("summary"),
        "gps_ready": plate.get("gps_ready"),
        "spatial_pass_ok": plate.get("spatial_pass_ok"),
        "this_one": plate.get("this_one") or sitrep.get("this_one"),
        "movement": plate.get("movement") or sitrep.get("movement"),
    }
    out: dict[str, Any] = {}
    for sid, row in sections.items():
        merged = dict(row) if isinstance(row, dict) else {"value": row}
        merged["locational"] = loc
        out[sid] = merged
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status", "sitrep"):
        print(json.dumps(build_plate(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "plate", "meld", "employ"):
        print(json.dumps(cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gather":
        refresh = "--no-refresh" not in sys.argv
        print(json.dumps(gather_sitrep(refresh_spatial=refresh), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-locational-sitrep-plate.py [json|cycle|gather|sitrep]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())