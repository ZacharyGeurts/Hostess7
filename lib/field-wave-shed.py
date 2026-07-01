#!/usr/bin/env pythong
"""Push out excess — discard strip, cut capture draw, advise lower system load."""
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
ADVISORY = STATE / "wave-shed-advisory.json"
STAMP = STATE / "wave-shed.stamp"

# Strip/wave RMS ratio above this → excess dominates; shed harder
SHED_RATIO_WARN = float(os.environ.get("NEXUS_WAVE_SHED_RATIO_WARN", "0.35"))
SHED_RATIO_CRIT = float(os.environ.get("NEXUS_WAVE_SHED_RATIO_CRIT", "0.65"))


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



def _import_strip():
    import importlib.util

    path = INSTALL / "lib" / "field-wave-strip.py"
    spec = importlib.util.spec_from_file_location("field_wave_strip", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(cmd: list[str], *, timeout: int = 8) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _stop_field_capture() -> list[str]:
    """Stop rtl_fm / live play — real USB/CPU draw reduction."""
    done: list[str] = []
    for pat in ("rtl_fm", "field-wave-fm", "field-wave-play"):
        try:
            subprocess.run(["pkill", "-f", pat], capture_output=True, timeout=4)
            done.append(f"pkill:{pat}")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return done


def _usb_rtl_autosuspend() -> list[str]:
    """Ask kernel to autosuspend RTL dongle — lowers idle USB draw."""
    done: list[str] = []
    base = Path("/sys/bus/usb/devices")
    if not base.is_dir():
        return done
    for dev in base.iterdir():
        v = dev / "idVendor"
        p = dev / "idProduct"
        try:
            if not v.is_file() or not p.is_file():
                continue
            if v.read_text().strip().lower() != "0bda":
                continue
            if p.read_text().strip().lower() not in ("2838", "2832"):
                continue
            ctrl = dev / "power" / "control"
            if ctrl.is_file():
                ctrl.write_text("auto\n", encoding="utf-8")
                done.append(f"usb_autosuspend:{dev.name}")
            autosuspend = dev / "power" / "autosuspend_delay_ms"
            if autosuspend.is_file():
                autosuspend.write_text("2000\n", encoding="utf-8")
        except OSError:
            continue
    return done


def _thermal_quota_bump(*, level: str) -> dict[str, Any]:
    """Advise wave shed level — hold quota unless crit when no-unexpected-slowdown is on."""
    no_slowdown = os.environ.get("NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN", "1") == "1"
    adv = STATE / "thermal-advisory.json"
    doc: dict[str, Any] = {"schema": "thermal-governor/v1", "quota_pct": 85}
    if adv.is_file():
        try:
            doc = json.loads(adv.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    base = int(doc.get("quota_pct") or 85)
    if level == "crit" and not no_slowdown:
        doc["quota_pct"] = max(25, base // 3)
        doc["wave_shed"] = "crit"
    elif level == "warn" and not no_slowdown:
        doc["quota_pct"] = max(40, int(base * 0.7))
        doc["wave_shed"] = "warn"
    else:
        doc["wave_shed"] = level if level != "ok" else "ok"
        if no_slowdown:
            doc["quota_pct"] = base
    doc["hotspot_advisory"] = level in ("warn", "crit")
    doc["updated"] = _now()
    STATE.mkdir(parents=True, exist_ok=True)
    adv.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "thermal_advisory": str(adv),
        "quota_pct": doc["quota_pct"],
        "quota_held": no_slowdown and level != "crit",
    }


def shed_from_wav(wav_path: Path, *, apply: bool = False) -> dict[str, Any]:
    """
    Strip to wave, push out excess (discard strip buffer), meter draw savings.
    apply=1: stop capture, USB autosuspend, lower quota advisory.
    """
    strip_mod = _import_strip()
    if strip_mod is None:
        return {"ok": False, "error": "field-wave-strip missing"}
    if not wav_path.is_file():
        return {"ok": False, "error": "wav_missing", "path": str(wav_path)}

    import numpy as np
    import wave as wave_mod

    with wave_mod.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    pcm_v = strip_mod.voltage_from_s16_pcm(frames)
    wave_v, strip_v, meta = strip_mod.strip_pcm_to_wave(pcm_v)
    e_wave = strip_mod.potential_energy_joules(wave_v, float(rate))
    e_strip = strip_mod.potential_energy_joules(strip_v, float(rate))
    w_rms = float(e_wave.get("watts_rms_proxy") or 0)
    s_rms = float(e_strip.get("watts_rms_proxy") or 0)
    total = w_rms + s_rms
    ratio = (s_rms / total) if total > 0 else 0.0

    level = "ok"
    if ratio >= SHED_RATIO_CRIT:
        level = "crit"
    elif ratio >= SHED_RATIO_WARN:
        level = "warn"

    # Push out excess: keep wave only, strip discarded (not written, not retained)
    wave_path = STATE / f"{wav_path.stem}-shed.vdat"
    wave_info = strip_mod.write_vdat(wave_path, wave_v, sample_rate_hz=float(rate), channels=1)
    shed_joules = float(e_strip.get("joules_proxy") or 0)

    actions: dict[str, Any] = {"pushed_out": True, "strip_retained": False}
    if apply:
        actions["capture_stopped"] = _stop_field_capture()
        actions["usb"] = _usb_rtl_autosuspend()
        actions["thermal"] = _thermal_quota_bump(level=level)

    doc = {
        "schema": "field-wave-shed/v1",
        "ts": _now(),
        "ok": True,
        "policy": "push_out_excess_reduce_draw",
        "level": level,
        "strip_wave_ratio": round(ratio, 6),
        "potential_energy_shed_joules_proxy": round(shed_joules, 12),
        "potential_energy_kept_joules_proxy": e_wave.get("joules_proxy"),
        "wave": wave_info,
        "draw_reduction": {
            "strip_not_stored": True,
            "strip_not_processed": True,
            "capture_halted": bool(apply and actions.get("capture_stopped")),
            "usb_autosuspend": bool(apply and actions.get("usb")),
            "quota_lowered": bool(apply and level != "ok"),
        },
        "actions": actions,
        "honest_limit": "Software sheds CPU/USB/disk draw; cannot dump RF at antenna.",
    }
    STATE.mkdir(parents=True, exist_ok=True)
    ADVISORY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STAMP.write_text(_now() + "\n", encoding="utf-8")
    ledger_py = INSTALL / "lib" / "field-power-ledger.py"
    if ledger_py.is_file():
        try:
            subprocess.run(
                [sys.executable, str(ledger_py), "board"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    return doc


def posture() -> dict[str, Any]:
    adv: dict[str, Any] = {}
    if ADVISORY.is_file():
        try:
            adv = json.loads(ADVISORY.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "field-wave-shed/v1",
        "ts": _now(),
        "last_shed": adv.get("ts"),
        "level": adv.get("level", "unknown"),
        "strip_wave_ratio": adv.get("strip_wave_ratio"),
        "shed_joules_proxy": adv.get("potential_energy_shed_joules_proxy"),
        "draw_reduction": adv.get("draw_reduction", {}),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    apply = os.environ.get("NEXUS_WAVE_SHED_APPLY", "0") == "1" or cmd == "apply"
    default_wav = STATE / "field-antenna-catch.wav"
    if cmd in ("json", "panel"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("shed", "apply"):
        wav = Path(sys.argv[2]) if len(sys.argv) > 2 else default_wav
        print(json.dumps(shed_from_wav(wav, apply=apply), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-wave-shed.py [json|shed [WAV]|apply [WAV]]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())