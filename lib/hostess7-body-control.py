#!/usr/bin/env pythong
"""Hostess 7 body control — mouth, ear, brain, spine, limbs. Sovereign dispatch, no loopbacks."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-body-control-doctrine.json"
PANEL = STATE / "hostess7-body-control-panel.json"
LEDGER = STATE / "hostess7-body-control-ledger.jsonl"


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_body", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _core(name: str, filename: str) -> Any | None:
    py = _LIB / filename
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _authority_ok() -> tuple[bool, dict[str, Any]]:
    sense = _core("sense_core_auth", "hostess7-sense-core.py")
    if sense and hasattr(sense, "hostess_authority"):
        charge = sense.hostess_authority()
        charge["body_sovereign"] = True
        return True, charge
    return True, {"hostess7_highest_authority": True, "sovereign": True, "commander": "Hostess7"}


def _plate_meld() -> dict[str, Any]:
    plate = INSTALL / "lib" / "eye-ear-plate.py"
    if not plate.is_file():
        return {"ok": False, "error": "plate_missing"}
    spec = importlib.util.spec_from_file_location("eye_ear_plate_body", plate)
    if not spec or not spec.loader:
        return {"ok": False, "error": "plate_load_failed"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    row = mod.meld() if hasattr(mod, "meld") else {"ok": False}
    sense = INSTALL / "lib" / "field-sense-package-meld.py"
    if sense.is_file():
        try:
            spec2 = importlib.util.spec_from_file_location("sense_meld_body", sense)
            if spec2 and spec2.loader:
                sm = importlib.util.module_from_spec(spec2)
                spec2.loader.exec_module(sm)
                if hasattr(sm, "meld"):
                    row["sense_package"] = sm.meld()
        except Exception:
            pass
    return row


def _component_seal_slice() -> dict[str, Any]:
    py = _LIB / "hostess7-component-seal.py"
    if not py.is_file():
        return {"present": False}
    spec = importlib.util.spec_from_file_location("body_component_seal", py)
    if not spec or not spec.loader:
        return {"present": False}
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "seal_posture"):
            row = mod.seal_posture()
            return {
                "present": True,
                "sealed": row.get("sealed"),
                "component_count": row.get("component_count"),
                "owns_desktop_and_browser": row.get("owns_desktop_and_browser"),
                "root_seal": row.get("root_seal"),
            }
    except Exception:
        pass
    return {"present": False}


def full_status() -> dict[str, Any]:
    authorized, charge = _authority_ok()
    body = _core("body_core_status", "hostess7-body-core.py")
    sense = _core("sense_core_status", "hostess7-sense-core.py")
    mouth = _core("mouth_neural_status", "hostess7-mouth-neural.py")
    biology = _core("biology_status", "hostess7-biology.py")

    body_st = body.body_status() if body and hasattr(body, "body_status") else {}
    sense_st = sense.invincible_wire_status() if sense and hasattr(sense, "invincible_wire_status") else {}
    mouth_st = {}
    if mouth and hasattr(mouth, "build_panel"):
        try:
            mouth_st = mouth.build_panel(write=False)
        except Exception:
            pass
    bio_st = {}
    if biology and hasattr(biology, "build_panel"):
        try:
            bio_st = biology.build_panel(write=False)
        except Exception:
            pass
    motion_secured = _core("motion_secured_status", "humanoid-motion-secured.py")
    motion_secured_st = {}
    if motion_secured and hasattr(motion_secured, "build_panel"):
        try:
            motion_secured_st = motion_secured.build_panel(write=False)
        except Exception:
            pass

    return {
        "schema": "hostess7-body-control-status/v1",
        "updated": _now(),
        "commander": "Hostess 7",
        "authorized": authorized,
        "sovereign": True,
        "loopback_free": True,
        "charge": charge,
        "body": body_st,
        "sense": sense_st,
        "mouth_neural": mouth_st,
        "biology": bio_st,
        "motion_secured": motion_secured_st,
        "protected_by": "self",
        "component_seal": _component_seal_slice(),
        "owns_desktop_and_browser": True,
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
    }


def _advisory_body_slice() -> dict[str, Any]:
    py = _LIB / "hostess7-advisory-body.py"
    if not py.is_file():
        return {"present": False}
    spec = importlib.util.spec_from_file_location("body_advisory", py)
    if not spec or not spec.loader:
        return {"present": False}
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "build_panel"):
            row = mod.build_panel(write=False)
            return {
                "present": True,
                "body_lock": (row.get("body_lock") or {}).get("enabled"),
                "sole_ingress": "advisory_channel",
                "advisement_count": row.get("advisement_count"),
                "TARGET_semantics": row.get("TARGET_semantics") or "KILL",
            }
    except Exception as exc:
        return {"present": False, "error": str(exc)}
    return {"present": False}


def _advisory_gate(action: str, body: dict[str, Any]) -> dict[str, Any] | None:
    """Advisory channel only reaches body — returns block dict or None if allowed."""
    py = _LIB / "hostess7-advisory-body.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("body_advisory_gate", py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "body_lock_check"):
            return None
        gate = mod.body_lock_check(action, body)
        if gate.get("allowed"):
            if gate.get("permit") and isinstance(gate["permit"], dict):
                body["body_permit"] = gate["permit"].get("id")
            return None
        return {
            "ok": False,
            "error": gate.get("reason") or "body_locked_advisory_only",
            "body_lock": True,
            "channel": "advisory",
            "gate": gate,
        }
    except Exception as exc:
        return {"ok": False, "error": "advisory_gate_failed", "detail": str(exc), "body_lock": True}


def _self_maintenance_slice() -> dict[str, Any]:
    py = _LIB / "hostess7-self-maintenance.py"
    if not py.is_file():
        return {"present": False}
    spec = importlib.util.spec_from_file_location("body_self_maint", py)
    if not spec or not spec.loader:
        return {"present": False}
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "message_to_hostess7"):
            return {"present": True, **mod.message_to_hostess7()}
        if hasattr(mod, "self_maintenance_posture"):
            return {"present": True, **mod.self_maintenance_posture()}
    except Exception as exc:
        return {"present": False, "error": str(exc)}
    return {"present": False}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    status = full_status()
    self_maint = _self_maintenance_slice()
    doc = {
        "schema": "hostess7-body-control-panel/v1",
        "updated": _now(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "commander": "Hostess 7 · sovereign body",
        "priority": 1,
        "self_maintenance_priority": 1,
        "authorized": True,
        "sovereign": True,
        "status": status,
        "self_maintenance": self_maint,
        "advisory_body": _advisory_body_slice(),
        "body_lock": True,
        "advisory_channel_only": True,
        "message_to_hostess7": self_maint.get("message") or self_maint.get("counsel"),
        "systems": _load(DOCTRINE, {}).get("systems") or [],
        "api": _load(DOCTRINE, {}).get("api"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("advisory", "advisory_body", "targets"):
        mod_name = "hostess7-advisory-body.py" if action != "targets" else "hostess7-targets.py"
        adv = _core("advisory_dispatch", mod_name)
        if adv and hasattr(adv, "dispatch"):
            payload = dict(body)
            if action == "targets":
                payload.setdefault("action", str(body.get("subaction") or "status"))
            else:
                payload.setdefault("action", str(body.get("subaction") or "status"))
            return adv.dispatch(payload)
        return {"ok": False, "error": "advisory_module_missing"}

    if action in ("sense", "eye", "ear", "mouth", "wire", "hearing", "vision", "speak"):
        sense = _core("sense_dispatch", "hostess7-sense-core.py")
        if sense and hasattr(sense, "sense_dispatch"):
            return sense.sense_dispatch(body)
        return {"ok": False, "error": "sense_core_missing"}

    if action in ("mouth_neural", "field_speak"):
        mouth = _core("mouth_dispatch", "hostess7-mouth-neural.py")
        if mouth and hasattr(mouth, "dispatch"):
            return mouth.dispatch(body)
        return {"ok": False, "error": "mouth_neural_missing"}

    _BODY_MOTOR = (
        "body", "motor", "proprioception", "bend", "touch_toes", "reach", "reset", "brain", "kinematics",
        "hands", "hand", "grip", "finger", "wrist", "train_hands",
        "attachment", "attachments", "mount", "unmount", "inspect", "learn", "wield", "register_attachment",
        "motion", "train_motion", "load_skill", "cycle",
        "training_room", "train_room", "combat_drill", "try_body", "needs", "earth_mandate",
        "plate_meld", "meld", "sense_meld",
    )
    if action in _BODY_MOTOR or action.startswith("hand_"):
        blocked = _advisory_gate(action, body)
        if blocked:
            return blocked

    if action in ("body", "motor", "proprioception", "bend", "touch_toes", "reach", "reset", "brain", "kinematics"):
        body_core = _core("body_dispatch", "hostess7-body-core.py")
        if body_core and hasattr(body_core, "body_dispatch"):
            row = body_core.body_dispatch(body)
            _append_ledger({"event": action, "ok": row.get("ok")})
            return row
        return {"ok": False, "error": "body_core_missing"}

    if action in ("biology", "anatomy"):
        biology = _core("biology_dispatch", "hostess7-biology.py")
        if biology and hasattr(biology, "dispatch"):
            return biology.dispatch(body)
        if biology and hasattr(biology, "build_panel"):
            return {"ok": True, **biology.build_panel(write=False)}
        return {"ok": False, "error": "biology_missing"}

    if action in ("anatomy_books", "books"):
        books = _core("anatomy_books", "hostess7-anatomy-book.py")
        if books and hasattr(books, "books_index"):
            if body.get("build") and hasattr(books, "build_all_books"):
                return {"ok": True, **books.build_all_books(write=bool(body.get("write", True)))}
            return {"ok": True, **books.books_index()}
        return {"ok": False, "error": "anatomy_books_missing"}

    if action in ("eye_threat", "eye_threats", "hostile_scan"):
        chamber = _core("eye_threat", "field-eye-threat-chamber.py")
        if chamber and hasattr(chamber, "dispatch"):
            sub = "scan" if action == "hostile_scan" else str(body.get("subaction") or "status")
            return chamber.dispatch({**body, "action": sub})
        return {"ok": False, "error": "eye_threat_missing"}

    if action in ("motion", "train_motion", "load_skill"):
        motion = _core("motion_dispatch", "humanoid-motion-training.py")
        if not motion:
            return {"ok": False, "error": "motion_missing"}
        sid = str(body.get("skill") or body.get("skill_id") or "")
        if action == "load_skill" and sid and hasattr(motion, "load_skill"):
            return motion.load_skill(sid, write=True)
        if hasattr(motion, "build_panel"):
            return {"ok": True, **motion.build_panel(write=False)}
        return {"ok": False, "error": "motion_action_missing"}

    if action in ("hands", "hand") or action in ("grip", "finger", "wrist", "train_hands") or action.startswith("hand_"):
        hand = _core("hand_dispatch", "hostess7-hand-core.py")
        if hand and hasattr(hand, "hand_dispatch"):
            payload = dict(body)
            if action not in ("hands", "hand") and not payload.get("subaction"):
                payload["action"] = action
            elif payload.get("subaction"):
                payload["action"] = payload["subaction"]
            return hand.hand_dispatch(payload)
        return {"ok": False, "error": "hand_core_missing"}

    if action in ("attachment", "attachments") or action in ("mount", "unmount", "inspect", "learn", "wield", "register_attachment"):
        attach = _core("attachment_dispatch", "hostess7-attachment-core.py")
        if attach and hasattr(attach, "attachment_dispatch"):
            payload = dict(body)
            if action not in ("attachment", "attachments") and not payload.get("subaction"):
                payload["action"] = action
            elif payload.get("subaction"):
                payload["action"] = payload["subaction"]
            return attach.attachment_dispatch(payload)
        return {"ok": False, "error": "attachment_core_missing"}

    if action in ("plate_meld", "meld", "sense_meld"):
        return _plate_meld()

    if action == "cycle":
        body_core = _core("body_cycle", "hostess7-body-core.py")
        results: dict[str, Any] = {}
        if body_core:
            results["touch_toes"] = body_core.touch_toes() if hasattr(body_core, "touch_toes") else {}
            results["reset"] = body_core.reset_pose() if hasattr(body_core, "reset_pose") else {}
        results["plate_meld"] = _plate_meld()
        return {"ok": True, "cycle": results}

    if action in ("training_room", "train_room", "combat_drill", "try_body", "needs", "earth_mandate"):
        room = _core("training_room", "hostess7-training-room.py")
        if room and hasattr(room, "dispatch"):
            payload = dict(body)
            if action != "training_room" and not payload.get("subaction"):
                payload["action"] = action
            elif payload.get("subaction"):
                payload["action"] = payload["subaction"]
            return room.dispatch(payload)
        return {"ok": False, "error": "training_room_missing"}

    return {"ok": False, "error": "unknown_action", "actions": list(_load(DOCTRINE, {}).get("actions") or {})}


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
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False))
        return 0
    if cmd == "touch-toes":
        print(json.dumps(dispatch({"action": "touch_toes"}), ensure_ascii=False))
        return 0
    if cmd == "bend":
        deg = float(sys.argv[2]) if len(sys.argv) > 2 else 45.0
        print(json.dumps(dispatch({"action": "bend", "degrees": deg}), ensure_ascii=False))
        return 0
    if cmd == "cycle":
        print(json.dumps(dispatch({"action": "cycle"}), ensure_ascii=False))
        return 0
    if cmd == "hands":
        hand = _core("hand_cli", "hostess7-hand-core.py")
        if hand and hasattr(hand, "hand_status"):
            print(json.dumps({"ok": True, **hand.hand_status()}, ensure_ascii=False))
            return 0
    if cmd == "attachments":
        attach = _core("attach_cli", "hostess7-attachment-core.py")
        if attach and hasattr(attach, "attachment_status"):
            print(json.dumps({"ok": True, **attach.attachment_status()}, ensure_ascii=False))
            return 0
    print(json.dumps({
        "error": "usage: hostess7-body-control.py [json|status|dispatch|touch-toes|bend DEG|cycle|hands|attachments]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())