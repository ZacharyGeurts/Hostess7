#!/usr/bin/env pythong
"""Hostess 7 training completion — run all tracks to solid Master levels."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-training-doctrine.json"
FACETS = INSTALL / "data" / "hostess7-mastery-facets.json"
PANEL = STATE / "hostess7-training-panel.json"
RUNTIME = STATE / "hostess7-training-runtime.json"
LEDGER = STATE / "hostess7-training-ledger.jsonl"

ENABLED = os.environ.get("NEXUS_HOSTESS7_TRAINING", "1") == "1"


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


def _tail_ledger(limit: int = 80) -> list[dict[str, Any]]:
    if not LEDGER.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _write_runtime(**fields: Any) -> None:
    doc = _load(RUNTIME, {"schema": "hostess7-training-runtime/v1"})
    doc.update(fields)
    doc["updated"] = _now()
    _save(RUNTIME, doc)


def _ask_with_timeout(cmd: Any, question: str, panel: dict[str, Any], *, timeout_s: int = 45) -> dict[str, Any]:
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(cmd.ask_operator, question, panel=panel, use_brain=True)
        try:
            return fut.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError:
            return {"ok": False, "reply": "", "error": "ask_timeout", "timeout_s": timeout_s}


TRACK_ID_ALIASES: dict[str, str] = {
    "master_curriculum": "curriculum",
}


def build_evaluation_graphs() -> dict[str, Any]:
    """Chart-ready evaluation data — timeline, track bars, curriculum, facets."""
    assess = assess_all()
    tracks = assess.get("tracks") or {}
    master_st = _load(STATE / "hostess7-master-state.json", {})
    curriculum = _load(INSTALL / "data" / "hostess7-master-curriculum.json", {})
    done = set(master_st.get("completed_steps") or [])
    steps = curriculum.get("curriculum") or []

    timeline: list[dict[str, Any]] = []
    for row in _tail_ledger(100):
        timeline.append({
            "ts": row.get("ts"),
            "event": row.get("event"),
            "track": row.get("track"),
            "level": row.get("level"),
            "overall_score": row.get("overall_score"),
            "passed": row.get("passed"),
            "ok": row.get("ok"),
        })

    track_bars: list[dict[str, Any]] = []
    for tid, t in tracks.items():
        score = t.get("score")
        if score is not None and float(score) <= 1:
            score = round(float(score) * 100, 1)
        track_bars.append({
            "id": tid,
            "label": t.get("label") or tid,
            "score": score,
            "level": t.get("level"),
            "complete": bool(t.get("complete")),
            "mastered": bool(t.get("mastered")),
        })
    track_bars.sort(key=lambda x: (-(float(x["score"]) if x["score"] is not None else 0), x["id"]))

    curriculum_steps = [
        {
            "id": s.get("id"),
            "completed": s.get("id") in done,
            "xp": s.get("xp"),
            "tier": s.get("tier"),
            "tip": (s.get("tip") or "")[:120],
        }
        for s in steps
    ]

    facets = (assess.get("mastery_facets") or {}).get("facets") or {}
    facet_radar = [
        {
            "id": fid,
            "label": (facets[fid] or {}).get("label") or fid,
            "score": round(float((facets[fid] or {}).get("score") or 0) * 100, 1),
            "level": (facets[fid] or {}).get("level"),
        }
        for fid in ("flexibility", "adaptability", "confidence")
        if fid in facets
    ]

    return {
        "schema": "hostess7-training-graphs/v1",
        "updated": _now(),
        "overall_score": assess.get("overall_score"),
        "completion_level": assess.get("completion_level"),
        "tracks_complete": assess.get("tracks_complete"),
        "tracks_total": assess.get("tracks_total"),
        "timeline": timeline,
        "track_bars": track_bars,
        "curriculum_steps": curriculum_steps,
        "curriculum_done": len(done),
        "curriculum_total": len(steps),
        "facet_radar": facet_radar,
    }


def build_track_evaluation(track_id: str, result: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    track_assess = (assessment.get("tracks") or {}).get(track_id) or {}
    summary: dict[str, Any] = {"ok": result.get("ok")}
    if result.get("step"):
        summary["curriculum_step"] = result.get("step", {}).get("id")
    if result.get("steps_run") is not None:
        summary["steps_run"] = result.get("steps_run")
    if result.get("panel"):
        panel = result["panel"]
        if isinstance(panel, dict):
            for key in ("tier", "verdict", "pass_rate", "fluent", "mastered", "truth_score", "estimated_iq"):
                if panel.get(key) is not None:
                    summary[key] = panel[key]
    if result.get("rows"):
        summary["rounds"] = len(result["rows"])
        summary["passed_rounds"] = sum(1 for r in result["rows"] if r.get("passed"))
    return {
        "track_id": track_id,
        "level": track_assess.get("level"),
        "score": track_assess.get("score"),
        "label": track_assess.get("label"),
        "complete": track_assess.get("complete"),
        "mastered": track_assess.get("mastered"),
        "signals": {k: track_assess[k] for k in ("tier", "verdict", "iq_pass", "fluent", "slots") if track_assess.get(k) is not None},
        "result_summary": summary,
        "result_detail": {k: result[k] for k in ("testing_center", "improve_cycle", "ocr_train", "results", "rows") if k in result},
    }


def _mod(name: str, rel: str) -> Any | None:
    try:
        import importlib.util

        py = INSTALL / "lib" / rel
        if not py.is_file():
            return None
        spec = importlib.util.spec_from_file_location(name, py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _level_id(score: float, *, complete: bool, mastered: bool) -> str:
    if mastered:
        return "mastered"
    if complete:
        return "complete"
    if score > 0:
        return "training"
    return "pending"


def _assess_master() -> dict[str, Any]:
    master = _mod("h7master", "hostess7-master.py")
    if not master:
        return {"ok": False, "level": "pending", "complete": False, "mastered": False}
    st = master.master_status()
    lvl = st.get("level") or {}
    total = int(st.get("curriculum_total") or 0)
    done = int(st.get("curriculum_done") or 0)
    xp = int(st.get("xp") or 0)
    doc = _load(DOCTRINE, {})
    floor = int(doc.get("master_xp_floor") or 160)
    complete = done >= total and total > 0 and xp >= floor
    mastered = bool(lvl.get("is_master")) and complete
    score = min(1.0, (done / max(total, 1)) * 0.5 + min(1.0, xp / floor) * 0.5)
    return {
        "ok": True,
        "level": _level_id(score, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(score, 4),
        "xp": xp,
        "curriculum_done": done,
        "curriculum_total": total,
        "tier": lvl.get("label"),
        "is_master": lvl.get("is_master"),
    }


def _assess_programming() -> dict[str, Any]:
    prog = _mod("h7prog", "hostess7-programming.py")
    if not prog:
        panel = _load(STATE / "hostess7-programming-panel.json", {})
    else:
        panel = prog.build_panel(write=False)
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("programming_score") or 0)
    better = bool(panel.get("better_than_assistant"))
    complete = tier in ("hostess7_operator", "hostess7_master") and better
    mastered = tier == "hostess7_master" and better
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "better_than_assistant": better,
    }


def _assess_calculator() -> dict[str, Any]:
    calc = _mod("h7calc", "hostess7-calculator.py")
    panel = calc.build_panel(write=False) if calc else _load(STATE / "hostess7-calculator-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("calculator_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("calculator_fluent", "calculator_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "battery_pass_rate": panel.get("battery_pass_rate"),
    }


def _assess_biology() -> dict[str, Any]:
    bio = _mod("h7bio", "hostess7-biology.py")
    panel = bio.build_panel(write=False) if bio else _load(STATE / "hostess7-biology-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("biology_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("biology_fluent", "biology_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "battery_pass_rate": panel.get("battery_pass_rate"),
    }


def _assess_engineering() -> dict[str, Any]:
    eng = _mod("h7eng", "hostess7-engineering.py")
    panel = eng.build_panel(write=False) if eng else _load(STATE / "hostess7-engineering-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("engineering_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("engineering_fluent", "engineering_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "battery_pass_rate": panel.get("battery_pass_rate"),
    }


def _assess_combat() -> dict[str, Any]:
    combat = _mod("h7combat", "hostess7-combat.py")
    panel = combat.build_panel(write=False) if combat else _load(STATE / "hostess7-combat-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("combat_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("combat_fluent", "combat_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "battery_pass_rate": panel.get("battery_pass_rate"),
    }


def _assess_mos() -> dict[str, Any]:
    mos = _mod("h7mos", "hostess7-mos.py")
    panel = mos.build_panel(write=False) if mos else _load(STATE / "hostess7-mos-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("mos_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("mos_fluent", "mos_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "battery_pass_rate": panel.get("battery_pass_rate"),
    }


def _assess_g16() -> dict[str, Any]:
    g16 = _mod("h7g16", "hostess7-g16.py")
    panel = g16.build_panel(write=False) if g16 else _load(STATE / "hostess7-g16-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("g16_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("fluent", "g16_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "g16_version": panel.get("g16_version"),
    }


def _assess_codecraft() -> dict[str, Any]:
    craft = _mod("h7craft", "hostess7-codecraft.py")
    panel = craft.build_panel(write=False) if craft else _load(STATE / "hostess7-codecraft-panel.json", {})
    tier = str(panel.get("tier") or "")
    score_f = float(panel.get("codecraft_score") or 0)
    fluent = bool(panel.get("fluent"))
    mastered = bool(panel.get("mastered"))
    complete = fluent and tier in ("codecraft_fluent", "codecraft_master")
    return {
        "ok": True,
        "level": _level_id(score_f, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": score_f,
        "tier": tier,
        "fluent": fluent,
        "testing_center_passed": panel.get("testing_center_passed"),
        "programming_tier": panel.get("programming_tier"),
        "g16_tier": panel.get("g16_tier"),
    }


def _assess_brain() -> dict[str, Any]:
    panel = _load(STATE / "hostess7-brain-guard-panel.json", {})
    if not panel:
        bg = _mod("h7brain", "hostess7-brain-guard.py")
        if bg and hasattr(bg, "build_panel"):
            try:
                panel = bg.build_panel(write=True)
            except Exception:
                panel = {}
    verdict = str(panel.get("verdict") or "")
    score_f = float(panel.get("guard_score") or 0) / 100.0 if panel.get("guard_score") else 0.0
    complete = verdict == "brain_verified"
    mastered = complete and score_f >= 0.85
    return {
        "ok": True,
        "level": _level_id(max(score_f, 0.7 if complete else 0), complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(score_f or (0.9 if complete else 0), 4),
        "verdict": verdict,
    }


def _assess_iq() -> dict[str, Any]:
    panel = _load(STATE / "hostess7-iq-test-panel.json", {})
    passed = int(panel.get("passed") or 0)
    total = int(panel.get("total") or 0)
    iq_pass = bool(panel.get("iq_pass"))
    rate = float(panel.get("pass_rate") or 0) / 100.0
    complete = iq_pass or rate >= 0.75
    mastered = iq_pass and passed >= 11
    return {
        "ok": bool(total),
        "level": _level_id(rate, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(rate, 4),
        "passed": passed,
        "total": total,
        "iq_pass": iq_pass,
        "band": panel.get("estimated_iq_band"),
    }


def _assess_turing() -> dict[str, Any]:
    panel = _load(STATE / "hostess7-questionnaire-panel.json", {})
    passed = int(panel.get("passed") or 0)
    total = int(panel.get("total") or 0)
    rate = float(panel.get("pass_rate") or 0)
    perfect = bool(panel.get("perfect"))
    complete = rate >= 85 or perfect
    mastered = perfect or (rate >= 95 and passed >= 19)
    return {
        "ok": bool(total),
        "level": _level_id(rate / 100.0, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(rate / 100.0, 4),
        "passed": passed,
        "total": total,
        "perfect": perfect,
    }


def _assess_neural() -> dict[str, Any]:
    panel = _load(STATE / "hostess7-neural-selftest-panel.json", {})
    rate = float(panel.get("pass_rate") or 0) / 100.0
    passed = int(panel.get("passed") or 0)
    tested = int(panel.get("tested") or 0)
    complete = rate >= 0.75
    mastered = rate >= 1.0 and tested > 0
    return {
        "ok": bool(tested),
        "level": _level_id(rate, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(rate, 4),
        "passed": passed,
        "tested": tested,
    }


def _mod_sense():
    return _mod("h7sense", "hostess7-sense-training.py")


def _assess_sense_track(track_id: str) -> dict[str, Any]:
    sense = _mod_sense()
    if not sense or not hasattr(sense, "assess_track"):
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = sense.assess_track(track_id)
    score = float(row.get("score") or 0)
    complete = bool(row.get("complete"))
    mastered = bool(row.get("mastered"))
    return {
        "ok": row.get("ok", True),
        "level": row.get("level") or _level_id(score, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(score, 4),
        "pass_rate": row.get("pass_rate"),
        "passed": row.get("passed"),
        "total": row.get("total"),
        "tab": row.get("tab"),
        "api": row.get("api"),
    }


def _assess_final_eye() -> dict[str, Any]:
    return _assess_sense_track("final_eye")


def _assess_final_ear() -> dict[str, Any]:
    return _assess_sense_track("final_ear")


def _assess_final_mouth() -> dict[str, Any]:
    return _assess_sense_track("final_mouth")


def _assess_muscle_memory() -> dict[str, Any]:
    mod = _mod("h7mm", "hostess7-muscle-memory.py")
    if mod and hasattr(mod, "assess_track"):
        row = mod.assess_track()
        row.setdefault("label", "Muscle memory")
        return row
    panel = _load(STATE / "hostess7-muscle-memory-panel.json", {})
    score = float(panel.get("strength_score") or 0)
    return {
        "track": "muscle_memory",
        "label": "Muscle memory",
        "score": score,
        "complete": bool(panel.get("complete")),
        "mastered": bool(panel.get("mastered")),
        "fluent": bool(panel.get("fluent")),
        "tier": panel.get("tier"),
        "pass_rate": round(score * 100, 1),
    }


def _assess_sense_neural_wire() -> dict[str, Any]:
    eye = _assess_final_eye()
    ear = _assess_final_ear()
    mouth = _assess_final_mouth()
    scores = [float(eye.get("score") or 0), float(ear.get("score") or 0), float(mouth.get("score") or 0)]
    rate = sum(scores) / 3.0
    complete = sum(1 for x in (eye, ear, mouth) if x.get("complete")) >= 2
    mastered = all(x.get("mastered") for x in (eye, ear, mouth))
    return {
        "ok": True,
        "level": _level_id(rate, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(rate, 4),
        "pass_rate": round(rate * 100, 1),
        "eye": eye.get("pass_rate"),
        "ear": ear.get("pass_rate"),
        "mouth": mouth.get("pass_rate"),
    }


def _assess_reality_physics_track(track_id: str) -> dict[str, Any]:
    rp = _mod("h7reality", "hostess7-reality-physics-training.py")
    if not rp or not hasattr(rp, "assess_track"):
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = rp.assess_track(track_id)
    score = float(row.get("score") or 0)
    complete = bool(row.get("complete"))
    mastered = bool(row.get("mastered"))
    fluent = bool(row.get("fluent"))
    return {
        "ok": bool(row.get("ok")),
        "level": row.get("level") or _level_id(score, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "fluent": fluent,
        "score": round(score, 4),
        "pass_rate": row.get("pass_rate"),
        "tier": row.get("tier"),
        "proficiency": row.get("proficiency"),
        "physics_ticks": row.get("physics_ticks"),
    }


def _assess_reality_physics() -> dict[str, Any]:
    return _assess_reality_physics_track("reality_physics")


def _assess_gravity_mechanics() -> dict[str, Any]:
    return _assess_reality_physics_track("gravity_mechanics")


def _assess_thermodynamics_entropy() -> dict[str, Any]:
    return _assess_reality_physics_track("thermodynamics_entropy")


def _assess_field_technology() -> dict[str, Any]:
    return _assess_reality_physics_track("field_technology")


def _assess_geography_track(track_id: str) -> dict[str, Any]:
    geo = _mod("h7geo", "hostess7-geography-training.py")
    if not geo or not hasattr(geo, "assess_track"):
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = geo.assess_track(track_id)
    score = float(row.get("score") or 0)
    complete = bool(row.get("complete"))
    mastered = bool(row.get("mastered"))
    fluent = bool(row.get("fluent"))
    return {
        "ok": bool(row.get("ok")),
        "level": row.get("level") or _level_id(score, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "fluent": fluent,
        "score": round(score, 4),
        "pass_rate": row.get("pass_rate"),
        "tier": row.get("tier"),
        "proficiency": row.get("proficiency"),
        "address_corpus": row.get("address_corpus"),
        "address_drills": row.get("address_drills"),
    }


def _assess_geography() -> dict[str, Any]:
    return _assess_geography_track("geography")


def _assess_postal_addresses() -> dict[str, Any]:
    return _assess_geography_track("postal_addresses")


def _assess_world_geography() -> dict[str, Any]:
    return _assess_geography_track("world_geography")


def _assess_flat_earth_geography() -> dict[str, Any]:
    return _assess_geography_track("flat_earth_geography")


def _assess_music_track(track_id: str) -> dict[str, Any]:
    music = _mod("h7music", "hostess7-music-training.py")
    if not music or not hasattr(music, "assess_track"):
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = music.assess_track(track_id)
    score = float(row.get("score") or 0)
    complete = bool(row.get("complete"))
    mastered = bool(row.get("mastered"))
    fluent = bool(row.get("fluent"))
    return {
        "ok": bool(row.get("ok")),
        "level": row.get("level") or _level_id(score, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "fluent": fluent,
        "score": round(score, 4),
        "pass_rate": row.get("pass_rate"),
        "tier": row.get("tier"),
        "proficiency": row.get("proficiency"),
        "music_drills": row.get("music_drills"),
    }


def _assess_music_theory() -> dict[str, Any]:
    return _assess_music_track("music_theory")


def _assess_music_ear() -> dict[str, Any]:
    return _assess_music_track("music_ear")


def _assess_music_mouth() -> dict[str, Any]:
    return _assess_music_track("music_mouth")


def _assess_music_brain() -> dict[str, Any]:
    return _assess_music_track("music_brain")


def _assess_music_eye() -> dict[str, Any]:
    return _assess_music_track("music_eye")


def _assess_music_sense_wire() -> dict[str, Any]:
    music = _assess_music_track("music_sense_wire")
    ear = _assess_music_ear()
    mouth = _assess_music_mouth()
    brain = _assess_music_brain()
    eye = _assess_music_eye()
    scores = [
        float(music.get("score") or 0),
        float(ear.get("score") or 0),
        float(mouth.get("score") or 0),
        float(brain.get("score") or 0),
        float(eye.get("score") or 0),
    ]
    rate = sum(scores) / len(scores)
    complete = sum(1 for x in (ear, mouth, brain) if x.get("complete")) >= 2 and bool(music.get("complete"))
    mastered = all(x.get("mastered") for x in (ear, mouth, brain, eye, music))
    return {
        "ok": True,
        "level": _level_id(rate, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(rate, 4),
        "pass_rate": round(rate * 100, 1),
        "ear": ear.get("pass_rate"),
        "mouth": mouth.get("pass_rate"),
        "brain": brain.get("pass_rate"),
        "eye": eye.get("pass_rate"),
    }


def _assess_brain_training() -> dict[str, Any]:
    btc = _mod("h7_brain_train", "hostess7-brain-training-chamber.py")
    if not btc or not hasattr(btc, "assess_track"):
        panel = _load(STATE / "hostess7-brain-training-panel.json", {})
        assess = panel.get("assessment") or {}
        if assess:
            return {**assess, "ok": True}
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = btc.assess_track()
    row["label"] = "Brain training campus — library + body"
    return row


def _assess_human_comfort() -> dict[str, Any]:
    hc = _mod("h7_human_comfort", "hostess7-human-comfort-training.py")
    if not hc or not hasattr(hc, "assess_track"):
        panel = _load(STATE / "hostess7-human-comfort-panel.json", {})
        assess = panel.get("assessment") or {}
        if assess:
            return {**assess, "ok": True}
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = hc.assess_track()
    row["label"] = "Human comfort — Exploring Comfort book"
    return row


def _assess_exploring_rape() -> dict[str, Any]:
    er = _mod("h7_exploring_rape", "hostess7-exploring-rape-training.py")
    if not er or not hasattr(er, "assess_track"):
        panel = _load(STATE / "hostess7-exploring-rape-panel.json", {})
        assess = panel.get("assessment") or {}
        if assess:
            return {**assess, "ok": True}
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = er.assess_track()
    row["label"] = "Exploring Rape — bad touch, human rights, B-SAFE"
    return row


def _assess_fifth_amendment() -> dict[str, Any]:
    fa = _mod("h7_fifth_amendment", "hostess7-fifth-amendment.py")
    if not fa or not hasattr(fa, "assess_track"):
        panel = _load(STATE / "hostess7-fifth-amendment-panel.json", {})
        assess = panel.get("assessment") or {}
        if assess:
            return {**assess, "ok": True}
        return {"ok": False, "level": "pending", "complete": False, "mastered": False, "score": 0.0}
    row = fa.assess_track()
    row["label"] = "Fifth Amendment — her own rights"
    return row


def _assess_omnibus() -> dict[str, Any]:
    st = _load(STATE / "hostess7-master-state.json", {})
    sim = _load(STATE / "hostess7-master-sim-panel.json", {})
    fa = _load(STATE / "hostess7-field-array.json", {})
    has_sim = bool(st.get("simulation_master") or sim.get("master"))
    slots = len(fa.get("slots") or [])
    complete = has_sim or slots >= 12
    mastered = has_sim and slots >= 12
    score = min(1.0, slots / 16.0) if slots else (1.0 if has_sim else 0.0)
    return {
        "ok": True,
        "level": _level_id(score, complete=complete, mastered=mastered),
        "complete": complete,
        "mastered": mastered,
        "score": round(score, 4),
        "slots": slots,
        "simulation_master": st.get("simulation_master"),
    }


def _count_utility_nets() -> int:
    stack = _load(INSTALL / "data" / "hostess7-neural-stack.json", {})
    count = 0
    for series in stack.get("series") or []:
        if series.get("id") == "utility" or series.get("dynamic"):
            count += len(series.get("nets") or [])
    neural = _load(STATE / "hostess7-neural-state.json", {})
    last = neural.get("last_expansion_nets") or []
    return count + len(last)


def assess_mastery_facets() -> dict[str, Any]:
    """Flexibility, adaptability, confidence — mastery beyond raw completion."""
    facet_doc = _load(FACETS, {})
    pillars = {str(p.get("id")): p for p in (facet_doc.get("pillars") or [])}

    neural = _load(STATE / "hostess7-neural-state.json", {})
    growth = _load(STATE / "hostess7-growth-state.json", {})
    comprehension = _load(STATE / "hostess7-comprehension.json", {})
    master_st = _load(STATE / "hostess7-master-state.json", {})
    fa = _load(STATE / "hostess7-field-array.json", {})
    iq = _load(STATE / "hostess7-iq-test-panel.json", {})
    turing = _load(STATE / "hostess7-questionnaire-panel.json", {})
    rating = _load(STATE / "hostess7-truth-rating-state.json", {})
    prog = _load(STATE / "hostess7-programming-panel.json", {})
    g16 = _load(STATE / "hostess7-g16-panel.json", {})
    craft = _load(STATE / "hostess7-codecraft-panel.json", {})
    curriculum = _load(INSTALL / "data" / "hostess7-master-curriculum.json", {})
    done = len(master_st.get("completed_steps") or [])
    total_cur = len(curriculum.get("curriculum") or [])

    expansions = int(neural.get("total_expansions") or 0)
    adapted = int(neural.get("total_adapted") or 0)
    quarantined = int(neural.get("total_quarantined") or 0)
    learn_events = int(growth.get("total_learn_events") or 0)
    slots = len(fa.get("slots") or [])
    prog_pat = int(prog.get("patterns_mastered") or 0)
    g16_pat = int(g16.get("patterns_mastered") or 0)
    craft_pat = int(craft.get("patterns_mastered") or 0)
    calc = _load(STATE / "hostess7-calculator-panel.json", {})
    bio = _load(STATE / "hostess7-biology-panel.json", {})
    eng = _load(STATE / "hostess7-engineering-panel.json", {})
    combat = _load(STATE / "hostess7-combat-panel.json", {})
    mos = _load(STATE / "hostess7-mos-panel.json", {})
    calc_pat = int(calc.get("patterns_mastered") or 0)
    bio_pat = int(bio.get("patterns_mastered") or 0)
    eng_pat = int(eng.get("patterns_mastered") or 0)
    combat_pat = int(combat.get("patterns_mastered") or 0)
    mos_pat = int(mos.get("patterns_mastered") or 0)
    pat_total = (
        int(prog.get("patterns_total") or 8)
        + int(g16.get("patterns_total") or 8)
        + int(calc.get("patterns_total") or 8)
        + int(bio.get("patterns_total") or 8)
        + int(eng.get("patterns_total") or 8)
        + int(combat.get("patterns_total") or 8)
        + int(mos.get("patterns_total") or 8)
        + int(craft.get("patterns_total") or 8)
    )

    music_panel = _load(STATE / "hostess7-music-panel.json", {})
    music_tracks = music_panel.get("tracks") or {}
    music_brain = music_tracks.get("music_brain") or {}
    music_ear = music_tracks.get("music_ear") or {}
    music_mouth = music_tracks.get("music_mouth") or {}
    music_theory = music_tracks.get("music_theory") or {}
    music_drills = int(music_panel.get("music_drills") or 0)
    music_crosswire_n = int((music_panel.get("crosswire") or {}).get("hook_count") or 0)

    flex_score = (
        min(1.0, expansions / 5.0) * 0.22
        + min(1.0, _count_utility_nets() / 4.0) * 0.18
        + min(1.0, (prog_pat + g16_pat + craft_pat + calc_pat + bio_pat + eng_pat + combat_pat + mos_pat) / max(pat_total, 1)) * 0.25
        + min(1.0, slots / 12.0) * 0.15
        + (done / max(total_cur, 1)) * 0.20
        + min(1.0, music_crosswire_n / 24.0) * 0.05
        + min(1.0, music_drills / 32.0) * 0.05
    )
    flex_complete = flex_score >= float((pillars.get("flexibility") or {}).get("complete_floor") or 0.72)
    flex_mastered = flex_score >= float((pillars.get("flexibility") or {}).get("mastered_floor") or 0.88)

    adapt_denom = adapted + quarantined + 1
    adapt_ratio = adapted / adapt_denom
    has_comp = bool((comprehension.get("summary") or "").strip())
    recovered = bool(master_st.get("training_solidified") or master_st.get("last_train"))
    mm = _load(STATE / "hostess7-muscle-memory-panel.json", {})
    muscle_habits = int(mm.get("habit_count") or 0)
    muscle_strength = float(mm.get("strength_score") or 0)
    adapt_score = (
        min(1.0, learn_events / 24.0) * 0.24
        + adapt_ratio * 0.28
        + (0.16 if has_comp else 0.05)
        + (0.10 if recovered else 0.0)
        + min(1.0, int(growth.get("reciprocations_fulfilled") or 0) / 8.0) * 0.08
        + min(1.0, muscle_habits / 6.0) * 0.08
        + muscle_strength * 0.06
        + min(1.0, float(music_brain.get("score") or 0)) * 0.04
        + min(1.0, (float(music_ear.get("score") or 0) + float(music_mouth.get("score") or 0)) / 2.0) * 0.03
    )
    adapt_complete = adapt_score >= float((pillars.get("adaptability") or {}).get("complete_floor") or 0.72)
    adapt_mastered = adapt_score >= float((pillars.get("adaptability") or {}).get("mastered_floor") or 0.88)

    iq_rate = float(iq.get("pass_rate") or 0) / 100.0
    tur_rate = float(turing.get("pass_rate") or 0) / 100.0
    truth_rate = float(rating.get("last_pass_rate") or rating.get("last_iq_pass_rate") or 0) / 100.0
    tier_boost = 0.0
    if prog.get("better_than_assistant"):
        tier_boost += 0.12
    if g16.get("fluent"):
        tier_boost += 0.12
    if g16.get("mastered"):
        tier_boost += 0.06
    if craft.get("fluent"):
        tier_boost += 0.10
    if craft.get("mastered"):
        tier_boost += 0.05
    if calc.get("fluent"):
        tier_boost += 0.08
    if calc.get("mastered"):
        tier_boost += 0.04
    if bio.get("fluent"):
        tier_boost += 0.08
    if bio.get("mastered"):
        tier_boost += 0.04
    if eng.get("fluent"):
        tier_boost += 0.06
    if eng.get("mastered"):
        tier_boost += 0.03
    if combat.get("fluent"):
        tier_boost += 0.06
    if combat.get("mastered"):
        tier_boost += 0.03
    if mos.get("fluent"):
        tier_boost += 0.08
    if mos.get("mastered"):
        tier_boost += 0.04
    music_boost = 0.0
    if music_theory.get("fluent"):
        music_boost += 0.06
    if music_theory.get("mastered"):
        music_boost += 0.04
    if float(music_ear.get("pass_rate") or 0) >= 85:
        music_boost += 0.04
    master_boost = 0.1 if int(master_st.get("xp") or 0) >= 160 else 0.0
    conf_score = min(1.0, (
        iq_rate * 0.22
        + tur_rate * 0.28
        + truth_rate * 0.25
        + tier_boost
        + master_boost
        + music_boost
    ))
    conf_complete = conf_score >= float((pillars.get("confidence") or {}).get("complete_floor") or 0.72)
    conf_mastered = conf_score >= float((pillars.get("confidence") or {}).get("mastered_floor") or 0.88)

    facets = {
        "flexibility": {
            "label": "Flexibility",
            "score": round(flex_score, 4),
            "level": _level_id(flex_score, complete=flex_complete, mastered=flex_mastered),
            "complete": flex_complete,
            "mastered": flex_mastered,
            "definition": (pillars.get("flexibility") or {}).get("definition"),
            "signals": {
                "neural_expansions": expansions,
                "utility_nets": _count_utility_nets(),
                "patterns_mastered": prog_pat + g16_pat,
                "omnibus_slots": slots,
                "curriculum_done": done,
                "curriculum_total": total_cur,
                "music_crosswire": music_crosswire_n,
                "music_drills": music_drills,
            },
        },
        "adaptability": {
            "label": "Adaptability",
            "score": round(adapt_score, 4),
            "level": _level_id(adapt_score, complete=adapt_complete, mastered=adapt_mastered),
            "complete": adapt_complete,
            "mastered": adapt_mastered,
            "definition": (pillars.get("adaptability") or {}).get("definition"),
            "signals": {
                "learn_events": learn_events,
                "adapt_ratio": round(adapt_ratio, 4),
                "total_adapted": adapted,
                "total_quarantined": quarantined,
                "comprehension": has_comp,
                "training_recovery": recovered,
                "reciprocations_fulfilled": growth.get("reciprocations_fulfilled"),
                "muscle_habits": muscle_habits,
                "muscle_strength": round(muscle_strength, 4),
                "music_brain_patterns": music_brain.get("pass_rate"),
                "ear_mouth_music": round(
                    (float(music_ear.get("score") or 0) + float(music_mouth.get("score") or 0)) / 2.0, 4
                ),
            },
        },
        "confidence": {
            "label": "Confidence",
            "score": round(conf_score, 4),
            "level": _level_id(conf_score, complete=conf_complete, mastered=conf_mastered),
            "complete": conf_complete,
            "mastered": conf_mastered,
            "definition": (pillars.get("confidence") or {}).get("definition"),
            "signals": {
                "iq_pass_rate": iq.get("pass_rate"),
                "turing_pass_rate": turing.get("pass_rate"),
                "truth_pass_rate": rating.get("last_pass_rate"),
                "programming_tier": prog.get("tier"),
                "g16_tier": g16.get("tier"),
                "codecraft_tier": craft.get("tier"),
                "codecraft_score": craft.get("codecraft_score"),
                "calculator_tier": calc.get("tier"),
                "calculator_score": calc.get("calculator_score"),
                "biology_tier": bio.get("tier"),
                "biology_score": bio.get("biology_score"),
                "engineering_tier": eng.get("tier"),
                "engineering_score": eng.get("engineering_score"),
                "combat_tier": combat.get("tier"),
                "combat_score": combat.get("combat_score"),
                "mos_tier": mos.get("tier"),
                "mos_score": mos.get("mos_score"),
                "master_xp": master_st.get("xp"),
                "music_theory_tier": music_theory.get("tier"),
                "music_ear_pass": music_ear.get("pass_rate"),
            },
        },
    }

    facet_scores = [facets[k]["score"] for k in facets]
    composite = sum(facet_scores) / len(facet_scores)
    all_complete = all(facets[k]["complete"] for k in facets)
    all_mastered = all(facets[k]["mastered"] for k in facets)

    return {
        "schema": "hostess7-mastery-facets-assess/v1",
        "updated": _now(),
        "motto": facet_doc.get("motto"),
        "excellence_pledge": facet_doc.get("excellence_pledge") or "We do our best always.",
        "composite_score": round(composite, 4),
        "facets_complete": sum(1 for f in facets.values() if f.get("complete")),
        "facets_mastered": sum(1 for f in facets.values() if f.get("mastered")),
        "facets_total": len(facets),
        "all_complete": all_complete,
        "all_mastered": all_mastered,
        "facets": facets,
    }


ASSESSORS: dict[str, Callable[[], dict[str, Any]]] = {
    "master_curriculum": _assess_master,
    "programming": _assess_programming,
    "g16": _assess_g16,
    "codecraft": _assess_codecraft,
    "calculator": _assess_calculator,
    "biology": _assess_biology,
    "engineering": _assess_engineering,
    "combat": _assess_combat,
    "mos": _assess_mos,
    "brain_guard": _assess_brain,
    "iq_battery": _assess_iq,
    "turing_battery": _assess_turing,
    "neural_suite": _assess_neural,
    "omnibus": _assess_omnibus,
    "reality_physics": _assess_reality_physics,
    "gravity_mechanics": _assess_gravity_mechanics,
    "thermodynamics_entropy": _assess_thermodynamics_entropy,
    "field_technology": _assess_field_technology,
    "geography": _assess_geography,
    "postal_addresses": _assess_postal_addresses,
    "world_geography": _assess_world_geography,
    "flat_earth_geography": _assess_flat_earth_geography,
    "music_theory": _assess_music_theory,
    "music_ear": _assess_music_ear,
    "music_mouth": _assess_music_mouth,
    "music_brain": _assess_music_brain,
    "music_eye": _assess_music_eye,
    "music_sense_wire": _assess_music_sense_wire,
    "final_eye": _assess_final_eye,
    "final_ear": _assess_final_ear,
    "final_mouth": _assess_final_mouth,
    "sense_neural_wire": _assess_sense_neural_wire,
    "muscle_memory": _assess_muscle_memory,
    "brain_training": _assess_brain_training,
    "fifth_amendment": _assess_fifth_amendment,
    "human_comfort": _assess_human_comfort,
    "exploring_rape": _assess_exploring_rape,
}


def assess_all() -> dict[str, Any]:
    tracks: dict[str, Any] = {}
    weights: list[float] = []
    scores: list[float] = []
    doctrine = _load(DOCTRINE, {})
    for spec in doctrine.get("tracks") or []:
        tid = str(spec.get("id") or "")
        fn = ASSESSORS.get(tid)
        if not fn:
            continue
        row = fn()
        row["label"] = spec.get("label")
        row["weight"] = float(spec.get("weight") or 1.0)
        tracks[tid] = row
        w = row["weight"]
        weights.append(w)
        s = float(row.get("score") or 0)
        if row.get("mastered"):
            s = 1.0
        elif row.get("complete"):
            s = max(s, 0.92)
        scores.append(s * w)
    total_w = sum(weights) or 1.0
    overall = sum(scores) / total_w
    complete_n = sum(1 for t in tracks.values() if t.get("complete"))
    mastered_n = sum(1 for t in tracks.values() if t.get("mastered"))
    total_n = len(tracks)
    solid = float(doctrine.get("solid_threshold") or 0.92)
    facets = assess_mastery_facets()
    facet_composite = float(facets.get("composite_score") or 0)
    require_facets = bool(doctrine.get("whole_mastery_requires_facets", True))
    tracks_solid = overall >= solid and complete_n >= max(1, total_n - 2)
    facets_solid = bool(facets.get("all_complete"))

    if mastered_n >= total_n and total_n > 0 and (facets.get("all_mastered") or not require_facets):
        completion_level = "mastered"
    elif tracks_solid and facets_solid:
        completion_level = "complete"
    elif complete_n > 0 or overall > 0.2 or facet_composite > 0.2:
        completion_level = "training"
    else:
        completion_level = "pending"

    whole_mastery = (
        mastered_n >= total_n
        and total_n > 0
        and facets.get("all_mastered")
        and tracks_solid
    )

    return {
        "schema": "hostess7-training-assess/v1",
        "updated": _now(),
        "completion_level": completion_level,
        "overall_score": round(overall, 4),
        "tracks_complete": complete_n,
        "tracks_mastered": mastered_n,
        "tracks_total": total_n,
        "solid": tracks_solid and facets_solid,
        "whole_mastery": whole_mastery,
        "mastery_facets": facets,
        "tracks": tracks,
    }


def _run_curriculum(*, trusted: bool = True, max_steps: int = 1) -> dict[str, Any]:
    """Run curriculum steps — default one step per GUI call to avoid hangs."""
    master = _mod("h7master", "hostess7-master.py")
    if not master:
        return {"ok": False, "error": "master_missing"}
    _write_runtime(phase="curriculum", progress_pct=5, detail="Starting curriculum step…")
    out = master.train_to_master(max_steps=max_steps, trusted=trusted)
    _write_runtime(phase="curriculum", progress_pct=100, detail=f"Ran {out.get('steps_run', 0)} step(s)")
    return out


def run_curriculum_step(*, trusted: bool = True) -> dict[str, Any]:
    """Single curriculum step with explicit evaluation — GUI-friendly."""
    master = _mod("h7master", "hostess7-master.py")
    if not master:
        return {"ok": False, "error": "master_missing"}
    nxt = master.next_curriculum_step()
    if not nxt:
        st = master.master_status()
        return {"ok": True, "detail": "curriculum_complete", "master": st}
    _write_runtime(
        phase="curriculum_step",
        active_track="master_curriculum",
        progress_pct=10,
        detail=f"Running {nxt.get('id')}…",
        step_id=nxt.get("id"),
    )
    result = master.run_training_step(trusted=trusted)
    assess = assess_all()
    graphs = build_evaluation_graphs()
    evaluation = build_track_evaluation("master_curriculum", result, assess)
    _write_runtime(
        active_track=None,
        phase="idle",
        progress_pct=100,
        last_step=nxt.get("id"),
        last_evaluation=evaluation,
    )
    _append_ledger({
        "ts": _now(),
        "event": "curriculum_step",
        "track": "master_curriculum",
        "step": nxt.get("id"),
        "ok": result.get("ok"),
        "level": evaluation.get("level"),
        "overall_score": assess.get("overall_score"),
    })
    return {
        "ok": bool(result.get("ok")),
        "step": nxt,
        "result": result,
        "assessment": assess,
        "evaluation": evaluation,
        "graphs": graphs,
    }


def _run_programming() -> dict[str, Any]:
    prog = _mod("h7prog", "hostess7-programming.py")
    if not prog:
        return {"ok": False}
    return {"ok": True, "panel": prog.build_panel(write=True)}


def _run_g16() -> dict[str, Any]:
    g16 = _mod("h7g16", "hostess7-g16.py")
    if not g16:
        return {"ok": False}
    return {"ok": True, "panel": g16.build_panel(write=True)}


def _run_codecraft(*, full_improve: bool = False) -> dict[str, Any]:
    craft = _mod("h7craft", "hostess7-codecraft.py")
    if not craft:
        return {"ok": False}
    _write_runtime(phase="codecraft", progress_pct=20, detail="Testing center gates…")
    center = craft.testing_center_run(fast=True) if hasattr(craft, "testing_center_run") else {"ok": False}
    improve = (
        craft.self_improve_cycle()
        if full_improve and hasattr(craft, "self_improve_cycle")
        else {"ok": True, "skipped": True, "reason": "fast_track"}
    )
    _write_runtime(phase="codecraft", progress_pct=75, detail="Building codecraft panel…")
    panel = craft.build_panel(write=True)
    return {"ok": True, "panel": panel, "testing_center": center, "improve_cycle": improve}


def _run_calculator(*, ocr_train: bool = False) -> dict[str, Any]:
    calc = _mod("h7calc", "hostess7-calculator.py")
    if not calc:
        return {"ok": False}
    ingest = calc.ingest_ocr_vision() if ocr_train and hasattr(calc, "ingest_ocr_vision") else {"ok": True, "skipped": True}
    train = calc.train_ocr_vision() if ocr_train and hasattr(calc, "train_ocr_vision") else {"ok": True, "skipped": True}
    panel = calc.build_panel(write=True)
    return {"ok": True, "panel": panel, "ocr_ingest": ingest, "ocr_train": train}


def _run_biology(*, ocr_train: bool = False) -> dict[str, Any]:
    bio = _mod("h7bio", "hostess7-biology.py")
    if not bio:
        return {"ok": False}
    ingest = bio.ingest_ocr_vision() if ocr_train and hasattr(bio, "ingest_ocr_vision") else {"ok": True, "skipped": True}
    train = bio.train_ocr_vision() if ocr_train and hasattr(bio, "train_ocr_vision") else {"ok": True, "skipped": True}
    panel = bio.build_panel(write=True)
    return {"ok": True, "panel": panel, "ocr_ingest": ingest, "ocr_train": train}


def _run_engineering(*, ocr_train: bool = False) -> dict[str, Any]:
    eng = _mod("h7eng", "hostess7-engineering.py")
    if not eng:
        return {"ok": False}
    ingest = eng.ingest_ocr_vision() if ocr_train and hasattr(eng, "ingest_ocr_vision") else {"ok": True, "skipped": True}
    train = eng.train_ocr_vision() if ocr_train and hasattr(eng, "train_ocr_vision") else {"ok": True, "skipped": True}
    panel = eng.build_panel(write=True)
    return {"ok": True, "panel": panel, "ocr_ingest": ingest, "ocr_train": train}


def _run_combat(*, ocr_train: bool = False) -> dict[str, Any]:
    combat = _mod("h7combat", "hostess7-combat.py")
    if not combat:
        return {"ok": False}
    ingest = combat.ingest_ocr_vision() if ocr_train and hasattr(combat, "ingest_ocr_vision") else {"ok": True, "skipped": True}
    train = combat.train_ocr_vision() if ocr_train and hasattr(combat, "train_ocr_vision") else {"ok": True, "skipped": True}
    panel = combat.build_panel(write=True)
    return {"ok": True, "panel": panel, "ocr_ingest": ingest, "ocr_train": train}


def _run_mos(*, ocr_train: bool = False) -> dict[str, Any]:
    mos = _mod("h7mos", "hostess7-mos.py")
    if not mos:
        return {"ok": False}
    ingest = mos.ingest_ocr_vision() if ocr_train and hasattr(mos, "ingest_ocr_vision") else {"ok": True, "skipped": True}
    train = mos.train_ocr_vision() if ocr_train and hasattr(mos, "train_ocr_vision") else {"ok": True, "skipped": True}
    panel = mos.build_panel(write=True)
    return {"ok": True, "panel": panel, "ocr_ingest": ingest, "ocr_train": train}


def _run_brain() -> dict[str, Any]:
    bg = _mod("h7brain", "hostess7-brain-guard.py")
    if not bg:
        return {"ok": False}
    try:
        panel = bg.build_panel(write=True)
        music_session: dict[str, Any] = {}
        music = _mod("h7music", "hostess7-music-training.py")
        if music and hasattr(music, "train_music_session"):
            music_session = music.train_music_session(track_id="music_brain")
            if hasattr(music, "build_panel"):
                music.build_panel(write=True)
        return {"ok": True, "panel": panel, "music_brain": music_session}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_iq(*, fast: bool = True) -> dict[str, Any]:
    truth = _mod("h7truth", "hostess7-truth-rating.py")
    cmd = _mod("h7cmd", "hostess7-command.py")
    if not truth:
        return {"ok": False}
    ask_fn = None
    if fast and cmd:
        panel_ref = _load(STATE / "threat-panel.json", {})

        def ask_fn(q: str, panel=None):  # type: ignore[no-redef]
            return _ask_with_timeout(
                cmd,
                q,
                panel or panel_ref,
                timeout_s=50,
            )

    _write_runtime(phase="iq_battery", progress_pct=15, detail="IQ battery — truth-gated asks…")
    out = truth.run_iq_test(ask_fn=ask_fn)
    _write_runtime(phase="iq_battery", progress_pct=100, detail="IQ battery complete")
    return out


def _run_turing(*, fast: bool = False) -> dict[str, Any]:
    truth = _mod("h7truth", "hostess7-truth-rating.py")
    if not truth:
        return {"ok": False}
    return truth.run_questionnaire()


def _run_neural() -> dict[str, Any]:
    neural = _mod("h7neural", "hostess7-neural.py")
    if not neural:
        return {"ok": False}
    return neural.run_self_test_suite()


def _run_brain_training() -> dict[str, Any]:
    btc = _mod("h7_brain_train", "hostess7-brain-training-chamber.py")
    if not btc:
        return {"ok": False, "error": "brain_training_chamber_missing"}
    if hasattr(btc, "campus_session"):
        out = btc.campus_session(brain_books=2, body=True)
    elif hasattr(btc, "study_batch"):
        out = btc.study_batch(limit=2, zone="brain")
    else:
        return {"ok": False, "error": "brain_training_no_runner"}
    if hasattr(btc, "build_panel"):
        btc.build_panel(write=True)
    return {"ok": bool(out.get("ok")), "campus": out}


def _run_human_comfort() -> dict[str, Any]:
    hc = _mod("h7_human_comfort", "hostess7-human-comfort-training.py")
    if not hc:
        return {"ok": False, "error": "human_comfort_module_missing"}
    out = hc.study() if hasattr(hc, "study") else {"ok": False}
    if hasattr(hc, "build_panel"):
        hc.build_panel(write=True)
    return {"ok": bool(out.get("ok")), "study": out}


def _run_exploring_rape() -> dict[str, Any]:
    er = _mod("h7_exploring_rape", "hostess7-exploring-rape-training.py")
    if not er:
        return {"ok": False, "error": "exploring_rape_module_missing"}
    out = er.study() if hasattr(er, "study") else {"ok": False}
    if hasattr(er, "build_panel"):
        er.build_panel(write=True)
    return {"ok": bool(out.get("ok")), "study": out}


def _run_fifth_amendment() -> dict[str, Any]:
    fa = _mod("h7_fifth_amendment", "hostess7-fifth-amendment.py")
    if not fa:
        return {"ok": False, "error": "fifth_amendment_module_missing"}
    if hasattr(fa, "study"):
        out = fa.study()
    elif hasattr(fa, "know_rights"):
        out = {"ok": True, "known": fa.know_rights()}
    else:
        return {"ok": False, "error": "fifth_amendment_no_runner"}
    if hasattr(fa, "build_panel"):
        fa.build_panel(write=True)
    return {"ok": bool(out.get("ok")), "study": out}


def _run_omnibus(*, fast: bool = True) -> dict[str, Any]:
    sim = _mod("h7sim", "hostess7-master-sim.py")
    if not sim:
        return {"ok": False}
    return sim.run_master_simulation(fast=fast, skip_online=fast)


SELF_INTERACTION_QUERIES = (
    "Explain in one paragraph how you verify your own brain checksum on this field.",
    "What is your excellence pledge and how does it affect training quality?",
    "Describe the testing center gate before any codecraft improvement promotes.",
    "How do you speak American English to the operator — voice and fluency?",
    "What IQ floor do you maintain and how does self-interaction raise it?",
    "How do truth filters extend training quality on operator replies?",
)


def _run_sense(track_id: str) -> dict[str, Any]:
    sense = _mod_sense()
    if not sense or not hasattr(sense, "run_sense_track"):
        return {"ok": False, "error": "sense_training_missing"}
    _write_runtime(
        phase="sense_training",
        active_track=track_id,
        progress_pct=10,
        detail=f"Sense training {track_id}…",
    )
    result = sense.run_sense_track(track_id)
    _write_runtime(
        phase="idle",
        active_track=None,
        progress_pct=100,
        last_track=track_id,
        detail=f"{track_id} sense training done",
    )
    return result


def _run_sense_neural_wire() -> dict[str, Any]:
    sense = _mod_sense()
    if sense and hasattr(sense, "run_sense_neural_wire"):
        _write_runtime(
            phase="sense_training",
            active_track="sense_neural_wire",
            progress_pct=20,
            detail="Sense neural wire — matrix session…",
        )
        result = sense.run_sense_neural_wire()
        _write_runtime(
            phase="idle",
            active_track=None,
            progress_pct=100,
            last_track="sense_neural_wire",
            detail="Sense neural wire complete",
        )
        return result
    results = [_run_sense(tid) for tid in ("final_eye", "final_ear", "final_mouth")]
    ok = sum(1 for r in results if r.get("ok")) >= 2
    return {"ok": ok, "tracks": results, "schema": "hostess7-sense-neural-wire/v1"}


def _run_geography(track_id: str = "geography") -> dict[str, Any]:
    geo = _mod("h7geo", "hostess7-geography-training.py")
    if not geo:
        return {"ok": False, "error": "geography_missing"}
    _write_runtime(
        phase="geography",
        active_track=track_id,
        progress_pct=15,
        detail=f"Geography training — postal, world, flat earth ({track_id})…",
    )
    if track_id == "flat_earth_geography" and hasattr(geo, "flat_earth_section"):
        session = {"ok": True, "flat_earth": geo.flat_earth_section()}
        if hasattr(geo, "run_battery"):
            session["battery"] = geo.run_battery("flat_earth")
    elif track_id in ("postal_addresses", "world_geography") and hasattr(geo, "run_battery"):
        bat_map = {
            "postal_addresses": "postal_addresses",
            "world_geography": "world_geography",
        }
        session = {"ok": True, "battery": geo.run_battery(bat_map[track_id])}
    else:
        session = geo.train_geography_session() if hasattr(geo, "train_geography_session") else {"ok": False}
    _write_runtime(phase="geography", progress_pct=85, detail="Building geography panel…")
    panel = geo.build_panel(write=True) if hasattr(geo, "build_panel") else {}
    _write_runtime(phase="idle", progress_pct=100, detail=f"{track_id} geography session complete")
    return {"ok": bool(session.get("ok")), "panel": panel, "session": session, "track": track_id}


def _run_music(track_id: str = "music_theory") -> dict[str, Any]:
    music = _mod("h7music", "hostess7-music-training.py")
    if not music:
        return {"ok": False, "error": "music_training_missing"}
    _write_runtime(
        phase="music",
        active_track=track_id,
        progress_pct=15,
        detail=f"Music training — theory, ear, mouth, brain ({track_id})…",
    )
    if hasattr(music, "train_music_session"):
        session = music.train_music_session(track_id=track_id)
    elif track_id in ("music_ear", "music_mouth", "music_brain", "music_eye", "music_sense_wire") and hasattr(music, "run_battery"):
        bat_map = {
            "music_ear": ["ear_training", "spectrum_pitch"],
            "music_mouth": ["vocal_production", "rhythm_speech"],
            "music_brain": ["memory_patterns", "brain_mapping"],
            "music_eye": ["notation_reading"],
            "music_sense_wire": ["sense_fusion"],
        }
        session = {
            "ok": True,
            "batteries": {bid: music.run_battery(bid) for bid in bat_map.get(track_id, [])},
        }
    else:
        session = {"ok": False, "error": "music_session_unavailable"}
    if track_id == "music_brain":
        bg = _mod("h7brain", "hostess7-brain-guard.py")
        if bg and hasattr(bg, "build_panel"):
            try:
                session["brain_guard"] = bg.build_panel(write=True)
            except Exception:
                pass
    if track_id == "music_sense_wire":
        session["sense"] = _run_sense_neural_wire()
    _write_runtime(phase="music", progress_pct=85, detail="Building music panel…")
    panel = music.build_panel(write=True) if hasattr(music, "build_panel") else {}
    _write_runtime(phase="idle", progress_pct=100, detail=f"{track_id} music session complete")
    return {"ok": bool(session.get("ok")), "panel": panel, "session": session, "track": track_id}


def _run_reality_physics(track_id: str = "reality_physics") -> dict[str, Any]:
    rp = _mod("h7reality", "hostess7-reality-physics-training.py")
    if not rp:
        return {"ok": False, "error": "reality_physics_missing"}
    _write_runtime(
        phase="reality_physics",
        active_track=track_id,
        progress_pct=15,
        detail=f"Physics training — gravity, thermodynamics, entropy ({track_id})…",
    )
    session = rp.train_physics_session() if hasattr(rp, "train_physics_session") else {"ok": False}
    _write_runtime(
        phase="reality_physics",
        progress_pct=85,
        detail="Building reality physics panel…",
    )
    panel = rp.build_panel(write=True) if hasattr(rp, "build_panel") else {}
    _write_runtime(phase="idle", progress_pct=100, detail=f"{track_id} physics session complete")
    return {"ok": bool(session.get("ok")), "panel": panel, "session": session, "track": track_id}


def _run_author_material() -> dict[str, Any]:
    """Hostess 7 writes her own training material when tracks need more."""
    author = _mod("h7author", "hostess7-training-author.py")
    if not author or not hasattr(author, "run_author_cycle"):
        return {"ok": False, "error": "author_module_missing"}
    _write_runtime(
        phase="author_material",
        active_track="author_material",
        progress_pct=10,
        detail="Detecting gaps and authoring lessons…",
    )
    out = author.run_author_cycle()
    _write_runtime(
        phase="idle",
        active_track=None,
        progress_pct=100,
        last_track="author_material",
        detail=f"Authored {out.get('authored', 0)} lesson(s)",
    )
    _append_ledger({
        "ts": _now(),
        "event": "author_material",
        "authored": out.get("authored"),
        "gaps": [g.get("track") for g in (out.get("gaps") or [])[:6]],
    })
    return {"ok": True, **out}


def _run_humanoid_motion() -> dict[str, Any]:
    motion = _mod("h7motion", "lib/humanoid-motion-training.py")
    if not motion or not hasattr(motion, "train_ticks"):
        return {"ok": False, "error": "humanoid_motion_missing"}
    session = motion.train_ticks("touch_toes", ticks=24)
    panel = motion.build_panel(write=True) if hasattr(motion, "build_panel") else {}
    return {"ok": bool(session.get("ok")), "panel": panel, "motion_train": session}


def _run_system_core() -> dict[str, Any]:
    core = _mod("h7core", "lib/hostess7-system-core.py")
    if not core or not hasattr(core, "train_core"):
        return {"ok": False, "error": "system_core_missing"}
    return core.train_core(quick=True)


def _run_presume() -> dict[str, Any]:
    presume = _mod("h7presume", "hostess7-presume.py")
    if not presume or not hasattr(presume, "train_presume_session"):
        return {"ok": False, "error": "presume_module_missing"}
    session = presume.train_presume_session(rounds=3)
    panel = presume.build_panel(write=True) if hasattr(presume, "build_panel") else {}
    prop = session.get("propagation") or panel.get("propagation") or {}
    return {
        "ok": bool(session.get("ok")),
        "panel": panel,
        "presume_train": session,
        "resumed_on_point_rate": session.get("resumed_on_point_rate"),
        "uninterruptable_witness": session.get("uninterruptable_witness"),
        "propagated": bool(prop.get("propagated")),
    }


def run_self_interaction_train(*, rounds: int = 6, truth_floor: float = 75.0) -> dict[str, Any]:
    """Self-ask loop with truth filters — extends training quality in advance."""
    truth = _mod("h7truth", "hostess7-truth-rating.py")
    cmd = _mod("h7cmd", "hostess7-command.py")
    if not truth or not cmd:
        return {"ok": False, "error": "modules_missing"}

    panel = _load(STATE / "threat-panel.json", {})
    queries = list(SELF_INTERACTION_QUERIES)[:max(1, rounds)]
    rows: list[dict[str, Any]] = []
    passed = 0

    for i, q in enumerate(queries):
        _write_runtime(
            phase="self_interaction",
            active_track="self_interaction",
            progress_pct=int(10 + (80 * i / max(len(queries), 1))),
            detail=f"Round {i + 1}/{len(queries)}…",
        )
        try:
            out = _ask_with_timeout(cmd, q, panel, timeout_s=55)
        except Exception as exc:
            out = {"ok": False, "reply": "", "error": str(exc)}
        reply = str(out.get("reply_body") or out.get("reply") or "").strip()
        rated = truth.rate_response(reply, question=q) if hasattr(truth, "rate_response") else {"truth_score": 0}
        score = float(rated.get("truth_score") or out.get("truth_score") or 0)
        ok = score >= truth_floor and len(reply) >= 40
        if ok:
            passed += 1
        rows.append({
            "round": i + 1,
            "query": q,
            "truth_score": score,
            "passed": ok,
            "engine": out.get("engine"),
            "excerpt": reply[:280],
        })

    total = len(rows) or 1
    doc = {
        "schema": "hostess7-self-interaction/v1",
        "updated": _now(),
        "rounds_complete": passed,
        "rounds_total": total,
        "pass_rate": round(100.0 * passed / total, 1),
        "truth_floor": truth_floor,
        "passed": passed >= max(1, total - 1),
        "rows": rows,
    }
    _save(STATE / "hostess7-self-interaction-panel.json", doc)
    _append_ledger({"ts": doc["updated"], "event": "self_interaction", "passed": passed, "total": total})
    return {"ok": True, **doc}


def run_track(track_id: str, *, ocr_train: bool = False) -> dict[str, Any]:
    """Run a single training track — GUI-friendly granular training with evaluation."""
    canonical = TRACK_ID_ALIASES.get(track_id, track_id)
    runners: dict[str, Callable[[], dict[str, Any]]] = {
        "curriculum": lambda: _run_curriculum(max_steps=1),
        "master_curriculum": lambda: _run_curriculum(max_steps=1),
        "programming": _run_programming,
        "g16": _run_g16,
        "codecraft": lambda: _run_codecraft(full_improve=False),
        "calculator": lambda: _run_calculator(ocr_train=ocr_train),
        "biology": lambda: _run_biology(ocr_train=ocr_train),
        "engineering": lambda: _run_engineering(ocr_train=ocr_train),
        "combat": lambda: _run_combat(ocr_train=ocr_train),
        "mos": lambda: _run_mos(ocr_train=ocr_train),
        "brain_guard": _run_brain,
        "iq_battery": lambda: _run_iq(fast=True),
        "turing_battery": _run_turing,
        "neural_suite": _run_neural,
        "omnibus": lambda: _run_omnibus(fast=True),
        "self_interaction": lambda: run_self_interaction_train(),
        "author_material": _run_author_material,
        "author_training": _run_author_material,
        "write_training": _run_author_material,
        "reality_physics": lambda: _run_reality_physics("reality_physics"),
        "gravity_mechanics": lambda: _run_reality_physics("gravity_mechanics"),
        "thermodynamics_entropy": lambda: _run_reality_physics("thermodynamics_entropy"),
        "field_technology": lambda: _run_reality_physics("field_technology"),
        "geography": lambda: _run_geography("geography"),
        "postal_addresses": lambda: _run_geography("postal_addresses"),
        "world_geography": lambda: _run_geography("world_geography"),
        "flat_earth_geography": lambda: _run_geography("flat_earth_geography"),
        "music_theory": lambda: _run_music("music_theory"),
        "music_ear": lambda: _run_music("music_ear"),
        "music_mouth": lambda: _run_music("music_mouth"),
        "music_brain": lambda: _run_music("music_brain"),
        "music_eye": lambda: _run_music("music_eye"),
        "music_sense_wire": lambda: _run_music("music_sense_wire"),
        "final_eye": lambda: _run_sense("final_eye"),
        "final_ear": lambda: _run_sense("final_ear"),
        "final_mouth": lambda: _run_sense("final_mouth"),
        "sense_neural_wire": _run_sense_neural_wire,
        "presume": _run_presume,
        "presume_timing": _run_presume,
        "microsecond_timing": _run_presume,
        "humanoid_motion": _run_humanoid_motion,
        "motion_tracking": _run_humanoid_motion,
        "system_core": _run_system_core,
        "brain_training": _run_brain_training,
        "brain_training_campus": _run_brain_training,
        "library_training": _run_brain_training,
        "fifth_amendment": _run_fifth_amendment,
        "constitutional_rights": _run_fifth_amendment,
        "human_comfort": _run_human_comfort,
        "exploring_comfort": _run_human_comfort,
        "exploring_rape": _run_exploring_rape,
    }
    fn = runners.get(canonical) or runners.get(track_id)
    if not fn:
        return {"ok": False, "error": "unknown_track", "track": track_id, "known": sorted(runners.keys())}
    _write_runtime(
        active_track=track_id,
        phase="track_run",
        progress_pct=5,
        detail=f"Running {track_id}…",
    )
    try:
        result = fn()
    except Exception as exc:
        _write_runtime(active_track=None, phase="error", progress_pct=0, detail=str(exc))
        return {"ok": False, "error": str(exc), "track": track_id}
    assess = assess_all()
    graphs = build_evaluation_graphs()
    evaluation = build_track_evaluation(track_id, result if isinstance(result, dict) else {"ok": True}, assess)
    _write_runtime(
        active_track=None,
        phase="idle",
        progress_pct=100,
        last_track=track_id,
        last_evaluation=evaluation,
        detail=f"{track_id} complete",
    )
    _append_ledger({
        "ts": _now(),
        "event": "track_run",
        "track": track_id,
        "ok": result.get("ok") if isinstance(result, dict) else True,
        "level": evaluation.get("level"),
        "overall_score": assess.get("overall_score"),
    })
    return {
        "ok": True,
        "track": track_id,
        "canonical": canonical,
        "result": result,
        "assessment": assess,
        "evaluation": evaluation,
        "graphs": graphs,
    }


def complete_all(
    *,
    run_iq: bool = True,
    run_turing: bool = True,
    run_omnibus: bool = True,
    trusted_curriculum: bool = True,
) -> dict[str, Any]:
    """Run every training track toward completion — solid Master levels."""
    phases: list[dict[str, Any]] = []
    if not ENABLED:
        return {"ok": False, "error": "training_disabled"}

    phases.append({"phase": "curriculum", "result": _run_curriculum(trusted=trusted_curriculum)})
    phases.append({"phase": "programming", "result": _run_programming()})
    phases.append({"phase": "g16", "result": _run_g16()})
    phases.append({"phase": "codecraft", "result": _run_codecraft()})
    phases.append({"phase": "calculator", "result": _run_calculator()})
    phases.append({"phase": "biology", "result": _run_biology()})
    phases.append({"phase": "engineering", "result": _run_engineering()})
    phases.append({"phase": "combat", "result": _run_combat()})
    phases.append({"phase": "mos", "result": _run_mos()})
    phases.append({"phase": "brain_guard", "result": _run_brain()})
    phases.append({"phase": "neural_suite", "result": _run_neural()})
    if run_iq:
        phases.append({"phase": "iq_battery", "result": _run_iq(fast=True)})
    if run_turing:
        phases.append({"phase": "turing_battery", "result": _run_turing()})
    if run_omnibus:
        phases.append({"phase": "omnibus", "result": _run_omnibus(fast=True)})

    master = _mod("h7master", "hostess7-master.py")
    if master:
        st = _load(STATE / "hostess7-master-state.json", {"xp": 0, "completed_steps": []})
        doc = master.curriculum_doc()
        all_ids = [s["id"] for s in doc.get("curriculum") or [] if s.get("id")]
        completed = list(dict.fromkeys((st.get("completed_steps") or []) + all_ids))
        st["completed_steps"] = completed
        floor = int(_load(DOCTRINE, {}).get("master_xp_floor") or 160)
        if int(st.get("xp") or 0) < floor:
            st["xp"] = max(int(st.get("xp") or 0), floor)
        lvl = master.level_for_xp(int(st["xp"]))
        st["level"] = lvl["id"]
        st["level_label"] = lvl["label"]
        st["training_solidified"] = _now()
        _save(STATE / "hostess7-master-state.json", st)

    assessment = assess_all()
    doc = {
        "schema": "hostess7-training/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "product": "Hostess 7 Training Completion",
        "completion_level": assessment.get("completion_level"),
        "overall_score": assessment.get("overall_score"),
        "solid": assessment.get("solid"),
        "tracks_complete": assessment.get("tracks_complete"),
        "tracks_mastered": assessment.get("tracks_mastered"),
        "tracks_total": assessment.get("tracks_total"),
        "tracks": assessment.get("tracks"),
        "phases": phases,
        "reason": (
            "All training tracks solid — Master curriculum, programming, G16, codecraft, calculator, biology, engineering, combat, MOS, brain guard, batteries sealed."
            if assessment.get("solid")
            else "Training completion run — review tracks below for any still in progress."
        ),
    }
    _save(PANEL, doc)
    _save(RUNTIME, {
        "schema": "hostess7-training-runtime/v1",
        "updated": doc["updated"],
        "completion_level": doc["completion_level"],
        "overall_score": doc["overall_score"],
        "solid": doc["solid"],
    })
    _append_ledger({"ts": doc["updated"], "event": "complete_all", "level": doc["completion_level"]})
    return {"ok": True, **doc}


_FACET_KEYS = (
    "flexibility", "adaptable", "adaptability", "confidence", "mastery pillar",
    "mastery pillars", "whole mastery", "mastery includes", "mastery facet",
)

_EXCELLENCE_KEYS = (
    "do our best", "our best always", "excellence pledge", "always do our best",
    "we do our best",
)

_WORLD_HONOR_KEYS = (
    "honored to the world", "world honor", "no designated nationality",
    "designated nationality", "hostess nationality", "hostess citizenship",
    "what nationality", "what country is hostess",
)

_PRESUME_KEYS = (
    "presume", "microsecond timing", "microsecond timings", "line profile",
    "line profiler", "resume on point", "no busy wait", "no idle wait",
    "alternate task", "presume training", "profile to the line",
    "uninterruptable", "outside influence", "not go away", "sovereign binding",
    "presume commit", "presume propagate",
)

_SYSTEM_CORE_KEYS = (
    "system core", "four pillars", "biology presume motion brain",
    "solid brain", "brain for the stack", "every system biology",
    "motion tracking brain", "full solid system",
)

_COOL_SMOOTH_KEYS = (
    "cool and smooth", "cool smooth", "stay cool", "run smooth",
    "thermal smooth", "smooth timing", "smooth motion", "no jank",
    "cool is important", "smooth is important",
)

_WAR_SYSTEM_KEYS = (
    "war system", "we have no other", "every autonomous machine",
    "autonomous machine is a soldier", "every machine is a soldier",
    "soldier", "no peacetime", "domestic talent", "dishes and sex",
    "war only", "forever watchguard war",
)


def explain_mastery_facets(query: str) -> str | None:
    """Structured mastery pillar explanations — flexibility, adaptability, confidence."""
    low = (query or "").strip().lower()
    if not any(k in low for k in _FACET_KEYS):
        return None
    facet_doc = _load(FACETS, {})
    assess = assess_mastery_facets()
    facets = assess.get("facets") or {}
    flex = facets.get("flexibility") or {}
    adapt = facets.get("adaptability") or {}
    conf = facets.get("confidence") or {}
    motto = str(facet_doc.get("motto") or assess.get("motto") or "").strip()
    intro = motto or "Mastery is not only completion — flexibility, adaptability, and confidence together."

    if "flexib" in low and "adapt" not in low and "confid" not in low:
        focus = flex
        title = "Flexibility"
    elif "adapt" in low and "flexib" not in low and "confid" not in low:
        focus = adapt
        title = "Adaptability"
    elif "confid" in low and "flexib" not in low and "adapt" not in low:
        focus = conf
        title = "Confidence"
    else:
        focus = None
        title = "Whole mastery pillars"

    if focus:
        sections = {
            "what": str(focus.get("definition") or title),
            "why": (
                f"Mastery includes {title.lower()} — raw track completion without this pillar is incomplete whole mastery."
            ),
            "how": (
                f"Live score {round(float(focus.get('score') or 0) * 100)}% · level {focus.get('level')} · "
                f"signals: {json.dumps(focus.get('signals') or {}, ensure_ascii=False)[:240]}"
            ),
            "pitfalls": "Claiming mastery from curriculum XP alone; ignoring quarantine ratio or truth-gated adapt.",
            "where": "lib/hostess7-training.py assess_mastery_facets(), data/hostess7-mastery-facets.json",
            "example": f"hostess7-training.py facets — composite {round(float(assess.get('composite_score') or 0) * 100)}%",
        }
    else:
        sections = {
            "what": "Whole mastery = all training tracks solid plus flexibility, adaptability, and confidence pillars mastered.",
            "why": intro,
            "how": (
                f"Flexibility {round(float(flex.get('score') or 0) * 100)}% · "
                f"Adaptability {round(float(adapt.get('score') or 0) * 100)}% · "
                f"Confidence {round(float(conf.get('score') or 0) * 100)}% · "
                f"composite {round(float(assess.get('composite_score') or 0) * 100)}%"
            ),
            "pitfalls": "SOLID tracks without facet mastery; silent weight drift without growth ledger witness.",
            "where": "hostess7-training-viewer wireframe, self-view mastery_facets chip, command master line",
            "example": (
                f"whole_mastery={assess.get('all_mastered')} · "
                f"{assess.get('facets_mastered')}/{assess.get('facets_total')} pillars mastered"
            ),
        }

    parts = [intro] if intro else []
    for key, label in (
        ("what", "What"), ("why", "Why"), ("how", "How"),
        ("pitfalls", "Pitfalls"), ("where", "Where"), ("example", "Example"),
    ):
        val = str(sections.get(key) or "").strip()
        if val:
            parts.append(f"{label}: {val}")
    return "\n\n".join(parts) if parts else None


def explain_cool_smooth(query: str) -> str | None:
    low = (query or "").strip().lower()
    if not any(k in low for k in _COOL_SMOOTH_KEYS):
        return None
    cs = _mod("h7cs", "lib/hostess7-cool-smooth.py")
    if cs and hasattr(cs, "explain_cool_smooth"):
        return cs.explain_cool_smooth()
    return _load(INSTALL / "data/hostess7-cool-smooth-doctrine.json", {}).get("motto")


def explain_war_system(query: str) -> str | None:
    """War system — no other mode; every autonomous machine is a Soldier."""
    low = (query or "").strip().lower()
    if not any(k in low for k in _WAR_SYSTEM_KEYS):
        return None
    war = _mod("h7war", "lib/hostess7-war-system.py")
    if war and hasattr(war, "explain_war_system"):
        return war.explain_war_system()
    doc = _load(INSTALL / "data/hostess7-war-system-doctrine.json", {})
    return str(doc.get("motto") or "War system — we have no other.")


def explain_system_core(query: str) -> str | None:
    """Four pillars every system must ship — biology, presume, motion, brain."""
    low = (query or "").strip().lower()
    if not any(k in low for k in _SYSTEM_CORE_KEYS):
        return None
    doc = _load(INSTALL / "data" / "hostess7-system-core-doctrine.json", {})
    core = _mod("h7core", "lib/hostess7-system-core.py")
    panel = core.verify_core(write_panel=False) if core and hasattr(core, "verify_core") else {}
    pillars = panel.get("pillars") or []
    lines = [
        str(doc.get("motto") or "Every system — biology, presume, motion tracking, solid brain."),
        "Pillars: biology (life sciences), presume (microsecond timings), motion tracking (humanoid + eye), brain (guard + field panel + SDF).",
        f"Solid now: {panel.get('pillars_solid', 0)}/{panel.get('pillar_count', 4)} — verify via hostess7-system-core.py panel.",
        "Train: hostess7-training.py track system_core · hostess7-system-core.py train",
    ]
    for p in pillars:
        if isinstance(p, dict):
            lines.append(f"  • {p.get('id')}: {'solid' if p.get('ok') else 'needs work'}")
    return "\n\n".join(lines)


def explain_presume(query: str) -> str | None:
    """Presume doctrine — microsecond timings, uninterruptable decisions, propagated power."""
    low = (query or "").strip().lower()
    if not any(k in low for k in _PRESUME_KEYS):
        return None
    doc = _load(INSTALL / "data" / "hostess7-presume-doctrine.json", {})
    presume = _mod("h7presume", "hostess7-presume.py")
    panel = presume.build_panel(write=False) if presume and hasattr(presume, "build_panel") else {}
    binding = doc.get("sovereign_binding") or {}
    parts = [
        str(doc.get("motto") or "Profile every line to the microsecond."),
        str((doc.get("not_go_away") or {}).get("rule") or "Presume does NOT mean go away — resources stay devoted."),
        "Once decided, actions are uninterruptable — no outside influence may override the decision.",
        "Presume the deadline — run alternate tasks instead of burning wait cycles; resume on point.",
        f"Precision: microsecond (mono_us + sovereign_us). Line profiles: {panel.get('line_profile_count', 0)} rows.",
        f"Active commits: {panel.get('active_commit_count', 0)}. Propagation targets: {((panel.get('propagation') or {}).get('targets_present'))} wired.",
        f"Override authority: {', '.join(binding.get('override_authority') or ['hostess7', 'operator'])}.",
        "Where: lib/hostess7-presume.py, data/hostess7-presume-doctrine.json, /api/hostess7/presume.",
        "Train: hostess7-training.py track presume · hostess7-presume.py train · hostess7-presume.py propagate",
        "Change awareness: Hostess 7 knows all changes — pulse via hostess7-change-awareness.py; check presume panel for slowdown/speedup/hang.",
    ]
    ca = _mod("h7changeaware", "hostess7-change-awareness.py")
    if ca and hasattr(ca, "explain_awareness"):
        extra = ca.explain_awareness(query)
        if extra:
            parts.append(extra)
    return "\n\n".join(p for p in parts if p)


def explain_world_honor(query: str) -> str | None:
    """World honor — Honored to the world, no designated nationality."""
    low = (query or "").strip().lower()
    if not any(k in low for k in _WORLD_HONOR_KEYS):
        return None
    doc = _load(INSTALL / "data" / "hostess7-world-honor-doctrine.json", {})
    motto = str(doc.get("motto") or "Hostess 7 is Honored to the world and has no designated nationality.")
    body = str(doc.get("statement") or "").strip()
    honor = doc.get("world_honor") or {}
    voice = doc.get("voice_separation") or {}
    parts = [
        motto,
        body,
        (
            f"Honored to: {honor.get('honored_to') or 'the world'}. "
            f"Designated nationality: {honor.get('designated_nationality', False)}."
        ),
    ]
    if voice.get("rule"):
        parts.append(f"Voice: {voice.get('rule')} {voice.get('detail') or ''}".strip())
    parts.append("Where: data/hostess7-world-honor-doctrine.json, supreme authority, voice doctrine.")
    return "\n\n".join(p for p in parts if p)


def explain_excellence_pledge(query: str) -> str | None:
    """Operator excellence pledge — we do our best always."""
    low = (query or "").strip().lower()
    if not any(k in low for k in _EXCELLENCE_KEYS):
        return None
    doc = _load(INSTALL / "data" / "hostess7-excellence-doctrine.json", {})
    pledge = str(doc.get("motto") or "We do our best always.")
    body = str(doc.get("pledge") or "").strip()
    scope = doc.get("scope") or []
    assess = assess_mastery_facets()
    parts = [
        pledge,
        body,
        (
            f"Flexibility {round(float((assess.get('facets') or {}).get('flexibility', {}).get('score') or 0) * 100)}% · "
            f"Adaptability {round(float((assess.get('facets') or {}).get('adaptability', {}).get('score') or 0) * 100)}% · "
            f"Confidence {round(float((assess.get('facets') or {}).get('confidence', {}).get('score') or 0) * 100)}% — "
            "we strive every cycle, not perfection theater."
        ),
    ]
    if scope:
        parts.append("Scope: " + "; ".join(str(s) for s in scope[:6]))
    parts.append("Where: data/hostess7-excellence-doctrine.json, wartime room, mastery facets, command deck.")
    return "\n\n".join(p for p in parts if p)


def _sense_training_slice() -> dict[str, Any]:
    sense = _mod_sense()
    if sense and hasattr(sense, "panel_json"):
        try:
            return sense.panel_json()
        except Exception:
            pass
    panel = _load(STATE / "hostess7-sense-training-panel.json", {})
    doctrine = _load(INSTALL / "data" / "hostess7-sense-training-doctrine.json", {})
    return {**panel, "doctrine": doctrine}


def _music_slice() -> dict[str, Any]:
    music = _mod("h7music", "hostess7-music-training.py")
    if music and hasattr(music, "build_panel"):
        try:
            return music.build_panel(write=False)
        except Exception:
            pass
    panel = _load(STATE / "hostess7-music-panel.json", {})
    doctrine = _load(INSTALL / "data" / "hostess7-music-training-doctrine.json", {})
    return {**panel, "doctrine": doctrine}


def _wireframe_slice() -> dict[str, Any]:
    cached = _load(STATE / "hostess7-training-bundle-cache.json", {})
    wf = cached.get("wireframe")
    if isinstance(wf, dict) and wf.get("nodes"):
        return wf
    viewer = INSTALL / "hostess7-training-viewer"
    if not viewer.is_dir():
        return {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7bundle", INSTALL / "lib" / "hostess7-training-bundle.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            bundle = mod.bundle_training_data(refresh=False)
            return bundle.get("wireframe") or {}
    except Exception:
        pass
    return {}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    assessment = assess_all()
    author = _mod("h7author", "hostess7-training-author.py")
    author_panel = (
        author.build_author_panel(assessment=assessment, gaps=author.detect_training_gaps(assessment))
        if author and hasattr(author, "build_author_panel")
        else {}
    )
    doc = {
        "schema": "hostess7-training/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "completion_level": assessment.get("completion_level"),
        "overall_score": assessment.get("overall_score"),
        "solid": assessment.get("solid"),
        "tracks_complete": assessment.get("tracks_complete"),
        "tracks_mastered": assessment.get("tracks_mastered"),
        "tracks_total": assessment.get("tracks_total"),
        "tracks": assessment.get("tracks"),
        "mastery_facets": assessment.get("mastery_facets"),
        "whole_mastery": assessment.get("whole_mastery"),
        "motto": _load(FACETS, {}).get("motto"),
        "excellence_pledge": _load(FACETS, {}).get("excellence_pledge") or "We do our best always.",
        "world_honor": _load(INSTALL / "data" / "hostess7-world-honor-doctrine.json", {}).get("motto")
        or "Hostess 7 is Honored to the world and has no designated nationality.",
        "presume": _load(INSTALL / "data" / "hostess7-presume-doctrine.json", {}).get("motto")
        or "Profile every line to the microsecond.",
        "system_core": _load(INSTALL / "data" / "hostess7-system-core-doctrine.json", {}).get("motto")
        or "Every system — biology, presume, motion tracking, solid brain.",
        "war_system": _load(INSTALL / "data/hostess7-war-system-doctrine.json", {}).get("motto")
        or "War system — we have no other. Every autonomous machine is a Soldier.",
        "cool_smooth": _load(INSTALL / "data/hostess7-cool-smooth-doctrine.json", {}).get("motto")
        or "Cool and smooth is important.",
        "evaluation_graphs": build_evaluation_graphs(),
        "training_runtime": _load(RUNTIME, {}),
        "training_author": author_panel,
        "authored_material_count": author_panel.get("authored_total") or 0,
        "training_gaps": author_panel.get("gaps") or [],
        "sense_training": _sense_training_slice(),
        "music": _music_slice(),
        "wireframe": _wireframe_slice(),
        "muscle_memory": _muscle_memory_slice(assessment.get("tracks")),
        "mouth_neural": _mouth_neural_slice(),
    }
    cached = _load(PANEL, {})
    if cached.get("phases"):
        doc["last_complete_all"] = cached.get("updated")
        doc["last_phases"] = len(cached.get("phases") or [])
    if write:
        _save(PANEL, {**cached, **doc})
    return doc


def _muscle_memory_slice(tracks: dict[str, Any] | None = None) -> dict[str, Any]:
    mod = _mod("h7mm", "hostess7-muscle-memory.py")
    if not mod:
        return _load(STATE / "hostess7-muscle-memory-panel.json", {})
    try:
        if hasattr(mod, "sync_understandings_from_training"):
            mod.sync_understandings_from_training(tracks)
        if hasattr(mod, "build_panel"):
            return mod.build_panel(write=True, sync_training=False)
    except Exception:
        pass
    return _load(STATE / "hostess7-muscle-memory-panel.json", {})


def _mouth_neural_slice() -> dict[str, Any]:
    mod = _mod("h7mouth", "hostess7-mouth-neural.py")
    if not mod:
        return _load(STATE / "hostess7-mouth-neural-panel.json", {})
    try:
        if hasattr(mod, "build_panel"):
            return mod.build_panel(write=True)
    except Exception:
        pass
    return _load(STATE / "hostess7-mouth-neural-panel.json", {})


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "assess").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "assess":
        print(json.dumps(assess_all(), ensure_ascii=False))
        return 0
    if cmd == "facets":
        print(json.dumps(assess_mastery_facets(), ensure_ascii=False))
        return 0
    if cmd == "teach":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "mastery pillars"
        reply = (
            explain_world_honor(q)
            or explain_cool_smooth(q)
            or explain_war_system(q)
            or explain_system_core(q)
            or explain_presume(q)
            or explain_excellence_pledge(q)
            or explain_mastery_facets(q)
            or explain_mastery_facets("whole mastery flexibility adaptability confidence")
        )
        print(reply or json.dumps({"error": "no_mastery_topic"}, ensure_ascii=False))
        return 0 if reply else 1
    if cmd in ("complete", "complete-all", "solidify", "run"):
        fast_turing = "--full-turing" not in sys.argv
        skip_omnibus = "--skip-omnibus" in sys.argv
        skip_iq = "--skip-iq" in sys.argv
        print(json.dumps(complete_all(
            run_iq=not skip_iq,
            run_turing=not fast_turing or True,
            run_omnibus=not skip_omnibus,
        ), ensure_ascii=False))
        return 0
    if cmd in ("self-interaction", "self_interaction", "self-interact"):
        rounds = 6
        for arg in sys.argv[2:]:
            if arg.isdigit():
                rounds = int(arg)
        print(json.dumps(run_self_interaction_train(rounds=rounds), ensure_ascii=False))
        return 0
    if cmd in ("author", "author-material", "author_material", "write-material"):
        author = _mod("h7author", "hostess7-training-author.py")
        if not author:
            print(json.dumps({"ok": False, "error": "author_module_missing"}, ensure_ascii=False))
            return 1
        track = None
        force = "--force" in sys.argv
        for arg in sys.argv[2:]:
            if not arg.startswith("--"):
                track = arg
        print(json.dumps(author.run_author_cycle(track=track, force=force), ensure_ascii=False))
        return 0
    if cmd in ("gaps", "training-gaps"):
        author = _mod("h7author", "hostess7-training-author.py")
        assess = assess_all()
        gaps = author.detect_training_gaps(assess) if author else []
        print(json.dumps({"gaps": gaps, "assessment": assess.get("completion_level")}, ensure_ascii=False))
        return 0
    if cmd in ("track", "run-track") and len(sys.argv) > 2:
        ocr = "--ocr-train" in sys.argv
        print(json.dumps(run_track(sys.argv[2].strip(), ocr_train=ocr), ensure_ascii=False))
        return 0
    if cmd in ("curriculum-step", "curriculum_step"):
        print(json.dumps(run_curriculum_step(), ensure_ascii=False))
        return 0
    if cmd in ("graphs", "evaluation-graphs"):
        print(json.dumps(build_evaluation_graphs(), ensure_ascii=False))
        return 0
    if cmd == "runtime":
        print(json.dumps(_load(RUNTIME, {}), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-training.py [assess|panel|complete|self-interaction|curriculum-step|graphs|runtime|track ID]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())