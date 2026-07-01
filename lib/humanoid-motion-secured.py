#!/usr/bin/env pythong
"""Humanoid motion secured — limb identity, expansive range, body image tie, self-protection."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "humanoid-motion-secured-doctrine.json"
PANEL = STATE / "humanoid-motion-secured-panel.json"
LEDGER = STATE / "humanoid-motion-secured.jsonl"
REGISTRY = STATE / "humanoid-motion-limb-registry.json"

_SIDE_MAP = {
    "head": "center",
    "neck": "center",
    "spine_upper": "center",
    "spine_mid": "center",
    "spine_lower": "center",
    "chest": "center",
    "hip": "center",
    "shoulder_l": "left",
    "elbow_l": "left",
    "wrist_l": "left",
    "hand_l": "left",
    "shoulder_r": "right",
    "elbow_r": "right",
    "wrist_r": "right",
    "hand_r": "right",
    "knee_l": "left",
    "ankle_l": "left",
    "foot_l": "left",
    "toe_l": "left",
    "knee_r": "right",
    "ankle_r": "right",
    "foot_r": "right",
    "toe_r": "right",
}

_LIMB_GROUP_FOR: dict[str, str] = {}


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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": row.get("ts") or _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import(rel: str, name: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _body_core() -> Any | None:
    return _import("hostess7-body-core.py", "h7ms_body_core")


def _limb_group_index(doc: dict[str, Any]) -> dict[str, str]:
    global _LIMB_GROUP_FOR
    if _LIMB_GROUP_FOR:
        return _LIMB_GROUP_FOR
    for group, joints in (doc.get("limb_groups") or {}).items():
        for j in joints:
            _LIMB_GROUP_FOR[str(j)] = str(group)
    return _LIMB_GROUP_FOR


def _zone_for_joint(joint: str, doc: dict[str, Any]) -> str:
    for zone, joints in (doc.get("zone_map") or {}).items():
        if joint in joints:
            return str(zone)
    return "unknown"


def limb_identity_registry(*, write: bool = False) -> dict[str, Any]:
    """Full limb identity — joint id, side, zone, group, range envelope, body image anchor."""
    doc = _load(DOCTRINE, {})
    body = _body_core()
    joints: tuple[str, ...] = ()
    bones: list[list[str]] = []
    motor_limits: dict[str, dict[str, float]] = {}
    if body:
        joints = getattr(body, "JOINTS", ())
        bones = [list(b) for b in getattr(body, "BONES", ())]
        motor_limits = dict(getattr(body, "JOINT_LIMITS", {}))

    expanded = doc.get("expanded_envelopes") or {}
    group_idx = _limb_group_index(doc)
    positions: dict[str, Any] = {}
    proprio: dict[str, Any] = {}
    if body:
        if hasattr(body, "joint_positions"):
            try:
                positions = body.joint_positions()
            except Exception:
                pass
        if hasattr(body, "proprioception_state"):
            try:
                proprio = body.proprioception_state()
            except Exception:
                pass

    limbs: list[dict[str, Any]] = []
    for joint in joints:
        motor = motor_limits.get(joint, {})
        envelope = expanded.get(joint) or motor
        cur = (proprio.get("joints") or {}).get(joint) or {}
        pos = positions.get(joint) or {}
        zone = _zone_for_joint(joint, doc)
        limbs.append({
            "id": joint,
            "side": _SIDE_MAP.get(joint, "center"),
            "zone": zone,
            "limb_group": group_idx.get(joint, "unknown"),
            "motor_limits": motor,
            "range_envelope": envelope,
            "expansive": bool(expanded.get(joint)),
            "body_image": {
                "x": pos.get("x"),
                "z": pos.get("z"),
                "flex": cur.get("flex"),
                "abduct": cur.get("abduct"),
                "rotate": cur.get("rotate"),
            },
            "stretch_ratio": (proprio.get("stretch_ratio") or {}).get(joint),
        })

    out = {
        "schema": "humanoid-motion-limb-registry/v1",
        "updated": _now(),
        "joint_count": len(limbs),
        "bone_count": len(bones),
        "bones": bones,
        "limbs": limbs,
        "zone_map": doc.get("zone_map") or {},
        "limb_groups": doc.get("limb_groups") or {},
        "range_policy": doc.get("range_policy") or {},
        "self_protection": doc.get("self_protection") or {},
    }
    if write:
        _save(REGISTRY, out)
    return out


def bind_body_image() -> dict[str, Any]:
    """Tie actual body pose, wireframe positions, and motion zones into one image."""
    doc = _load(DOCTRINE, {})
    body = _body_core()
    registry = limb_identity_registry(write=False)
    motion_panel = _load(STATE / "humanoid-motion-panel.json", {})
    amplitudes: dict[str, float] = dict(motion_panel.get("joint_amplitudes") or {})
    body_motion: list[dict[str, Any]] = list(motion_panel.get("body_motion") or [])
    motion = _import("humanoid-motion-training.py", "h7ms_motion")
    if motion:
        if not amplitudes and hasattr(motion, "joint_amplitudes"):
            try:
                amplitudes = motion.joint_amplitudes()
            except Exception:
                pass
        if not body_motion and hasattr(motion, "body_motion_amplitudes"):
            try:
                body_motion = motion.body_motion_amplitudes()
            except Exception:
                pass

    positions: dict[str, Any] = {}
    proprio: dict[str, Any] = {}
    if body:
        if hasattr(body, "joint_positions"):
            try:
                positions = body.joint_positions()
            except Exception:
                pass
        if hasattr(body, "proprioception_state"):
            try:
                proprio = body.proprioception_state()
            except Exception:
                pass

    zone_overlay: dict[str, dict[str, Any]] = {}
    for zone, joint_ids in (doc.get("zone_map") or {}).items():
        pts: list[dict[str, Any]] = []
        for jid in joint_ids:
            p = positions.get(jid) or {}
            if p:
                pts.append({"joint": jid, "x": p.get("x"), "z": p.get("z")})
        zone_overlay[str(zone)] = {
            "joints": list(joint_ids),
            "positions": pts,
            "amplitude": max((amplitudes.get(j, 0.0) for j in joint_ids), default=0.0),
        }

    return {
        "schema": "humanoid-motion-body-image/v1",
        "updated": _now(),
        "source": (doc.get("body_image") or {}).get("source"),
        "positions": positions,
        "proprioception": {
            "can_touch_toes": proprio.get("can_touch_toes"),
            "hand_height_norm": proprio.get("hand_height_norm"),
            "grounded": proprio.get("grounded"),
            "balance": proprio.get("balance"),
        },
        "registry_joint_count": registry.get("joint_count"),
        "zone_overlay": zone_overlay,
        "joint_amplitudes": amplitudes,
        "body_motion": body_motion,
        "active_skill": motion_panel.get("active_skill"),
        "wireframe_bones": registry.get("bones"),
    }


def _component_path(spec: dict[str, Any]) -> Path:
    rel = str(spec.get("module") or "").strip()
    if not rel:
        return INSTALL / "missing"
    p = Path(rel)
    if p.is_absolute():
        return p
    if rel.startswith("lib/"):
        return INSTALL / rel
    return INSTALL / "lib" / rel


def _component_present(spec: dict[str, Any]) -> bool:
    return _component_path(spec).is_file()


def self_protection_status() -> dict[str, Any]:
    """Every motion component must be present and protected by self."""
    doc = _load(DOCTRINE, {})
    policy = doc.get("self_protection") or {}
    components: list[dict[str, Any]] = []
    all_ok = True
    for spec in doc.get("protected_components") or []:
        present = _component_present(spec)
        row = {
            "id": spec.get("id"),
            "module": spec.get("module"),
            "role": spec.get("role"),
            "present": present,
            "protected_by": policy.get("protected_by") or "self",
            "outside_override": False,
        }
        if not present:
            all_ok = False
        components.append(row)

    self_maint = _import("hostess7-self-maintenance.py", "h7ms_self_maint")
    posture: dict[str, Any] = {}
    if self_maint and hasattr(self_maint, "self_maintenance_posture"):
        try:
            posture = self_maint.self_maintenance_posture()
        except Exception:
            pass

    return {
        "schema": "humanoid-motion-self-protection/v1",
        "updated": _now(),
        "protected_by": policy.get("protected_by") or "self",
        "sovereign_operator": policy.get("sovereign_operator") or "hostess7",
        "outside_override": bool(policy.get("outside_override", False)),
        "advisory_only_ingress": bool(policy.get("advisory_only_ingress", True)),
        "all_components_present": all_ok,
        "component_count": len(components),
        "components": components,
        "self_maintenance": {
            "self_maintained": posture.get("self_maintained"),
            "visibility": posture.get("visibility"),
            "due_count": posture.get("due_count"),
        },
        "secured": all_ok and not bool(policy.get("outside_override", False)),
    }


def guard_motion_command(
    joint: str,
    *,
    flex: float | None = None,
    abduct: float | None = None,
    rotate: float | None = None,
    operator: str = "hostess7",
) -> dict[str, Any]:
    """Identity + expansive envelope guard — rejects outside override and out-of-range."""
    doc = _load(DOCTRINE, {})
    policy = doc.get("self_protection") or {}
    op = str(operator or "").strip().lower()
    sovereign = str(policy.get("sovereign_operator") or "hostess7").lower()
    if op not in (sovereign, "self", "hostess7", "body_cycle", "motion_secure_cycle"):
        return {
            "ok": False,
            "allowed": False,
            "error": "outside_override_rejected",
            "operator": op,
            "protected_by": "self",
        }

    registry = limb_identity_registry(write=False)
    known = {l["id"]: l for l in registry.get("limbs") or []}
    jid = str(joint or "").strip()
    if jid not in known:
        return {"ok": False, "allowed": False, "error": "unknown_joint_identity", "joint": jid}

    limb = known[jid]
    envelope = limb.get("range_envelope") or {}
    angles: dict[str, float] = {}
    violations: list[str] = []
    for axis, val in (("flex", flex), ("abduct", abduct), ("rotate", rotate)):
        if val is None:
            continue
        cap = envelope.get(axis)
        v = float(val)
        angles[axis] = v
        if cap is not None and abs(v) > float(cap):
            violations.append(f"{axis}:{v}>{cap}")

    allowed = len(violations) == 0
    row = {
        "ok": allowed,
        "allowed": allowed,
        "joint": jid,
        "identity": {
            "side": limb.get("side"),
            "zone": limb.get("zone"),
            "limb_group": limb.get("limb_group"),
        },
        "angles": angles,
        "range_envelope": envelope,
        "violations": violations,
        "protected_by": "self",
        "operator": op,
    }
    _append({"event": "guard_motion", **row})
    return row


def protect_component(fn: Callable[..., Any], *, component_id: str = "motion") -> Callable[..., Any]:
    """Wrap a motion callable — self-protection gate before execution."""

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        status = self_protection_status()
        if not status.get("secured"):
            return {
                "ok": False,
                "error": "motion_not_secured",
                "protected_by": "self",
                "component_id": component_id,
                "status": status,
            }
        body = kwargs.get("body") if isinstance(kwargs.get("body"), dict) else {}
        operator = str(kwargs.get("operator") or body.get("operator") or "hostess7")
        policy = _load(DOCTRINE, {}).get("self_protection") or {}
        sovereign = str(policy.get("sovereign_operator") or "hostess7").lower()
        if str(operator).lower() not in (sovereign, "self", "hostess7", "body_cycle", "motion_secure_cycle"):
            return {
                "ok": False,
                "error": "outside_override_rejected",
                "protected_by": "self",
                "component_id": component_id,
            }
        joint = kwargs.get("joint") or (body.get("joint") if body else None)
        if joint:
            gate = guard_motion_command(
                str(joint),
                flex=kwargs.get("flex") or body.get("flex"),
                abduct=kwargs.get("abduct") or body.get("abduct"),
                rotate=kwargs.get("rotate") or body.get("rotate"),
                operator=operator,
            )
            if not gate.get("allowed"):
                return {**gate, "component_id": component_id}
        return fn(*args, **kwargs)

    wrapped.__name__ = getattr(fn, "__name__", "protected")
    wrapped.__doc__ = fn.__doc__
    return wrapped


def witness_cycle(*, operator: str = "hostess7") -> dict[str, Any]:
    """Self-maintenance witness — refresh registry, body image, protection receipts."""
    registry = limb_identity_registry(write=True)
    image = bind_body_image()
    protection = self_protection_status()
    row = {
        "schema": "humanoid-motion-secured-witness/v1",
        "ok": bool(protection.get("secured")),
        "operator": operator,
        "joint_count": registry.get("joint_count"),
        "zone_count": len(registry.get("zone_map") or {}),
        "body_image_zones": len(image.get("zone_overlay") or {}),
        "components_secured": protection.get("component_count"),
        "all_components_present": protection.get("all_components_present"),
        "protected_by": "self",
    }
    _append({"event": "witness_cycle", **row})
    self_maint = _import("hostess7-self-maintenance.py", "h7ms_witness_maint")
    if self_maint and hasattr(self_maint, "record_task"):
        try:
            self_maint.record_task("motion_secure_cycle", note=f"joints={registry.get('joint_count')}", operator=operator)
        except Exception:
            pass
    return row


def merge_into_motion_panel(panel: dict[str, Any]) -> dict[str, Any]:
    """Enrich humanoid-motion panel with secured limb identity and body image."""
    registry = limb_identity_registry(write=False)
    image = bind_body_image()
    protection = self_protection_status()
    panel["secured"] = {
        "schema": "humanoid-motion-secured-slice/v1",
        "protected_by": "self",
        "outside_override": False,
        "limb_identity_count": registry.get("joint_count"),
        "zone_count": len(registry.get("zone_map") or {}),
        "expansive_envelopes": sum(1 for l in (registry.get("limbs") or []) if l.get("expansive")),
        "body_image": image,
        "protection": protection,
        "registry_path": str(REGISTRY.relative_to(STATE)) if REGISTRY.is_relative_to(STATE) else str(REGISTRY),
    }
    panel["body_image"] = image
    panel["limb_registry"] = {
        "joint_count": registry.get("joint_count"),
        "zones": list((registry.get("zone_map") or {}).keys()),
        "limb_groups": list((registry.get("limb_groups") or {}).keys()),
    }
    panel["joint_amplitudes"] = {
        **(panel.get("joint_amplitudes") or {}),
        **(image.get("joint_amplitudes") or {}),
    }
    return panel


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    registry = limb_identity_registry(write=write)
    image = bind_body_image()
    protection = self_protection_status()
    motion_slice = _load(STATE / "humanoid-motion-panel.json", {})

    out = {
        "schema": "humanoid-motion-secured-panel/v1",
        "updated": _now(),
        "ok": bool(protection.get("secured")),
        "motto": doc.get("motto"),
        "protected_by": "self",
        "outside_override": False,
        "commander": doc.get("commander") or "hostess7",
        "limb_registry": registry,
        "body_image": image,
        "self_protection": protection,
        "motion_training": {
            "active_skill": motion_slice.get("active_skill"),
            "loaded_count": motion_slice.get("loaded_count"),
            "physics_mode": motion_slice.get("physics_mode"),
            "joint_amplitudes": motion_slice.get("joint_amplitudes"),
        },
        "range_policy": doc.get("range_policy"),
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_relative_to(INSTALL) else str(DOCTRINE),
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower().replace("-", "_")
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "registry":
        print(json.dumps(limb_identity_registry(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "body_image":
        print(json.dumps(bind_body_image(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "protection":
        print(json.dumps(self_protection_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "witness":
        print(json.dumps(witness_cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "guard":
        joint = sys.argv[2] if len(sys.argv) > 2 else "hip"
        flex = float(sys.argv[3]) if len(sys.argv) > 3 else None
        print(json.dumps(guard_motion_command(joint, flex=flex), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: humanoid-motion-secured.py [panel|registry|body_image|protection|witness|guard JOINT [FLEX]]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())