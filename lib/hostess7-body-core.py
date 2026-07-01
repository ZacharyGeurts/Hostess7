#!/usr/bin/env pythong
"""Hostess7 body core — spine, limbs, proprioception, kinematics. Sovereign motor lane."""
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
DOCTRINE = INSTALL / "data" / "hostess7-body-motor-doctrine.json"
POSE = STATE / "hostess7-body-pose.json"
PANEL = STATE / "hostess7-body-panel.json"

# Full humanoid chain — spine segments, shoulders, ankles, toes for bend/touch/reach.
JOINTS: tuple[str, ...] = (
    "head", "neck",
    "spine_upper", "spine_mid", "spine_lower",
    "chest", "hip",
    "shoulder_l", "shoulder_r",
    "elbow_l", "elbow_r",
    "wrist_l", "wrist_r",
    "hand_l", "hand_r",
    "knee_l", "knee_r",
    "ankle_l", "ankle_r",
    "foot_l", "foot_r",
    "toe_l", "toe_r",
)

BONES: tuple[tuple[str, str], ...] = (
    ("head", "neck"),
    ("neck", "spine_upper"),
    ("spine_upper", "spine_mid"),
    ("spine_mid", "spine_lower"),
    ("spine_lower", "chest"),
    ("chest", "hip"),
    ("neck", "shoulder_l"), ("shoulder_l", "elbow_l"), ("elbow_l", "wrist_l"), ("wrist_l", "hand_l"),
    ("neck", "shoulder_r"), ("shoulder_r", "elbow_r"), ("elbow_r", "wrist_r"), ("wrist_r", "hand_r"),
    ("hip", "knee_l"), ("knee_l", "ankle_l"), ("ankle_l", "foot_l"), ("foot_l", "toe_l"),
    ("hip", "knee_r"), ("knee_r", "ankle_r"), ("ankle_r", "foot_r"), ("foot_r", "toe_r"),
)

ZONE_JOINTS: dict[str, tuple[str, ...]] = {
    "head": ("head", "neck"),
    "spine": ("spine_upper", "spine_mid", "spine_lower", "chest"),
    "centerline": ("chest", "spine_mid", "hip"),
    "shoulders": ("shoulder_l", "shoulder_r"),
    "hands": ("hand_l", "hand_r", "wrist_l", "wrist_r"),
    "elbows": ("elbow_l", "elbow_r"),
    "hips": ("hip",),
    "knees": ("knee_l", "knee_r"),
    "ankles": ("ankle_l", "ankle_r"),
    "feet": ("foot_l", "foot_r"),
    "toes": ("toe_l", "toe_r"),
}

# Joint limits (degrees) — flex positive forward/down unless noted.
JOINT_LIMITS: dict[str, dict[str, float]] = {
    "spine_upper": {"flex": 45, "extend": 20, "lateral": 15},
    "spine_mid": {"flex": 55, "extend": 15, "lateral": 12},
    "spine_lower": {"flex": 70, "extend": 10, "lateral": 8},
    "hip": {"flex": 120, "extend": 30, "abduct": 45},
    "knee_l": {"flex": 140, "extend": 5},
    "knee_r": {"flex": 140, "extend": 5},
    "ankle_l": {"flex": 50, "extend": 30},
    "ankle_r": {"flex": 50, "extend": 30},
    "shoulder_l": {"flex": 180, "abduct": 180},
    "shoulder_r": {"flex": 180, "abduct": 180},
}

DEFAULT_POSE: dict[str, dict[str, float]] = {j: {"flex": 0.0, "abduct": 0.0, "rotate": 0.0} for j in JOINTS}


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


def _clamp_joint(joint: str, angles: dict[str, float]) -> dict[str, float]:
    lim = JOINT_LIMITS.get(joint, {})
    out = dict(angles)
    for axis, val in list(out.items()):
        cap = lim.get(axis)
        if cap is not None:
            out[axis] = max(-cap, min(cap, float(val)))
    return out


def load_pose() -> dict[str, Any]:
    doc = _load(POSE, {})
    joints = doc.get("joints") or {}
    merged = {j: {**DEFAULT_POSE.get(j, {}), **(joints.get(j) or {})} for j in JOINTS}
    return {
        "schema": "hostess7-body-pose/v1",
        "updated": doc.get("updated") or _ts(),
        "joints": merged,
        "balance": doc.get("balance") or {"com_x": 0.0, "com_z": 0.55, "grounded": True},
        "stretch": doc.get("stretch") or {},
    }


def save_pose(pose: dict[str, Any]) -> None:
    pose["updated"] = _ts()
    _save(POSE, pose)


def _motion_mod() -> Any | None:
    py = INSTALL / "lib" / "humanoid-motion-training.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("humanoid_motion_body", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _brain_mod() -> Any | None:
    py = INSTALL / "Hostess7" / "scripts" / "field_brain_core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_brain_core_body", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def proprioception_state() -> dict[str, Any]:
    """Joint receipts, stretch limits, balance — what the body knows about itself."""
    pose = load_pose()
    joints = pose["joints"]
    stretch: dict[str, float] = {}
    for joint, lim in JOINT_LIMITS.items():
        cur = joints.get(joint) or {}
        flex = abs(float(cur.get("flex") or 0))
        cap = float(lim.get("flex") or 90)
        stretch[joint] = round(min(1.0, flex / max(cap, 1)), 4)

    com_z = float(pose.get("balance", {}).get("com_z") or 0.55)
    hip_flex = float((joints.get("hip") or {}).get("flex") or 0)
    spine_flex = sum(float((joints.get(j) or {}).get("flex") or 0) for j in ("spine_upper", "spine_mid", "spine_lower"))
    hand_z = 0.75 - (spine_flex + hip_flex) * 0.008
    toe_reach = max(0.0, hand_z - 0.14)

    return {
        "schema": "hostess7-proprioception/v1",
        "updated": _ts(),
        "joint_count": len(JOINTS),
        "bone_count": len(BONES),
        "joints": joints,
        "stretch_ratio": stretch,
        "balance": pose.get("balance"),
        "hand_height_norm": round(hand_z, 4),
        "toe_reach_gap": round(toe_reach, 4),
        "can_touch_toes": hand_z <= 0.16 and hip_flex >= 40 and spine_flex >= 45,
        "grounded": bool(pose.get("balance", {}).get("grounded", True)),
    }


def joint_positions() -> dict[str, dict[str, float]]:
    """Forward kinematics — normalized body coordinates for wireframe."""
    pose = load_pose()
    j = pose["joints"]
    spine_f = sum(float((j.get(k) or {}).get("flex") or 0) for k in ("spine_upper", "spine_mid", "spine_lower")) / 180.0
    hip_f = float((j.get("hip") or {}).get("flex") or 0) / 180.0
    knee_l = float((j.get("knee_l") or {}).get("flex") or 0) / 180.0
    knee_r = float((j.get("knee_r") or {}).get("flex") or 0) / 180.0

    base_z = 0.12
    hip_z = 0.45 - spine_f * 0.08
    chest_z = 0.55 - spine_f * 0.12
    neck_z = 0.72 - spine_f * 0.18
    head_z = 0.92 - spine_f * 0.22

    hand_drop = (spine_f + hip_f) * 0.35
    hand_z = 0.75 - hand_drop
    foot_z = base_z

    return {
        "head": {"x": 0.0, "z": round(head_z, 4)},
        "neck": {"x": 0.0, "z": round(neck_z, 4)},
        "chest": {"x": 0.0, "z": round(chest_z, 4)},
        "hip": {"x": 0.0, "z": round(hip_z, 4)},
        "hand_l": {"x": -0.26, "z": round(hand_z, 4)},
        "hand_r": {"x": 0.26, "z": round(hand_z, 4)},
        "knee_l": {"x": -0.1, "z": round(0.28 + knee_l * 0.05, 4)},
        "knee_r": {"x": 0.1, "z": round(0.28 + knee_r * 0.05, 4)},
        "foot_l": {"x": -0.11, "z": foot_z},
        "foot_r": {"x": 0.11, "z": foot_z},
        "toe_l": {"x": -0.11, "z": round(foot_z + 0.03, 4)},
        "toe_r": {"x": 0.11, "z": round(foot_z + 0.03, 4)},
    }


def _secured_guard() -> Any | None:
    py = INSTALL / "lib" / "humanoid-motion-secured.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("h7bc_secured", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def motor_command(
    joint: str,
    *,
    flex: float | None = None,
    abduct: float | None = None,
    rotate: float | None = None,
    operator: str = "hostess7",
) -> dict[str, Any]:
    if joint not in JOINTS:
        return {"ok": False, "error": "unknown_joint", "joint": joint}
    secured = _secured_guard()
    if secured and hasattr(secured, "guard_motion_command"):
        gate = secured.guard_motion_command(
            joint, flex=flex, abduct=abduct, rotate=rotate, operator=operator,
        )
        if not gate.get("allowed"):
            return {**gate, "ok": False, "error": gate.get("error") or "motion_guard_rejected"}
    pose = load_pose()
    cur = pose["joints"].setdefault(joint, dict(DEFAULT_POSE[joint]))
    if flex is not None:
        cur["flex"] = float(flex)
    if abduct is not None:
        cur["abduct"] = float(abduct)
    if rotate is not None:
        cur["rotate"] = float(rotate)
    pose["joints"][joint] = _clamp_joint(joint, cur)
    save_pose(pose)
    return {"ok": True, "joint": joint, "angles": pose["joints"][joint], "proprioception": proprioception_state()}


def bend_forward(*, degrees: float = 45.0) -> dict[str, Any]:
    """Spinal flexion — fold torso forward."""
    deg = max(0.0, min(90.0, float(degrees)))
    thirds = deg / 3.0
    results = []
    for j in ("spine_upper", "spine_mid", "spine_lower"):
        results.append(motor_command(j, flex=thirds))
    prop = proprioception_state()
    return {
        "ok": True,
        "action": "bend_forward",
        "degrees": deg,
        "joints": [r.get("joint") for r in results],
        "proprioception": prop,
        "positions": joint_positions(),
    }


def touch_toes(*, side: str = "both") -> dict[str, Any]:
    """Hip hinge + spinal flexion + knee soft bend — reach hands to toes."""
    side = str(side or "both").strip().lower()
    bend_forward(degrees=55.0)
    motor_command("hip", flex=75.0)
    motor_command("knee_l", flex=15.0)
    motor_command("knee_r", flex=15.0)
    if side in ("left", "both"):
        motor_command("hand_l", flex=90.0)
    if side in ("right", "both"):
        motor_command("hand_r", flex=90.0)
    prop = proprioception_state()
    secured = _secured_guard()
    if secured and hasattr(secured, "witness_cycle"):
        try:
            secured.witness_cycle(operator="body_cycle")
        except Exception:
            pass
    motion = _motion_mod()
    skill_row = {}
    if motion and hasattr(motion, "load_skill"):
        try:
            skill_row = motion.load_skill("touch_toes", write=True)
        except Exception:
            pass
    return {
        "ok": True,
        "action": "touch_toes",
        "side": side,
        "can_touch_toes": prop.get("can_touch_toes"),
        "proprioception": prop,
        "positions": joint_positions(),
        "motion_skill": skill_row,
    }


def reach(*, target: str = "toes", height: float | None = None) -> dict[str, Any]:
    tgt = str(target or "toes").strip().lower()
    if tgt in ("toes", "feet", "ground"):
        return touch_toes(side="both")
    if tgt in ("knees", "shin"):
        bend_forward(degrees=30.0)
        motor_command("hip", flex=45.0)
        motor_command("hand_l", flex=45.0)
        motor_command("hand_r", flex=45.0)
    elif height is not None:
        h = float(height)
        motor_command("shoulder_l", flex=h * 90)
        motor_command("shoulder_r", flex=h * 90)
    prop = proprioception_state()
    return {"ok": True, "action": "reach", "target": tgt, "proprioception": prop, "positions": joint_positions()}


def reset_pose() -> dict[str, Any]:
    pose = {
        "schema": "hostess7-body-pose/v1",
        "updated": _ts(),
        "joints": {j: dict(DEFAULT_POSE[j]) for j in JOINTS},
        "balance": {"com_x": 0.0, "com_z": 0.55, "grounded": True},
        "stretch": {},
    }
    save_pose(pose)
    return {"ok": True, "action": "reset_pose", "proprioception": proprioception_state()}


def brain_posture() -> dict[str, Any]:
    areas: list[dict[str, Any]] = []
    try:
        brain = _brain_mod()
        if brain and hasattr(brain, "BRAIN_AREAS"):
            areas = [
                {"id": a.get("id"), "name": a.get("name"), "hemisphere": a.get("hemisphere")}
                for a in brain.BRAIN_AREAS
            ]
    except Exception:
        areas = [
            {"id": "prefrontal", "name": "Prefrontal cortex", "hemisphere": "left"},
            {"id": "motor_cortex", "name": "Motor cortex", "hemisphere": "both"},
            {"id": "somatosensory", "name": "Somatosensory cortex", "hemisphere": "both"},
            {"id": "broca", "name": "Broca's area", "hemisphere": "left"},
            {"id": "wernicke", "name": "Wernicke's area", "hemisphere": "left"},
            {"id": "cerebellum", "name": "Cerebellum", "hemisphere": "both"},
        ]
    guard = _load(STATE / "hostess7-brain-guard-panel.json", {})
    return {
        "schema": "hostess7-body-brain/v1",
        "areas": areas,
        "area_count": len(areas),
        "motor_cortex": "body_motor_chamber",
        "brain_guard": guard,
        "sovereign": True,
    }


def body_status() -> dict[str, Any]:
    motion = _motion_mod()
    motion_panel = {}
    if motion and hasattr(motion, "build_panel"):
        try:
            motion_panel = motion.build_panel(write=False)
        except Exception:
            pass
    secured_slice: dict[str, Any] = {}
    secured = _secured_guard()
    if secured and hasattr(secured, "bind_body_image"):
        try:
            secured_slice = {
                "body_image": secured.bind_body_image(),
                "protection": secured.self_protection_status() if hasattr(secured, "self_protection_status") else {},
            }
        except Exception:
            pass
    doctrine = _load(DOCTRINE, {})
    return {
        "schema": "hostess7-body-status/v1",
        "updated": _ts(),
        "commander": "Hostess 7",
        "sovereign": True,
        "loopback_free": True,
        "motto": doctrine.get("motto"),
        "joints": list(JOINTS),
        "zones": list(ZONE_JOINTS.keys()),
        "bones": [list(b) for b in BONES],
        "proprioception": proprioception_state(),
        "positions": joint_positions(),
        "brain": brain_posture(),
        "motion": {
            "active_skill": motion_panel.get("active_skill"),
            "loaded_count": motion_panel.get("loaded_count"),
            "joint_amplitudes": motion_panel.get("joint_amplitudes"),
            "secured": motion_panel.get("secured") or secured_slice,
            "body_image": motion_panel.get("body_image") or secured_slice.get("body_image"),
            "protected_by": "self",
        },
    }


def body_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "posture"):
        return {"ok": True, **body_status()}

    if action in ("proprioception", "proprio", "feel"):
        return {"ok": True, **proprioception_state()}

    if action in ("positions", "fk", "kinematics"):
        return {"ok": True, "positions": joint_positions(), "proprioception": proprioception_state()}

    if action in ("bend", "bend_forward", "flex"):
        return bend_forward(degrees=float(body.get("degrees") or body.get("angle") or 45))

    if action in ("touch_toes", "touch_toe", "toe_touch"):
        return touch_toes(side=str(body.get("side") or "both"))

    if action == "reach":
        return reach(target=str(body.get("target") or "toes"), height=body.get("height"))

    if action in ("reset", "reset_pose", "stand"):
        return reset_pose()

    if action == "motor":
        return motor_command(
            str(body.get("joint") or ""),
            flex=body.get("flex"),
            abduct=body.get("abduct"),
            rotate=body.get("rotate"),
        )

    if action in ("brain", "brain_status"):
        return {"ok": True, **brain_posture()}

    if action in ("load_skill", "train_mobility"):
        motion = _motion_mod()
        sid = str(body.get("skill") or body.get("skill_id") or "touch_toes")
        if motion and hasattr(motion, "load_skill"):
            return {"ok": True, **motion.load_skill(sid, write=True)}
        return {"ok": False, "error": "motion_missing"}

    return {"ok": False, "error": "unknown_body_action", "action": action}