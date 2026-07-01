#!/usr/bin/env pythong
"""Hostess 7 positional awareness — location, heading, movement always known; P1 until familiar."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-positional-awareness-doctrine.json"
PANEL = STATE / "hostess7-positional-awareness-panel.json"
FAMILIARITY = STATE / "hostess7-positional-familiarity.json"
LEDGER = STATE / "hostess7-positional-awareness.jsonl"


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_pos", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _import_call(rel: str, name: str, fn: str, *args: Any, **kwargs: Any) -> Any:
    mod = _import_mod(name, rel)
    if not mod:
        return None
    call = getattr(mod, fn, None)
    if not callable(call):
        return None
    try:
        return call(*args, **kwargs)
    except Exception:
        return None


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def _object_id(kind: str, key: str) -> str:
    raw = f"{kind}:{key}".strip().lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _has_coords(row: dict[str, Any]) -> bool:
    lat = row.get("lat") or row.get("latitude")
    lon = row.get("lon") or row.get("longitude")
    if lat is None or lon is None:
        return False
    try:
        return not (float(lat) == 0.0 and float(lon) == 0.0)
    except (TypeError, ValueError):
        return False


def _heading_resolved(val: Any) -> bool:
    if val is None:
        return False
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False


def _load_familiarity() -> dict[str, Any]:
    doc = _load(FAMILIARITY, {"objects": {}, "updated": None})
    if "objects" not in doc:
        doc["objects"] = {}
    return doc


def _save_familiarity(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save(FAMILIARITY, doc)


def _touch_familiarity(
    obj_id: str,
    *,
    label: str,
    kind: str,
    familiar: bool = False,
    location_resolved: bool = False,
    heading_resolved: bool = False,
) -> dict[str, Any]:
    reg = _load_familiarity()
    objects = reg.setdefault("objects", {})
    row = objects.get(obj_id) or {
        "id": obj_id,
        "label": label,
        "kind": kind,
        "familiar": False,
        "sightings": 0,
        "first_seen": _now(),
    }
    row["label"] = label or row.get("label") or obj_id
    row["kind"] = kind or row.get("kind") or "positional"
    row["sightings"] = int(row.get("sightings") or 0) + 1
    row["last_seen"] = _now()
    row["location_resolved"] = location_resolved or row.get("location_resolved")
    row["heading_resolved"] = heading_resolved or row.get("heading_resolved")
    if familiar:
        row["familiar"] = True
        row["familiarized_at"] = _now()
    doctrine = load_doctrine()
    rule = (doctrine.get("unfamiliar_priority") or {})
    threshold = int(rule.get("auto_familiarize_after_sightings") or 3)
    requires = rule.get("requires_for_auto") or []
    auto_ok = True
    if "location_resolved" in requires:
        auto_ok = auto_ok and bool(row.get("location_resolved"))
    if "heading_resolved" in requires:
        auto_ok = auto_ok and bool(row.get("heading_resolved"))
    if "label_or_ip" in requires:
        auto_ok = auto_ok and bool(row.get("label")) and row["label"] != obj_id
    if not row.get("familiar") and auto_ok and int(row.get("sightings") or 0) >= threshold:
        row["familiar"] = True
        row["familiarized_at"] = _now()
        row["auto_familiarized"] = True
    objects[obj_id] = row
    _save_familiarity(reg)
    return row


def gather_operator_posture() -> dict[str, Any]:
    op = _import_call("lib/operator-location.py", "op_loc", "panel_json") or _load(
        STATE / "operator-location.json", {}
    )
    lat, lon = op.get("lat"), op.get("lon")
    gps_ready = lat is not None and lon is not None and not (float(lat or 0) == 0 and float(lon or 0) == 0)
    return {
        "location_known": gps_ready,
        "lat": lat,
        "lon": lon,
        "label": op.get("label") or op.get("address") or "",
        "source": op.get("source") or "unset",
        "address": op.get("address") or "",
        "wireless": bool(op.get("wireless")),
        "census_geographies": op.get("census_geographies") or [],
    }


def gather_heading_movement() -> dict[str, Any]:
    spatial_doc = _load(STATE / "field-spatial-panel.json", {}) or _load(
        STATE / "field-spatial-runtime.json", {}
    )
    if not spatial_doc:
        built = _import_call("lib/field-spatial-cognition.py", "field_spatial", "build_spatial", write=False)
        spatial_doc = built or {}

    mv = spatial_doc.get("movement_vector") or {}
    bearing = mv.get("bearing_deg")
    geometry = str(mv.get("geometry") or "stable")
    approach = bool(mv.get("approach"))
    recede = bool(mv.get("recede"))
    stable = bool(mv.get("stable")) or (not approach and not recede)

    sitrep = _import_call(
        "lib/field-locational-sitrep-plate.py", "loc_sitrep", "gather_sitrep", refresh_spatial=False
    ) or _load(STATE / "field-locational-sitrep-plate.json", {}).get("sitrep") or {}
    sitrep_mv = sitrep.get("movement") or {}
    if bearing is None:
        bearing = sitrep_mv.get("bearing_deg")

    sense = _load(STATE / "field-sense-package-panel.json", {})
    sense_brg = (sense.get("localization") or {}).get("bearing_deg")
    if bearing is None and sense_brg is not None:
        bearing = sense_brg

    humanoid = _load(STATE / "humanoid-motion-runtime.json", {})
    motion_mode = geometry
    active_skill = humanoid.get("active_skill") or humanoid.get("policy")
    if active_skill:
        motion_mode = f"{geometry}+{active_skill}"

    movement_state = "stable"
    if approach:
        movement_state = "approach"
    elif recede:
        movement_state = "recede"

    return {
        "heading_known": _heading_resolved(bearing),
        "heading_deg": bearing,
        "movement_known": bool(spatial_doc) or bool(sitrep),
        "movement": movement_state,
        "movement_mode_known": bool(geometry),
        "movement_mode": motion_mode,
        "geometry": geometry,
        "approach": approach,
        "recede": recede,
        "stable": stable,
        "trespass": bool(mv.get("trespass")),
        "delta_t": spatial_doc.get("delta_t"),
        "target_count": spatial_doc.get("target_count") or 0,
    }


def _targets_from_threat_panel() -> list[dict[str, Any]]:
    panel = _load(STATE / "threat-panel.json", {})
    ha = panel.get("host_attacks") or {}
    pts = ha.get("points") or ha.get("hosts") or ha.get("pins") or []
    if isinstance(pts, dict):
        pts = list(pts.values())
    out: list[dict[str, Any]] = []
    for p in pts if isinstance(pts, list) else []:
        if not isinstance(p, dict):
            continue
        ip = str(p.get("ip") or p.get("host") or "").strip()
        kind = str(p.get("kind") or p.get("vector") or "hostile")
        lat = p.get("lat") or p.get("latitude")
        lon = p.get("lon") or p.get("longitude")
        key = ip or f"{lat},{lon}" or p.get("id") or kind
        out.append({
            "source": "threat_panel",
            "kind": kind,
            "label": ip or str(p.get("label") or key)[:80],
            "ip": ip or None,
            "lat": lat,
            "lon": lon,
            "bearing_deg": p.get("bearing_deg"),
            "heat": p.get("heat") or p.get("threat_heat"),
            "object_id": _object_id(kind, key),
        })
    return out


def _targets_from_registry() -> list[dict[str, Any]]:
    reg = _load(STATE / "hostess7-targets-registry.json", {"targets": {}})
    out: list[dict[str, Any]] = []
    for tid, row in (reg.get("targets") or {}).items():
        if not isinstance(row, dict):
            continue
        if row.get("status") == "dead":
            continue
        geo = row.get("geo") if isinstance(row.get("geo"), dict) else {}
        lat = geo.get("lat") or geo.get("latitude")
        lon = geo.get("lon") or geo.get("longitude")
        ip = str(row.get("ip") or "").strip()
        kind = str(row.get("mechanism") or row.get("TARGET") or "target").upper()
        label = str(row.get("subject") or ip or tid)[:120]
        key = str(row.get("target_id") or tid or ip)
        out.append({
            "source": "hostess7-targets",
            "kind": kind,
            "label": label,
            "ip": ip or None,
            "lat": lat,
            "lon": lon,
            "bearing_deg": geo.get("bearing_deg"),
            "target_id": key,
            "object_id": _object_id(kind.lower(), key),
        })
    return out


def _humanoid_opponents() -> list[dict[str, Any]]:
    panel = _load(STATE / "humanoid-motion-panel.json", {})
    opponents = panel.get("opponents") or panel.get("arena_opponents") or []
    out: list[dict[str, Any]] = []
    for o in opponents if isinstance(opponents, list) else []:
        if not isinstance(o, dict):
            continue
        oid = str(o.get("id") or o.get("label") or "opponent")
        out.append({
            "source": "humanoid_motion",
            "kind": str(o.get("kind") or "opponent"),
            "label": str(o.get("label") or oid)[:80],
            "ip": o.get("ip"),
            "lat": o.get("lat"),
            "lon": o.get("lon"),
            "bearing_deg": o.get("bearing_deg"),
            "geometry": o.get("geometry"),
            "object_id": _object_id("opponent", oid),
        })
    return out


def collect_positionals() -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for row in _targets_from_threat_panel() + _targets_from_registry() + _humanoid_opponents():
        oid = row.get("object_id") or _object_id(row.get("kind", "positional"), row.get("label", ""))
        if oid in seen:
            continue
        seen.add(oid)
        loc_ok = _has_coords(row)
        hdg_ok = _heading_resolved(row.get("bearing_deg"))
        fam = _touch_familiarity(
            oid,
            label=str(row.get("label") or oid),
            kind=str(row.get("kind") or "positional"),
            location_resolved=loc_ok,
            heading_resolved=hdg_ok,
        )
        merged.append({
            **row,
            "object_id": oid,
            "location_resolved": loc_ok,
            "heading_resolved": hdg_ok,
            "familiar": bool(fam.get("familiar")),
            "sightings": fam.get("sightings"),
            "priority": 1 if not fam.get("familiar") else 5,
            "mission": "IDENTIFY" if not fam.get("familiar") else "WATCH",
        })
    merged.sort(key=lambda r: (r.get("priority", 9), -float(r.get("heat") or 0)))
    return merged


def posture_verdict(operator: dict[str, Any], kinematics: dict[str, Any]) -> str:
    if not operator.get("location_known"):
        return "HOLD"
    if not kinematics.get("heading_known") or not kinematics.get("movement_known"):
        return "WATCH"
    if kinematics.get("trespass"):
        return "ALERT"
    return "GREEN"


def identify_missions(positionals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in positionals:
        if row.get("familiar"):
            continue
        gaps = []
        if not row.get("location_resolved"):
            gaps.append("location")
        if not row.get("heading_resolved"):
            gaps.append("heading")
        if not row.get("label") or row.get("label") == row.get("object_id"):
            gaps.append("label")
        out.append({
            "lane": "positional_identify",
            "rank": 0,
            "priority": 1,
            "title": f"IDENTIFY — {row.get('label') or row.get('object_id')}",
            "detail": (
                f"Priority 1 until familiar · gaps: {', '.join(gaps) or 'confirm identity'} · "
                f"kind={row.get('kind')} · source={row.get('source')}"
            )[:500],
            "source": "hostess7-positional-awareness",
            "mechanism": "IDENTIFY",
            "meta": {
                "object_id": row.get("object_id"),
                "kind": row.get("kind"),
                "familiar": False,
                "gaps": gaps,
                "ip": row.get("ip"),
                "lat": row.get("lat"),
                "lon": row.get("lon"),
                "bearing_deg": row.get("bearing_deg"),
            },
        })
    return out


def gather_awareness(*, refresh_spatial: bool = False) -> dict[str, Any]:
    doctrine = load_doctrine()
    if refresh_spatial:
        _import_call("lib/field-spatial-cognition.py", "field_spatial", "build_spatial", write=True)
        _import_call("lib/field-locational-sitrep-plate.py", "loc_sitrep", "build_plate", write=True)

    operator = gather_operator_posture()
    kinematics = gather_heading_movement()
    positionals = collect_positionals()
    unfamiliar = [p for p in positionals if not p.get("familiar")]
    verdict = posture_verdict(operator, kinematics)

    always = doctrine.get("always_known") or {}
    posture = {
        "location_known": operator.get("location_known"),
        "heading_known": kinematics.get("heading_known"),
        "movement_known": kinematics.get("movement_known"),
        "movement_mode_known": kinematics.get("movement_mode_known"),
        "all_known": (
            operator.get("location_known")
            and kinematics.get("heading_known")
            and kinematics.get("movement_known")
            and kinematics.get("movement_mode_known")
        ),
    }

    summary_parts = []
    if operator.get("location_known"):
        summary_parts.append(f"This one at {operator.get('label') or operator.get('lat')},{operator.get('lon')}")
    else:
        summary_parts.append("Location unset — HOLD until GPS or address seals")
    if kinematics.get("heading_known"):
        summary_parts.append(f"Heading {kinematics.get('heading_deg')}°")
    else:
        summary_parts.append("Heading unresolved — WATCH")
    summary_parts.append(
        f"Movement {kinematics.get('movement')} · mode {kinematics.get('movement_mode')}"
    )
    if unfamiliar:
        summary_parts.append(f"{len(unfamiliar)} object(s) priority 1 until familiarized")

    return {
        "schema": "hostess7-positional-awareness/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "verdict": verdict,
        "posture": posture,
        "always_known_rule": always,
        "operator": operator,
        "kinematics": kinematics,
        "positionals": positionals,
        "positional_count": len(positionals),
        "unfamiliar_count": len(unfamiliar),
        "unfamiliar_priority": (doctrine.get("unfamiliar_priority") or {}).get("priority", 1),
        "identify_missions": identify_missions(positionals),
        "summary": " — ".join(summary_parts),
    }


def build_panel(*, write: bool = True, refresh_spatial: bool = False) -> dict[str, Any]:
    doctrine = load_doctrine()
    awareness = gather_awareness(refresh_spatial=refresh_spatial)
    doc = {
        "schema": "hostess7-positional-awareness-panel/v1",
        "updated": awareness.get("updated"),
        "motto": doctrine.get("motto"),
        "api": doctrine.get("api"),
        "ok": awareness.get("posture", {}).get("all_known", False),
        "verdict": awareness.get("verdict"),
        "awareness": awareness,
        "summary": awareness.get("summary"),
    }
    if write:
        _save(PANEL, doc)
        _append({
            "verdict": doc.get("verdict"),
            "ok": doc.get("ok"),
            "unfamiliar_count": awareness.get("unfamiliar_count"),
            "positional_count": awareness.get("positional_count"),
            "all_known": awareness.get("posture", {}).get("all_known"),
        })
    return doc


def format_output(doc: dict[str, Any] | None = None) -> str:
    doc = doc or build_panel(write=False)
    aw = doc.get("awareness") or doc
    lines = [
        "=== Hostess 7 — Positional Awareness ===",
        f"Updated: {aw.get('updated', doc.get('updated', '—'))}",
        f"Verdict: {aw.get('verdict', doc.get('verdict', '—'))}",
        f"Summary: {aw.get('summary', doc.get('summary', ''))}",
        "",
        "— Always known —",
        f"  Location: {'YES' if (aw.get('posture') or {}).get('location_known') else 'NO'}",
        f"  Heading: {'YES' if (aw.get('posture') or {}).get('heading_known') else 'NO'}",
        f"  Movement: {'YES' if (aw.get('posture') or {}).get('movement_known') else 'NO'}",
        f"  Movement mode: {'YES' if (aw.get('posture') or {}).get('movement_mode_known') else 'NO'}",
        "",
        f"— Positionals ({aw.get('unfamiliar_count', 0)} unfamiliar · P1 until familiar) —",
    ]
    for p in (aw.get("positionals") or [])[:24]:
        flag = "P1 IDENTIFY" if not p.get("familiar") else "familiar"
        loc = f"{p.get('lat')},{p.get('lon')}" if p.get("lat") is not None else "—"
        lines.append(
            f"  [{flag}] {p.get('label')} · {p.get('kind')} · loc={loc} · brg={p.get('bearing_deg', '—')}°"
        )
    if not aw.get("positionals"):
        lines.append("  (no positionals tracked)")
    lines.append("")
    lines.append("Doctrine: data/hostess7-positional-awareness-doctrine.json")
    return "\n".join(lines)


def mark_familiar(object_id: str, *, familiar: bool = True) -> dict[str, Any]:
    reg = _load_familiarity()
    objects = reg.setdefault("objects", {})
    row = objects.get(object_id)
    if not row:
        row = {"id": object_id, "label": object_id, "kind": "positional", "sightings": 0}
    row["familiar"] = familiar
    if familiar:
        row["familiarized_at"] = _now()
        row["operator_marked"] = True
    objects[object_id] = row
    _save_familiarity(reg)
    return {"ok": True, "object_id": object_id, "familiar": familiar}


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Hostess 7 positional awareness")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--id", dest="obj_id", default="")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("awareness", "gather"):
        refresh = "--refresh" in sys.argv
        print(json.dumps(gather_awareness(refresh_spatial=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("output", "text", "report"):
        print(format_output())
        return 0
    if cmd in ("familiar", "familiarize"):
        oid = args.obj_id.strip() or (sys.argv[2] if len(sys.argv) > 2 else "")
        if not oid:
            print(json.dumps({"ok": False, "error": "object_id required"}, ensure_ascii=False))
            return 1
        print(json.dumps(mark_familiar(oid), ensure_ascii=False, indent=2))
        return 0
    if cmd == "missions":
        aw = gather_awareness()
        print(json.dumps({"identify_missions": aw.get("identify_missions") or []}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-positional-awareness.py [panel|awareness|output|missions|familiar --id=OBJ]",
        "api": "/api/hostess7/positional-awareness",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())