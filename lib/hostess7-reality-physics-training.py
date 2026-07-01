#!/usr/bin/env pythong
"""Reality physics training — gravity, thermodynamics, entropy, field technology on live state."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-reality-physics-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-reality-physics-battery.json"
RUNTIME = STATE / "hostess7-reality-physics-runtime.json"
PANEL = STATE / "hostess7-reality-physics-panel.json"
LEDGER = STATE / "hostess7-reality-physics-ledger.jsonl"

G_EARTH = float(os.environ.get("NEXUS_PHYSICS_G", "9.80665"))
KB = 1.380649e-23
KT_LN2 = 2.87e-21
T_ROOM = float(os.environ.get("NEXUS_PHYSICS_T_K", "300.0"))
ENABLED = os.environ.get("NEXUS_REALITY_PHYSICS_TRAINING", "1") == "1"


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


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _si() -> dict[str, float]:
    doc = _load(DOCTRINE, {})
    si = doc.get("si_units") or {}
    return {
        "g": float(si.get("gravity_m_s2") or G_EARTH),
        "kb": float(si.get("boltzmann_j_k") or KB),
        "t_k": float(si.get("room_temp_k") or T_ROOM),
        "landauer": float(si.get("landauer_j_per_bit") or KT_LN2),
    }


def _sim_policy() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    return doc.get("physics_sim") or {}


def _runtime() -> dict[str, Any]:
    return _load(RUNTIME, {
        "schema": "hostess7-reality-physics-runtime/v1",
        "physics_sim": {},
        "battery_results": {},
        "proficiency": 0.0,
        "total_ticks": 0,
        "grounded_ticks": 0,
    })


def landauer_joules(*, temp_k: float | None = None, bits: int = 1) -> float:
    si = _si()
    t = temp_k if temp_k is not None else si["t_k"]
    return bits * si["kb"] * t * math.log(2)


def shannon_entropy_bits(probs: list[float]) -> float:
    if not probs:
        return 0.0
    total = sum(probs) or 1.0
    norm = [max(p, 0.0) / total for p in probs]
    return -sum(p * math.log2(p) for p in norm if p > 0)


def gravity_sim_state() -> dict[str, Any]:
    rt = _runtime()
    sim = rt.get("physics_sim") or {}
    policy = _sim_policy()
    return {
        "com_y": float(sim.get("com_y") or policy.get("ground_y_norm") or 0.12),
        "com_vy": float(sim.get("com_vy") or 0.0),
        "mass_kg": float(sim.get("mass_kg") or policy.get("humanoid_mass_kg") or 68.0),
        "grounded": bool(sim.get("grounded", True)),
        "kinetic_j": float(sim.get("kinetic_j") or 0.0),
        "potential_j": float(sim.get("potential_j") or 0.0),
        "energy_drift_pct": float(sim.get("energy_drift_pct") or 0.0),
        "stance_stability": float(sim.get("stance_stability") or 0.0),
        "ticks": int(sim.get("ticks") or 0),
    }


def gravity_sim_step(*, impulse_vy: float = 0.0, write: bool = True) -> dict[str, Any]:
    """Semi-implicit Euler — COM under gravity with ground contact."""
    si = _si()
    policy = _sim_policy()
    g = si["g"]
    dt = float(policy.get("dt_s") or (1.0 / 60.0))
    mass = float(policy.get("humanoid_mass_kg") or 68.0)
    ground_y = float(policy.get("ground_y_norm") or 0.12)
    tol_pct = float(policy.get("energy_tolerance_pct") or 2.5)

    rt = _runtime()
    sim = dict(rt.get("physics_sim") or {})
    y = float(sim.get("com_y") or ground_y)
    vy = float(sim.get("com_vy") or 0.0) + impulse_vy
    grounded = bool(sim.get("grounded", True))

    ref_h = max(0.0, ground_y - y)
    e0 = mass * g * ref_h + 0.5 * mass * vy * vy

    vy -= g * dt
    y += vy * dt
    grounded = False
    if y >= ground_y:
        y = ground_y
        if vy < 0:
            vy = -vy * 0.35
        grounded = True
        vy *= 0.92

    ref_h2 = max(0.0, ground_y - y)
    e1 = mass * g * ref_h2 + 0.5 * mass * vy * vy
    drift = abs(e1 - e0) / max(abs(e0), mass * g * 0.02 + 0.05) * 100.0
    stability = 1.0 if grounded and abs(vy) < 0.05 else max(0.0, 1.0 - min(1.0, abs(vy) / 2.5))

    sim.update({
        "com_y": round(y, 6),
        "com_vy": round(vy, 6),
        "mass_kg": mass,
        "grounded": grounded,
        "kinetic_j": round(0.5 * mass * vy * vy, 6),
        "potential_j": round(mass * g * ref_h2, 6),
        "energy_drift_pct": round(drift, 4),
        "stance_stability": round(stability, 4),
        "ticks": int(sim.get("ticks") or 0) + 1,
        "gravity_m_s2": g,
        "dt_s": dt,
        "energy_ok": drift <= tol_pct or grounded,
    })
    rt["physics_sim"] = sim
    rt["total_ticks"] = int(rt.get("total_ticks") or 0) + 1
    if grounded:
        rt["grounded_ticks"] = int(rt.get("grounded_ticks") or 0) + 1
    rt["updated"] = _now()
    if write:
        _save(RUNTIME, rt)
    return {"ok": True, "physics_sim": sim, "grounded": grounded, "energy_drift_pct": drift}


def _eval_battery_item(item: dict[str, Any], kind: str) -> dict[str, Any]:
    si = _si()
    g = si["g"]
    params = item.get("params") or {}
    got: float | bool | None = None
    passed = False
    detail = ""

    try:
        if kind == "kinematic":
            t = float(params.get("t_s") or 1.0)
            got = 0.5 * g * t * t
            exp = float(item.get("expected_m") or 0)
            passed = abs(got - exp) < max(0.02, abs(exp) * 0.02)

        elif kind == "energy":
            h = float(params.get("h_m") or 1.0)
            got = math.sqrt(2.0 * g * h)
            exp = float(item.get("expected_v_m_s") or 0)
            passed = abs(got - exp) < max(0.05, abs(exp) * 0.02)

        elif kind == "force":
            m = float(params.get("mass_kg") or 1.0)
            got = m * g
            exp = float(item.get("expected_n") or 0)
            passed = abs(got - exp) < max(0.5, abs(exp) * 0.01)

        elif kind == "projectile":
            v0 = float(params.get("v0_m_s") or 1.0)
            got = (v0 * v0) / (2.0 * g)
            exp = float(item.get("expected_h_m") or 0)
            passed = abs(got - exp) < max(0.02, abs(exp) * 0.03)

        elif kind == "landauer":
            t = float(params.get("temp_k") or si["t_k"])
            got = landauer_joules(temp_k=t, bits=1)
            exp = float(item.get("expected_j") or KT_LN2)
            passed = abs(got - exp) / max(exp, 1e-30) < 0.05

        elif kind == "first_law":
            q_in = float(params.get("q_in_j") or 0)
            w_out = float(params.get("w_out_j") or 0)
            got = q_in - w_out
            exp = float(item.get("expected_delta_u") or 0)
            passed = abs(got - exp) < 1e-6

        elif kind == "carnot":
            th = float(params.get("th_k") or 500)
            tc = float(params.get("tc_k") or 300)
            got = 1.0 - tc / th
            exp = float(item.get("expected_eta") or 0)
            passed = abs(got - exp) < 0.01

        elif kind == "live_thermal":
            panel = _load(STATE / "field-thermal-guard.json", {})
            got = float(panel.get("headroom_pct") or panel.get("thermal_headroom_pct") or 100.0)
            exp_min = float(item.get("expected_min_headroom_pct") or 0)
            passed = got >= exp_min
            detail = f"headroom={got}%"

        elif kind == "shannon":
            n = max(1, int(params.get("symbols") or 2))
            probs = [1.0 / n] * n if n > 1 else [1.0]
            got = shannon_entropy_bits(probs)
            exp = float(item.get("expected_bits") or 0)
            passed = abs(got - exp) < 0.05

        elif kind == "second_law":
            ds = float(params.get("delta_s") or 0)
            got = ds >= 0
            passed = bool(item.get("expected_ok", True)) == got

        elif kind == "live_entropy":
            demod = _import_mod("field_spectrum_demod", "field-spectrum-demod.py")
            got = 0.5
            if demod and hasattr(demod, "_field_physics_state"):
                phys = demod._field_physics_state({"mesh": {"tri_compare": {}}}, {})
                got = float(phys.get("entropy_norm") or 0.5)
            exp_max = float(item.get("expected_max") or 1.0)
            passed = 0.0 <= got <= exp_max + 0.01
            detail = f"entropy_norm={got}"

        elif kind == "doctrine_landauer":
            doc = _load(INSTALL / "data" / "field-thermal-guard-doctrine.json", {})
            got = float((doc.get("landauer") or {}).get("kt_ln2_j_per_bit") or 0)
            exp = float(item.get("expected_j") or KT_LN2)
            passed = abs(got - exp) / max(exp, 1e-30) < 0.05

        elif kind == "live_joules":
            guard = _import_mod("field_thermal_guard", "field-thermal-guard.py")
            got = 0.0
            if guard and hasattr(guard, "FieldThermalGuard"):
                got = float(guard.FieldThermalGuard().joules_per_field_op)
            exp_min = float(item.get("expected_min") or 1e-12)
            passed = got >= exp_min
            detail = f"joules_per_op={got}"

        elif kind == "policy":
            doc = _load(INSTALL / "data" / "field-thermal-guard-doctrine.json", {})
            pol = doc.get("policy") or {}
            got = bool(pol.get("incremental_redata_only"))
            passed = got == bool(item.get("expected", True))

        elif kind == "fabric_map":
            doc = _load(INSTALL / "data" / "amouranthrtx-field-fabric-map.json", {})
            slots = doc.get("slots") or doc.get("fabric_slots") or {}
            entropy = doc.get("entropy_watch") or (slots.get("entropy") if isinstance(slots, dict) else None)
            passed = bool(entropy) or "entropy" in json.dumps(doc).lower()
            detail = "entropy slot mapped" if passed else "missing entropy map"

        else:
            detail = f"unknown kind {kind}"
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        detail = str(exc)
        passed = False

    return {
        "id": item.get("id"),
        "query": item.get("query"),
        "kind": kind,
        "passed": passed,
        "got": got if isinstance(got, (int, float)) else None,
        "expected": item.get("expected_m") or item.get("expected_v_m_s") or item.get("expected_n")
        or item.get("expected_h_m") or item.get("expected_j") or item.get("expected_bits")
        or item.get("expected_eta") or item.get("expected_delta_u") or item.get("expected_ok")
        or item.get("expected_min_headroom_pct") or item.get("expected_min") or item.get("expected"),
        "detail": detail,
    }


def run_battery(battery_id: str) -> dict[str, Any]:
    bat_doc = _load(BATTERY, {})
    items = (bat_doc.get("batteries") or {}).get(battery_id) or []
    rows = [_eval_battery_item(it, str(it.get("kind") or "")) for it in items]
    passed = sum(1 for r in rows if r.get("passed"))
    total = len(rows) or 1
    rate = round(100.0 * passed / total, 1)
    out = {
        "ok": True,
        "battery": battery_id,
        "passed": passed,
        "total": total,
        "pass_rate": rate,
        "fluent": rate >= 92,
        "mastered": rate >= 98 and passed == total,
        "rows": rows,
    }
    rt = _runtime()
    results = rt.setdefault("battery_results", {})
    results[battery_id] = {**out, "updated": _now()}
    rt["updated"] = _now()
    _save(RUNTIME, rt)
    _append_ledger({"ts": rt["updated"], "event": "battery", "battery": battery_id, "pass_rate": rate})
    return out


def run_all_batteries() -> dict[str, Any]:
    bat_doc = _load(BATTERY, {})
    ids = list((bat_doc.get("batteries") or {}).keys())
    results = {bid: run_battery(bid) for bid in ids}
    passed = sum(r.get("passed", 0) for r in results.values())
    total = sum(r.get("total", 0) for r in results.values()) or 1
    rate = round(100.0 * passed / total, 1)
    return {"ok": True, "batteries": results, "pass_rate": rate, "passed": passed, "total": total}


def train_physics_session(*, ticks: int | None = None) -> dict[str, Any]:
    """Physics-ticked training — gravity sim + battery refresh."""
    policy = _sim_policy()
    n = ticks if ticks is not None else int(policy.get("session_ticks") or 180)
    n = max(1, min(n, 2000))
    rate = float(policy.get("train_tick_proficiency") or 0.012)
    max_prof = float(policy.get("max_proficiency") or 1.0)

    sim_results: list[dict[str, Any]] = []
    for i in range(n):
        impulse = -0.06 * math.sin(i * 0.17)
        sim_results.append(gravity_sim_step(impulse_vy=impulse, write=True))

    batteries = run_all_batteries()
    last_sim = sim_results[-1].get("physics_sim") or {}
    stability = float(last_sim.get("stance_stability") or 0)
    energy_ok = bool(last_sim.get("energy_ok"))
    bat_rate = float(batteries.get("pass_rate") or 0) / 100.0

    rt = _runtime()
    prof = float(rt.get("proficiency") or 0)
    grounded_ratio = float(rt.get("grounded_ticks") or 0) / max(int(rt.get("total_ticks") or 1), 1)
    tick_gain = rate * (0.4 + 0.35 * bat_rate + 0.25 * stability)
    if energy_ok:
        tick_gain *= 1.05
    prof = min(max_prof, prof + tick_gain)
    fluent = prof >= 0.92 and bat_rate >= 0.85 and grounded_ratio >= 0.88
    mastered = prof >= 0.98 and bat_rate >= 0.98 and stability >= 0.72

    rt["proficiency"] = round(prof, 4)
    rt["fluent"] = fluent
    rt["mastered"] = mastered
    rt["tier"] = "reality_physics_master" if mastered else "reality_physics_fluent" if fluent else "reality_physics_training"
    rt["last_session"] = {
        "ticks": n,
        "battery_pass_rate": batteries.get("pass_rate"),
        "stance_stability": stability,
        "grounded_ratio": round(grounded_ratio, 4),
        "updated": _now(),
    }
    rt["updated"] = _now()
    _save(RUNTIME, rt)
    _append_ledger({
        "ts": rt["updated"],
        "event": "train_session",
        "ticks": n,
        "proficiency": prof,
        "pass_rate": batteries.get("pass_rate"),
    })
    return {
        "ok": True,
        "ticks": n,
        "proficiency": prof,
        "fluent": fluent,
        "mastered": mastered,
        "tier": rt["tier"],
        "batteries": batteries,
        "physics_sim": last_sim,
        "grounded_ratio": grounded_ratio,
    }


def _track_batteries(track_id: str) -> list[str]:
    doc = _load(DOCTRINE, {})
    for row in doc.get("tracks") or []:
        if row.get("id") == track_id:
            return list(row.get("batteries") or [])
    mapping = {
        "reality_physics": ["gravity", "thermodynamics", "entropy", "field_technology"],
        "gravity_mechanics": ["gravity"],
        "thermodynamics_entropy": ["thermodynamics", "entropy"],
        "field_technology": ["field_technology"],
    }
    return mapping.get(track_id, [])


def assess_track(track_id: str) -> dict[str, Any]:
    rt = _runtime()
    results = rt.get("battery_results") or {}
    bat_ids = _track_batteries(track_id)
    if not bat_ids:
        return {"ok": False, "error": "unknown_track", "track": track_id}

    passed = 0
    total = 0
    for bid in bat_ids:
        row = results.get(bid) or {}
        passed += int(row.get("passed") or 0)
        total += int(row.get("total") or 0)
        if not row:
            bat = run_battery(bid)
            passed += int(bat.get("passed") or 0)
            total += int(bat.get("total") or 0)

    total = max(total, 1)
    rate = passed / total
    comp = _load(DOCTRINE, {}).get("completion") or {}
    prof = float(rt.get("proficiency") or 0)
    grounded_ratio = float(rt.get("grounded_ticks") or 0) / max(int(rt.get("total_ticks") or 1), 1)
    ticks_ok = int(rt.get("total_ticks") or 0) >= int(comp.get("physics_sim_ticks_min") or 120)

    complete = (
        rate >= float(comp.get("pass_rate_pct") or 85) / 100.0
        and (track_id != "reality_physics" or ticks_ok)
    )
    fluent = complete and rate >= float(comp.get("fluent_rate_pct") or 92) / 100.0 and prof >= 0.85
    mastered = fluent and rate >= float(comp.get("master_rate_pct") or 98) / 100.0 and bool(rt.get("mastered"))

    if track_id == "gravity_mechanics":
        sim = rt.get("physics_sim") or {}
        complete = complete and grounded_ratio >= float(comp.get("grounded_ratio_min") or 0.88)
        fluent = fluent and float(sim.get("stance_stability") or 0) >= 0.65

    level = "mastered" if mastered else "fluent" if fluent else "complete" if complete else "training" if rate > 0.2 else "pending"
    return {
        "ok": True,
        "level": level,
        "complete": complete,
        "mastered": mastered,
        "fluent": fluent,
        "score": round(max(rate, prof * 0.35), 4),
        "pass_rate": round(rate * 100, 1),
        "proficiency": prof,
        "grounded_ratio": round(grounded_ratio, 4),
        "physics_ticks": int(rt.get("total_ticks") or 0),
        "batteries": bat_ids,
    }


def assess_all_tracks() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    tracks: dict[str, Any] = {}
    for row in doc.get("tracks") or []:
        tid = str(row.get("id") or "")
        if tid:
            tracks[tid] = assess_track(tid)
            tracks[tid]["label"] = row.get("label")
    return {"schema": "hostess7-reality-physics-assess/v1", "updated": _now(), "tracks": tracks}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    assess = assess_all_tracks()
    rt = _runtime()
    sim = gravity_sim_state()
    panel = {
        "schema": "hostess7-reality-physics/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "motto": doc.get("motto"),
        "foundation": doc.get("foundation"),
        "physics_sim": sim,
        "gravity_m_s2": _si()["g"],
        "landauer_j_per_bit": _si()["landauer"],
        "proficiency": rt.get("proficiency"),
        "fluent": rt.get("fluent"),
        "mastered": rt.get("mastered"),
        "tier": rt.get("tier") or "reality_physics_pending",
        "total_ticks": rt.get("total_ticks"),
        "grounded_ticks": rt.get("grounded_ticks"),
        "battery_results": rt.get("battery_results"),
        "tracks": assess.get("tracks"),
        "last_session": rt.get("last_session"),
        "under_god": True,
        "training_mode": "physics",
        "ironclad": doc.get("ironclad") or {},
        "ironclad_sealed": bool((doc.get("ironclad") or {}).get("sealed")),
        "universe_bounds": {
            "floor": (doc.get("ironclad") or {}).get("floor"),
            "ceiling": (doc.get("ironclad") or {}).get("ceiling"),
            "declaration": (doc.get("ironclad") or {}).get("declaration"),
        },
    }
    if write:
        _save(PANEL, panel)
    return panel


_OCR_API: dict | None = None


def _ocr_api() -> dict:
    global _OCR_API
    if _OCR_API is None:
        import importlib.util
        py = INSTALL / "lib" / "hostess7-ocr-bind.py"
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_reality_physics", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("reality_physics", install=INSTALL, state=STATE, ledger=LEDGER)
    return _OCR_API


def ingest_ocr_vision(**kw):
    return _ocr_api()["ingest_ocr_vision"](**kw)


def train_ocr_vision(**kw):
    return _ocr_api()["train_ocr_vision"](**kw)


def ocr_vision_status():
    return _ocr_api()["ocr_vision_status"]()


def _handle_ocr_cli(cmd: str) -> int | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-ocr-feed.py"
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_reality_physics", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd,
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-reality-physics-training.py [json|assess|battery|train|sim|track-assess|ocr-ingest|ocr-train|ocr-status]",
    )


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "assess":
        print(json.dumps(assess_all_tracks(), ensure_ascii=False))
        return 0
    if cmd == "battery" and len(sys.argv) > 2:
        print(json.dumps(run_battery(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd in ("batteries", "run-batteries"):
        print(json.dumps(run_all_batteries(), ensure_ascii=False))
        return 0
    if cmd in ("train", "session"):
        ticks = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
        print(json.dumps(train_physics_session(ticks=ticks), ensure_ascii=False))
        return 0
    if cmd == "sim":
        n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
        last = {}
        for _ in range(n):
            last = gravity_sim_step()
        print(json.dumps(last, ensure_ascii=False))
        return 0
    if cmd == "track-assess" and len(sys.argv) > 2:
        print(json.dumps(assess_track(sys.argv[2]), ensure_ascii=False))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({
        "error": "usage: hostess7-reality-physics-training.py [json|assess|battery ID|batteries|train [ticks]|sim [n]|track-assess ID]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())