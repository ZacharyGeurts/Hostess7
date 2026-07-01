#!/usr/bin/env pythong
"""Final_Eye threat chamber — track every eye hazard; prevent in hostile; report Hostess 7."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE = fcc.STATE
DOCTRINE = INSTALL / "data" / "field-eye-threat-doctrine.json"
ENTITY = INSTALL / "Final_Eye" / "data" / "entity-eyeball.json"
PANEL = STATE / "field-eye-threat-panel.json"
LEDGER = STATE / "field-eye-threat-ledger.jsonl"
HOSTILE = STATE / "field-eye-threat-hostile.json"


def _entity_forward() -> dict[str, Any]:
    if not ENTITY.is_file():
        return {}
    doc = fcc.load(ENTITY, {})
    return doc.get("forward") or {}


def threat_catalog() -> dict[str, Any]:
    """Merge doctrine threats with entity-eyeball lie_markers and weapon map."""
    doc = fcc.load(DOCTRINE, {})
    forward = _entity_forward()
    lie_markers = set(forward.get("lie_markers") or [])
    weapon_map = dict(forward.get("threat_weapon_map") or {})
    threats: list[dict[str, Any]] = []
    for row in doc.get("threats") or []:
        tid = str(row.get("id") or "")
        merged = dict(row)
        merged["lie_marker"] = tid in lie_markers
        merged["weapon"] = weapon_map.get(tid) or row.get("weapon")
        threats.append(merged)
    for marker in lie_markers:
        if not any(t.get("id") == marker for t in threats):
            threats.append({
                "id": marker,
                "label": marker.replace("_", " ").title(),
                "category": "digital_path",
                "hostile": True,
                "lie_marker": True,
                "weapon": weapon_map.get(marker),
                "source": "entity-eyeball",
            })
    return {
        "schema": "field-eye-threat-catalog/v1",
        "updated": fcc.ts(),
        "count": len(threats),
        "categories": doc.get("categories") or [],
        "threats": threats,
        "lie_markers": sorted(lie_markers),
        "threat_weapon_map": weapon_map,
    }


def _append_ledger(row: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": fcc.ts()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def report_hostess7(
    threats: list[dict[str, Any]],
    *,
    event: str = "detect",
    hostile: bool = False,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send eye threat recognition to Hostess 7 growth ledger."""
    doctrine = fcc.load(DOCTRINE, {})
    h7_cfg = doctrine.get("hostess7") or {}
    ids = [str(t.get("id") or t) for t in threats]
    labels = [str(t.get("label") or t.get("id") or t) for t in threats if isinstance(t, dict)]
    text = (
        f"Eye threat {event}: {', '.join(labels[:8])}"
        + (f" (+{len(labels) - 8} more)" if len(labels) > 8 else "")
        + (" — HOSTILE ENVIRONMENT" if hostile else "")
    )
    out: dict[str, Any] = {"ok": False, "shared": False, "consumer": "Hostess7"}
    growth = fcc.mod("fet_growth", "hostess7-growth.py")
    if growth and hasattr(growth, "record_learning"):
        try:
            result = growth.record_learning(
                str(h7_cfg.get("growth_kind") or "eye_threat_alert"),
                text,
                source="final_eye_threat_chamber",
                meta={
                    "event": event,
                    "hostile": hostile,
                    "threat_ids": ids,
                    "threat_count": len(ids),
                    "sense_lane": h7_cfg.get("sense_lane", "eye"),
                    **(meta or {}),
                },
                truth_gate=True,
            )
            out = {"ok": bool(result.get("ok")), "shared": bool(result.get("ok")), "consumer": "Hostess7", "growth": result}
        except Exception as exc:
            out = {"ok": False, "shared": False, "error": str(exc)}
    sense = fcc.mod("fet_sense", "hostess7-sense-core.py")
    if sense and hasattr(sense, "sense_dispatch"):
        try:
            sense_out = sense.sense_dispatch({
                "action": "eye",
                "subaction": "threat_alert",
                "threats": ids,
                "hostile": hostile,
                "event": event,
            })
            out["sense"] = sense_out
        except Exception:
            pass
    _append_ledger({"event": event, "hostile": hostile, "threat_ids": ids, "hostess7": out})
    return out


def hostile_posture(*, active: bool | None = None) -> dict[str, Any]:
    doc = fcc.load(HOSTILE, {"active": False, "armed_threats": []})
    if active is not None:
        doc["active"] = bool(active)
        doc["updated"] = fcc.ts()
        if active:
            cat = threat_catalog()
            doc["armed_threats"] = [t["id"] for t in cat.get("threats") or [] if t.get("hostile")]
            doc["prevention"] = True
        fcc.save_atomic(HOSTILE, doc)
    return doc


def _match_threats(signals: dict[str, Any]) -> list[dict[str, Any]]:
    """Match incoming signals to catalog threats."""
    cat = threat_catalog()
    hits: list[dict[str, Any]] = []
    explicit = [str(x) for x in (signals.get("threats") or signals.get("threat_ids") or [])]
    if explicit:
        by_id = {t["id"]: t for t in cat.get("threats") or []}
        for tid in explicit:
            if tid in by_id:
                hits.append(by_id[tid])
        return hits
    blob = json.dumps(signals, ensure_ascii=False).lower()
    for row in cat.get("threats") or []:
        tid = str(row.get("id") or "")
        if tid and tid.replace("_", " ") in blob.replace("_", " "):
            hits.append(row)
            continue
        for sig in row.get("signatures") or []:
            if str(sig).lower() in blob:
                hits.append(row)
                break
    return hits


def prevent_threat(threat_id: str, *, force: bool = False) -> dict[str, Any]:
    """Apply prevention countermeasure for a recognized threat."""
    cat = threat_catalog()
    by_id = {t["id"]: t for t in cat.get("threats") or []}
    row = by_id.get(threat_id)
    if not row:
        return {"ok": False, "error": "unknown_threat", "threat_id": threat_id}
    weapon = row.get("weapon")
    results: list[dict[str, Any]] = []
    eye = fcc.mod("fet_eye", "field-broadcaster-final-eye.py")
    if eye and hasattr(eye, "probe_health"):
        results.append({"step": "eye_probe", **eye.probe_health()})
    entity = fcc.mod("fet_entity", "Final_Eye/zocr_entity_eyeball.py", lib=INSTALL / "Final_Eye")
    if entity and hasattr(entity, "auto_weapon_for_threat"):
        try:
            w = entity.auto_weapon_for_threat(threat_id)
            results.append({"step": "weapon_resolve", "weapon": w})
        except Exception as exc:
            results.append({"step": "weapon_resolve", "error": str(exc)})
    bridge = INSTALL / "lib" / "obs-threat-posterity-bridge.py"
    if bridge.is_file() and row.get("hostile"):
        mod = fcc.mod("fet_threat", "obs-threat-posterity-bridge.py")
        if mod and hasattr(mod, "panel_json"):
            try:
                results.append({"step": "threat_posterity", "panel": mod.panel_json()})
            except Exception:
                pass
    out = {
        "ok": True,
        "threat_id": threat_id,
        "label": row.get("label"),
        "weapon": weapon,
        "prevent": row.get("prevent") or [],
        "forced": force,
        "results": results,
    }
    _append_ledger({"event": "prevent", "threat_id": threat_id, "weapon": weapon})
    return out


def scan_hostile(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Scan for eye threats — especially when brought into hostile environment."""
    req = body or {}
    hostile_doc = hostile_posture()
    hostile = bool(req.get("hostile") or req.get("hostile_environment") or hostile_doc.get("active"))
    if req.get("arm_hostile"):
        hostile_doc = hostile_posture(active=True)
        hostile = True
    signals = {
        "threats": req.get("threats") or req.get("threat_ids"),
        "signatures": req.get("signatures"),
        "frame": req.get("frame"),
        "operator_hostile_flag": hostile,
        "scene_guard": req.get("scene_guard"),
    }
    matched = _match_threats({**req, **signals})
    if hostile and not matched:
        by_id = {t["id"]: t for t in threat_catalog().get("threats") or []}
        if by_id.get("hostile_proximity"):
            matched.append(by_id["hostile_proximity"])
    prevented: list[dict[str, Any]] = []
    doctrine = fcc.load(DOCTRINE, {})
    auto_prevent = hostile and (doctrine.get("hostile_environment") or {}).get("prevention_default", True)
    if auto_prevent or req.get("prevent"):
        for row in matched[:6]:
            prevented.append(prevent_threat(str(row.get("id")), force=bool(req.get("force"))))
    h7 = report_hostess7(matched, event="hostile_scan" if hostile else "scan", hostile=hostile, meta=req)
    return {
        "schema": "field-eye-threat-scan/v1",
        "updated": fcc.ts(),
        "ok": True,
        "hostile": hostile,
        "hostile_posture": hostile_doc,
        "matched_count": len(matched),
        "matched": matched,
        "prevented": prevented,
        "hostess7": h7,
        "truth_gate": fcc.truth_gate(),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    cat = threat_catalog()
    hostile_doc = hostile_posture()
    anatomy = fcc.load(INSTALL / "data" / "hostess7-anatomy-books-index.json", {})
    doc = {
        "schema": "field-eye-threat-panel/v1",
        "updated": fcc.ts(),
        "ok": True,
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "hostile": bool(hostile_doc.get("active")),
        "hostile_posture": hostile_doc,
        "threat_count": cat.get("count", 0),
        "categories": cat.get("categories"),
        "catalog": cat,
        "anatomy_books": {
            "count": len(anatomy.get("books") or []),
            "index": "data/hostess7-anatomy-books-index.json",
            "builder": anatomy.get("builder"),
        },
        "hostess7": doctrine.get("hostess7"),
        "routes": {
            "panel": "/api/field-eye-threat",
            "catalog": "/api/field-eye-threat/catalog",
            "scan": "/api/field-eye-threat/scan",
            "hostile": "/api/field-eye-threat/hostile",
            "anatomy_books": "/api/hostess7/anatomy-books",
            "body_system": "/api/field-body-system",
        },
        "truth_gate": fcc.truth_gate(),
        "posture": (
            f"Eye threats — {cat.get('count', 0)} tracked · "
            f"{'HOSTILE armed' if hostile_doc.get('active') else 'vigilance'} · "
            f"H7 {'linked' if doctrine.get('hostess7') else 'standby'}"
        ),
    }
    if write:
        doc["permanency"] = fcc.save_permanent(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "posture"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("catalog", "threats", "registry"):
        return {"ok": True, **threat_catalog()}

    if action in ("scan", "hostile_scan", "detect"):
        return scan_hostile(body)

    if action in ("hostile", "arm_hostile", "enter_hostile"):
        active = body.get("active", body.get("hostile", True))
        doc = hostile_posture(active=bool(active))
        if active:
            h7 = report_hostess7(
                [{"id": "hostile_proximity", "label": "Hostile environment entry"}],
                event="hostile_entry",
                hostile=True,
                meta=body,
            )
            doc["hostess7"] = h7
        return {"ok": True, **doc}

    if action in ("prevent", "countermeasure"):
        tid = str(body.get("threat") or body.get("threat_id") or "")
        if not tid:
            return {"ok": False, "error": "missing_threat_id"}
        prev = prevent_threat(tid, force=bool(body.get("force")))
        h7 = report_hostess7([{"id": tid, "label": tid}], event="prevent", hostile=bool(body.get("hostile")))
        return {"ok": prev.get("ok"), "prevent": prev, "hostess7": h7}

    if action in ("report", "notify_hostess7", "hostess7"):
        threats = body.get("threats") or body.get("threat_ids") or []
        if isinstance(threats, list) and threats and isinstance(threats[0], str):
            threats = [{"id": t, "label": t} for t in threats]
        return report_hostess7(threats, event=str(body.get("event") or "report"), hostile=bool(body.get("hostile")), meta=body)

    if action in ("anatomy_books", "books"):
        books = fcc.mod("fet_anatomy", "hostess7-anatomy-book.py")
        if books and hasattr(books, "books_index"):
            return {"ok": True, **books.books_index()}
        return {"ok": True, **fcc.load(INSTALL / "data" / "hostess7-anatomy-books-index.json", {})}

    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(threat_catalog(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        patch = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(json.dumps(scan_hostile(patch), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-eye-threat-chamber.py [json|catalog|scan|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())