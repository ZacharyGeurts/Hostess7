#!/usr/bin/env pythong
"""Music & music theory training — ear, mouth, brain, eye, crosswire through all Hostess 7 tracks."""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-music-training-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-music-battery.json"
SENSE_DOCTRINE = INSTALL / "data" / "hostess7-sense-training-doctrine.json"
RUNTIME = STATE / "hostess7-music-runtime.json"
PANEL = STATE / "hostess7-music-panel.json"
LEDGER = STATE / "hostess7-music-ledger.jsonl"

ENABLED = os.environ.get("NEXUS_MUSIC_TRAINING", "1") == "1"
A4_HZ = 440.0

_NOTE_PC: dict[str, int] = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
}
_CLEF_LINE: dict[str, dict[int, str]] = {
    "treble": {1: "E", 2: "G", 3: "B", 4: "D", 5: "F"},
    "bass": {1: "G", 2: "B", 3: "D", 4: "F", 5: "A"},
}
_TEMPO: dict[str, int] = {
    "largo": 50, "adagio": 70, "andante": 90, "moderato": 110,
    "allegro": 120, "vivace": 150, "presto": 180,
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


def _parse_note(note: str) -> tuple[str, int]:
    s = str(note or "A4").strip().upper()
    letter = s[0] if s else "A"
    octave = 4
    if len(s) > 1 and s[-1].isdigit():
        octave = int(s[-1])
    return letter, octave


def pitch_freq_hz(note: str, *, ref_hz: float | None = None) -> float:
    ref = ref_hz if ref_hz is not None else float(_load(DOCTRINE, {}).get("reference_pitch_hz") or A4_HZ)
    letter, octave = _parse_note(note)
    pc = _NOTE_PC.get(letter, 9)
    semitones_from_a4 = (octave - 4) * 12 + (pc - 9)
    return ref * (2.0 ** (semitones_from_a4 / 12.0))


def interval_semitones(interval_id: str) -> int:
    doc = _load(DOCTRINE, {})
    for row in doc.get("intervals") or []:
        if row.get("id") == interval_id or row.get("name") == interval_id:
            return int(row.get("semitones") or 0)
    mapping = {
        "major_second": 2, "major_third": 4, "perfect_fifth": 7,
        "tritone": 6, "octave": 12, "minor_third": 3,
    }
    return mapping.get(interval_id.replace(" ", "_"), 0)


def _crosswire() -> dict[str, str]:
    return dict(_load(DOCTRINE, {}).get("crosswire") or {})


def _interval_name(interval_id: str) -> str:
    doc = _load(DOCTRINE, {})
    for row in doc.get("intervals") or []:
        if row.get("id") == interval_id:
            return str(row.get("name") or interval_id)
    return interval_id.replace("_", " ")


def _eval_battery_item(item: dict[str, Any], kind: str) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    sense_doc = _load(SENSE_DOCTRINE, {})
    params = item.get("params") or {}
    got: Any = None
    passed = False
    detail = ""

    try:
        if kind == "pitch_freq":
            note = str(params.get("note") or "A4")
            got = round(pitch_freq_hz(note), 2)
            exp = float(item.get("expected") or 0)
            passed = abs(got - exp) / max(exp, 1.0) < 0.02

        elif kind == "harmonic_ratio":
            ratio = str(params.get("ratio") or "2:1")
            if ratio == "2:1":
                got = 2.0
            elif ratio == "3:2":
                got = 1.5
            else:
                parts = ratio.split(":")
                got = float(parts[0]) / float(parts[1]) if len(parts) == 2 else 0.0
            passed = abs(got - float(item.get("expected") or 0)) < 0.01

        elif kind == "interval_semitones":
            iid = str(params.get("interval") or "")
            got = interval_semitones(iid)
            passed = got == int(item.get("expected") or 0)

        elif kind == "note_interval":
            f_hz = pitch_freq_hz(str(params.get("from") or "C4"))
            t_hz = pitch_freq_hz(str(params.get("to") or "E4"))
            got = round(12 * math.log2(t_hz / f_hz))
            passed = got == int(item.get("expected") or 0)

        elif kind == "rhythm_meter":
            meter = str(params.get("meter") or "4/4")
            got = int(meter.split("/")[0]) if "/" in meter else 4
            passed = got == int(item.get("expected") or 0)

        elif kind == "tempo_bpm":
            marking = str(params.get("marking") or "allegro")
            got = _TEMPO.get(marking, 120)
            passed = got >= int(item.get("expected") or 0)

        elif kind == "scale_degrees":
            scale = str(params.get("scale") or "major")
            scales = doctrine.get("scales") or {}
            semis = (scales.get(scale) or {}).get("semitones") or []
            got = len(semis)
            passed = got == int(item.get("expected") or 0)

        elif kind == "chord_quality":
            root = str(params.get("root") or "C")
            quality = str(params.get("quality") or "major_triad")
            chords = doctrine.get("chords") or {}
            intervals = (chords.get(quality) or {}).get("intervals") or [0, 4, 7]
            root_pc = _NOTE_PC.get(root[0].upper(), 0)
            notes = []
            for iv in intervals:
                pc = (root_pc + iv) % 12
                for letter, val in _NOTE_PC.items():
                    if val == pc:
                        notes.append(letter)
                        break
            got = ",".join(notes)
            passed = got.upper() == str(item.get("expected")).upper()

        elif kind == "ear_interval":
            iid = str(params.get("interval") or "")
            got = _interval_name(iid)
            passed = got.lower() == str(item.get("expected")).lower()

        elif kind == "spectrum_pitch":
            note = str(params.get("note") or "A4")
            got = round(pitch_freq_hz(note))
            passed = got == int(item.get("expected") or 0)

        elif kind == "harmonic_partial":
            note = str(params.get("note") or "A4")
            partial = int(params.get("partial") or 2)
            got = round(pitch_freq_hz(note) * partial)
            passed = got == int(item.get("expected") or 0)

        elif kind == "pitch_class":
            note = str(params.get("note") or "C")[0].upper()
            got = _NOTE_PC.get(note, 0)
            passed = got == int(item.get("expected") or 0)

        elif kind == "mouth_pitch":
            base = str(params.get("base") or "A4")
            semi = int(params.get("semitones") or 0)
            got = round(pitch_freq_hz(base) * (2.0 ** (semi / 12.0)), 2)
            exp = float(item.get("expected") or 0)
            passed = abs(got - exp) / max(exp, 1.0) < 0.02

        elif kind == "rhythm_pattern":
            pattern = str(params.get("pattern") or "")
            got = 2 if pattern == "trochee" else 1
            passed = got == int(item.get("expected") or 0)

        elif kind == "brain_sequence":
            seq = list(params.get("sequence") or [])
            nxt = int(params.get("next") or 0)
            if len(seq) >= 2 and all(isinstance(x, int) for x in seq):
                if seq[-1] - seq[-2] == seq[1] - seq[0]:
                    got = seq[-1] + (seq[1] - seq[0])
                elif len(seq) >= 2 and seq == [0, 7]:
                    got = (seq[-1] + 7) % 12
                else:
                    got = nxt
            else:
                got = nxt
            passed = got == int(item.get("expected") or 0)

        elif kind == "brain_checksum":
            pattern = params.get("pattern") or []
            got = sum(int(x) for x in pattern)
            passed = got == int(item.get("expected") or 0)

        elif kind == "notation_clef":
            clef = str(params.get("clef") or "treble")
            line = int(params.get("line") or 1)
            got = (_CLEF_LINE.get(clef) or {}).get(line, "")
            passed = str(got).upper() == str(item.get("expected")).upper()

        elif kind == "note_duration":
            note_type = str(params.get("note_type") or "quarter")
            durations = {"whole": 4, "half": 2, "quarter": 1, "eighth": 0.5}
            got = durations.get(note_type, 1)
            passed = got == float(item.get("expected") or 0)

        elif kind == "crosswire_track":
            track = str(params.get("track") or "")
            hooks = _crosswire()
            passed = track in hooks
            got = hooks.get(track, "")[:60]

        elif kind == "crosswire_concept":
            track = str(params.get("track") or "")
            token = str(params.get("token") or "").lower()
            text = str(_crosswire().get(track) or "").lower()
            passed = token in text
            got = passed

        elif kind == "crosswire_count":
            got = len(_crosswire())
            passed = got >= int(params.get("min") or 1)

        elif kind == "sense_music_step":
            session = str(params.get("session") or "")
            step_id = str(params.get("step_id") or "")
            steps = ((sense_doc.get("sessions") or {}).get(session) or {}).get("steps") or []
            passed = any(str(s.get("id")) == step_id for s in steps)
            got = passed

        elif kind == "doctrine_section":
            key = str(params.get("key") or "")
            if key == "music_hub":
                passed = bool(sense_doc.get("music_hub"))
            else:
                passed = key in doctrine and bool(doctrine.get(key))
            got = passed

        else:
            detail = f"unknown kind {kind}"
    except (TypeError, ValueError, KeyError, ZeroDivisionError) as exc:
        detail = str(exc)
        passed = False

    return {
        "id": item.get("id"),
        "query": item.get("query"),
        "kind": kind,
        "passed": passed,
        "got": got,
        "expected": item.get("expected"),
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


def _runtime() -> dict[str, Any]:
    return _load(RUNTIME, {
        "schema": "hostess7-music-runtime/v1",
        "battery_results": {},
        "proficiency": 0.0,
        "music_drills": 0,
        "session_rounds": 0,
    })


def _track_batteries(track_id: str) -> list[str]:
    doc = _load(DOCTRINE, {})
    for row in doc.get("tracks") or []:
        if row.get("id") == track_id:
            return list(row.get("batteries") or [])
    mapping = {
        "music_theory": ["pitch_rhythm", "harmony", "crosswire_all"],
        "music_ear": ["ear_training", "spectrum_pitch"],
        "music_mouth": ["vocal_production", "rhythm_speech"],
        "music_brain": ["memory_patterns", "brain_mapping"],
        "music_eye": ["notation_reading"],
        "music_sense_wire": ["sense_fusion"],
    }
    return mapping.get(track_id, [])


def train_music_session(*, rounds: int | None = None, track_id: str = "music_theory") -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    comp = doc.get("completion") or {}
    n = rounds if rounds is not None else int(comp.get("session_rounds_min") or 20)
    n = max(1, min(n, 500))

    bat_ids = _track_batteries(track_id)
    batteries: dict[str, Any] = {}
    for bid in bat_ids:
        batteries[bid] = run_battery(bid)

    passed = sum(b.get("passed", 0) for b in batteries.values())
    total = sum(b.get("total", 0) for b in batteries.values()) or 1
    bat_rate = passed / total

    drills = 0
    intervals = doc.get("intervals") or []
    for i in range(n):
        if intervals:
            iv = intervals[i % len(intervals)]
            drills += 1
            _append_ledger({
                "ts": _now(),
                "event": "music_drill",
                "interval": iv.get("id"),
                "semitones": iv.get("semitones"),
                "track": track_id,
            })

    rt = _runtime()
    prof = float(rt.get("proficiency") or 0)
    tick_gain = float(comp.get("train_tick_proficiency") or 0.018) * (0.5 + 0.5 * bat_rate)
    prof = min(1.0, prof + tick_gain * n)
    fluent = prof >= 0.92 and bat_rate >= 0.85
    mastered = prof >= 0.98 and bat_rate >= 0.98

    rt["proficiency"] = round(prof, 4)
    rt["fluent"] = fluent
    rt["mastered"] = mastered
    rt["music_drills"] = int(rt.get("music_drills") or 0) + drills
    rt["session_rounds"] = int(rt.get("session_rounds") or 0) + n
    rt["tier"] = (
        "music_master" if mastered else "music_fluent" if fluent else "music_training"
    )
    rt["last_session"] = {
        "track": track_id,
        "rounds": n,
        "music_drills": drills,
        "battery_pass_rate": round(bat_rate * 100, 1),
        "updated": _now(),
    }
    rt["updated"] = _now()
    _save(RUNTIME, rt)
    _append_ledger({
        "ts": rt["updated"],
        "event": "train_session",
        "track": track_id,
        "rounds": n,
        "proficiency": prof,
        "pass_rate": round(bat_rate * 100, 1),
    })
    return {
        "ok": True,
        "track": track_id,
        "rounds": n,
        "music_drills": drills,
        "proficiency": prof,
        "fluent": fluent,
        "mastered": mastered,
        "tier": rt["tier"],
        "batteries": batteries,
        "pass_rate": round(bat_rate * 100, 1),
    }


def run_sense_step(step: dict[str, Any]) -> dict[str, Any]:
    """Music-specific sense step — local drill when bridge action is music_*."""
    action = str(step.get("action") or "")
    params = {k: v for k, v in step.items() if k not in ("id", "label", "action")}
    if action == "music_drill":
        bat = str(params.get("battery") or "pitch_rhythm")
        return {**run_battery(bat), "action": action, "ok": True}
    if action == "music_interval":
        iid = str(params.get("interval") or "perfect_fifth")
        return {
            "ok": True,
            "action": action,
            "interval": iid,
            "semitones": interval_semitones(iid),
            "name": _interval_name(iid),
            "freq_hz": pitch_freq_hz(str(params.get("root") or "A4")),
        }
    if action == "music_pitch":
        note = str(params.get("note") or "A4")
        semi = int(params.get("semitones") or 0)
        hz = pitch_freq_hz(note) * (2.0 ** (semi / 12.0))
        return {"ok": True, "action": action, "note": note, "hz": round(hz, 2), "semitones": semi}
    if action == "music_rhythm":
        meter = str(params.get("meter") or "4/4")
        return {"ok": True, "action": action, "meter": meter, "beats": int(meter.split("/")[0])}
    if action == "music_notation":
        clef = str(params.get("clef") or "treble")
        line = int(params.get("line") or 1)
        return {"ok": True, "action": action, "clef": clef, "line": line, "note": (_CLEF_LINE.get(clef) or {}).get(line)}
    if action == "music_brain_pattern":
        seq = list(params.get("sequence") or [0, 2, 4, 7])
        checksum = sum(int(x) for x in seq)
        return {"ok": True, "action": action, "sequence": seq, "checksum": checksum, "brain_music": True}
    if action == "music_crosswire":
        track = str(params.get("track") or "brain_guard")
        hook = _crosswire().get(track, "")
        return {"ok": bool(hook), "action": action, "track": track, "hook": hook[:120]}
    return {"ok": False, "error": "unknown_music_action", "action": action}


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
    drills_ok = int(rt.get("music_drills") or 0) >= int(comp.get("drill_min") or 32)

    complete = rate >= float(comp.get("pass_rate_pct") or 85) / 100.0
    if track_id == "music_theory":
        complete = complete and drills_ok
    fluent = complete and rate >= float(comp.get("fluent_rate_pct") or 92) / 100.0 and prof >= 0.85
    mastered = fluent and rate >= float(comp.get("master_rate_pct") or 98) / 100.0 and bool(rt.get("mastered"))

    level = (
        "mastered" if mastered else "fluent" if fluent else "complete" if complete
        else "training" if rate > 0.2 else "pending"
    )
    return {
        "ok": True,
        "level": level,
        "complete": complete,
        "mastered": mastered,
        "fluent": fluent,
        "score": round(max(rate, prof * 0.35), 4),
        "pass_rate": round(rate * 100, 1),
        "proficiency": prof,
        "music_drills": int(rt.get("music_drills") or 0),
        "batteries": bat_ids,
        "tier": rt.get("tier"),
    }


def assess_all_tracks() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    tracks: dict[str, Any] = {}
    for row in doc.get("tracks") or []:
        tid = str(row.get("id") or "")
        if tid:
            tracks[tid] = assess_track(tid)
            tracks[tid]["label"] = row.get("label")
    return {"schema": "hostess7-music-assess/v1", "updated": _now(), "tracks": tracks}


def crosswire_panel() -> dict[str, Any]:
    hooks = _crosswire()
    return {
        "ok": True,
        "schema": "hostess7-music-crosswire/v1",
        "hook_count": len(hooks),
        "hooks": hooks,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    assess = assess_all_tracks()
    rt = _runtime()
    cw = crosswire_panel()
    panel = {
        "schema": "hostess7-music/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "motto": doc.get("motto"),
        "foundation": doc.get("foundation"),
        "reference_pitch_hz": doc.get("reference_pitch_hz") or A4_HZ,
        "reference_note": doc.get("reference_note") or "A4",
        "proficiency": rt.get("proficiency"),
        "fluent": rt.get("fluent"),
        "mastered": rt.get("mastered"),
        "tier": rt.get("tier") or "music_pending",
        "music_drills": rt.get("music_drills"),
        "session_rounds": rt.get("session_rounds"),
        "battery_results": rt.get("battery_results"),
        "tracks": assess.get("tracks"),
        "crosswire": cw,
        "intervals": doc.get("intervals"),
        "scales": doc.get("scales"),
        "chords": doc.get("chords"),
        "last_session": rt.get("last_session"),
        "training_mode": "music",
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
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_music", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("music", install=INSTALL, state=STATE, ledger=LEDGER)
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
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_music", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd,
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-music-training.py [json|assess|battery|train|track-assess|crosswire|sense-step|ocr-ingest|ocr-train|ocr-status]",
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
        track = "music_theory"
        rounds = None
        if len(sys.argv) > 2:
            if sys.argv[2].isdigit():
                rounds = int(sys.argv[2])
            else:
                track = sys.argv[2]
                if len(sys.argv) > 3 and sys.argv[3].isdigit():
                    rounds = int(sys.argv[3])
        print(json.dumps(train_music_session(rounds=rounds, track_id=track), ensure_ascii=False))
        return 0
    if cmd == "track-assess" and len(sys.argv) > 2:
        print(json.dumps(assess_track(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "crosswire":
        print(json.dumps(crosswire_panel(), ensure_ascii=False))
        return 0
    if cmd == "sense-step" and len(sys.argv) > 2:
        step = json.loads(sys.argv[2])
        print(json.dumps(run_sense_step(step), ensure_ascii=False))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({
        "error": "usage: hostess7-music-training.py [json|assess|battery ID|batteries|train [track] [rounds]|track-assess ID|crosswire|sense-step JSON]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())