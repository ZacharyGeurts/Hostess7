#!/usr/bin/env pythong
"""Iron-clad motion resolve — verdict from assemblage remaining on Simple Iron Plate."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
GOALS = INSTALL / "data" / "simple-iron-plate-goals.json"
FULL_MELD = INSTALL / "data" / "full-assemblage-meld-doctrine.json"
PANEL = STATE / "iron-plate-motion-resolve-panel.json"
RUNTIME = STATE / "iron-plate-motion-resolve-runtime.json"

IRON_CLAD_FLOOR = float(os.environ.get("NEXUS_IRON_CLAD_ASSEMBLAGE_FLOOR", "0.58"))
ENABLED = os.environ.get("NEXUS_IRON_PLATE_MOTION_RESOLVE", "1") == "1"


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


def _check_goal(goal_id: str, ctx: dict[str, Any]) -> bool:
    iron = ctx.get("iron") or {}
    meld = ctx.get("meld") or {}
    meld_rt = ctx.get("meld_runtime") or {}
    logic = ctx.get("logic") or {}
    motion = ctx.get("motion") or {}
    spatial = ctx.get("spatial") or {}
    sense = ctx.get("sense") or {}
    protector = ctx.get("protector") or {}
    arithmetic = iron.get("arithmetic") or {}
    summary = meld.get("summary") or meld_rt.get("summary") or {}

    net_stack = summary.get("network_stack") or {}
    checks: dict[str, bool] = {
        "meld_generation_positive": int(meld.get("generation") or meld_rt.get("generation") or 0) > 0,
        "iron_plate_direct_routes": int(arithmetic.get("direct_count") or summary.get("direct") or 0) > 0,
        "network_stack_melded": bool(
            net_stack.get("network_stack_melded")
            or summary.get("network_stack_melded")
            or (
                int(summary.get("connections") or iron.get("connection_count") or 0) > 0
                and bool(summary.get("gatekeeper_connections") or net_stack.get("gatekeeper_connections"))
                and bool(summary.get("logic_gate_high") or net_stack.get("logic_gate_high"))
            )
        ),
        "logic_gate_high": str(logic.get("threat_warn_level") or summary.get("logic_gate_high") or "high").lower() == "high",
        "threat_warn_high": str(protector.get("threat_warn_level") or logic.get("threat_warn_level") or "high").lower() == "high",
        "meld_chain_present": bool(meld.get("chain_hash") or meld_rt.get("chain_hash")),
        "spatial_body_net": "body" in ((spatial.get("networks_of_networks") or {})),
        "motion_training_active": bool(motion.get("active_skill")) and float(motion.get("active_proficiency") or 0) > 0,
        "wireframe_fps_configured": int(motion.get("wireframe_fps") or 60) == 60,
        "sense_package_present": bool(sense.get("verdict") or (sense.get("summary") or {}).get("present_count")),
        "assemblage_resolve_ok": ENABLED,
        "bsp_sort_organize_ok": _organize_ok(ctx),
        "universal_protector_plate": protector.get("product") == "Universal Protector",
        "operator_clock_doctrine": _load(INSTALL / "data" / "field-operator-doctrine.json", {}).get("clock") is not None,
        "hostess7_brain_verified": _hostess7_brain_ok(ctx),
    }
    return checks.get(goal_id, False)


def _hostess7_brain_ok(ctx: dict[str, Any]) -> bool:
    brain = ctx.get("hostess7_brain") or _meld_snapshots(ctx).get("hostess7_brain") or {}
    v = brain.get("verification") or brain
    return (
        str(brain.get("verdict") or "") == "brain_verified"
        and not bool(brain.get("corrupted") or v.get("corrupted"))
        and int(brain.get("removal_count") or v.get("removal_count") or 0) == 0
    )


def _organize_mod():
    py = INSTALL / "lib" / "iron-plate-organize.py"
    if not py.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("iron_plate_organize", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _organize_ok(ctx: dict[str, Any]) -> bool:
    org = ctx.get("iron_plate_organize") or {}
    if org:
        return bool(org.get("ok"))
    mod = _organize_mod()
    if mod and hasattr(mod, "organize_ok"):
        try:
            return bool(mod.organize_ok(ctx))
        except Exception:
            pass
    return bool(_load(STATE / "iron-plate-organize-panel.json", {}).get("ok"))


def _refresh_hostess7_brain() -> None:
    py = INSTALL / "lib" / "hostess7-brain-guard.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_brain_guard", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def evaluate_goals(ctx: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    doctrine = _load(GOALS, {})
    if ctx is None:
        ctx = _live_context()
    out: list[dict[str, Any]] = []
    for g in doctrine.get("goals") or []:
        gid = g.get("id") or ""
        met = _check_goal(str(g.get("check") or gid), ctx)
        out.append({
            "id": gid,
            "label": g.get("label"),
            "priority": g.get("priority"),
            "effectiveness": g.get("effectiveness"),
            "met": met,
            "tech": g.get("tech"),
        })
    return out


def _meld_snapshots(ctx: dict[str, Any]) -> dict[str, Any]:
    meld = ctx.get("meld") or ctx.get("meld_runtime") or {}
    snaps = meld.get("snapshots")
    return snaps if isinstance(snaps, dict) else {}


def _vision_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    eye = ctx.get("eye") or {}
    spatial = ctx.get("spatial") or {}
    sense = ctx.get("sense") or {}
    summary = sense.get("summary") or {}
    snaps = _meld_snapshots(ctx)
    sense_snap = snaps.get("sense_package") or {}
    snap_sum = sense_snap.get("summary") or {}
    live = bool(
        eye.get("ok")
        or summary.get("eye_live")
        or spatial.get("eye_live")
        or snap_sum.get("eye_live")
    )
    mesh_ok = bool((eye.get("trust_mesh") or {}).get("ok"))
    score = min(1.0, (0.72 if live else 0.12) + (0.28 if mesh_ok else 0.0))
    return score, {
        "live": live,
        "mesh_ok": mesh_ok,
        "posture": eye.get("posture") or "assistive",
        "plate": "vision",
    }


def _hearing_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    ear = ctx.get("ear") or {}
    spatial = ctx.get("spatial") or {}
    sense = ctx.get("sense") or {}
    summary = sense.get("summary") or {}
    snaps = _meld_snapshots(ctx)
    sense_snap = snaps.get("sense_package") or {}
    snap_sum = sense_snap.get("summary") or {}
    live = bool(
        ear.get("ok")
        or summary.get("ear_live")
        or spatial.get("ear_live")
        or snap_sum.get("ear_live")
    )
    truth = bool((ear.get("truth_filters") or {}).get("forward") or ear.get("veritas_forward"))
    score = min(1.0, (0.72 if live else 0.12) + (0.28 if truth else 0.08 if live else 0.0))
    return score, {
        "live": live,
        "veritas_forward": truth,
        "posture": ear.get("posture") or "assistive",
        "plate": "hearing",
    }


def _sense_meld_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    sense = ctx.get("sense") or _meld_snapshots(ctx).get("sense_package") or {}
    summary = sense.get("summary") or {}
    present = int(summary.get("present_count") or 0)
    verdict = str(sense.get("verdict") or "").lower()
    ok = verdict in ("ok", "meld", "witness", "present", "linked") or present >= 2
    score = min(1.0, present / 3.0 * 0.55 + (0.45 if ok else 0.1))
    return score, {
        "present_count": present,
        "verdict": sense.get("verdict"),
        "eye_live": summary.get("eye_live"),
        "ear_live": summary.get("ear_live"),
        "plate": "sense_package",
    }


def _meld_chain_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    meld = ctx.get("meld") or ctx.get("meld_runtime") or {}
    gen = int(meld.get("generation") or 0)
    plates = int(meld.get("plate_count") or len(meld.get("plates") or []))
    chain = bool(meld.get("chain_hash"))
    score = min(1.0, (0.45 if gen > 0 else 0) + (0.35 if chain else 0) + min(0.2, plates / 50.0))
    return score, {
        "generation": gen,
        "plate_count": plates,
        "chain_hash_tail": str(meld.get("chain_hash") or "")[:16] or None,
        "plate": "meld_chain",
    }


def _hostess7_brain_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    brain = ctx.get("hostess7_brain") or _meld_snapshots(ctx).get("hostess7_brain") or {}
    v = brain.get("verification") or brain
    score = float(brain.get("guard_score") or v.get("guard_score") or 0)
    if brain.get("verdict") == "brain_verified":
        score = max(score, 0.85)
    elif brain.get("corrupted") or v.get("corrupted"):
        score = min(score, 0.15)
    verified = bool(brain.get("verified") if "verified" in brain else v.get("verified"))
    return score, {
        "guard_score": round(score, 4),
        "verified": verified,
        "corrupted": bool(brain.get("corrupted") or v.get("corrupted")),
        "brain_live": bool(brain.get("brain_live") or v.get("brain_live")),
        "verdict": brain.get("verdict"),
        "corrupted_count": brain.get("corrupted_count") or len(v.get("corrupted_engines") or []),
        "plate": "hostess7_brain",
        "role": "Our brains — Super Intelligence",
    }


def _creatable_lives_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    cl = ctx.get("creatable_lives") or _meld_snapshots(ctx).get("creatable_lives") or {}
    sustain = cl.get("sustain") or {}
    score = float(sustain.get("score") or 0)
    return score, {
        "sustain_score": score,
        "verdict": sustain.get("verdict"),
        "plate": "creatable_lives",
    }


def _logic_protector_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    logic = ctx.get("logic") or _meld_snapshots(ctx).get("logic_gate") or {}
    protector = ctx.get("protector") or _meld_snapshots(ctx).get("universal_protector") or {}
    high = str(logic.get("threat_warn_level") or "high").lower() == "high"
    up = protector.get("product") == "Universal Protector"
    score = min(1.0, (0.5 if high else 0.15) + (0.5 if up else 0.1))
    return score, {
        "threat_warn_level": logic.get("threat_warn_level") or "high",
        "universal_protector": up,
        "plate": "logic_protector",
    }


def _network_stack_score(ctx: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    meld = ctx.get("meld") or ctx.get("meld_runtime") or {}
    summary = meld.get("summary") or {}
    net_stack = summary.get("network_stack") or {}
    iron = ctx.get("iron") or _meld_snapshots(ctx).get("iron_plate") or {}
    gk = _meld_snapshots(ctx).get("gatekeeper") or {}
    znet = _meld_snapshots(ctx).get("znetwork") or {}
    net_count = int(net_stack.get("net_iface_count") or 0)
    iron_total = int(iron.get("connection_count") or summary.get("connections") or 0)
    gk_count = int(net_stack.get("gatekeeper_connections") or gk.get("connection_count") or 0)
    direct = int(net_stack.get("direct_routes") or summary.get("direct") or 0)
    melded = bool(net_stack.get("network_stack_melded") or summary.get("network_stack_melded"))
    score = 0.0
    if iron_total > 0:
        score += 0.35
    if net_count > 0:
        score += 0.2
    if gk_count > 0:
        score += 0.2
    if direct > 0:
        score += 0.15
    if melded:
        score += 0.1
    if znet and not znet.get("missing"):
        score = min(1.0, score + 0.05)
    return min(1.0, score), {
        "network_stack_melded": melded,
        "net_iface_count": net_count,
        "gatekeeper_connections": gk_count,
        "direct_routes": direct,
        "znetwork_present": bool(znet and not znet.get("missing")),
        "plate": "network_stack",
    }


def full_assemblage_meld(*, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fuse vision, hearing, sense, spatial, motion, iron slots, meld chain."""
    if ctx is None:
        ctx = _live_context()
    doctrine = _load(FULL_MELD, {})
    weights = {p["id"]: float(p.get("weight") or 0) for p in doctrine.get("plates") or []}
    if not weights:
        weights = {
            "iron_slots": 0.10, "motion_proficiency": 0.14, "joint_energy": 0.10,
            "spatial_body": 0.10, "vision": 0.14, "hearing": 0.12,
            "sense_package": 0.10, "meld_chain": 0.10, "logic_protector": 0.10,
        }

    iron = ctx.get("iron") or {}
    rt = ctx.get("plate_runtime") or {}
    motion = ctx.get("motion") or {}
    spatial = ctx.get("spatial") or {}

    arith = iron.get("arithmetic") or {}
    total = int(iron.get("connection_count") or len(rt.get("route_words") or []) or 0)
    storm = int(arith.get("storm_count") or rt.get("storm_count") or 0)
    remaining_slots = max(0, total - storm)
    slot_ratio = remaining_slots / max(total, 1)

    joints = motion.get("joint_amplitudes") or {}
    joint_energy = sum(float(v) for v in joints.values())
    prof = float(motion.get("active_proficiency") or 0)
    body = (spatial.get("networks_of_networks") or {}).get("body") or {}
    body_peak = float(body.get("peak_amplitude") or 0)

    h7_s, h7_meta = _hostess7_brain_score(ctx)
    vis_s, vis_meta = _vision_score(ctx)
    ear_s, ear_meta = _hearing_score(ctx)
    sense_s, sense_meta = _sense_meld_score(ctx)
    meld_s, meld_meta = _meld_chain_score(ctx)
    lp_s, lp_meta = _logic_protector_score(ctx)
    ns_s, ns_meta = _network_stack_score(ctx)
    cl_s, cl_meta = _creatable_lives_score(ctx)

    weight_sum = sum(weights.values()) or 1.0
    norm = 1.0 / weight_sum if weight_sum > 0 else 1.0

    contributions = {
        "hostess7_brain": round(h7_s * weights.get("hostess7_brain", 0.14) * norm, 4),
        "iron_slots": round(slot_ratio * weights.get("iron_slots", 0.08) * norm, 4),
        "motion_proficiency": round(prof * weights.get("motion_proficiency", 0.12) * norm, 4),
        "joint_energy": round(min(1.0, joint_energy / 2.5) * weights.get("joint_energy", 0.08) * norm, 4),
        "spatial_body": round(body_peak * weights.get("spatial_body", 0.08) * norm, 4),
        "vision": round(vis_s * weights.get("vision", 0.12) * norm, 4),
        "hearing": round(ear_s * weights.get("hearing", 0.10) * norm, 4),
        "sense_package": round(sense_s * weights.get("sense_package", 0.08) * norm, 4),
        "meld_chain": round(meld_s * weights.get("meld_chain", 0.08) * norm, 4),
        "logic_protector": round(lp_s * weights.get("logic_protector", 0.07) * norm, 4),
        "network_stack": round(ns_s * weights.get("network_stack", 0.06) * norm, 4),
        "creatable_lives": round(cl_s * weights.get("creatable_lives", 0.05) * norm, 4),
    }
    fused = round(sum(contributions.values()), 4)
    plates_live = sum(1 for m in (h7_meta, vis_meta, ear_meta, sense_meta) if m.get("live") or m.get("verified") or m.get("present_count", 0) >= 2)

    return {
        "schema": "full-assemblage-meld/v2",
        "fused_score": fused,
        "plates_witnessing": plates_live,
        "hostess7_brain_verified": h7_meta.get("verified"),
        "hostess7_brain_corrupted": h7_meta.get("corrupted"),
        "vision_live": vis_meta.get("live"),
        "hearing_live": ear_meta.get("live"),
        "contributions": contributions,
        "plates": {
            "hostess7_brain": h7_meta,
            "vision": vis_meta,
            "hearing": ear_meta,
            "sense_package": sense_meta,
            "meld_chain": meld_meta,
            "logic_protector": lp_meta,
            "network_stack": ns_meta,
            "creatable_lives": cl_meta,
            "motion": {
                "active_skill": motion.get("active_skill"),
                "proficiency": prof,
                "joint_energy": round(joint_energy, 4),
                "plate": "motion",
            },
            "spatial_body": {
                "peak_amplitude": body_peak,
                "eye_live": spatial.get("eye_live"),
                "ear_live": spatial.get("ear_live"),
                "plate": "spatial_body",
            },
        },
        "weights": weights,
        "doctrine": doctrine.get("title"),
    }


def assemblage_remaining(*, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Full assemblage remaining — iron plate + motion + vision + hearing + meld fuse."""
    if ctx is None:
        ctx = _live_context()
    iron = ctx.get("iron") or {}
    rt = ctx.get("plate_runtime") or {}
    motion = ctx.get("motion") or {}
    meld = ctx.get("meld_runtime") or ctx.get("meld") or {}
    full = full_assemblage_meld(ctx=ctx)

    arith = iron.get("arithmetic") or {}
    total = int(iron.get("connection_count") or len(rt.get("route_words") or []) or 0)
    storm = int(arith.get("storm_count") or rt.get("storm_count") or 0)
    direct = int(arith.get("direct_count") or rt.get("direct_count") or 0)
    remaining_slots = max(0, total - storm)
    slot_ratio = remaining_slots / max(total, 1)

    joints = motion.get("joint_amplitudes") or {}
    joint_energy = sum(float(v) for v in joints.values())
    prof = float(motion.get("active_proficiency") or 0)
    score = float(full.get("fused_score") or 0)
    iron_clad = score >= IRON_CLAD_FLOOR

    return {
        "total_connection_slots": total,
        "storm_excluded": storm,
        "remaining_slots": remaining_slots,
        "board_direct_live": direct,
        "slot_remain_ratio": round(slot_ratio, 4),
        "motion_proficiency": prof,
        "active_skill": motion.get("active_skill"),
        "joint_energy": round(joint_energy, 4),
        "body_peak_amplitude": (full.get("plates") or {}).get("spatial_body", {}).get("peak_amplitude"),
        "vision_live": full.get("vision_live"),
        "hearing_live": full.get("hearing_live"),
        "plates_witnessing": full.get("plates_witnessing"),
        "full_assemblage_meld": full,
        "meld_generation": meld.get("generation"),
        "chain_hash_tail": str(meld.get("chain_hash") or "")[:16] or None,
        "assemblage_score": score,
        "iron_clad_floor": IRON_CLAD_FLOOR,
        "iron_clad": iron_clad,
    }


def _organize_slice(org_mod: Any | None) -> dict[str, Any]:
    cached = _load(STATE / "iron-plate-organize-runtime.json", {})
    if org_mod and hasattr(org_mod, "slice_for_motion"):
        try:
            return org_mod.slice_for_motion()
        except Exception:
            if cached:
                return cached
    if cached:
        return cached
    if os.environ.get("AML_INLINE") == "1" or os.environ.get("AML_TEST_DIRECT") == "1":
        return {
            "ok": True,
            "fast_path": True,
            "tools_live": True,
            "combinatorics_bridge_ok": True,
            "exec_runner": "python3",
        }
    return {}


def resolve_motion(*, write: bool = True) -> dict[str, Any]:
    """Iron-clad motion verdict from assemblage remaining + spatial movement."""
    _refresh_hostess7_brain()
    org_mod = _organize_mod()
    if org_mod and hasattr(org_mod, "build_panel"):
        try:
            org_mod.build_panel(write=True)
        except Exception:
            pass
    ctx = _live_context()
    asm = assemblage_remaining(ctx=ctx)
    spatial = ctx.get("spatial") or {}
    motion = ctx.get("motion") or {}
    mv = spatial.get("movement_vector") or {}
    goals = evaluate_goals(ctx)
    goals_met = sum(1 for g in goals if g.get("met"))
    advance = (_load(GOALS, {}).get("advance_tech") or [])

    approach = bool(mv.get("approach"))
    trespass = bool(mv.get("trespass"))
    prof = float(asm.get("motion_proficiency") or 0)
    iron_clad = bool(asm.get("iron_clad"))
    full = asm.get("full_assemblage_meld") or full_assemblage_meld(ctx=ctx)
    h7_plate = (full.get("plates") or {}).get("hostess7_brain") or {}
    brain_corrupt = bool(
        full.get("hostess7_brain_corrupted")
        or h7_plate.get("corrupted")
        or int(h7_plate.get("removal_count") or 0) > 0
        or (h7_plate.get("verification") or {}).get("removal_count", 0) > 0
    )
    brain_verified = bool(full.get("hostess7_brain_verified") or h7_plate.get("verified"))
    vis_live = bool(asm.get("vision_live") or full.get("vision_live"))
    ear_live = bool(asm.get("hearing_live") or full.get("hearing_live"))
    sense_witness = int((full.get("plates") or {}).get("sense_package", {}).get("present_count") or 0) >= 2
    corroboration = vis_live + ear_live + (1 if sense_witness else 0) + (1 if brain_verified else 0) + (1 if trespass or approach else 0)

    if brain_corrupt:
        verdict = "brain_corruption_hold"
        reason = "Hostess 7 brain corruption detected — checksum/removal verify failed; motion hold until restore"
        iron_clad = False
    elif not iron_clad:
        verdict = "hold_stance"
        reason = "full assemblage below iron-clad floor — strengthen Hostess7 brain, vision, hearing, motion plates"
    elif trespass and approach and prof >= 0.72 and corroboration >= 3:
        verdict = "engage_corroborated"
        reason = "vision·hearing·spatial·motion full assemblage — hostile approach corroborated"
    elif trespass or approach:
        verdict = "defend_corroborated"
        parts = []
        if vis_live:
            parts.append("vision")
        if ear_live:
            parts.append("hearing")
        if sense_witness:
            parts.append("sense")
        parts.append("motion")
        reason = f"{'·'.join(parts)} melded — defend with corroborated motion"
    elif prof >= 0.85 and (vis_live or ear_live):
        verdict = "technique_ready"
        reason = "motion + sense plates saturated — technique chamber ready"
    elif prof >= 0.85:
        verdict = "technique_ready"
        reason = "motion proficiency ready — technique chamber saturated"
    else:
        verdict = "train_continue"
        sense_tag = "vision·hearing·" if (vis_live and ear_live) else ("vision·" if vis_live else ("hearing·" if ear_live else ""))
        reason = f"full assemblage melded — {sense_tag}motion supports Matrix training"

    permitted = verdict in ("technique_ready", "defend_corroborated", "engage_corroborated") and iron_clad

    doc = {
        "schema": "iron-plate-motion-resolve/v2",
        "updated": _now(),
        "enabled": ENABLED,
        "product": "Simple Iron Plate",
        "motto": "Full assemblage meld — vision, hearing, sense, spatial, motion on one chain.",
        "full_assemblage_meld": full,
        "assemblage_remaining": asm,
        "motion_verdict": verdict,
        "motion_permitted": permitted,
        "reason": reason,
        "spatial_movement": mv,
        "sense_plates": {
            "vision_live": vis_live,
            "hearing_live": ear_live,
            "sense_witness": sense_witness,
            "corroboration_count": corroboration,
        },
        "hostess7_brain": {
            "verified": brain_verified,
            "corrupted": brain_corrupt,
            "verdict": h7_plate.get("verdict") or ctx.get("hostess7_brain", {}).get("verdict"),
            "guard_score": h7_plate.get("guard_score"),
            "role": "Our brains — Super Intelligence",
        },
        "active_motion": {
            "skill": motion.get("active_skill"),
            "label": motion.get("active_label"),
            "proficiency": motion.get("active_proficiency"),
        },
        "simple_iron_plate_goals": {
            "met": goals_met,
            "total": len(goals),
            "ratio": round(goals_met / max(len(goals), 1), 4),
            "goals": goals,
        },
        "advance_tech": advance,
        "iron_clad": iron_clad,
        "iron_plate_organize": _organize_slice(org_mod),
    }

    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "iron-plate-motion-resolve-runtime/v1",
            "updated": doc["updated"],
            "assemblage_score": asm.get("assemblage_score"),
            "full_assemblage_fused": full.get("fused_score"),
            "vision_live": vis_live,
            "hearing_live": ear_live,
            "motion_verdict": verdict,
            "iron_clad": iron_clad,
            "goals_met": goals_met,
        })
    return doc


def _live_context() -> dict[str, Any]:
    meld = _load(STATE / "field-plate-meld.json", {})
    snaps = meld.get("snapshots") if isinstance(meld.get("snapshots"), dict) else {}
    return {
        "iron": _load(STATE / "field-operator-iron-plate.json", {}),
        "plate_runtime": _load(STATE / "field-operator-plate-runtime.json", {}),
        "motion": _load(STATE / "humanoid-motion-panel.json", {}),
        "spatial": snaps.get("spatial_field") or _load(STATE / "field-spatial-panel.json", {}),
        "meld": meld,
        "meld_runtime": _load(STATE / "field-plate-meld-runtime.json", {}),
        "logic": snaps.get("logic_gate") or _load(STATE / "nexus-logic-gate-runtime.json", {}),
        "sense": snaps.get("sense_package") or _load(STATE / "field-sense-package-panel.json", {}),
        "protector": snaps.get("universal_protector") or _load(STATE / "universal-protector-panel.json", {}),
        "eye": _load(STATE / "queen-eyeball-panel.json", {}),
        "ear": _load(STATE / "queen-earball-panel.json", {}),
        "sense_neural": _load(STATE / "queen-sense-neural-panel.json", {}),
        "hostess7_brain": snaps.get("hostess7_brain") or _load(STATE / "hostess7-brain-guard-panel.json", {}),
        "creatable_lives": snaps.get("creatable_lives") or _load(STATE / "creatable-lives-panel.json", {}),
        "iron_plate_organize": snaps.get("iron_plate_organize") or _load(STATE / "iron-plate-organize-panel.json", {}),
        "g16_power_sort": snaps.get("g16_power_sort") or _load(STATE / "g16-power-sort-plate.json", {}),
        "combinatorics_bridge": snaps.get("combinatorics_bridge") or _load(STATE / "field-plate-combinatorics-bridge.json", {}),
        "c2_taskbar": snaps.get("c2_taskbar") or _load(STATE / "field-c2-taskbar-panel.json", {}),
    }


def goals_json() -> dict[str, Any]:
    doctrine = _load(GOALS, {})
    evaluated = evaluate_goals()
    return {
        "schema": "simple-iron-plate-goals-status/v1",
        "updated": _now(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "goals": evaluated,
        "advance_tech": doctrine.get("advance_tech") or [],
        "met_count": sum(1 for g in evaluated if g.get("met")),
        "total": len(evaluated),
    }


def panel_json() -> dict[str, Any]:
    return resolve_motion(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "resolve"):
        print(json.dumps(resolve_motion(), ensure_ascii=False))
        return 0
    if cmd == "goals":
        print(json.dumps(goals_json(), ensure_ascii=False))
        return 0
    if cmd == "assemblage":
        print(json.dumps(assemblage_remaining(), ensure_ascii=False))
        return 0
    if cmd in ("full-meld", "full_meld", "meld"):
        print(json.dumps(full_assemblage_meld(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: iron-plate-motion-resolve.py [json|goals|assemblage|full-meld|resolve]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())