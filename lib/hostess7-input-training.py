#!/usr/bin/env pythong
"""Hostess 7 input training — keyboard, mouse, gamepad, hand → arcade play with operators."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-input-training-doctrine.json"
RUNTIME = STATE / "hostess7-input-training-runtime.json"
PANEL = STATE / "hostess7-input-training-panel.json"
BATTERY = STATE / "hostess7-input-training.json"
LEDGER = STATE / "hostess7-input-training-ledger.jsonl"

BASE_MODALITIES = ("keyboard", "mouse", "gamepad", "hand", "voice")
SENSE_MODALITIES = ("final_eye", "final_ear", "final_mouth", "final_hands", "stereo_vision")
VOICE_GAMES = INSTALL / "data" / "field-voice-games-doctrine.json"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _modalities() -> tuple[str, ...]:
    doc = _load(DOCTRINE, {})
    mods = doc.get("modalities") or list(BASE_MODALITIES) + list(SENSE_MODALITIES)
    return tuple(str(m) for m in mods)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _ts()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _sense_ball(rel: str, body: dict[str, Any], *, timeout: int = 90) -> dict[str, Any]:
    """Dispatch queen-eyeball / earball / mouthball bridge."""
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "sense_ball_missing", "path": str(py)}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    queen_lib = str(INSTALL / "Queen" / "lib")
    py_parts = [queen_lib]
    for root in ("Final_Eye", "Final_Ear", "Final_Mouth"):
        p = str(INSTALL.parent / root)
        if Path(p).is_dir():
            py_parts.append(p)
    if env.get("PYTHONPATH"):
        py_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(py_parts)
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "dispatch"],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(INSTALL / "Queen"),
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "sense_ball_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "sense_ball_dispatch_failed", "tail": (proc.stderr or "")[:160]}


def _voice_game_profile(game_id: str) -> dict[str, Any]:
    doc = _load(VOICE_GAMES, {})
    return dict((doc.get("games") or {}).get(game_id) or {})


def _mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _default_modality(mod: str) -> dict[str, Any]:
    return {
        "modality": mod,
        "samples": 0,
        "proficiency": 0.0,
        "last_key": None,
        "last_event": None,
        "bursts": 0,
        "axes_peak": 0.0,
        "grip": "open",
    }


def load_store() -> dict[str, Any]:
    doc = _load(RUNTIME, {})
    if isinstance(doc.get("modalities"), list):
        doc = {}
    if not doc:
        doc = {
            "schema": "hostess7-input-training/v1",
            "updated": _ts(),
            "commander": "Hostess 7",
            "modalities": {m: _default_modality(m) for m in _modalities()},
            "samples_total": 0,
            "play_ready": False,
            "system": "nes",
        }
    for m in _modalities():
        doc.setdefault("modalities", {}).setdefault(m, _default_modality(m))
    return doc


def save_store(doc: dict[str, Any]) -> None:
    doc["updated"] = _ts()
    _save(RUNTIME, doc)
    _save(BATTERY, steel_battery_from_store(doc))


def _target() -> float:
    return float(_load(DOCTRINE, {}).get("proficiency_target") or 0.72)


def _bump_proficiency(cur: float, *, delta: float = 0.04) -> float:
    return round(min(1.0, cur + delta), 4)


def _ensure_stereo(context: str = "input_training") -> dict[str, Any]:
    fsv = _mod("hit_fsv", "field-stereo-vision.py")
    if fsv and hasattr(fsv, "ensure_stereo"):
        return fsv.ensure_stereo(context=context)
    return {"ok": False, "skipped": True}


def ingest_sample(
    modality: str,
    payload: dict[str, Any] | None = None,
    *,
    kind: str = "",
    key: str = "",
    dt_ms: float | None = None,
    speed: float | None = None,
    x: float | None = None,
    y: float | None = None,
    buttons: list[dict[str, Any]] | None = None,
    axes: list[dict[str, Any]] | None = None,
    grip: str = "",
) -> dict[str, Any]:
    """Ingest operator input sample — trains Hostess 7 play profile."""
    payload = payload or {}
    mod = (modality or payload.get("modality") or kind or "").strip().lower()
    if mod not in _modalities():
        return {"ok": False, "error": "unknown_modality", "modalities": list(_modalities())}

    doc = load_store()
    row = doc["modalities"][mod]
    ticks = int(_load(DOCTRINE, {}).get("train_ticks_per_ingest") or 2)
    row["samples"] = int(row.get("samples") or 0) + 1
    doc["samples_total"] = int(doc.get("samples_total") or 0) + 1

    uw = _mod("hit_uw", "hostess7-userwatch.py")
    if uw and hasattr(uw, "ingest_sample"):
        uw.ingest_sample(
            mod if mod != "gamepad" else "keydown",
            dt_ms=dt_ms or payload.get("dt_ms"),
            speed=speed or payload.get("speed"),
            key=key or str(payload.get("key") or ""),
            x=x if x is not None else payload.get("x"),
            y=y if y is not None else payload.get("y"),
            meta={"modality": mod, "source": "input_training"},
        )

    hand = _mod("hit_hand", "hostess7-hand-core.py")
    if mod == "hand" and hand:
        g = (grip or payload.get("grip") or "precision").strip().lower()
        row["grip"] = g
        if hasattr(hand, "set_grip"):
            hand.set_grip("right", g)
            hand.set_grip("left", "open")
        if hasattr(hand, "train_hands"):
            hand.train_hands(ticks=ticks)

    if mod == "keyboard":
        k = key or str(payload.get("key") or "")
        row["last_key"] = k
        if dt_ms is not None and float(dt_ms) < 160:
            row["bursts"] = int(row.get("bursts") or 0) + 1

    if mod == "mouse":
        row["last_event"] = payload.get("event") or kind or "move"
        if speed is not None:
            row["axes_peak"] = round(max(float(row.get("axes_peak") or 0), float(speed)), 2)

    if mod == "gamepad":
        btns = buttons or payload.get("buttons") or []
        ax = axes or payload.get("axes") or []
        pressed = sum(1 for b in btns if b.get("pressed") or float(b.get("value") or 0) > 0.5)
        row["bursts"] = int(row.get("bursts") or 0) + (1 if pressed else 0)
        if ax:
            peak = max(abs(float(a.get("value") or a) if isinstance(a, dict) else float(a)) for a in ax)
            row["axes_peak"] = round(max(float(row.get("axes_peak") or 0), peak), 3)

    if mod in ("stereo_vision", "final_eye"):
        _ensure_stereo(context="input_training" if mod == "stereo_vision" else "emulator")

    if mod == "voice":
        utter = str(payload.get("utterance") or payload.get("text") or payload.get("transcript") or "")
        row["last_event"] = payload.get("event") or "utterance"
        row["last_key"] = utter[:48] if utter else None
        if payload.get("game"):
            row["grip"] = str(payload.get("game"))

    if mod in ("final_ear", "final_mouth") and payload.get("game"):
        row["last_event"] = str(payload.get("event") or payload.get("game"))

    row["proficiency"] = _bump_proficiency(float(row.get("proficiency") or 0), delta=0.035 + 0.01 * min(5, ticks))
    doc["modalities"][mod] = row
    doc["play_ready"] = all(
        float((doc["modalities"].get(m) or {}).get("proficiency") or 0) >= _target() * 0.85
        for m in ("keyboard", "gamepad")
    ) and float((doc["modalities"].get("hand") or {}).get("proficiency") or 0) >= _target() * 0.6
    save_store(doc)
    _append_ledger({"event": "ingest", "modality": mod, "proficiency": row["proficiency"]})
    return {
        "ok": True,
        "modality": mod,
        "proficiency": row["proficiency"],
        "play_ready": doc.get("play_ready"),
        "samples_total": doc.get("samples_total"),
    }


def train_tick(*, modality: str | None = None, ticks: int = 12) -> dict[str, Any]:
    doc = load_store()
    mods = _modalities()
    targets = [modality] if modality and modality in mods else list(mods)
    steps: list[dict[str, Any]] = []
    for mod in targets:
        row = doc["modalities"][mod]
        n = max(1, int(ticks))
        for _ in range(n):
            row["proficiency"] = _bump_proficiency(float(row.get("proficiency") or 0), delta=0.02)
            row["samples"] = int(row.get("samples") or 0) + 1
        doc["modalities"][mod] = row
        steps.append({"modality": mod, "proficiency": row["proficiency"], "ticks": n})
    doc["samples_total"] = int(doc.get("samples_total") or 0) + len(targets) * max(1, int(ticks))
    save_store(doc)
    return {"ok": True, "action": "train_tick", "steps": steps, "play_ready": doc.get("play_ready")}


def hostess_to_sap_inputs(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map Hostess 7 trained profile → SAP gamepad snapshot for lockstep relay."""
    doc = load_store()
    snap = snapshot or {}
    gp = snap.get("gamepad") or {}
    kb = doc["modalities"].get("keyboard") or {}
    pad = doc["modalities"].get("gamepad") or {}
    hand = doc["modalities"].get("hand") or {}

    prof_k = float(kb.get("proficiency") or 0)
    prof_p = float(pad.get("proficiency") or 0)
    prof_h = float(hand.get("proficiency") or 0)
    blend = max(prof_k, prof_p, prof_h)

    buttons = list(gp.get("buttons") or [])
    if not buttons:
        buttons = [{"i": i, "pressed": False, "value": 0.0} for i in range(16)]
    axes = list(gp.get("axes") or [])
    if not axes:
        axes = [{"i": 0, "value": 0.0}, {"i": 1, "value": 0.0}]

    last_key = str(kb.get("last_key") or "").lower()
    key_map = {
        "arrowup": (13, True), "w": (13, True),
        "arrowdown": (14, True), "s": (14, True),
        "arrowleft": (15, True), "a": (15, True),
        "arrowright": (16, True), "d": (16, True),
        " ": (0, True), "space": (0, True), "z": (0, True),
        "enter": (9, True), "x": (1, True),
    }
    if last_key in key_map and prof_k >= 0.4:
        idx, on = key_map[last_key]
        if idx < len(buttons):
            buttons[idx] = {**buttons[idx], "i": idx, "pressed": on, "value": 1.0 if on else 0.0}

    grip = str(hand.get("grip") or "open")
    if grip == "trigger" and prof_h >= 0.5:
        for i in (7, 6):
            if i < len(buttons):
                buttons[i] = {"i": i, "pressed": True, "value": 0.9}

    return {
        "connected": True,
        "id": "Hostess7-VirtualPad",
        "index": 0,
        "buttons": buttons,
        "axes": axes,
        "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
        "hostess_blend": round(blend, 3),
        "source": "hostess7_input_training",
    }


def relay_to_sap(*, system: str | None = None, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Push Hostess 7 trained inputs into SAP sync_frame."""
    proxy = _mod("hit_proxy", "field-queen-world-proxy.py")
    sys_id = (system or load_store().get("system") or "nes").strip().lower()
    inputs = hostess_to_sap_inputs(snapshot)
    body = {"action": "sync_frame", "inputs": inputs, "system": sys_id, "role": "hostess7"}
    if proxy and hasattr(proxy, "proxy_json_post"):
        out = proxy.proxy_json_post("/api/sap", body, timeout=12.0)
        return {"ok": bool(out.get("ok", True)), "relay": out, "inputs": inputs, "system": sys_id}
    sap = _mod("hit_sap", "Queen/lib/queen-sweet-anita-protocol.py")
    if sap and hasattr(sap, "dispatch"):
        qbody = {**body}
        return {"ok": True, "relay": sap.dispatch(qbody), "inputs": inputs, "system": sys_id}
    return {"ok": False, "error": "sap_relay_missing", "inputs": inputs}


def verify_emulators(*, capture: bool = False, final_eye: bool = False) -> dict[str, Any]:
    stereo = _ensure_stereo(context="emulator")
    queen_chips = INSTALL / "Queen" / "lib" / "queen-chips.py"
    if not queen_chips.is_file():
        return {"ok": False, "error": "queen_chips_missing"}
    args = ["verify"]
    if capture:
        args.append("--capture")
    if final_eye:
        args.append("--final-eye")
    try:
        proc = subprocess.run(
            [sys.executable, str(queen_chips), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=180 if capture else 45,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            out = json.loads(raw)
            out["stereo_vision"] = stereo
            return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120], "stereo_vision": stereo}
    return {"ok": False, "error": "verify_failed", "stereo_vision": stereo}


def play_with_us(*, system: str = "nes", spawn_rtx: bool = True) -> dict[str, Any]:
    """Wire Hostess 7 into Arcade Battalion — tournament host + SAP relay."""
    stereo = _ensure_stereo(context="gaming")
    doc = load_store()
    doc["system"] = system
    save_store(doc)
    batt = _mod("hit_batt", "field-arcade-battalion.py")
    tournament: dict[str, Any] = {}
    if batt and hasattr(batt, "tournament_host"):
        tournament = batt.tournament_host(system=system, spawn_rtx=spawn_rtx)
    relay = relay_to_sap(system=system)
    train = train_tick(modality="gamepad", ticks=8)
    verify = verify_emulators(capture=spawn_rtx, final_eye=True) if spawn_rtx else verify_emulators()
    out = {
        "ok": bool(tournament.get("ok")) or bool(relay.get("ok")),
        "schema": "hostess7-play-with-us/v1",
        "updated": _ts(),
        "commander": "Hostess 7",
        "system": system,
        "play_ready": doc.get("play_ready"),
        "modalities": doc.get("modalities"),
        "tournament": tournament,
        "sap_relay": relay,
        "training_tick": train,
        "emulator_verify": verify,
        "stereo_vision": stereo,
        "message": "Hostess 7 armed for Arcade Battalion — trained inputs on SAP lane.",
    }
    _append_ledger({"event": "play_with_us", "system": system, "ok": out["ok"]})
    return out


def steel_battery_from_store(doc: dict[str, Any]) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    systems = doctrine.get("game_systems") or ["nes"]
    modalities = []
    for mod, row in (doc.get("modalities") or {}).items():
        prof = float(row.get("proficiency") or 0)
        for sys_id in systems:
            modalities.append({
                "id": f"input_{mod}_{sys_id}",
                "modality": mod,
                "system": sys_id,
                "chip_id": f"system_{sys_id}",
                "proficiency": prof,
                "samples": int(row.get("samples") or 0),
                "facet": doctrine.get("steel_plate", {}).get("facet") or "hostess7_input",
                "label": f"Hostess7 {mod} · {sys_id}",
            })
    return {
        "schema": "hostess7-input-training-battery/v1",
        "updated": doc.get("updated") or _ts(),
        "modalities": modalities,
        "play_ready": bool(doc.get("play_ready")),
        "samples_total": int(doc.get("samples_total") or 0),
    }


def sync_senses() -> dict[str, Any]:
    """Wire Final Eye, Ear, Mouth, Hands into training store."""
    doc = load_store()
    doctrine = _load(DOCTRINE, {})
    modules = doctrine.get("senses_modules") or {}
    rows: dict[str, Any] = {}
    fh = _mod("hit_fh", "final-hands.py")
    if fh and hasattr(fh, "senses_stack"):
        stack = fh.senses_stack()
        rows["stack"] = stack
        for key, val in (stack.get("stack") or {}).items():
            mod_name = key.replace("final_", "final_")
            if mod_name in doc.get("modalities", {}):
                row = doc["modalities"][mod_name]
                row["proficiency"] = _bump_proficiency(
                    float(row.get("proficiency") or 0),
                    delta=0.08 if isinstance(val, dict) and val.get("ok") else 0.02,
                )
                row["last_event"] = "sense_sync"
                doc["modalities"][mod_name] = row
    for sense, rel in modules.items():
        mod = _mod(f"sense_{sense}", str(rel).replace("lib/", ""))
        if not mod:
            mod = _mod(f"sense_{sense}", rel)
        live = False
        if sense == "final_eye" and mod and hasattr(mod, "final_eye_root"):
            live = (mod.final_eye_root() / "zocr.py").is_file()
        elif mod and hasattr(mod, "posture"):
            live = bool((mod.posture() or {}).get("ok"))
        elif mod and hasattr(mod, "build_panel"):
            live = bool((mod.build_panel(write=False) or {}).get("ok"))
        if sense in doc.get("modalities", {}):
            row = doc["modalities"][sense]
            row["proficiency"] = _bump_proficiency(float(row.get("proficiency") or 0), delta=0.06 if live else 0.01)
            row["last_event"] = "live" if live else "pending"
            doc["modalities"][sense] = row
        rows[sense] = {"live": live}
    doc["senses_synced"] = _ts()
    save_store(doc)
    return {"ok": True, "senses": rows, "modalities": doc.get("modalities")}


def voice_game(
    *,
    game_id: str = "seaman",
    system: str | None = None,
    utterance: str | None = None,
    listen_seconds: float | None = None,
    speak: bool = True,
) -> dict[str, Any]:
    """Voice-driven games — Final Ear hears, Final Mouth speaks (Seaman, etc.)."""
    profile = _voice_game_profile(game_id)
    if not profile:
        return {"ok": False, "error": "unknown_voice_game", "game": game_id}
    sys_id = (system or profile.get("system") or "dreamcast").strip().lower()
    sync_senses()
    stereo = _ensure_stereo(context="voice_game") if profile.get("stereo_vision", True) else {}
    seconds = float(listen_seconds if listen_seconds is not None else profile.get("listen_seconds") or 0.8)
    heard = str(utterance or "").strip()
    ear: dict[str, Any] = {"ok": True, "skipped": True, "reason": "utterance_provided"} if heard else {}
    if not heard:
        ear = _sense_ball("Queen/lib/queen-earball.py", {"action": "spectrum", "seconds": seconds})
        heard = str(ear.get("transcript") or ear.get("text") or "").strip()
    replies = profile.get("reply_templates") or profile.get("prompts") or ["I hear you."]
    doc = load_store()
    n = int(doc.get("samples_total") or 0)
    reply = str(replies[n % len(replies)])
    if heard:
        reply = f"{reply} You said: {heard[:80]}."
    mouth: dict[str, Any] = {"ok": False, "skipped": not speak}
    if speak:
        mouth = _sense_ball(
            "Queen/lib/queen-mouthball.py",
            {"action": "speak", "text": reply, "game": game_id},
            timeout=120,
        )
    ingest_sample("voice", {"event": "voice_game", "game": game_id, "utterance": heard, "system": sys_id})
    ingest_sample("final_ear", {"event": "voice_hear", "game": game_id, "spectrum_ok": ear.get("ok")})
    ingest_sample("final_mouth", {"event": "voice_speak", "game": game_id, "text": reply})
    fh = _mod("vg_fh", "final-hands.py")
    periph_train: dict[str, Any] = {}
    pid = str(profile.get("peripheral_id") or "dreamcast_voice_mic")
    if fh and hasattr(fh, "ingest_peripheral"):
        periph_train = fh.ingest_peripheral(pid, {"ticks": 4, "system": sys_id, "game": game_id})
    doc = load_store()
    doc["system"] = sys_id
    save_store(doc)
    return {
        "ok": True,
        "schema": "hostess7-voice-game/v1",
        "updated": _ts(),
        "game": game_id,
        "label": profile.get("label"),
        "system": sys_id,
        "peripheral_id": pid,
        "heard": heard,
        "reply": reply,
        "ear": ear,
        "mouth": mouth,
        "stereo_vision": stereo,
        "peripheral_train": periph_train,
        "modalities": doc.get("modalities"),
        "message": f"Voice game armed — {profile.get('label') or game_id} on {sys_id}.",
    }


def play_universe(*, system: str = "nes", peripheral_id: str | None = None) -> dict[str, Any]:
    """Full play universe — senses + peripherals + arcade."""
    sync_senses()
    fh = _mod("pu_fh", "final-hands.py")
    universe: dict[str, Any] = {}
    if fh and hasattr(fh, "play_universe"):
        universe = fh.play_universe(system=system, peripheral_id=peripheral_id)
    arcade = play_with_us(system=system, spawn_rtx=False)
    comb = _mod("pu_comb", "field-game-peripherals-combinatronic.py")
    snap: dict[str, Any] = {}
    if comb and hasattr(comb, "snap"):
        snap = comb.snap()
    voice_lane: dict[str, Any] = {}
    vdoc = _load(VOICE_GAMES, {})
    for gid, gprof in (vdoc.get("games") or {}).items():
        if str(gprof.get("system") or "") == system:
            voice_lane = voice_game(game_id=gid, system=system, speak=False)
            break
    return {
        "ok": True,
        "schema": "hostess7-play-universe/v1",
        "system": system,
        "universe": universe,
        "arcade": arcade,
        "voice_game": voice_lane or None,
        "peripherals_snap": snap,
        "message": "Play universe — every game in history, with or without us.",
    }


def assess_gaps() -> dict[str, Any]:
    doc = load_store()
    doctrine = _load(DOCTRINE, {})
    target = _target()
    gaps: list[dict[str, Any]] = []
    satisfied: list[str] = []
    for item in doctrine.get("needs_catalog") or []:
        iid = str(item.get("id") or "")
        if iid == "arcade_play_ready":
            if doc.get("play_ready"):
                satisfied.append(iid)
            else:
                gaps.append(dict(item))
            continue
        mod = iid.replace("input_", "")
        prof = float((doc.get("modalities") or {}).get(mod, {}).get("proficiency") or 0)
        if prof >= target:
            satisfied.append(iid)
        else:
            gaps.append({**item, "proficiency": prof, "target": target})
    return {
        "schema": "hostess7-input-training-gaps/v1",
        "gaps": gaps,
        "satisfied": satisfied,
        "play_ready": doc.get("play_ready"),
        "modalities": doc.get("modalities"),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = load_store()
    gaps = assess_gaps()
    stereo = _ensure_stereo(context="input_training")
    fsv = _mod("hit_fsv_panel", "field-stereo-vision.py")
    stereo_status: dict[str, Any] = stereo
    if fsv and hasattr(fsv, "rig_status"):
        try:
            stereo_status = fsv.rig_status()
        except Exception:
            pass
    panel = {
        "ok": True,
        "schema": "hostess7-input-training-panel/v1",
        "updated": _ts(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "commander": "Hostess 7",
        "modalities": doc.get("modalities"),
        "play_ready": doc.get("play_ready"),
        "samples_total": doc.get("samples_total"),
        "system": doc.get("system") or "nes",
        "gaps": gaps,
        "api": "/api/hostess7/input-training",
        "surfaces": {
            "controller_setup": "/queen-game-room.html#arcade",
            "game_room": "/queen-game-room.html",
            "final_hands": "/api/final-hands",
            "lab_tour": "/api/hostess7/lab/tour",
            "voice_games": "/api/hostess7/input-training",
        },
        "voice_games": _load(VOICE_GAMES, {}).get("default_game") or "seaman",
        "senses_synced": doc.get("senses_synced"),
        "stereo_vision": stereo_status,
        "stereoscopic_always_on": True,
    }
    if write:
        _save(PANEL, panel)
        save_store(doc)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action in ("ingest", "sample"):
        return ingest_sample(
            str(body.get("modality") or body.get("kind") or ""),
            body,
            kind=str(body.get("kind") or ""),
            key=str(body.get("key") or ""),
            dt_ms=body.get("dt_ms"),
            speed=body.get("speed"),
            x=body.get("x"),
            y=body.get("y"),
            buttons=body.get("buttons"),
            axes=body.get("axes"),
            grip=str(body.get("grip") or ""),
        )
    if action in ("train", "train_tick", "tick"):
        return train_tick(modality=body.get("modality"), ticks=int(body.get("ticks") or 12))
    if action in ("sap", "sap_relay", "relay"):
        return relay_to_sap(system=body.get("system"), snapshot=body.get("snapshot"))
    if action in ("hostess_inputs", "virtual_pad", "to_sap"):
        return {"ok": True, "inputs": hostess_to_sap_inputs(body.get("snapshot"))}
    if action in ("verify", "verify_emulators", "emulators"):
        return verify_emulators(
            capture=bool(body.get("capture")),
            final_eye=bool(body.get("final_eye", body.get("witness"))),
        )
    if action in ("play", "play_with_us", "arcade", "join"):
        return play_with_us(
            system=str(body.get("system") or "nes"),
            spawn_rtx=body.get("spawn_rtx", True) is not False,
        )
    if action in ("gaps", "needs", "assess"):
        return assess_gaps()
    if action in ("senses", "sync_senses", "senses_sync"):
        return sync_senses()
    if action in ("play_universe", "universe", "every_game"):
        return play_universe(
            system=str(body.get("system") or "nes"),
            peripheral_id=body.get("peripheral_id"),
        )
    if action in ("stereo", "stereo_vision", "stereo_status", "stereo_ensure"):
        fsv = _mod("hit_fsv_dispatch", "field-stereo-vision.py")
        if fsv and hasattr(fsv, "dispatch"):
            sub = {k: v for k, v in body.items() if k != "action"}
            sub.setdefault("action", "status" if action == "stereo_status" else "ensure")
            return fsv.dispatch(sub)
        return _ensure_stereo(context=str(body.get("context") or "input_training"))
    if action in ("tv_watch", "webcam_tv", "tv_capture", "configure_webcam_tv"):
        fsv = _mod("hit_fsv_tv", "field-stereo-vision.py")
        if fsv and hasattr(fsv, "dispatch"):
            sub = dict(body)
            sub["action"] = {
                "tv_watch": "tv_watch",
                "webcam_tv": "configure_webcam_tv",
                "tv_capture": "capture_tv",
                "configure_webcam_tv": "configure_webcam_tv",
            }.get(action, "tv_watch")
            return fsv.dispatch(sub)
        return {"ok": False, "error": "stereo_vision_missing"}
    if action in ("zapper", "zapper_timing"):
        fh = _mod("zt_fh", "final-hands.py")
        if fh and hasattr(fh, "zapper_timing"):
            return fh.zapper_timing(
                display=str(body.get("display") or "ntsc_60"),
                frame=int(body.get("frame") or 0),
            )
        return {"ok": False, "error": "final_hands_missing"}
    if action in ("peripheral", "peripheral_train"):
        fh = _mod("pt_fh", "final-hands.py")
        if fh and hasattr(fh, "ingest_peripheral"):
            return fh.ingest_peripheral(str(body.get("peripheral_id") or body.get("id") or ""), body)
        return {"ok": False, "error": "final_hands_missing"}
    if action in ("voice_game", "voice_drill", "seaman", "seaman_drill"):
        game_id = str(body.get("game") or body.get("game_id") or "seaman")
        if action.startswith("seaman"):
            game_id = "seaman"
        return voice_game(
            game_id=game_id,
            system=body.get("system"),
            utterance=body.get("utterance") or body.get("text") or body.get("transcript"),
            listen_seconds=body.get("listen_seconds"),
            speak=body.get("speak", True) is not False,
        )
    if action in ("voice_games", "list_voice_games"):
        vdoc = _load(VOICE_GAMES, {})
        return {
            "ok": True,
            "schema": "hostess7-voice-games-list/v1",
            "games": list((vdoc.get("games") or {}).keys()),
            "default": vdoc.get("default_game") or "seaman",
            "profiles": vdoc.get("games") or {},
        }
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        raw = sys.argv[2] if len(sys.argv) >= 3 else (sys.stdin.read() or "{}")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "panel"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False))
        return 0
    if cmd == "play":
        sys_id = sys.argv[2] if len(sys.argv) > 2 else "nes"
        print(json.dumps(play_with_us(system=sys_id), ensure_ascii=False))
        return 0
    if cmd == "verify":
        cap = "--capture" in sys.argv[2:]
        eye = "--final-eye" in sys.argv[2:]
        print(json.dumps(verify_emulators(capture=cap, final_eye=eye), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())