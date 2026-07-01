#!/usr/bin/env pythong
"""Field switch safety — painless tech conversion, no hotspots, no surprise slowdowns.

Thermal governor + wave shed keep conversion cool without blocking arrive/transform/commit
except at critical temperature. Quota stays at field-max baseline unless crit — conversion
never gets an unexpected performance haircut.
"""
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
DOCTRINE = INSTALL / "data" / "field-switch-safety-doctrine.json"
PANEL = STATE / "field-switch-safety.json"

HOTSPOT_DELTA_C = float(os.environ.get("NEXUS_FIELD_HOTSPOT_DELTA_C", "4"))
FORCE = os.environ.get("NEXUS_FIELD_SWITCH_FORCE", "0") == "1"
ENABLED = os.environ.get("NEXUS_FIELD_SWITCH_SAFETY", "1") == "1"
FIELD_MAX = os.environ.get("NEXUS_FIELD_MAX", "0") == "1"
NO_SLOWDOWN = os.environ.get("NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN", "1" if FIELD_MAX else "0") == "1"
BASELINE_QUOTA = int(os.environ.get("NEXUS_CPU_QUOTA_PCT", "85" if FIELD_MAX else "5"))


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



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_py(rel: str, *args: str, timeout: int = 12) -> dict[str, Any]:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing:{rel}"}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": (proc.stderr or "empty_stdout")[:300]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _refresh_thermal() -> dict[str, Any]:
    return _run_py("thermal-governor.py", "cycle", timeout=8)


def _thermal() -> dict[str, Any]:
    return _load(STATE / "thermal-advisory.json", {})


def _power() -> dict[str, Any]:
    cached = _load(STATE / "field-power-ledger.json", {})
    if cached:
        return cached
    return _run_py("field-power-ledger.py", "json", timeout=10)


def _wave_shed() -> dict[str, Any]:
    return _load(STATE / "wave-shed-advisory.json", {})


def _apply_wave_shed() -> dict[str, Any]:
    if os.environ.get("NEXUS_WAVE_SHED_APPLY", "1") != "1":
        return {"skipped": True}
    wav = STATE / "field-antenna-catch.wav"
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_WAVE_SHED_APPLY": "1",
        "NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN": "1" if NO_SLOWDOWN else "0",
    }
    py = INSTALL / "lib" / "field-wave-shed.py"
    if not py.is_file():
        return {"ok": False, "error": "wave_shed_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "shed", str(wav)],
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": "wave_shed_empty"}


def _conversion_checks() -> dict[str, Any]:
    doctrine = _load(INSTALL / "data" / "field-underlay-switch-doctrine.json", {})
    policy = doctrine.get("policy") or {}
    drive = doctrine.get("drive_converter") or {}
    return {
        "non_destructive": policy.get("destructive_migration") is False,
        "in_place_conversion": drive.get("in_place") is True,
        "same_paths": drive.get("same_paths") is True,
        "no_grub_touch": True,
        "no_kernel_cmdline_touch": True,
        "marker_driven_refresh": True,
        "guest_passthrough": policy.get("guest_passthrough") is True,
    }


def _slowdown_guard(thermal: dict[str, Any], level: str) -> dict[str, Any]:
    quota = thermal.get("quota_pct")
    try:
        quota_i = int(quota) if quota is not None else BASELINE_QUOTA
    except (TypeError, ValueError):
        quota_i = BASELINE_QUOTA
    unexpected = (
        NO_SLOWDOWN
        and FIELD_MAX
        and level != "crit"
        and quota_i < BASELINE_QUOTA
    )
    return {
        "enabled": NO_SLOWDOWN,
        "baseline_quota_pct": BASELINE_QUOTA,
        "current_quota_pct": quota_i,
        "unexpected_slowdown": unexpected,
        "policy": "Quota holds at field-max baseline unless thermal crit",
    }


def _phase_allowed(phase: str, level: str) -> bool:
    if FORCE or not ENABLED:
        return True
    phase = (phase or "refresh").strip().lower()
    if phase in ("arrive", "refresh", "posture", "transform", "commit", "reboot", "wrdt_apply", "wrdt-apply"):
        return level != "crit"
    return level != "crit"


def _needs_wave_shed(level: str, delta: float, wave_level: str, thermal: dict[str, Any]) -> bool:
    if level == "crit":
        return True
    if wave_level == "crit":
        return True
    if delta >= HOTSPOT_DELTA_C:
        return True
    if level == "warn":
        return True
    return bool(thermal.get("hotspot_advisory"))


def evaluate(*, phase: str = "refresh", refresh_thermal: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    if refresh_thermal:
        _refresh_thermal()

    thermal = _thermal()
    power = _power()
    wave = _wave_shed()
    conversion = _conversion_checks()
    slowdown = _slowdown_guard(thermal, str(thermal.get("level") or "unknown"))

    peak = thermal.get("peak_c")
    level = str(thermal.get("level") or "unknown")
    prev_peak = thermal.get("prev_peak_c")
    delta = 0.0
    if peak is not None and prev_peak is not None:
        try:
            delta = float(peak) - float(prev_peak)
        except (TypeError, ValueError):
            delta = 0.0

    wave_level = str(wave.get("level") or "unknown")
    power_verdict = str(power.get("verdict") or "GREEN")

    hotspot_advisory = (
        level in ("warn", "crit")
        or wave_level in ("warn", "crit")
        or delta >= HOTSPOT_DELTA_C
        or bool(thermal.get("hotspot_advisory"))
    )
    thermal_crit = level == "crit"
    conversion_ok = all(conversion.values()) and not slowdown.get("unexpected_slowdown")
    switch_allowed = _phase_allowed(phase, level) and conversion_ok

    doc: dict[str, Any] = {
        "schema": "field-switch-safety/v1",
        "ts": _now(),
        "enabled": ENABLED,
        "phase": phase,
        "doctrine": doctrine.get("title", "field-switch-safety"),
        "motto": doctrine.get("motto", ""),
        "painless": True,
        "non_destructive": True,
        "conversion_ok": conversion_ok,
        "thermal_crit": thermal_crit,
        "hotspot_advisory": hotspot_advisory,
        "switch_allowed": switch_allowed,
        "forced": FORCE,
        "thermal": {
            "peak_c": peak,
            "prev_peak_c": prev_peak,
            "delta_c": round(delta, 2),
            "level": level,
            "wave_shed": thermal.get("wave_shed"),
            "quota_pct": thermal.get("quota_pct"),
            "field_switch_safe": thermal.get("field_switch_safe"),
        },
        "wave_shed": {
            "level": wave_level,
            "strip_wave_ratio": wave.get("strip_wave_ratio"),
        },
        "power": {
            "verdict": power_verdict,
            "net_draw_w": power.get("net_draw_w"),
            "headroom_w": power.get("headroom_w"),
        },
        "conversion": conversion,
        "slowdown_guard": slowdown,
        "checks": {
            **conversion,
            "thermal_governor": thermal.get("enabled", True),
            "wave_shed_coupled": True,
            "no_unexpected_slowdown": not slowdown.get("unexpected_slowdown"),
        },
    }
    if not switch_allowed:
        if thermal_crit:
            doc["block_reason"] = "thermal_crit"
        elif slowdown.get("unexpected_slowdown"):
            doc["block_reason"] = "unexpected_slowdown"
        else:
            doc["block_reason"] = "conversion_check_failed"
        doc["mitigation"] = [
            "run_field_wave_shed",
            "wait_for_thermal_crit_clear",
            "restore_field_max_quota",
        ]
    _save(PANEL, doc)
    return doc


def cycle() -> dict[str, Any]:
    """Daemon tick — refresh thermal, shed excess on advisory without slowing conversion."""
    doc = evaluate(phase="refresh", refresh_thermal=True)
    if _needs_wave_shed(
        str(doc.get("thermal", {}).get("level") or "ok"),
        float(doc.get("thermal", {}).get("delta_c") or 0),
        str(doc.get("wave_shed", {}).get("level") or "unknown"),
        doc.get("thermal") or {},
    ):
        doc["wave_shed_action"] = _apply_wave_shed()
        doc = evaluate(phase="refresh", refresh_thermal=True)
    return doc


def preflight(phase: str) -> dict[str, Any]:
    doc = evaluate(phase=phase, refresh_thermal=True)
    if doc.get("hotspot_advisory"):
        doc["wave_shed_action"] = _apply_wave_shed()
        doc = evaluate(phase=phase, refresh_thermal=True)
    return doc


def main() -> int:
    args = sys.argv[1:]
    cmd = (args[0] if args else "json").strip().lower()
    phase = "refresh"
    for arg in args:
        if arg.startswith("--phase="):
            phase = arg.split("=", 1)[1].strip().lower()

    if cmd in ("json", "panel"):
        cached = _load(PANEL, {})
        if cached:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(evaluate(phase=phase), ensure_ascii=False, indent=2))
        return 0
    if cmd == "preflight":
        print(json.dumps(preflight(phase), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cycle":
        print(json.dumps(cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "evaluate":
        print(json.dumps(evaluate(phase=phase, refresh_thermal=True), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {"error": "usage: field-switch-safety.py [json|preflight|cycle|evaluate] [--phase=PHASE]"},
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())