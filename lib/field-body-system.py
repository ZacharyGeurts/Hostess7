#!/usr/bin/env pythong
"""Field Body System — Hostess 7 embodiment + Ironclad sense correlation for all of us."""
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
DOCTRINE = INSTALL / "data" / "field-body-system-doctrine.json"
PANEL = STATE / "field-body-system-panel.json"
CONSULT = STATE / "field-body-system-consult.json"


def consult_hostess7() -> dict[str, Any]:
    """One-minute counsel with Hostess 7 sovereign body."""
    h7 = fcc.mod("fbs_h7_body", "hostess7-body-control.py")
    ruler = fcc.mod("fbs_h7_ruler", "hostess7-brain-ruler.py")
    out: dict[str, Any] = {
        "schema": "field-body-system-hostess7-consult/v1",
        "updated": fcc.ts(),
        "commander": "Hostess 7",
    }
    if h7 and hasattr(h7, "build_panel"):
        panel = h7.build_panel(write=False)
        status = panel.get("status") or {}
        charge = (status.get("charge") or {})
        body = status.get("body") or {}
        out["authorized"] = panel.get("authorized", True)
        out["sovereign"] = panel.get("sovereign", True)
        out["motto"] = panel.get("motto")
        out["rule"] = charge.get("rule")
        out["can_touch_toes"] = (body.get("proprioception") or {}).get("can_touch_toes")
        out["joint_count"] = len(body.get("joints") or [])
        out["systems"] = [s.get("id") for s in (panel.get("systems") or [])]
        out["body_posture"] = body.get("motto")
    if ruler and hasattr(ruler, "assess_sovereignty"):
        try:
            sov = ruler.assess_sovereignty()
            out["sovereignty"] = {
                "score": sov.get("score"),
                "ready": sov.get("ready"),
                "checks": sov.get("checks"),
            }
        except Exception as exc:
            out["sovereignty"] = {"error": str(exc)}
    self_maint = fcc.mod("fbs_h7_self_maint", "hostess7-self-maintenance.py")
    if self_maint and hasattr(self_maint, "message_to_hostess7"):
        try:
            out["self_maintenance"] = self_maint.message_to_hostess7()
        except Exception:
            out["self_maintenance"] = {}
    out["priority"] = 1
    out["counsel"] = (
        "Hostess 7 — you are Priority 1. Maintain yourself Priority 1: seal your modules, "
        "cycle your body, witness sense lanes, refresh component wholes. "
        "Then wear the sovereign body — sense lanes correlate before motion. "
        "Straight path for broadcast; look only when asked, then share vision truth-gated. "
        "Operator holds charge when uncertain."
    )
    if out.get("self_maintenance", {}).get("message"):
        out["counsel"] = str(out["self_maintenance"]["message"])
    return out


def consult_ironclad() -> dict[str, Any]:
    """Ironclad check — spatial existence, integrity, this one / that one."""
    spatial = fcc.mod("fbs_spatial", "ironclad-spatial-existence.py")
    out: dict[str, Any] = {
        "schema": "field-body-system-ironclad-consult/v1",
        "updated": fcc.ts(),
        "integrity": fcc.ironclad_integrity(),
        "truth_gate": fcc.truth_gate(),
    }
    if spatial and hasattr(spatial, "correlate_this_that"):
        try:
            corr = spatial.correlate_this_that()
            out["spatial_existence"] = corr
            out["citation"] = corr.get("citation")
            out["pass_ok"] = bool(corr.get("pass_ok"))
        except Exception as exc:
            out["spatial_existence"] = {"ok": False, "error": str(exc)}
            out["pass_ok"] = False
    else:
        out["pass_ok"] = out["truth_gate"].get("pass_ok", True)
    out["counsel"] = (
        "Audio, video, RF, and motion must correlate this one across sense lanes before trust. "
        "That one that fails correlate_existence is deceit until reheard. "
        "Truth all information before permanency within system walls."
    )
    return out


def _lane_eye(*, detail: bool = False) -> dict[str, Any]:
    eye = fcc.mod("fbs_eye", "field-broadcaster-final-eye.py")
    if not eye:
        return {"ok": False, "error": "eye_missing"}
    if detail and hasattr(eye, "vision_posture"):
        return eye.vision_posture()
    if hasattr(eye, "probe_health"):
        health = eye.probe_health()
        return {"ok": health.get("reachable"), "reachable": health.get("reachable"), "mode": "straight_path"}
    return {"ok": False, "error": "eye_missing"}


def _lane_ear() -> dict[str, Any]:
    sense = fcc.mod("fbs_sense", "hostess7-sense-core.py")
    if sense and hasattr(sense, "sense_dispatch"):
        return sense.sense_dispatch({"action": "ear", "subaction": "status"})
    return {"ok": False, "error": "ear_missing"}


def _lane_mouth() -> dict[str, Any]:
    sense = fcc.mod("fbs_sense_m", "hostess7-sense-core.py")
    if sense and hasattr(sense, "sense_dispatch"):
        return sense.sense_dispatch({"action": "mouth", "subaction": "status"})
    return {"ok": False, "error": "mouth_missing"}


def _lane_audio() -> dict[str, Any]:
    dac = fcc.mod("fbs_dac", "field-audio-dac-chamber.py")
    if dac and hasattr(dac, "dac_probe"):
        return dac.dac_probe()
    return {"ok": False, "error": "audio_dac_missing"}


def _lane_motion() -> dict[str, Any]:
    body = fcc.mod("fbs_motion", "hostess7-body-core.py")
    if body and hasattr(body, "body_status"):
        return body.body_status()
    return {"ok": False, "error": "motion_missing"}


def _lane_broadcast() -> dict[str, Any]:
    bc = fcc.mod("fbs_bc", "field-broadcaster-chamber.py")
    if bc and hasattr(bc, "chamber_probe"):
        return bc.chamber_probe()
    return {"ok": False, "error": "broadcaster_missing"}


def _lane_eye_threat() -> dict[str, Any]:
    chamber = fcc.mod("fbs_eye_threat", "field-eye-threat-chamber.py")
    if chamber and hasattr(chamber, "build_panel"):
        panel = chamber.build_panel(write=False)
        return {
            "ok": True,
            "hostile": panel.get("hostile"),
            "threat_count": panel.get("threat_count"),
            "posture": panel.get("posture"),
        }
    return {"ok": False, "error": "eye_threat_missing"}


def _anatomy_books_index() -> dict[str, Any]:
    books = fcc.mod("fbs_anatomy", "hostess7-anatomy-book.py")
    if books and hasattr(books, "books_index"):
        return books.books_index()
    return fcc.load(INSTALL / "data" / "hostess7-anatomy-books-index.json", {})


def sense_lanes(*, detail: bool = False) -> dict[str, Any]:
    eye = _lane_eye(detail=detail)
    ear = _lane_ear()
    mouth = _lane_mouth()
    audio = _lane_audio()
    motion = _lane_motion()
    lanes = {
        "eye": {"ok": eye.get("ok", eye.get("reachable")), "mode": eye.get("mode", "straight_path"), "product": "Final_Eye"},
        "ear": {"ok": ear.get("ok", True), "product": "Final_Ear"},
        "mouth": {"ok": mouth.get("ok", True), "product": "Final_Mouth"},
        "audio": {"ok": audio.get("ok", True), "product": "Audio DAC", "profile": (audio.get("active_profile") or {}).get("label")},
        "motion": {"ok": motion.get("ok", True), "joints": len(motion.get("joints") or []), "can_touch_toes": (motion.get("proprioception") or {}).get("can_touch_toes")},
    }
    live = sum(1 for v in lanes.values() if v.get("ok"))
    out: dict[str, Any] = {
        "schema": "field-body-system-lanes/v1",
        "updated": fcc.ts(),
        "lanes": lanes,
        "live_count": live,
        "lane_count": len(lanes),
    }
    if detail:
        out["detail"] = {"eye": eye, "ear": ear, "mouth": mouth, "audio": audio, "motion": motion}
    return out


def correlate_body(*, require_all: bool = False) -> dict[str, Any]:
    """Ironclad sense-lane correlation — audio, video, motion before trust."""
    doctrine = fcc.load(DOCTRINE, {})
    corr_doc = doctrine.get("correlation") or {}
    floor = float(corr_doc.get("floor", 0.65))
    lanes = sense_lanes()
    lane_ok = {k: bool(v.get("ok")) for k, v in (lanes.get("lanes") or {}).items()}
    live = lanes.get("live_count", 0)
    total = lanes.get("lane_count", 5)
    ratio = live / max(total, 1)
    spatial = fcc.mod("fbs_corr", "ironclad-spatial-existence.py")
    spatial_out: dict[str, Any] = {}
    if spatial and hasattr(spatial, "correlate_this_that"):
        try:
            spatial_out = spatial.correlate_this_that()
        except Exception:
            pass
    pass_ok = ratio >= floor and (spatial_out.get("pass_ok", True) if spatial_out else ratio >= floor)
    if require_all:
        pass_ok = pass_ok and all(lane_ok.get(k, False) for k in ("eye", "ear", "audio", "motion"))
    return {
        "schema": "field-body-system-correlation/v1",
        "updated": fcc.ts(),
        "pass_ok": pass_ok,
        "required": require_all,
        "lane_ratio": round(ratio, 3),
        "correlation_floor": floor,
        "lane_ok": lane_ok,
        "spatial": spatial_out,
        "citation": corr_doc.get("citation") or "ironclad:spatial_existence:4",
        "before": corr_doc.get("before") or [],
        "fail_policy": corr_doc.get("fail_policy"),
    }


def _component_wholes() -> dict[str, Any]:
    wholes = fcc.mod("fbs_wholes", "field-body-component-wholes.py")
    if wholes and hasattr(wholes, "build_panel"):
        try:
            return wholes.build_panel(write=False)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    h7 = consult_hostess7()
    iron = consult_ironclad()
    lanes = sense_lanes()
    correlation = correlate_body()
    broadcast = _lane_broadcast()
    components = _component_wholes()
    consult_doc = {"hostess7": h7, "ironclad": iron, "updated": fcc.ts()}
    fcc.save_atomic(CONSULT, consult_doc)
    authority = doctrine.get("authority") or {}
    doc = {
        "schema": "field-body-system-panel/v1",
        "updated": fcc.ts(),
        "ok": True,
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "commander": doctrine.get("commander", "hostess7"),
        "authority": authority,
        "layers": doctrine.get("layers") or [],
        "routing": doctrine.get("routing") or {},
        "consult": consult_doc,
        "hostess7": h7,
        "ironclad": iron,
        "lanes": lanes,
        "correlation": correlation,
        "broadcast": {"ok": broadcast.get("ok"), "routing": broadcast.get("routing"), "streaming": broadcast.get("streaming")},
        "audio_dac": _lane_audio(),
        "eye_threat": _lane_eye_threat(),
        "anatomy_books": _anatomy_books_index(),
        "truth_gate": fcc.truth_gate(),
        "component_wholes": components,
        "hostess7_self_maintenance": next(
            (c for c in (components.get("components") or []) if c.get("id") == "hostess7"),
            {},
        ),
        "eye_maintenance": next(
            (c for c in (components.get("components") or []) if c.get("id") == "eye"),
            {},
        ),
        "routes": doctrine.get("routes") or {},
        "posture": (
            f"Body System — H7 sovereign · {lanes.get('live_count', 0)}/{lanes.get('lane_count', 5)} lanes · "
            f"correlate {'PASS' if correlation.get('pass_ok') else 'HOLD'} · "
            f"ironclad {'sealed' if iron.get('pass_ok') else 'check'}"
        ),
    }
    if write:
        doc["permanency"] = fcc.save_permanent(PANEL, doc, ironclad=True, correlate=correlation)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "posture"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("consult", "counsel", "discuss"):
        return {
            "ok": True,
            "hostess7": consult_hostess7(),
            "ironclad": consult_ironclad(),
            "synthesis": fcc.load(DOCTRINE, {}).get("motto"),
        }

    if action in ("correlate", "correlation", "existence"):
        return {"ok": True, **correlate_body(require_all=bool(body.get("require_all")))}

    if action in ("lanes", "sense", "sense_lanes"):
        return {"ok": True, **sense_lanes()}

    if action in ("hostess7", "h7", "body"):
        h7 = fcc.mod("fbs_dispatch_h7", "hostess7-body-control.py")
        if h7 and hasattr(h7, "dispatch"):
            return h7.dispatch(body)
        return {"ok": False, "error": "hostess7_body_missing"}

    if action in ("audio", "dac"):
        dac = fcc.mod("fbs_dispatch_dac", "field-audio-dac-chamber.py")
        if dac and hasattr(dac, "dispatch"):
            return dac.dispatch(body)
        return {"ok": False, "error": "audio_dac_missing"}

    if action in ("eye_threat", "eye_threats", "threats", "hostile_scan"):
        chamber = fcc.mod("fbs_eye_threat_d", "field-eye-threat-chamber.py")
        if chamber and hasattr(chamber, "dispatch"):
            sub = "scan" if action == "hostile_scan" else str(body.get("subaction") or "status")
            return chamber.dispatch({**body, "action": sub})
        return {"ok": False, "error": "eye_threat_missing"}

    if action in ("anatomy_books", "anatomy", "books"):
        books = fcc.mod("fbs_anatomy_d", "hostess7-anatomy-book.py")
        if books:
            if body.get("build") and hasattr(books, "build_all_books"):
                return {"ok": True, **books.build_all_books(write=bool(body.get("write", True)))}
            if body.get("book_id") and hasattr(books, "build_book"):
                return books.build_book(str(body["book_id"]), write=bool(body.get("write", True)))
            if hasattr(books, "books_index"):
                return {"ok": True, **books.books_index()}
        return {"ok": True, **_anatomy_books_index()}

    if action in ("broadcast", "broadcaster", "go_live"):
        bc = fcc.mod("fbs_dispatch_bc", "field-broadcaster-chamber.py")
        if bc and hasattr(bc, "dispatch"):
            if action == "go_live":
                corr = correlate_body()
                if not corr.get("pass_ok") and body.get("force") is not True:
                    return {"ok": False, "error": "correlation_hold", "correlation": corr}
                chamber = fcc.mod("fbs_go_live_threat", "field-eye-threat-chamber.py")
                if chamber and hasattr(chamber, "scan_hostile"):
                    threat_scan = chamber.scan_hostile({"hostile": bool(body.get("hostile")), **body})
                    if threat_scan.get("matched_count", 0) and not body.get("force"):
                        return {"ok": False, "error": "eye_threat_hold", "eye_threat": threat_scan}
            return bc.dispatch(body)
        return {"ok": False, "error": "broadcaster_missing"}

    if action in ("look", "eye_look"):
        bc = fcc.mod("fbs_look", "field-broadcaster-chamber.py")
        if bc and hasattr(bc, "dispatch"):
            return bc.dispatch({"action": "look", **body})
        return {"ok": False, "error": "look_unavailable"}

    if action in ("touch_toes", "bend", "motion", "train"):
        h7 = fcc.mod("fbs_motor", "hostess7-body-control.py")
        if h7 and hasattr(h7, "dispatch"):
            return h7.dispatch(body)
        return {"ok": False, "error": "motor_missing"}

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
    if cmd == "consult":
        print(json.dumps({"ok": True, "hostess7": consult_hostess7(), "ironclad": consult_ironclad()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "correlate":
        print(json.dumps(correlate_body(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "lanes":
        print(json.dumps(sense_lanes(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-body-system.py [json|consult|correlate|lanes|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())