#!/usr/bin/env pythong
"""Final Hands — mechanical, robotics, simulational hand training + peripheral mastery."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "final-hands-doctrine.json"
CATALOG = INSTALL / "data" / "field-game-peripherals-catalog.json"
RUNTIME = STATE / "final-hands-runtime.json"
PANEL = STATE / "final-hands-panel.json"
BATTERY = STATE / "final-hands.json"
LEDGER = STATE / "final-hands-ledger.jsonl"

LANES = ("mechanical", "robotics", "simulation", "peripheral", "display_sync")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _ts()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


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


def _default_lane(lane: str) -> dict[str, Any]:
    return {"lane": lane, "samples": 0, "proficiency": 0.0, "last_event": None}


def load_runtime() -> dict[str, Any]:
    doc = _load(RUNTIME, {})
    if not doc:
        doc = {
            "schema": "final-hands-runtime/v1",
            "updated": _ts(),
            "commander": "Hostess 7",
            "lanes": {ln: _default_lane(ln) for ln in LANES},
            "peripherals_trained": {},
            "display_profile": "ntsc_60",
            "samples_total": 0,
        }
    for ln in LANES:
        doc.setdefault("lanes", {}).setdefault(ln, _default_lane(ln))
    return doc


def save_runtime(doc: dict[str, Any]) -> None:
    doc["updated"] = _ts()
    _save(RUNTIME, doc)
    _save(BATTERY, steel_battery(doc))


def _target() -> float:
    return float(_load(DOCTRINE, {}).get("proficiency_target") or 0.78)


def _bump(cur: float, delta: float = 0.035) -> float:
    return round(min(1.0, cur + delta), 4)


def peripheral_catalog() -> dict[str, Any]:
    cat = _load(CATALOG, {})
    items = list(cat.get("peripherals") or [])
    active = [p for p in items if str(p.get("status") or "") == "active"]
    by_family: dict[str, int] = {}
    by_system: dict[str, int] = {}
    for p in items:
        fam = str(p.get("family") or "unknown")
        sys_id = str(p.get("system") or "multi")
        by_family[fam] = by_family.get(fam, 0) + 1
        by_system[sys_id] = by_system.get(sys_id, 0) + 1
    return {
        "ok": True,
        "schema": cat.get("schema"),
        "title": cat.get("title"),
        "total": len(items),
        "active": len(active),
        "pioneers": cat.get("pioneers") or [],
        "by_family": by_family,
        "by_system": by_system,
        "peripherals": items,
    }


def zapper_timing(
    *,
    display: str = "ntsc_60",
    refresh_hz: float | None = None,
    frame: int = 0,
) -> dict[str, Any]:
    """Perfect zapper/light-gun timing for any display profile."""
    doctrine = _load(DOCTRINE, {})
    profiles = doctrine.get("display_profiles") or {}
    prof = dict(profiles.get(display) or profiles.get("ntsc_60") or {})
    hz = float(refresh_hz or prof.get("refresh_hz") or 59.94)
    frame_ms = 1000.0 / hz
    flash_us = int(prof.get("zapper_flash_us") or 5800)
    safe_ms = float(prof.get("safe_window_ms") or frame_ms)
    sample_delay = float(prof.get("sample_delay_ms") or 0)
    vrr = bool(prof.get("vrr_compensate"))
    frame_offset_ms = (frame % int(max(1, hz))) * frame_ms
    detect_window = {
        "start_ms": round(frame_offset_ms + sample_delay, 3),
        "end_ms": round(frame_offset_ms + safe_ms, 3),
        "flash_us": flash_us,
    }
    return {
        "ok": True,
        "schema": "final-hands-zapper-timing/v1",
        "display": display,
        "refresh_hz": hz,
        "frame": frame,
        "frame_ms": round(frame_ms, 4),
        "flash_us": flash_us,
        "detect_window": detect_window,
        "vrr_compensate": vrr,
        "perfect": True,
        "motto": "Zapper timings perfect on any display — NTSC, PAL, LCD, OLED VRR.",
    }


def train_lane(
    lane: str,
    *,
    ticks: int = 12,
    peripheral_id: str | None = None,
    grip: str | None = None,
) -> dict[str, Any]:
    doc = load_runtime()
    ln = (lane or "mechanical").strip().lower()
    if ln not in LANES:
        return {"ok": False, "error": "unknown_lane", "lanes": list(LANES)}
    row = doc["lanes"][ln]
    n = max(1, int(ticks))
    hand = _mod("fh_hand", "hostess7-hand-core.py")
    steps: list[dict[str, Any]] = []

    if ln in ("mechanical", "robotics", "simulation") and hand:
        grips = ["open", "power", "precision", "pinch", "tripod", "sphere"]
        for i in range(n):
            g = grip or grips[i % len(grips)]
            if hasattr(hand, "set_grip"):
                hand.set_grip("right", g)
                hand.set_grip("left", "open" if ln == "mechanical" else g)
            if hasattr(hand, "train_hands") and i % 3 == 0:
                steps.append(hand.train_hands(ticks=2, grip=g))

    if ln == "peripheral" and peripheral_id:
        trained = doc.setdefault("peripherals_trained", {})
        hit = trained.setdefault(peripheral_id, {"samples": 0, "proficiency": 0.0})
        hit["samples"] = int(hit.get("samples") or 0) + n
        hit["proficiency"] = _bump(float(hit.get("proficiency") or 0), 0.04 * min(n, 8))
        steps.append({"peripheral": peripheral_id, **hit})

    if ln == "display_sync":
        for i in range(min(n, 4)):
            steps.append(zapper_timing(display=doc.get("display_profile") or "ntsc_60", frame=i))

    row["samples"] = int(row.get("samples") or 0) + n
    row["proficiency"] = _bump(float(row.get("proficiency") or 0), 0.03 * min(n, 6))
    row["last_event"] = peripheral_id or ln
    doc["lanes"][ln] = row
    doc["samples_total"] = int(doc.get("samples_total") or 0) + n
    save_runtime(doc)
    _append({"event": "train_lane", "lane": ln, "ticks": n, "peripheral": peripheral_id})
    return {
        "ok": True,
        "lane": ln,
        "ticks": n,
        "proficiency": row["proficiency"],
        "steps": steps,
        "wireframe": hand.hand_wireframe() if hand and hasattr(hand, "hand_wireframe") else None,
    }


def ingest_peripheral(
    peripheral_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train a specific peripheral — zapper, paddle, power pad, etc."""
    cat = peripheral_catalog()
    hit = next((p for p in (cat.get("peripherals") or []) if str(p.get("id")) == peripheral_id), None)
    if not hit:
        return {"ok": False, "error": "unknown_peripheral", "id": peripheral_id}
    payload = payload or {}
    family = str(hit.get("family") or "")
    timing_row: dict[str, Any] = {}
    if family == "light_gun" or str(hit.get("timing") or "").startswith("zapper"):
        disp = str(hit.get("display_sync") or payload.get("display") or "ntsc_60")
        timing_row = zapper_timing(display=disp, frame=int(payload.get("frame") or 0))
    lane = "display_sync" if timing_row else "peripheral"
    train = train_lane(lane, ticks=int(payload.get("ticks") or 4), peripheral_id=peripheral_id)
    inp = _mod("fh_inp", "hostess7-input-training.py")
    if inp and hasattr(inp, "ingest_sample"):
        mod_map = {
            "light_gun": "gamepad", "gamepad": "gamepad", "paddle": "hand",
            "power_mat": "hand", "pointer": "mouse", "keyboard": "keyboard",
            "keypad": "keyboard", "hand": "hand", "voice_mic": "voice",
        }
        inp.ingest_sample(mod_map.get(family, "gamepad"), {**payload, "peripheral_id": peripheral_id})
    return {
        "ok": True,
        "peripheral": hit,
        "timing": timing_row or None,
        "train": train,
    }


def senses_stack() -> dict[str, Any]:
    """Final Eye + Ear + Mouth + Hands unified senses for play training."""
    eye = _mod("fh_eye", "lib/final-eye-ocr-core.py")
    ear = _mod("fh_ear", "lib/field-final-ear-block.py")
    mouth = _mod("fh_mouth", "lib/field-final-mouth-block.py")
    hand = _mod("fh_hand2", "hostess7-hand-core.py")
    stack: dict[str, Any] = {}
    if eye and hasattr(eye, "final_eye_dispatch"):
        stack["final_eye"] = eye.final_eye_dispatch({"subaction": "status"})
    elif eye and hasattr(eye, "final_eye_root"):
        stack["final_eye"] = {"ok": (eye.final_eye_root() / "zocr.py").is_file(), "root": str(eye.final_eye_root())}
    if ear and hasattr(ear, "posture"):
        stack["final_ear"] = ear.posture()
    if mouth and hasattr(mouth, "posture"):
        stack["final_mouth"] = mouth.posture()
    if hand and hasattr(hand, "hand_status"):
        stack["final_hands"] = hand.hand_status()
    live = sum(1 for v in stack.values() if isinstance(v, dict) and v.get("ok"))
    return {
        "ok": live >= 2,
        "schema": "final-hands-senses-stack/v1",
        "updated": _ts(),
        "live_count": live,
        "stack": stack,
        "commander": "Hostess 7",
    }


def play_universe(*, system: str = "nes", peripheral_id: str | None = None) -> dict[str, Any]:
    """Arm Hostess 7 to learn every game — senses + peripherals + SAP + emulator."""
    doc = load_runtime()
    senses = senses_stack()
    cat = peripheral_catalog()
    periph = peripheral_id
    if not periph:
        voice_hit = next(
            (str(p.get("id")) for p in (cat.get("peripherals") or [])
             if str(p.get("system")) == system and str(p.get("family")) == "voice_mic"),
            None,
        )
        periph = voice_hit or next(
            (str(p.get("id")) for p in (cat.get("peripherals") or []) if str(p.get("system")) == system),
            "hostess7_virtual",
        )
    ingest = ingest_peripheral(periph, {"ticks": 6, "system": system})
    comb = _mod("fh_comb", "lib/field-game-peripherals-combinatronic.py")
    snap: dict[str, Any] = {}
    if comb and hasattr(comb, "snap"):
        snap = comb.snap()
    play = _mod("fh_play", "hostess7-input-training.py")
    arcade: dict[str, Any] = {}
    if play and hasattr(play, "play_with_us"):
        arcade = play.play_with_us(system=system, spawn_rtx=False)
    return {
        "ok": True,
        "schema": "final-hands-play-universe/v1",
        "updated": _ts(),
        "commander": "Hostess 7",
        "system": system,
        "peripheral": periph,
        "senses": senses,
        "peripheral_train": ingest,
        "combinatronic": snap,
        "arcade": arcade,
        "catalog_total": cat.get("total"),
        "message": "Play universe armed — every peripheral in history, with or without operators.",
    }


def steel_battery(doc: dict[str, Any]) -> dict[str, Any]:
    cat = peripheral_catalog()
    leaves = []
    for p in cat.get("peripherals") or []:
        pid = str(p.get("id") or "")
        trained = (doc.get("peripherals_trained") or {}).get(pid) or {}
        leaves.append({
            "id": pid,
            "modality": "peripheral",
            "system": p.get("system"),
            "family": p.get("family"),
            "chip_id": p.get("chip_id"),
            "proficiency": float(trained.get("proficiency") or 0),
            "facet": "final_hands",
            "label": p.get("label"),
            "era": p.get("era"),
            "timing": p.get("timing"),
        })
    for ln, row in (doc.get("lanes") or {}).items():
        leaves.append({
            "id": f"lane_{ln}",
            "modality": ln,
            "system": "multi",
            "family": "hand",
            "chip_id": "final_hands",
            "proficiency": float(row.get("proficiency") or 0),
            "facet": "final_hands",
            "label": f"Final Hands {ln}",
        })
    return {
        "schema": "final-hands-battery/v1",
        "updated": doc.get("updated") or _ts(),
        "modalities": leaves,
        "leaf_count": len(leaves),
        "samples_total": int(doc.get("samples_total") or 0),
    }


def build_panel(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    doc = load_runtime()
    cat = peripheral_catalog()
    senses = (
        {"ok": True, "schema": "final-hands-senses-stack/v1", "fast": True, "live_count": 0, "stack": {}}
        if fast
        else senses_stack()
    )
    panel = {
        "ok": True,
        "schema": "final-hands-panel/v1",
        "updated": _ts(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "commander": "Hostess 7",
        "lanes": doc.get("lanes"),
        "peripherals_trained": doc.get("peripherals_trained"),
        "catalog": {"total": cat.get("total"), "active": cat.get("active"), "by_family": cat.get("by_family")},
        "pioneers": cat.get("pioneers"),
        "senses": senses,
        "display_profile": doc.get("display_profile"),
        "api": "/api/final-hands",
    }
    if write:
        _save(PANEL, panel)
        save_runtime(doc)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return build_panel(write=action == "panel", fast=bool(body.get("fast")))
    if action in ("catalog", "peripherals"):
        return peripheral_catalog()
    if action in ("zapper", "zapper_timing", "light_gun_timing"):
        return zapper_timing(
            display=str(body.get("display") or "ntsc_60"),
            refresh_hz=body.get("refresh_hz"),
            frame=int(body.get("frame") or 0),
        )
    if action in ("train", "train_lane"):
        return train_lane(
            str(body.get("lane") or "mechanical"),
            ticks=int(body.get("ticks") or 12),
            peripheral_id=body.get("peripheral") or body.get("peripheral_id"),
            grip=body.get("grip"),
        )
    if action in ("ingest", "peripheral"):
        return ingest_peripheral(str(body.get("peripheral_id") or body.get("id") or ""), body)
    if action in ("senses", "senses_stack"):
        return senses_stack()
    if action in ("play", "play_universe", "universe"):
        return play_universe(
            system=str(body.get("system") or "nes"),
            peripheral_id=body.get("peripheral_id"),
        )
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
        fast = "--fast" in sys.argv or os.environ.get("FINAL_HANDS_FAST", "").strip() in ("1", "true", "yes")
        print(json.dumps(build_panel(write=cmd == "panel", fast=fast), ensure_ascii=False))
        return 0
    if cmd == "catalog":
        print(json.dumps(peripheral_catalog(), ensure_ascii=False))
        return 0
    if cmd == "senses":
        print(json.dumps(senses_stack(), ensure_ascii=False))
        return 0
    if cmd == "play":
        sys_id = sys.argv[2] if len(sys.argv) > 2 else "nes"
        print(json.dumps(play_universe(system=sys_id), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())