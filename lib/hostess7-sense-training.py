#!/usr/bin/env pythong
"""Hostess 7 sense training — Final Eye, Ear, Mouth sessions wired to matrix + panel tabs."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(INSTALL.parent / "Queen")))
DOCTRINE = INSTALL / "data" / "hostess7-sense-training-doctrine.json"
PANEL = STATE / "hostess7-sense-training-panel.json"
LEDGER = STATE / "hostess7-sense-training-ledger.jsonl"

TRACKS = ("final_eye", "final_ear", "final_mouth")
MUSIC_ACTIONS = frozenset({
    "music_drill", "music_interval", "music_pitch", "music_rhythm",
    "music_notation", "music_brain_pattern", "music_crosswire",
})
BRIDGE = {
    "final_eye": QUEEN / "lib" / "queen-eyeball.py",
    "final_ear": QUEEN / "lib" / "queen-earball.py",
    "final_mouth": QUEEN / "lib" / "queen-mouthball.py",
}


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


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    env.setdefault("SG_ROOT", str(SG))
    env.setdefault("QUEEN_ROOT", str(QUEEN))
    env.setdefault("HOSTESS7_ROOT", str(INSTALL / "Hostess7"))
    env.setdefault("FINAL_EYE_ROOT", str(SG / "Final_Eye"))
    env.setdefault("FINAL_EAR_ROOT", str(SG / "Final_Ear"))
    env.setdefault("FINAL_MOUTH_ROOT", str(SG / "Final_Mouth"))
    py_parts = [
        str(QUEEN / "lib"),
        str(SG / "Final_Eye"),
        str(SG / "Final_Ear"),
        str(SG / "Final_Mouth"),
    ]
    if env.get("PYTHONPATH"):
        py_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(py_parts)
    return env


def _sense_core() -> Any | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-sense-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("hostess7_sense_core_train", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _track_channel(track_id: str) -> str:
    return {
        "final_eye": "eye",
        "final_ear": "ear",
        "final_mouth": "mouth",
    }.get(track_id, track_id)


def _dispatch(bridge: Path, body: dict[str, Any], *, timeout: int = 120) -> dict[str, Any]:
    core = _sense_core()
    if core and hasattr(core, "sense_ball_dispatch"):
        for track_id, path in BRIDGE.items():
            if path == bridge:
                return core.sense_ball_dispatch(_track_channel(track_id), body)
    if not bridge.is_file():
        return {"ok": False, "error": "bridge_missing", "path": str(bridge)}
    try:
        proc = subprocess.run(
            [sys.executable, str(bridge), "dispatch"],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            cwd=str(QUEEN),
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "dispatch_failed", "stderr": (proc.stderr or "")[:200]}


def _music_mod() -> Any | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-music-training.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("h7music", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _run_music_step(step: dict[str, Any]) -> dict[str, Any]:
    music = _music_mod()
    if not music or not hasattr(music, "run_sense_step"):
        return {"ok": False, "error": "music_training_missing"}
    return music.run_sense_step(step)


def _step_ok(result: dict[str, Any], *, action: str = "") -> bool:
    """Training pass — verify steps accept sealed ZOCR code when mesh/bench is advisory."""
    if str(action).startswith("music_"):
        if result.get("ok") is False:
            return False
        if result.get("pass_rate") is not None:
            return float(result["pass_rate"]) >= 75.0
        return True
    if str(action) in ("verify", "verify_earball", "verify-eyeball"):
        seal = result.get("verify") or result.get("code_seal") or {}
        if seal.get("ok") and not seal.get("tampered") and not seal.get("missing"):
            return True
    if result.get("ok") is False:
        return False
    if result.get("verdict") == "hold":
        return False
    if result.get("fusion_score") is not None:
        return float(result["fusion_score"]) >= 0.72
    return True


def run_sense_track(track_id: str) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    session = (doc.get("sessions") or {}).get(track_id)
    if not session:
        return {"ok": False, "error": "unknown_sense_track", "track": track_id}
    bridge = BRIDGE.get(track_id)
    if not bridge:
        return {"ok": False, "error": "bridge_missing", "track": track_id}

    steps_out: list[dict[str, Any]] = []
    passed = 0
    for step in session.get("steps") or []:
        body = {k: v for k, v in step.items() if k not in ("id", "label")}
        if "action" not in body:
            continue
        action = str(body.get("action") or "")
        if action in MUSIC_ACTIONS:
            result = _run_music_step(step)
        else:
            result = _dispatch(bridge, body, timeout=180 if action in ("eye_ear_fusion", "fused_analyze") else 90)
        ok = _step_ok(result, action=action)
        if ok:
            passed += 1
        steps_out.append({
            "id": step.get("id"),
            "label": step.get("label"),
            "ok": ok,
            "action": body.get("action"),
            "detail": (result.get("error") or result.get("verdict") or result.get("schema") or "")[:120],
        })

    total = len(steps_out) or 1
    rate = passed / total
    threshold = float(doc.get("pass_threshold") or 0.75)
    master_threshold = float(doc.get("master_threshold") or 0.95)
    complete = rate >= threshold
    mastered = rate >= master_threshold and passed == total

    panel = _load(PANEL, {"schema": "hostess7-sense-training-panel/v1", "tracks": {}})
    tracks = panel.setdefault("tracks", {})
    tracks[track_id] = {
        "label": session.get("label"),
        "tab": session.get("tab"),
        "api": session.get("api"),
        "passed": passed,
        "total": total,
        "pass_rate": round(rate * 100, 1),
        "complete": complete,
        "mastered": mastered,
        "level": "mastered" if mastered else "complete" if complete else "training" if passed else "pending",
        "score": round(rate, 4),
        "steps": steps_out,
        "updated": _now(),
    }
    panel["updated"] = _now()
    _save(PANEL, panel)
    _append_ledger({"ts": _now(), "event": "sense_track", "track": track_id, "passed": passed, "total": total})
    return {
        "ok": complete,
        "track": track_id,
        "passed": passed,
        "total": total,
        "pass_rate": round(rate * 100, 1),
        "complete": complete,
        "mastered": mastered,
        "steps": steps_out,
        "panel": tracks[track_id],
    }


def assess_track(track_id: str) -> dict[str, Any]:
    panel = _load(PANEL, {})
    row = (panel.get("tracks") or {}).get(track_id) or {}
    doc = _load(DOCTRINE, {})
    session = (doc.get("sessions") or {}).get(track_id) or {}
    score = float(row.get("score") or 0)
    complete = bool(row.get("complete"))
    mastered = bool(row.get("mastered"))
    if not row:
        bridge = BRIDGE.get(track_id)
        if bridge and bridge.is_file():
            try:
                proc = subprocess.run(
                    [sys.executable, str(bridge), "json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=_env(),
                    cwd=str(QUEEN),
                )
                live = json.loads(proc.stdout or "{}")
                if live.get("ok") is not False:
                    score = 0.35
                    complete = False
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
                pass
    return {
        "ok": bool(row) or score > 0,
        "level": row.get("level") or ("training" if score > 0.2 else "pending"),
        "complete": complete,
        "mastered": mastered,
        "score": score,
        "pass_rate": row.get("pass_rate"),
        "passed": row.get("passed"),
        "total": row.get("total"),
        "label": session.get("label") or track_id,
        "tab": session.get("tab"),
        "api": session.get("api"),
        "steps": row.get("steps") or [],
    }


def run_sense_neural_wire() -> dict[str, Any]:
    """Wire all three sense tracks — matrix quorum session."""
    results = [run_sense_track(tid) for tid in TRACKS]
    passed = sum(1 for r in results if r.get("ok"))
    rate = passed / max(len(results), 1)
    doc = _load(DOCTRINE, {})
    threshold = float(doc.get("pass_threshold") or 0.75)
    complete = passed >= 2
    mastered = passed == len(TRACKS) and all(r.get("mastered") for r in results)
    panel = _load(PANEL, {"schema": "hostess7-sense-training-panel/v1", "tracks": {}})
    tracks = panel.setdefault("tracks", {})
    tracks["sense_neural_wire"] = {
        "label": "Sense neural wire",
        "tab": "training",
        "api": "/api/hostess7/training/track/sense_neural_wire",
        "passed": passed,
        "total": len(results),
        "pass_rate": round(rate * 100, 1),
        "complete": complete,
        "mastered": mastered,
        "level": "mastered" if mastered else "complete" if complete else "training",
        "score": round(rate, 4),
        "steps": [
            {"id": r.get("track"), "label": r.get("track"), "ok": r.get("ok"), "detail": f"{r.get('passed')}/{r.get('total')}"}
            for r in results
        ],
        "updated": _now(),
    }
    panel["tracks_complete"] = sum(1 for t in tracks.values() if t.get("complete"))
    panel["tracks_mastered"] = sum(1 for t in tracks.values() if t.get("mastered"))
    panel["overall_score"] = round(
        sum(float(t.get("score") or 0) for t in tracks.values() if t.get("score") is not None)
        / max(len(tracks), 1),
        4,
    )
    panel["updated"] = _now()
    _save(PANEL, panel)
    _append_ledger({"ts": _now(), "event": "sense_neural_wire", "passed": passed, "total": len(results)})
    return {
        "ok": complete,
        "schema": "hostess7-sense-neural-wire/v1",
        "tracks": results,
        "passed": passed,
        "total": len(results),
        "pass_rate": round(rate * 100, 1),
        "complete": complete,
        "mastered": mastered,
        "panel": tracks["sense_neural_wire"],
    }


def assess_all() -> dict[str, Any]:
    tracks = {tid: assess_track(tid) for tid in TRACKS}
    scores = [float(t.get("score") or 0) for t in tracks.values()]
    overall = sum(scores) / max(len(scores), 1)
    wire_eye = tracks.get("final_eye") or {}
    wire_ear = tracks.get("final_ear") or {}
    wire_mouth = tracks.get("final_mouth") or {}
    wire_scores = [
        float(wire_eye.get("score") or 0),
        float(wire_ear.get("score") or 0),
        float(wire_mouth.get("score") or 0),
    ]
    wire_rate = sum(wire_scores) / 3.0
    wire_complete = sum(1 for x in (wire_eye, wire_ear, wire_mouth) if x.get("complete")) >= 2
    wire_mastered = all(x.get("mastered") for x in (wire_eye, wire_ear, wire_mouth))
    panel = _load(PANEL, {})
    wire_row = (panel.get("tracks") or {}).get("sense_neural_wire") or {}
    tracks["sense_neural_wire"] = {
        "ok": wire_complete,
        "level": wire_row.get("level") or ("mastered" if wire_mastered else "complete" if wire_complete else "training"),
        "complete": wire_complete,
        "mastered": wire_mastered,
        "score": round(wire_rate, 4),
        "pass_rate": round(wire_rate * 100, 1),
        "passed": wire_row.get("passed") or sum(1 for x in (wire_eye, wire_ear, wire_mouth) if x.get("complete")),
        "total": 3,
        "label": "Sense neural wire",
        "tab": "training",
        "api": "/api/hostess7/training/track/sense_neural_wire",
        "steps": wire_row.get("steps") or [],
    }
    return {
        "schema": "hostess7-sense-training-assess/v1",
        "updated": _now(),
        "tracks": tracks,
        "overall_score": round(overall, 4),
        "tracks_complete": sum(1 for t in tracks.values() if t.get("complete")),
        "tracks_mastered": sum(1 for t in tracks.values() if t.get("mastered")),
    }


def wireframe_nodes() -> list[dict[str, Any]]:
    assess = assess_all()
    doc = _load(DOCTRINE, {})
    nodes: list[dict[str, Any]] = []
    for tid in TRACKS:
        t = assess["tracks"][tid]
        sess = (doc.get("sessions") or {}).get(tid) or {}
        nodes.append({
            "id": f"sense_train_{tid}",
            "label": str(sess.get("label") or tid)[:24],
            "track_id": tid,
            "tab": sess.get("tab"),
            "api": sess.get("api"),
            "level": t.get("level"),
            "score": t.get("score"),
            "passed": t.get("passed"),
            "total": t.get("total"),
            "steps": t.get("steps") or [],
        })
    return nodes


def panel_json() -> dict[str, Any]:
    return {
        "schema": "hostess7-sense-training-panel/v1",
        "updated": _now(),
        "doctrine": _load(DOCTRINE, {}),
        **assess_all(),
        "wire_nodes": wireframe_nodes(),
    }


_OCR_API: dict | None = None


def _ocr_api() -> dict:
    global _OCR_API
    if _OCR_API is None:
        import importlib.util
        py = INSTALL / "lib" / "hostess7-ocr-bind.py"
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_sense", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("sense", install=INSTALL, state=STATE, ledger=LEDGER)
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
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_sense", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd.lower(),
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-sense-training.py [json|assess|run TRACK|final_eye|final_ear|final_mouth|sense_neural_wire|ocr-ingest|ocr-train|ocr-status]",
    )


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "assess":
        print(json.dumps(assess_all(), ensure_ascii=False))
        return 0
    if cmd == "run" and len(sys.argv) > 2:
        print(json.dumps(run_sense_track(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd in TRACKS:
        print(json.dumps(run_sense_track(cmd), ensure_ascii=False))
        return 0
    if cmd in ("sense_neural_wire", "wire", "wire-all"):
        print(json.dumps(run_sense_neural_wire(), ensure_ascii=False))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({"error": "usage: hostess7-sense-training.py [json|assess|run TRACK|final_eye|final_ear|final_mouth|sense_neural_wire|ocr-ingest|ocr-train|ocr-status]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())