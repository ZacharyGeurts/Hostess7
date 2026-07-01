#!/usr/bin/env pythong
"""Hostess7 hand core — per-finger control, grips, dexterity. Sovereign, in-process."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-hand-doctrine.json"
HAND_STATE = STATE / "hostess7-hand-state.json"
HAND_PANEL = STATE / "hostess7-hand-panel.json"

SIDES = ("left", "right")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")


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


def _finger_keys(side: str) -> list[str]:
    keys: list[str] = []
    for finger in FINGERS:
        segs = ("cmc", "mcp", "ip") if finger == "thumb" else ("mcp", "pip", "dip")
        for seg in segs:
            keys.append(f"{side}_{finger}_{seg}")
    return keys


def _default_fingers() -> dict[str, float]:
    out: dict[str, float] = {}
    for side in SIDES:
        for key in _finger_keys(side):
            out[key] = 0.0
    return out


GRIP_ANGLES: dict[str, dict[str, float]] = {
    "open": {},
    "power": {
        "left_thumb_mcp": 35, "left_thumb_ip": 20,
        "left_index_mcp": 70, "left_index_pip": 65, "left_index_dip": 45,
        "left_middle_mcp": 72, "left_middle_pip": 68, "left_middle_dip": 48,
        "left_ring_mcp": 70, "left_ring_pip": 65, "left_ring_dip": 45,
        "left_pinky_mcp": 68, "left_pinky_pip": 62, "left_pinky_dip": 40,
        "right_thumb_mcp": 35, "right_thumb_ip": 20,
        "right_index_mcp": 70, "right_index_pip": 65, "right_index_dip": 45,
        "right_middle_mcp": 72, "right_middle_pip": 68, "right_middle_dip": 48,
        "right_ring_mcp": 70, "right_ring_pip": 65, "right_ring_dip": 45,
        "right_pinky_mcp": 68, "right_pinky_pip": 62, "right_pinky_dip": 40,
    },
    "precision": {
        "left_thumb_mcp": 45, "left_thumb_ip": 35,
        "left_index_mcp": 55, "left_index_pip": 50, "left_index_dip": 35,
        "right_thumb_mcp": 45, "right_thumb_ip": 35,
        "right_index_mcp": 55, "right_index_pip": 50, "right_index_dip": 35,
    },
    "pinch": {
        "left_thumb_mcp": 50, "left_thumb_ip": 40,
        "left_index_mcp": 58, "left_index_pip": 52, "left_index_dip": 38,
        "right_thumb_mcp": 50, "right_thumb_ip": 40,
        "right_index_mcp": 58, "right_index_pip": 52, "right_index_dip": 38,
    },
    "tripod": {
        "left_thumb_mcp": 42, "left_index_mcp": 52, "left_index_pip": 48,
        "left_middle_mcp": 54, "left_middle_pip": 50,
        "right_thumb_mcp": 42, "right_index_mcp": 52, "right_index_pip": 48,
        "right_middle_mcp": 54, "right_middle_pip": 50,
    },
    "hook": {
        "left_index_mcp": 85, "left_middle_mcp": 88, "left_ring_mcp": 86, "left_pinky_mcp": 84,
        "right_index_mcp": 85, "right_middle_mcp": 88, "right_ring_mcp": 86, "right_pinky_mcp": 84,
    },
    "lateral": {
        "left_thumb_mcp": 30, "left_index_mcp": 25, "left_index_pip": 15,
        "right_thumb_mcp": 30, "right_index_mcp": 25, "right_index_pip": 15,
    },
    "sphere": {
        "left_thumb_mcp": 40, "left_index_mcp": 62, "left_middle_mcp": 64,
        "left_ring_mcp": 62, "left_pinky_mcp": 58,
        "right_thumb_mcp": 40, "right_index_mcp": 62, "right_middle_mcp": 64,
        "right_ring_mcp": 62, "right_pinky_mcp": 58,
    },
}


def load_hand_state() -> dict[str, Any]:
    doc = _load(HAND_STATE, {})
    fingers = {**_default_fingers(), **(doc.get("fingers") or {})}
    return {
        "schema": "hostess7-hand-state/v1",
        "updated": doc.get("updated") or _ts(),
        "fingers": fingers,
        "grip_l": doc.get("grip_l") or "open",
        "grip_r": doc.get("grip_r") or "open",
        "wrist_l": doc.get("wrist_l") or {"flex": 0, "rotate": 0},
        "wrist_r": doc.get("wrist_r") or {"flex": 0, "rotate": 0},
        "proficiency": float(doc.get("proficiency") or 0.35),
        "trained_ticks": int(doc.get("trained_ticks") or 0),
    }


def save_hand_state(state: dict[str, Any]) -> None:
    state["updated"] = _ts()
    _save(HAND_STATE, state)


def set_finger(side: str, finger: str, segment: str, angle: float) -> dict[str, Any]:
    side = side.strip().lower()
    if side not in SIDES:
        return {"ok": False, "error": "invalid_side", "side": side}
    key = f"{side}_{finger}_{segment}"
    state = load_hand_state()
    if key not in state["fingers"]:
        return {"ok": False, "error": "unknown_finger_joint", "key": key}
    state["fingers"][key] = max(0.0, min(95.0, float(angle)))
    save_hand_state(state)
    return {"ok": True, "key": key, "angle": state["fingers"][key]}


def set_grip(side: str, grip: str) -> dict[str, Any]:
    side = side.strip().lower()
    if side not in SIDES:
        return {"ok": False, "error": "invalid_side"}
    grip = grip.strip().lower()
    doctrine = _load(DOCTRINE, {})
    if grip not in (doctrine.get("grips") or GRIP_ANGLES):
        return {"ok": False, "error": "unknown_grip", "grip": grip}
    state = load_hand_state()
    angles = GRIP_ANGLES.get(grip, {})
    if grip == "open":
        for key in state["fingers"]:
            if key.startswith(f"{side}_"):
                state["fingers"][key] = 0.0
    else:
        for key, val in angles.items():
            if key.startswith(f"{side}_") and key in state["fingers"]:
                state["fingers"][key] = float(val)
    if side == "left":
        state["grip_l"] = grip
    else:
        state["grip_r"] = grip
    save_hand_state(state)
    return {"ok": True, "side": side, "grip": grip, "fingers": {k: v for k, v in state["fingers"].items() if k.startswith(f"{side}_")}}


def set_wrist(side: str, *, flex: float | None = None, rotate: float | None = None) -> dict[str, Any]:
    side = side.strip().lower()
    if side not in SIDES:
        return {"ok": False, "error": "invalid_side"}
    state = load_hand_state()
    wrist = state[f"wrist_{side[0]}"] if side == "left" else state["wrist_r"]
    if side == "left":
        wrist = state["wrist_l"]
    else:
        wrist = state["wrist_r"]
    if flex is not None:
        wrist["flex"] = max(-45.0, min(45.0, float(flex)))
    if rotate is not None:
        wrist["rotate"] = max(-90.0, min(90.0, float(rotate)))
    save_hand_state(state)
    return {"ok": True, "side": side, "wrist": wrist}


def finger_summary(side: str) -> dict[str, Any]:
    state = load_hand_state()
    by_finger: dict[str, dict[str, float]] = {}
    for finger in FINGERS:
        segs = ("cmc", "mcp", "ip") if finger == "thumb" else ("mcp", "pip", "dip")
        by_finger[finger] = {
            seg: state["fingers"].get(f"{side}_{finger}_{seg}", 0.0) for seg in segs
        }
    grip = state["grip_l"] if side == "left" else state["grip_r"]
    wrist = state["wrist_l"] if side == "left" else state["wrist_r"]
    return {"side": side, "grip": grip, "wrist": wrist, "fingers": by_finger}


def hand_wireframe() -> dict[str, Any]:
    """Normalized finger chain positions for UI render."""
    state = load_hand_state()
    hands: dict[str, Any] = {}
    for side in SIDES:
        palm = {"x": -0.26 if side == "left" else 0.26, "z": 0.72}
        tips: dict[str, dict[str, float]] = {}
        for finger in FINGERS:
            segs = ("cmc", "mcp", "ip") if finger == "thumb" else ("mcp", "pip", "dip")
            flex_sum = sum(state["fingers"].get(f"{side}_{finger}_{s}", 0) for s in segs)
            span = 0.04 + (finger != "thumb") * (FINGERS.index(finger) * 0.018)
            if side == "left":
                span = -abs(span) if finger != "thumb" else -0.02
            else:
                span = abs(span) if finger != "thumb" else 0.02
            drop = min(0.22, flex_sum * 0.0025)
            tips[finger] = {"x": round(palm["x"] + span, 4), "z": round(palm["z"] + drop, 4), "flex": round(flex_sum, 1)}
        hands[side] = {"palm": palm, "tips": tips, **finger_summary(side)}
    return {"schema": "hostess7-hand-wireframe/v1", "updated": _ts(), "hands": hands, "proficiency": state.get("proficiency")}


def train_hands(*, ticks: int = 24, grip: str | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    gain = float(doctrine.get("train_tick_gain") or 0.018)
    state = load_hand_state()
    grips = list((doctrine.get("grips") or GRIP_ANGLES).keys())
    sequence = grips[:6] if not grip else [grip]
    for i in range(max(1, int(ticks))):
        g = sequence[i % len(sequence)]
        set_grip("left", g)
        set_grip("right", g)
    state = load_hand_state()
    state["trained_ticks"] = int(state.get("trained_ticks") or 0) + int(ticks)
    prof = min(1.0, float(state.get("proficiency") or 0) + gain * int(ticks))
    state["proficiency"] = round(prof, 4)
    floor = float(doctrine.get("proficiency_floor") or 0.72)
    master = float(doctrine.get("master_floor") or 0.95)
    save_hand_state(state)
    return {
        "ok": True,
        "trained_ticks": state["trained_ticks"],
        "proficiency": state["proficiency"],
        "fluent": prof >= floor,
        "mastered": prof >= master,
        "wireframe": hand_wireframe(),
    }


def hand_status() -> dict[str, Any]:
    state = load_hand_state()
    doctrine = _load(DOCTRINE, {})
    floor = float(doctrine.get("proficiency_floor") or 0.72)
    prof = float(state.get("proficiency") or 0)
    return {
        "schema": "hostess7-hand-status/v1",
        "updated": _ts(),
        "commander": "Hostess7",
        "sovereign": True,
        "grips": list((doctrine.get("grips") or {}).keys()),
        "left": finger_summary("left"),
        "right": finger_summary("right"),
        "proficiency": prof,
        "fluent": prof >= floor,
        "mastered": prof >= float(doctrine.get("master_floor") or 0.95),
        "trained_ticks": state.get("trained_ticks"),
        "wireframe": hand_wireframe(),
        "finger_joint_count": len(state.get("fingers") or {}),
    }


def hand_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "wireframe"):
        st = hand_status()
        if action == "wireframe":
            st = {"ok": True, **hand_wireframe()}
        else:
            st = {"ok": True, **st}
        return st

    if action in ("grip", "set_grip"):
        side = str(body.get("side") or body.get("hand") or "both")
        grip = str(body.get("grip") or "open")
        if side == "both":
            return {"ok": True, "left": set_grip("left", grip), "right": set_grip("right", grip), "wireframe": hand_wireframe()}
        return {**set_grip(side, grip), "wireframe": hand_wireframe()}

    if action in ("finger", "set_finger"):
        return set_finger(
            str(body.get("side") or "right"),
            str(body.get("finger") or "index"),
            str(body.get("segment") or "mcp"),
            float(body.get("angle") or body.get("flex") or 0),
        )

    if action == "wrist":
        return set_wrist(str(body.get("side") or "right"), flex=body.get("flex"), rotate=body.get("rotate"))

    if action in ("open", "open_hand"):
        return hand_dispatch({"action": "grip", "side": str(body.get("side") or "both"), "grip": "open"})

    if action in ("train", "train_hands"):
        return train_hands(ticks=int(body.get("ticks") or 24), grip=body.get("grip"))

    if action in ("primitive", "run_primitive"):
        prim = str(body.get("primitive") or "point")
        grip_map = {
            "power_squeeze": "power", "precision_aim": "precision", "point": "precision",
            "precision_grip": "precision", "sphere": "sphere", "release": "open", "open": "open", "close": "power",
        }
        g = grip_map.get(prim, "precision")
        side = str(body.get("side") or "right")
        row = set_grip(side, g)
        return {"ok": True, "primitive": prim, "grip": g, **row, "wireframe": hand_wireframe()}

    return {"ok": False, "error": "unknown_hand_action", "action": action}


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(hand_dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "status", "panel"):
        print(json.dumps({"ok": True, **hand_status()}, ensure_ascii=False))
        return 0
    if cmd == "wireframe":
        print(json.dumps({"ok": True, **hand_wireframe()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-hand-core.py [json|wireframe|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())