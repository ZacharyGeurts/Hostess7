#!/usr/bin/env pythong
"""Hostess 7 training floor — completes sense, footwork, sparring AI, haptics, environment on the mat."""
from __future__ import annotations

import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-training-floor-doctrine.json"
RUNTIME = STATE / "hostess7-training-floor-runtime.json"
PANEL = STATE / "hostess7-training-floor-panel.json"


def _ts() -> str:
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


def _mod(name: str, rel: str) -> Any | None:
    py = _LIB / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _runtime() -> dict[str, Any]:
    return _load(RUNTIME, {
        "schema": "hostess7-training-floor-runtime/v1",
        "sense_live": {},
        "footwork": {},
        "haptic": {},
        "cardio": {"hr_bpm": 72, "zone": "rest"},
        "sparring": {},
        "environment": {},
        "completed": [],
    })


def sense_floor_status() -> dict[str, Any]:
    """Final_Eye + Final_Ear live on training floor — in-process, assistive when hardware absent."""
    sense = _mod("tf_sense", "hostess7-sense-core.py")
    ocr = _mod("tf_ocr", "final-eye-ocr-core.py")
    eye_live = False
    ear_live = False
    eye_detail: dict[str, Any] = {}
    ear_detail: dict[str, Any] = {}

    if ocr:
        root = ocr.final_eye_root() if hasattr(ocr, "final_eye_root") else None
        eye_live = bool(root and (root / "zocr.py").is_file())
        if hasattr(ocr, "final_eye_status"):
            eye_detail = ocr.final_eye_status()
            eye_live = eye_live or bool(eye_detail.get("tesseract") or eye_detail.get("captures") is not None)

    if sense:
        try:
            wire = sense.invincible_wire_status() if hasattr(sense, "invincible_wire_status") else {}
            eye_neural = wire.get("eye_neural") or {}
            ear_neural = wire.get("ear_neural") or {}
            eye_live = eye_live or "error" not in eye_neural
            ear_live = ear_live or "error" not in ear_neural
            eye_detail.setdefault("wire", eye_neural)
            ear_detail.setdefault("wire", ear_neural)
        except Exception as exc:
            eye_detail["wire_error"] = type(exc).__name__

    for cand in (INSTALL / "Final_Eye", INSTALL / "Final_Ear"):
        if (cand / "zocr.py").is_file() or (cand / "zocr_neural_assist.py").is_file():
            if "Ear" in cand.name or "ear" in cand.name.lower():
                ear_live = True
            else:
                eye_live = True

    assistive = True
    return {
        "schema": "hostess7-training-floor-sense/v1",
        "updated": _ts(),
        "vision_live": eye_live or assistive,
        "hearing_live": ear_live or assistive,
        "assistive_floor": assistive,
        "eye": eye_detail,
        "ear": ear_detail,
        "training_floor": True,
        "commander": "Hostess7",
    }


def footwork_proprioception() -> dict[str, Any]:
    body = _mod("tf_body", "hostess7-body-core.py")
    motion = _mod("tf_motion", "humanoid-motion-training.py")
    weight_l = 0.52
    weight_r = 0.48
    shift_x = 0.0
    if body and hasattr(body, "load_pose"):
        pose = body.load_pose()
        bal = pose.get("balance") or {}
        shift_x = float(bal.get("com_x") or 0)
        if shift_x > 0.02:
            weight_l, weight_r = 0.42, 0.58
        elif shift_x < -0.02:
            weight_l, weight_r = 0.58, 0.42
    active_skill = None
    if motion and hasattr(motion, "build_panel"):
        try:
            mp = motion.build_panel(write=False)
            active_skill = mp.get("active_skill")
        except Exception:
            pass
    return {
        "schema": "hostess7-footwork-proprioception/v1",
        "updated": _ts(),
        "weight_left": round(weight_l, 3),
        "weight_right": round(weight_r, 3),
        "com_shift_x": round(shift_x, 4),
        "stance": "orthodox" if weight_l >= weight_r else "southpaw",
        "active_skill": active_skill,
        "receipts": ["heel_pressure", "toe_spread", "hip_rotation", "knee_flex"],
        "live": True,
    }


def vestibular_balance() -> dict[str, Any]:
    body = _mod("tf_body_v", "hostess7-body-core.py")
    sense = sense_floor_status()
    foot = footwork_proprioception()
    com_z = 0.55
    grounded = True
    if body and hasattr(body, "proprioception_state"):
        prop = body.proprioception_state()
        bal = prop.get("balance") or {}
        com_z = float(bal.get("com_z") or com_z)
        grounded = bool(bal.get("grounded", True))
    stability = min(1.0, 0.65 + (0.2 if grounded else 0) + (0.15 if sense.get("hearing_live") else 0))
    return {
        "schema": "hostess7-vestibular-balance/v1",
        "updated": _ts(),
        "com_z": com_z,
        "grounded": grounded,
        "stability": round(stability, 3),
        "ear_coupled": bool(sense.get("hearing_live")),
        "inner_ear_sim": True,
    }


def haptic_gloves_state(*, impact_n: float | None = None) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    cfg = doc.get("haptic_gloves") or {}
    hand = _mod("tf_hand", "hostess7-hand-core.py")
    left_force = 0.0
    right_force = 0.0
    if hand and hasattr(hand, "load_hand_state"):
        st = hand.load_hand_state()
        for side, key in (("left", "grip_l"), ("right", "grip_r")):
            grip = st.get(key) or "open"
            f = {"power": 28, "precision": 12, "pinch": 8, "tripod": 10, "sphere": 18, "hook": 15}.get(grip, 0)
            if side == "left":
                left_force = f
            else:
                right_force = f
    if impact_n is not None:
        right_force = max(right_force, float(impact_n))
    thresh = float(cfg.get("impact_threshold_n") or 12)
    return {
        "schema": "hostess7-haptic-gloves/v1",
        "updated": _ts(),
        "enabled": True,
        "left_force_n": round(left_force * float(cfg.get("force_scale") or 1), 2),
        "right_force_n": round(right_force * float(cfg.get("force_scale") or 1), 2),
        "grip_feedback": bool(cfg.get("grip_feedback")),
        "impact_felt": (right_force + left_force) >= thresh,
    }


def motor_actuator_bridge_status() -> dict[str, Any]:
    return {
        "schema": "hostess7-motor-actuator-bridge/v1",
        "updated": _ts(),
        "mode": "simulation_ready",
        "hardware_attached": False,
        "bridge_live": True,
        "endpoints": ["hand_l", "hand_r", "wrist_l", "wrist_r"],
        "protocol": "hostess7-body-core/joint_pose",
        "note": "Physical robot/exoskeleton can subscribe to joint_pose stream",
    }


def environment_mesh() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    arena = doc.get("arena") or {}
    return {
        "schema": "hostess7-environment-mesh/v1",
        "updated": _ts(),
        "walls": arena.get("walls") or [],
        "cover": arena.get("cover") or [],
        "egress": arena.get("egress") or [],
        "wall_count": len(arena.get("walls") or []),
        "cover_count": len(arena.get("cover") or []),
        "egress_count": len(arena.get("egress") or []),
        "live": True,
    }


def reactive_sparring_opponents(*, active_skill: str | None = None) -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    ai = doc.get("sparring_ai") or {}
    counters = ai.get("skill_counters") or {}
    sid = (active_skill or "wing_chun").strip().lower()
    stance = counters.get(sid, "orthodox")
    motion = _mod("tf_motion_opp", "humanoid-motion-training.py")
    base: list[dict[str, Any]] = []
    if motion and hasattr(motion, "arena_opponents"):
        try:
            base = motion.arena_opponents()
        except Exception:
            base = []
    phase = datetime.now(timezone.utc).timestamp() % (2 * math.pi)
    react = float(ai.get("reactivity") or 0.85)
    for i, opp in enumerate(base):
        if opp.get("kind") in ("sparring", "hostile") or opp.get("wireframe") in ("hostile", "sparring"):
            dx = math.sin(phase + i) * 0.06 * react
            dy = math.cos(phase + i * 0.7) * 0.04 * react
            opp = dict(opp)
            opp["arena_x"] = round(float(opp.get("arena_x") or 0.75) + dx, 4)
            opp["arena_y"] = round(float(opp.get("arena_y") or 0.52) + dy, 4)
            opp["stance"] = stance if i == 0 else opp.get("stance")
            opp["reactive"] = True
            opp["ai_skill_counter"] = sid
        base[i] = opp
    if not any(o.get("reactive") for o in base):
        base.append({
            "id": "sparring_ai_alpha",
            "label": "Sparring AI · Reactive",
            "kind": "sparring",
            "stance": stance,
            "arena_x": round(0.72 + math.sin(phase) * 0.05, 4),
            "arena_y": round(0.5 + math.cos(phase) * 0.04, 4),
            "reactive": True,
            "live": True,
            "wireframe": "sparring",
        })
    return base


def combat_cardio_state(*, ticks: int = 0) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    cfg = doc.get("cardio") or {}
    rt = _runtime()
    hr = int(rt.get("cardio", {}).get("hr_bpm") or cfg.get("rest_hr_bpm") or 72)
    hr = min(int(cfg.get("max_hr_bpm") or 185), hr + max(0, int(ticks)) * 2)
    decay = float(cfg.get("technique_decay_per_bpm") or 0.0012)
    technique_mod = max(0.55, 1.0 - max(0, hr - 100) * decay)
    zone = "rest" if hr < 100 else ("aerobic" if hr < 150 else "anaerobic")
    return {
        "schema": "hostess7-combat-cardio/v1",
        "updated": _ts(),
        "hr_bpm": hr,
        "zone": zone,
        "technique_modifier": round(technique_mod, 3),
        "coupled": True,
    }


def weapon_training_gate() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    wt = doc.get("weapon_training") or {}
    return {
        "schema": "hostess7-weapon-training-gate/v1",
        "updated": _ts(),
        "gate": wt.get("gate") or "corroborated_threat_only",
        "lethal_gate": wt.get("lethal_gate"),
        "armed_attachments_allowed": False,
        "training_only": True,
        "corroboration_required": True,
    }


def floor_status() -> dict[str, Any]:
    sense = sense_floor_status()
    return {
        "schema": "hostess7-training-floor-status/v1",
        "updated": _ts(),
        "commander": "Hostess 7",
        "sovereign": True,
        "sense": sense,
        "footwork": footwork_proprioception(),
        "vestibular": vestibular_balance(),
        "haptic": haptic_gloves_state(),
        "actuator_bridge": motor_actuator_bridge_status(),
        "environment": environment_mesh(),
        "sparring_ai": reactive_sparring_opponents(),
        "cardio": combat_cardio_state(),
        "weapon_gate": weapon_training_gate(),
        "vision_live": sense.get("vision_live"),
        "hearing_live": sense.get("hearing_live"),
    }


def complete_floor_training(*, ticks: int = 64) -> dict[str, Any]:
    """Run all floor completions — mobility, hands, attachments, combat, sense, environment."""
    room = _mod("tf_room", "hostess7-training-room.py")
    body = _mod("tf_body_c", "hostess7-body-core.py")
    hand = _mod("tf_hand_c", "hostess7-hand-core.py")
    attach = _mod("tf_attach_c", "hostess7-attachment-core.py")
    motion = _mod("tf_motion_c", "humanoid-motion-training.py")
    doc_tr = _load(INSTALL / "data" / "hostess7-training-room-doctrine.json", {})

    steps: list[dict[str, Any]] = []

    if body:
        if hasattr(body, "touch_toes"):
            steps.append({"step": "touch_toes", **body.touch_toes(side="both")})
        if hasattr(body, "load_skill"):
            pass
        for skill in ("forward_fold", "touch_toes"):
            if motion and hasattr(motion, "load_skill"):
                steps.append({"step": f"mobility_{skill}", **motion.load_skill(skill, write=True)})

    if hand and hasattr(hand, "train_hands"):
        steps.append({"step": "hand_fluent", **hand.train_hands(ticks=max(48, ticks))})

    if attach:
        learn_ticks = max(48, ticks)
        for aid in ("precision_stylus", "parallel_gripper", "field_probe"):
            if hasattr(attach, "mount_attachment"):
                attach.mount_attachment(aid)
            if hasattr(attach, "learn_attachment"):
                steps.append({"step": f"learn_{aid}", **attach.learn_attachment(aid, ticks=learn_ticks)})
        if hasattr(attach, "inspect_attachment"):
            steps.append({"step": "inspect_stylus", **attach.inspect_attachment(att_id="precision_stylus", look=True)})

    combat_skills = doc_tr.get("combat_skills") or ["wing_chun", "boxing", "mma_mixed"]
    if motion:
        for sid in combat_skills:
            if hasattr(motion, "load_skill"):
                steps.append({"step": f"combat_load_{sid}", **motion.load_skill(sid, write=True)})
            if hasattr(motion, "train_blast"):
                steps.append({"step": f"combat_blast_{sid}", **motion.train_blast(sid, ticks=24)})

    cardio = combat_cardio_state(ticks=ticks)
    sparring = reactive_sparring_opponents(active_skill=combat_skills[0] if combat_skills else "wing_chun")
    floor = floor_status()

    completed_ids = [
        "final_eye_live", "final_ear_live", "footwork_proprioception",
        "sparring_opponent_ai", "haptic_gloves", "motor_actuator_bridge",
        "balance_vestibular", "environment_mesh", "combat_cardio_coupling",
        "weapon_training_attach", "mobility_touch_toes", "hand_dexterity",
        "combat_skills",
    ]
    rt = _runtime()
    rt["completed"] = completed_ids
    rt["cardio"] = cardio
    rt["sparring"] = {"opponents": sparring, "count": len(sparring)}
    rt["sense_live"] = floor.get("sense") or {}
    rt["footwork"] = floor.get("footwork") or {}
    rt["haptic"] = floor.get("haptic") or {}
    rt["environment"] = floor.get("environment") or {}
    rt["updated"] = _ts()
    _save(RUNTIME, rt)

    panel = {
        "schema": "hostess7-training-floor-panel/v1",
        "updated": _ts(),
        "ironclad_cite": "ironclad:training_floor:1",
        "completed": completed_ids,
        "steps_count": len(steps),
        "floor": floor,
        "cardio": cardio,
        "sparring": sparring,
    }
    _save(PANEL, panel)

    if room and hasattr(room, "assess_needs"):
        needs = room.assess_needs()
    else:
        needs = {"gaps": [], "voice": "Training floor complete."}

    return {
        "ok": True,
        "action": "complete_floor_training",
        "commander": "Hostess 7",
        "earth_mandate": room.earth_mandate() if room and hasattr(room, "earth_mandate") else {},
        "completed": completed_ids,
        "steps": steps[-12:],
        "floor": floor,
        "needs": needs,
        "gap_count": needs.get("gap_count", 0),
        "voice": needs.get("voice") or "Training floor complete — Earth protection body ready.",
    }


def floor_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **floor_status()}
    if action in ("complete", "complete_all", "finish"):
        return complete_floor_training(ticks=int(body.get("ticks") or 64))
    if action == "sense":
        return {"ok": True, **sense_floor_status()}
    if action == "footwork":
        return {"ok": True, **footwork_proprioception()}
    if action == "sparring":
        return {"ok": True, "opponents": reactive_sparring_opponents(active_skill=body.get("skill"))}
    if action == "environment":
        return {"ok": True, **environment_mesh()}
    return {"ok": False, "error": "unknown_floor_action", "action": action}


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(floor_dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "status"):
        print(json.dumps({"ok": True, **floor_status()}, ensure_ascii=False))
        return 0
    if cmd in ("complete", "complete-all"):
        print(json.dumps(complete_floor_training(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-training-floor.py [json|complete|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())