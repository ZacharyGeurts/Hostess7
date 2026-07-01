#!/usr/bin/env pythong
"""Humanoid motion training — Matrix-style skill load (kung fu, MMA, grappling)."""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "humanoid-motion-doctrine.json"
RUNTIME = STATE / "humanoid-motion-runtime.json"
PANEL = STATE / "humanoid-motion-panel.json"
LEDGER = STATE / "humanoid-motion-ledger.jsonl"

TRAIN_TICKS_DEFAULT = int(os.environ.get("NEXUS_HUMANOID_MOTION_TRAIN_TICKS", "120"))
TRAIN_BLAST_TICKS_BASE = int(os.environ.get("NEXUS_HUMANOID_MOTION_TRAIN_BLAST_TICKS", "48"))
TRAIN_INTENSITY = float(os.environ.get("NEXUS_HUMANOID_MOTION_TRAIN_INTENSITY", "0.85"))
TRAIN_BLAST_TICKS = max(1, int(TRAIN_BLAST_TICKS_BASE * TRAIN_INTENSITY))
WIREFRAME_FPS = int(os.environ.get("NEXUS_HUMANOID_WIREFRAME_FPS", "60"))
DATA_PEEK_FPS = int(os.environ.get("NEXUS_HUMANOID_DATA_PEEK_FPS", "60"))
ENABLED = os.environ.get("NEXUS_HUMANOID_MOTION_TRAINING", "1") == "1"
FULL_BLAST = os.environ.get("NEXUS_HUMANOID_MOTION_FULL_BLAST", "1") == "1"


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _skill_catalog(doctrine: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    doc = doctrine or _load(DOCTRINE, {})
    return {s["id"]: s for s in doc.get("skills") or [] if s.get("id")}


def _runtime() -> dict[str, Any]:
    return _load(RUNTIME, {
        "schema": "humanoid-motion-runtime/v1",
        "loaded": {},
        "active_skill": None,
        "training": None,
        "total_ticks": 0,
    })


def _matrix_policy(doctrine: dict[str, Any]) -> dict[str, Any]:
    return doctrine.get("matrix_load") or {}


def _physics_mod() -> Any | None:
    import importlib.util

    py = INSTALL / "lib" / "hostess7-reality-physics-training.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("h7reality_physics", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _physics_state() -> dict[str, Any]:
    rp = _physics_mod()
    if rp and hasattr(rp, "gravity_sim_state"):
        return rp.gravity_sim_state()
    policy = _matrix_policy(_load(DOCTRINE, {}))
    return {
        "com_y": float(policy.get("ground_y_norm") or 0.12),
        "com_vy": 0.0,
        "grounded": True,
        "gravity_m_s2": float(policy.get("gravity_m_s2") or 9.80665),
        "stance_stability": 0.0,
    }


def _physics_train_tick() -> dict[str, Any]:
    rp = _physics_mod()
    if not rp or not hasattr(rp, "gravity_sim_step"):
        return {"ok": False, "skipped": True}
    return rp.gravity_sim_step(impulse_vy=0.04, write=True)


def load_skill(skill_id: str, *, write: bool = True) -> dict[str, Any]:
    """Skill scaffold on body lattice — physics floor, not Matrix instant proficiency."""
    doctrine = _load(DOCTRINE, {})
    catalog = _skill_catalog(doctrine)
    sid = (skill_id or "").strip().lower().replace(" ", "_")
    skill = catalog.get(sid)
    if not skill:
        return {"ok": False, "error": "unknown_skill", "skill_id": sid, "available": sorted(catalog.keys())}

    policy = _matrix_policy(doctrine)
    physics_mode = bool(doctrine.get("physics_mode", True))
    instant = 0.0 if physics_mode else float(policy.get("instant_proficiency", 0.72))
    floor = float(policy.get("physics_tick_bonus", 0.06)) if physics_mode else instant
    rt = _runtime()
    loaded = rt.setdefault("loaded", {})
    prev = loaded.get(sid) or {}
    proficiency = max(float(prev.get("proficiency") or 0), instant, floor if not prev else 0.0)
    loaded[sid] = {
        "id": sid,
        "label": skill.get("label"),
        "family": skill.get("family"),
        "proficiency": round(min(1.0, proficiency), 4),
        "matrix_loaded": not physics_mode,
        "physics_loaded": physics_mode,
        "loaded_at": _now(),
        "ticks": int(prev.get("ticks") or 0),
        "primitives": skill.get("primitives") or [],
        "matrix_quote": skill.get("matrix_quote") or f"I know {skill.get('label')}.",
        "training_quote": f"Training {skill.get('label')} under gravity — receipts, not instant load.",
    }
    rt["active_skill"] = sid
    rt["updated"] = _now()
    if write:
        _save(RUNTIME, rt)
        _append_ledger({"ts": rt["updated"], "event": "matrix_load", "skill": sid, "proficiency": proficiency})
    return {
        "ok": True,
        "event": "matrix_load",
        "skill": loaded[sid],
        "matrix_quote": loaded[sid]["matrix_quote"],
        "training_quote": loaded[sid].get("training_quote"),
        "physics_mode": physics_mode,
        "message": (
            loaded[sid].get("training_quote")
            if physics_mode
            else f"{loaded[sid]['matrix_quote']} Skill amplitude injected."
        ),
    }


def train_ticks(skill_id: str | None = None, *, ticks: int = 1, write: bool = True) -> dict[str, Any]:
    """Run training ticks — proficiency climbs on the body lattice."""
    doctrine = _load(DOCTRINE, {})
    catalog = _skill_catalog(doctrine)
    policy = _matrix_policy(doctrine)
    doctrine_doc = doctrine
    physics_mode = bool(doctrine_doc.get("physics_mode", True))
    rate = float(policy.get("train_tick_proficiency", 0.018)) * TRAIN_INTENSITY
    phys_bonus = float(policy.get("physics_tick_bonus", 0.006)) if physics_mode else 0.0
    max_prof = float(policy.get("max_proficiency", 1.0))
    rt = _runtime()
    sid = (skill_id or rt.get("active_skill") or "").strip().lower()
    if not sid or sid not in catalog:
        return {"ok": False, "error": "no_active_skill", "hint": "load a skill first"}

    loaded = rt.setdefault("loaded", {})
    row = loaded.setdefault(sid, {
        "id": sid,
        "label": catalog[sid].get("label"),
        "family": catalog[sid].get("family"),
        "proficiency": 0.0,
        "ticks": 0,
        "primitives": catalog[sid].get("primitives") or [],
    })

    n = max(1, min(int(ticks), 10_000))
    last_phys: dict[str, Any] = {}
    for _ in range(n):
        tick_rate = rate
        if physics_mode:
            last_phys = _physics_train_tick()
            sim = last_phys.get("physics_sim") or {}
            stability = float(sim.get("stance_stability") or 0)
            if sim.get("grounded") and sim.get("energy_ok"):
                tick_rate += phys_bonus * (0.5 + stability * 0.5)
        row["proficiency"] = round(min(max_prof, float(row.get("proficiency") or 0) + tick_rate), 4)
        row["ticks"] = int(row.get("ticks") or 0) + 1
    rt["total_ticks"] = int(rt.get("total_ticks") or 0) + n
    rt["active_skill"] = sid
    rt["training"] = {
        "skill": sid,
        "ticks_ran": n,
        "proficiency": row["proficiency"],
        "physics_mode": physics_mode,
        "physics_sim": last_phys.get("physics_sim") if physics_mode else None,
        "updated": _now(),
    }
    if physics_mode:
        rt["physics_state"] = _physics_state()
    rt["updated"] = _now()
    if write:
        _save(RUNTIME, rt)
        _append_ledger({
            "ts": rt["updated"],
            "event": "train",
            "skill": sid,
            "ticks": n,
            "proficiency": row["proficiency"],
        })
    return {
        "ok": True,
        "event": "train",
        "skill": row,
        "ticks_ran": n,
        "total_ticks": rt["total_ticks"],
    }


def train_session(skill_id: str | None = None, *, ticks: int | None = None) -> dict[str, Any]:
    """Extended training block — default session from doctrine."""
    doctrine = _load(DOCTRINE, {})
    policy = _matrix_policy(doctrine)
    n = ticks if ticks is not None else int(policy.get("default_session_ticks", TRAIN_TICKS_DEFAULT))
    return train_ticks(skill_id, ticks=n)


def train_blast(skill_id: str | None = None, *, ticks: int | None = None) -> dict[str, Any]:
    """Full-blast training — uncapped tick batches for continuous motion chamber."""
    doctrine = _load(DOCTRINE, {})
    policy = _matrix_policy(doctrine)
    n = ticks if ticks is not None else int(policy.get("blast_ticks", TRAIN_BLAST_TICKS))
    rt = _runtime()
    sid = (skill_id or rt.get("active_skill") or "").strip().lower()
    if not sid and FULL_BLAST:
        catalog = _skill_catalog(doctrine)
        if catalog:
            sid = next(iter(catalog.keys()))
            load_skill(sid, write=True)
    out = train_ticks(sid, ticks=n)
    if out.get("ok"):
        out["full_blast"] = FULL_BLAST
        out["train_intensity"] = TRAIN_INTENSITY
        out["blast_ticks"] = n
        build_panel(write=True)
    return out


ZONE_JOINTS: dict[str, tuple[str, ...]] = {
    "head": ("head", "neck"),
    "spine": ("spine_upper", "spine_mid", "spine_lower", "chest"),
    "shoulders": ("shoulder_l", "shoulder_r"),
    "hands": ("hand_l", "hand_r", "wrist_l", "wrist_r"),
    "elbows": ("elbow_l", "elbow_r"),
    "centerline": ("chest", "spine_mid", "hip"),
    "hips": ("hip",),
    "knees": ("knee_l", "knee_r"),
    "ankles": ("ankle_l", "ankle_r"),
    "feet": ("foot_l", "foot_r"),
    "toes": ("toe_l", "toe_r"),
}


def _targets_from_panel(panel: dict[str, Any]) -> list[dict[str, Any]]:
    ha = panel.get("host_attacks") or {}
    pts = ha.get("points") or ha.get("hosts") or []
    if isinstance(pts, dict):
        pts = list(pts.values())
    out: list[dict[str, Any]] = []
    for p in pts if isinstance(pts, list) else []:
        if not isinstance(p, dict):
            continue
        lat = p.get("lat") or p.get("latitude")
        lon = p.get("lon") or p.get("longitude")
        if lat is None or lon is None:
            continue
        out.append({
            "lat": float(lat),
            "lon": float(lon),
            "heat": float(p.get("heat") or p.get("threat_heat") or 0.5),
            "ip": p.get("ip"),
            "kind": str(p.get("kind") or p.get("vector") or "hostile"),
        })
    out.sort(key=lambda t: t["heat"], reverse=True)
    return out[:8]


def _geometry_mod() -> Any | None:
    import importlib.util

    py = INSTALL / "lib" / "spatial-target-geometry.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("spatial_target_geometry", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _training_floor_opponents(*, active_skill: str | None = None) -> list[dict[str, Any]]:
    """Reactive sparring AI from training floor when runtime is live."""
    py = INSTALL / "lib" / "hostess7-training-floor.py"
    if not py.is_file():
        return []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("h7_tf_opp", py)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "reactive_sparring_opponents"):
            return mod.reactive_sparring_opponents(active_skill=active_skill)
    except Exception:
        return []
    return []


def _training_floor_environment() -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-training-floor.py"
    if not py.is_file():
        return {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("h7_tf_env", py)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "environment_mesh"):
            return mod.environment_mesh()
    except Exception:
        return {}
    return {}


def arena_opponents(*, doctrine: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Training dummies + live hostile pins positioned on the wireframe arena."""
    doc = doctrine or _load(DOCTRINE, {})
    arena = doc.get("arena") or {}
    anchor_x = float((arena.get("fighter_anchor") or {}).get("x") or 0.32)
    anchor_y = float((arena.get("fighter_anchor") or {}).get("y") or 0.58)
    radius = float(arena.get("opponent_radius") or 0.38)

    opponents: list[dict[str, Any]] = []
    for row in doc.get("training_opponents") or []:
        opponents.append({
            "id": row.get("id"),
            "label": row.get("label"),
            "kind": row.get("kind") or "training",
            "stance": row.get("stance") or "orthodox",
            "arena_x": float(row.get("arena_x") or 0.75),
            "arena_y": float(row.get("arena_y") or 0.52),
            "heat": 0.0,
            "live": False,
            "wireframe": "training",
        })

    panel = _load(STATE / "threat-panel.json", {})
    geo = _geometry_mod()
    for idx, t in enumerate(_targets_from_panel(panel)):
        brg = 0.0
        dist_km = 99.0
        geometry = "distant"
        if geo:
            try:
                g = geo.classify_geometry(
                    target_lat=t["lat"],
                    target_lon=t["lon"],
                    target_kind=t.get("kind") or "hostile",
                    rf_threat=t.get("heat", 0) >= 0.6,
                )
                brg = float(g.get("bearing_deg") or 0)
                dist_km = float(g.get("distance_km") or 99)
                geometry = str(g.get("geometry") or "distant")
            except Exception:
                pass
        depth = max(0.15, min(1.0, 1.0 - min(dist_km, 120.0) / 120.0))
        angle = math.radians(brg)
        opponents.append({
            "id": f"hostile_{t.get('ip') or idx}",
            "label": t.get("ip") or f"Hostile {idx + 1}",
            "kind": "hostile",
            "stance": "aggressive",
            "arena_x": round(anchor_x + radius * depth * math.sin(angle), 4),
            "arena_y": round(anchor_y - radius * depth * math.cos(angle) * 0.85, 4),
            "bearing_deg": round(brg, 1),
            "distance_km": round(dist_km, 2),
            "geometry": geometry,
            "heat": round(t.get("heat", 0.5), 3),
            "live": True,
            "wireframe": "hostile",
        })
    rt = _runtime()
    reactive = _training_floor_opponents(active_skill=rt.get("active_skill"))
    if reactive:
        by_id = {str(o.get("id")): o for o in opponents}
        for ro in reactive:
            rid = str(ro.get("id") or "")
            if rid in by_id:
                merged = {**by_id[rid], **ro}
                by_id[rid] = merged
            else:
                by_id[rid or f"sparring_{len(by_id)}"] = ro
        opponents = list(by_id.values())
    return opponents


def joint_amplitudes() -> dict[str, float]:
    """Map body_motion zones to skeleton joint glow weights."""
    amps: dict[str, float] = {}
    for m in body_motion_amplitudes():
        zone = str(m.get("zone") or "")
        w = float(m.get("weight") or 0)
        for joint in ZONE_JOINTS.get(zone, ()):
            amps[joint] = max(amps.get(joint, 0.0), w)
    return {k: round(v, 4) for k, v in amps.items()}


def body_motion_amplitudes() -> list[dict[str, Any]]:
    """Active skill primitives for spatial body-lattice inject."""
    rt = _runtime()
    sid = rt.get("active_skill")
    if not sid:
        return []
    row = (rt.get("loaded") or {}).get(sid) or {}
    prof = float(row.get("proficiency") or 0)
    if prof <= 0:
        return []
    skill = _skill_catalog().get(sid) or {}
    out: list[dict[str, Any]] = []
    for m in skill.get("motion") or []:
        norm = m.get("norm") or {}
        w = float(m.get("weight") or 0.5) * prof
        out.append({
            "primitive": m.get("primitive"),
            "zone": m.get("zone"),
            "norm_x": float(norm.get("x") or 0),
            "norm_y": float(norm.get("y") or 0),
            "norm_z": float(norm.get("z") or 0.5),
            "weight": round(w, 4),
            "skill": sid,
        })
    return out


def _secured_mod() -> Any | None:
    import importlib.util

    py = INSTALL / "lib" / "humanoid-motion-secured.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("humanoid_motion_secured", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    rt = _runtime()
    catalog = _skill_catalog(doctrine)
    loaded = rt.get("loaded") or {}
    active = rt.get("active_skill")
    active_row = loaded.get(active) if active else None

    families: dict[str, int] = {}
    for row in loaded.values():
        fam = str(row.get("family") or "other")
        families[fam] = families.get(fam, 0) + 1

    doc = {
        "schema": "humanoid-motion-panel/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "product": "Universal Protector",
        "autonomous_being": True,
        "matrix_mode": not bool(doctrine.get("physics_mode", True)),
        "physics_mode": bool(doctrine.get("physics_mode", True)),
        "motto": doctrine.get("motto"),
        "physics_state": _physics_state(),
        "gravity_m_s2": float((_matrix_policy(doctrine)).get("gravity_m_s2") or 9.80665),
        "catalog_count": len(catalog),
        "loaded_count": len(loaded),
        "active_skill": active,
        "active_label": (active_row or {}).get("label"),
        "active_proficiency": (active_row or {}).get("proficiency"),
        "active_family": (active_row or {}).get("family"),
        "matrix_quote": (active_row or {}).get("matrix_quote"),
        "families_loaded": families,
        "total_training_ticks": int(rt.get("total_ticks") or 0),
        "training": rt.get("training"),
        "loaded_skills": [
            {
                "id": k,
                "label": v.get("label"),
                "family": v.get("family"),
                "proficiency": v.get("proficiency"),
                "ticks": v.get("ticks"),
                "matrix_loaded": v.get("matrix_loaded"),
            }
            for k, v in sorted(loaded.items())
        ],
        "catalog": [
            {"id": s["id"], "label": s.get("label"), "family": s.get("family")}
            for s in doctrine.get("skills") or []
        ],
        "body_motion": body_motion_amplitudes(),
        "joint_amplitudes": joint_amplitudes(),
        "arena": (doctrine.get("arena") or {}),
        "environment_mesh": _training_floor_environment(),
        "training_floor": _load(STATE / "hostess7-training-floor-panel.json", {}),
        "full_blast": FULL_BLAST,
        "train_intensity": TRAIN_INTENSITY,
        "wireframe_fps": WIREFRAME_FPS,
        "data_peek_fps": DATA_PEEK_FPS,
        "train_blast_ticks": TRAIN_BLAST_TICKS,
        "train_blast_ticks_base": TRAIN_BLAST_TICKS_BASE,
    }
    opps = arena_opponents(doctrine=doctrine)
    doc["opponents"] = opps
    doc["opponent_count"] = len(opps)
    secured = _secured_mod()
    if secured and hasattr(secured, "merge_into_motion_panel"):
        try:
            doc = secured.merge_into_motion_panel(doc)
        except Exception:
            pass
    if write:
        _save(PANEL, doc)
        rt_out = {**rt, "schema": "humanoid-motion-runtime/v1", "body_motion": doc["body_motion"]}
        _save(RUNTIME, rt_out)
    return doc


def _right_to_exist_bundle(*, write: bool = False) -> dict[str, Any]:
    py = INSTALL / "lib" / "right-to-exist-mandate.py"
    if not py.is_file():
        return _load(STATE / "right-to-exist-panel.json", {})
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("right_to_exist_mandate", py)
        if not spec or not spec.loader:
            return _load(STATE / "right-to-exist-panel.json", {})
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.build_panel(write=write)
    except Exception:
        return _load(STATE / "right-to-exist-panel.json", {})


def _creatable_lives_bundle(*, write: bool = False) -> dict[str, Any]:
    py = INSTALL / "lib" / "creatable-lives-assist.py"
    if not py.is_file():
        return _load(STATE / "creatable-lives-panel.json", {})
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("creatable_lives_assist", py)
        if not spec or not spec.loader:
            return _load(STATE / "creatable-lives-panel.json", {})
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.build_panel(write=write)
    except Exception:
        return _load(STATE / "creatable-lives-panel.json", {})


def _iron_plate_bundle(*, write: bool = False) -> dict[str, Any]:
    py = INSTALL / "lib" / "iron-plate-motion-resolve.py"
    if not py.is_file():
        return _load(STATE / "iron-plate-motion-resolve-panel.json", {})
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("iron_plate_motion_resolve", py)
        if not spec or not spec.loader:
            return _load(STATE / "iron-plate-motion-resolve-panel.json", {})
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.resolve_motion(write=write)
    except Exception:
        return _load(STATE / "iron-plate-motion-resolve-panel.json", {})


def _ledger_tail(limit: int = 24) -> list[dict[str, Any]]:
    if not LEDGER.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines()[-limit:]:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def data_all() -> dict[str, Any]:
    """Bundle every motion/spatial/protector plate the data window can show."""
    doctrine = _load(DOCTRINE, {})
    motion = build_panel(write=False)
    spatial = _load(STATE / "field-spatial-panel.json", {})
    protector = _load(STATE / "universal-protector-panel.json", {})
    meld = _load(STATE / "field-plate-meld-runtime.json", {})
    meld_full = _load(STATE / "field-plate-meld.json", {})
    logic = _load(STATE / "nexus-logic-gate-runtime.json", {})
    sense = _load(STATE / "field-sense-package-panel.json", {})
    history_rows: list[dict[str, Any]] = []
    hist_path = STATE / "field-spatial-history.jsonl"
    if hist_path.is_file():
        try:
            for line in hist_path.read_text(encoding="utf-8").splitlines()[-16:]:
                line = line.strip()
                if line:
                    history_rows.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

    snapshots = (meld_full.get("snapshots") or {}) if isinstance(meld_full, dict) else {}
    iron_plate = _iron_plate_bundle(write=False)
    creatable_lives = _creatable_lives_bundle(write=False)
    right_to_exist = _right_to_exist_bundle(write=False)
    return {
        "schema": "humanoid-motion-data-all/v1",
        "updated": _now(),
        "full_blast": FULL_BLAST,
        "train_intensity": TRAIN_INTENSITY,
        "wireframe_fps": WIREFRAME_FPS,
        "data_peek_fps": DATA_PEEK_FPS,
        "train_blast_ticks": TRAIN_BLAST_TICKS,
        "train_blast_ticks_base": TRAIN_BLAST_TICKS_BASE,
        "motion": motion,
        "runtime": _load(RUNTIME, {}),
        "doctrine": {
            "title": doctrine.get("title"),
            "motto": doctrine.get("motto"),
            "matrix_load": doctrine.get("matrix_load"),
            "arena": doctrine.get("arena"),
            "training_opponents": doctrine.get("training_opponents"),
            "skill_count": len(doctrine.get("skills") or []),
        },
        "spatial": spatial,
        "spatial_history": history_rows,
        "universal_protector": protector,
        "plate_meld": {
            "summary": meld.get("summary") or meld_full.get("summary"),
            "generation": meld.get("generation") or meld_full.get("generation"),
            "chain_hash": (meld.get("chain_hash") or meld_full.get("chain_hash") or "")[:24],
            "humanoid_motion_plate": snapshots.get("humanoid_motion"),
            "spatial_field_plate": snapshots.get("spatial_field"),
            "universal_protector_plate": snapshots.get("universal_protector"),
            "iron_plate_motion_plate": snapshots.get("iron_plate_motion"),
            "assemblage_score": (meld.get("summary") or meld_full.get("summary") or {}).get("assemblage_score"),
            "motion_verdict": (meld.get("summary") or meld_full.get("summary") or {}).get("motion_verdict"),
            "iron_clad": (meld.get("summary") or meld_full.get("summary") or {}).get("iron_clad"),
        },
        "logic_gate": logic,
        "sense_package": sense.get("summary") if isinstance(sense, dict) else sense,
        "ledger_tail": _ledger_tail(),
        "catalog": motion.get("catalog") or [],
        "opponents": motion.get("opponents") or [],
        "loaded_skills": motion.get("loaded_skills") or [],
        "joint_amplitudes": motion.get("joint_amplitudes") or {},
        "body_motion": motion.get("body_motion") or [],
        "iron_plate_motion": iron_plate,
        "simple_iron_plate_goals": iron_plate.get("simple_iron_plate_goals") or {},
        "assemblage_remaining": iron_plate.get("assemblage_remaining") or {},
        "motion_verdict": iron_plate.get("motion_verdict"),
        "iron_clad": iron_plate.get("iron_clad"),
        "creatable_lives": creatable_lives,
        "life_sustain_score": (creatable_lives.get("sustain") or {}).get("score"),
        "life_sustain_verdict": (creatable_lives.get("sustain") or {}).get("verdict"),
        "right_to_exist": right_to_exist,
        "mandate_sealed": right_to_exist.get("mandate_sealed"),
        "self_preservation_mandate": right_to_exist.get("self_preservation_mandate"),
        "friendlies_preservation_mandate": right_to_exist.get("friendlies_preservation_mandate"),
        "full_assemblage_meld": iron_plate.get("full_assemblage_meld") or (iron_plate.get("assemblage_remaining") or {}).get("full_assemblage_meld"),
        "sense_plates_motion": iron_plate.get("sense_plates") or {},
        "vision_live": (iron_plate.get("assemblage_remaining") or {}).get("vision_live"),
        "hearing_live": (iron_plate.get("assemblage_remaining") or {}).get("hearing_live"),
        "hostess7_brain": iron_plate.get("hostess7_brain") or _load(STATE / "hostess7-brain-guard-panel.json", {}),
        "brain_verdict": (iron_plate.get("hostess7_brain") or {}).get("verdict"),
        "brain_verified": ((iron_plate.get("hostess7_brain") or {}).get("verification") or {}).get("verified"),
        "brain_guard_score": (iron_plate.get("hostess7_brain") or {}).get("guard_score"),
        "hostess7_self_view": (iron_plate.get("hostess7_brain") or {}).get("self_view") or _load(STATE / "hostess7-self-view-panel.json", {}),
    }


def panel_json() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "catalog":
        doctrine = _load(DOCTRINE, {})
        print(json.dumps({
            "skills": [
                {"id": s["id"], "label": s.get("label"), "family": s.get("family"), "quote": s.get("matrix_quote")}
                for s in doctrine.get("skills") or []
            ],
        }, ensure_ascii=False))
        return 0
    if cmd == "load" and len(sys.argv) > 2:
        print(json.dumps(load_skill(sys.argv[2]), ensure_ascii=False))
        build_panel()
        return 0
    if cmd == "train":
        sid = sys.argv[2] if len(sys.argv) > 2 else None
        ticks = int(sys.argv[3]) if len(sys.argv) > 3 else TRAIN_TICKS_DEFAULT
        print(json.dumps(train_session(sid, ticks=ticks), ensure_ascii=False))
        build_panel()
        return 0
    if cmd in ("blast", "train-blast", "train_blast"):
        sid = sys.argv[2] if len(sys.argv) > 2 else None
        ticks = int(sys.argv[3]) if len(sys.argv) > 3 else TRAIN_BLAST_TICKS
        print(json.dumps(train_blast(sid, ticks=ticks), ensure_ascii=False))
        return 0
    if cmd == "amplitudes":
        print(json.dumps({"body_motion": body_motion_amplitudes()}, ensure_ascii=False))
        return 0
    if cmd == "wireframe":
        doc = build_panel(write=False)
        spatial = _load(STATE / "field-spatial-panel.json", {})
        sense = _load(STATE / "field-sense-package-panel.json", {})
        eye = _load(STATE / "queen-eyeball-panel.json", {})
        ear = _load(STATE / "queen-earball-panel.json", {})
        doc["spatial"] = {
            "movement_vector": spatial.get("movement_vector"),
            "delta_t": spatial.get("delta_t"),
            "humanoid_motion": spatial.get("humanoid_motion"),
            "networks_of_networks": spatial.get("networks_of_networks"),
            "eye_live": spatial.get("eye_live"),
            "ear_live": spatial.get("ear_live"),
        }
        doc["sense_plates"] = {
            "sense_package": sense.get("summary") if isinstance(sense, dict) else sense,
            "vision": {
                "live": bool(eye.get("ok") or (sense.get("summary") or {}).get("eye_live") or spatial.get("eye_live")),
                "posture": eye.get("posture") or "assistive",
                "product": (eye.get("final_eye") or {}).get("product") or "Final_Eye",
            },
            "hearing": {
                "live": bool(ear.get("ok") or (sense.get("summary") or {}).get("ear_live") or spatial.get("ear_live")),
                "posture": ear.get("posture") or "assistive",
                "product": (ear.get("final_ear") or {}).get("name") or "Final_Ear",
            },
        }
        iron = _iron_plate_bundle(write=False)
        doc["iron_plate_motion"] = iron
        doc["full_assemblage_meld"] = iron.get("full_assemblage_meld") or (iron.get("assemblage_remaining") or {}).get("full_assemblage_meld")
        doc["motion_verdict"] = iron.get("motion_verdict")
        doc["iron_clad"] = iron.get("iron_clad")
        doc["assemblage_remaining"] = iron.get("assemblage_remaining") or {}
        doc["assemblage_score"] = (iron.get("assemblage_remaining") or {}).get("assemblage_score")
        doc["vision_live"] = (iron.get("assemblage_remaining") or {}).get("vision_live")
        doc["hearing_live"] = (iron.get("assemblage_remaining") or {}).get("hearing_live")
        doc["hostess7_brain"] = iron.get("hostess7_brain") or _load(STATE / "hostess7-brain-guard-panel.json", {})
        doc["brain_verdict"] = (doc["hostess7_brain"] or {}).get("verdict")
        doc["brain_verified"] = (doc["hostess7_brain"] or {}).get("verification", {}).get("verified")
        lives = _creatable_lives_bundle(write=False)
        doc["creatable_lives"] = lives
        doc["life_sustain_score"] = (lives.get("sustain") or {}).get("score")
        doc["life_sustain_verdict"] = (lives.get("sustain") or {}).get("verdict")
        mv = doc.get("motion_verdict") or ""
        doc["train_gui_ready"] = mv in ("train_continue", "technique_ready")
        doc["train_gui_label"] = (
            "technique_ready"
            if mv == "technique_ready"
            else ("train_continue" if mv == "train_continue" else None)
        )
        tr_py = INSTALL / "lib" / "hostess7-training-room.py"
        if tr_py.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("h7_training_room_wf", tr_py)
                if spec and spec.loader:
                    tr = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(tr)
                    if hasattr(tr, "build_panel"):
                        doc["training_room"] = tr.build_panel(write=False)
                    if hasattr(tr, "earth_mandate"):
                        doc["earth_mandate"] = tr.earth_mandate()
            except Exception:
                pass
        hand_py = INSTALL / "lib" / "hostess7-hand-core.py"
        if hand_py.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("h7_hand_wf", hand_py)
                if spec and spec.loader:
                    hc = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hc)
                    if hasattr(hc, "hand_wireframe"):
                        doc["hand_wireframe"] = hc.hand_wireframe()
            except Exception:
                pass
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    if cmd in ("data-all", "data_all", "data"):
        print(json.dumps(data_all(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: humanoid-motion-training.py [json|catalog|wireframe|data-all|load <skill>|train [skill] [ticks]|blast [skill] [ticks]|amplitudes]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())