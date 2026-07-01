#!/usr/bin/env pythong
"""Thermal governor — read hwmon sensors, write energy advisory for daemon quota."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
ADVISORY = STATE / "thermal-advisory.json"


def _read_temps_c() -> list[float]:
    temps: list[float] = []
    hwmon = Path("/sys/class/hwmon")
    if not hwmon.is_dir():
        return temps
    for chip in sorted(hwmon.glob("hwmon*")):
        for entry in chip.glob("temp*_input"):
            try:
                milli = int(entry.read_text(encoding="utf-8").strip())
                temps.append(milli / 1000.0)
            except (OSError, ValueError):
                continue
    return temps


def _prev_peak() -> float | None:
    if not ADVISORY.is_file():
        return None
    try:
        prev = json.loads(ADVISORY.read_text(encoding="utf-8"))
        val = prev.get("peak_c")
        return float(val) if val is not None else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def evaluate() -> dict[str, Any]:
    field_max = os.environ.get("NEXUS_FIELD_MAX", "0") == "1"
    enabled = os.environ.get("NEXUS_THERMAL_GOVERNOR", "1") == "1"
    no_slowdown = os.environ.get("NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN", "1" if field_max else "0") == "1"
    warn_c = float(os.environ.get("NEXUS_THERMAL_WARN_C", "78"))
    crit_c = float(os.environ.get("NEXUS_THERMAL_CRIT_C", "88"))
    hotspot_delta = float(os.environ.get("NEXUS_FIELD_HOTSPOT_DELTA_C", "4"))
    baseline_quota = int(os.environ.get("NEXUS_CPU_QUOTA_PCT", "85" if field_max else "5"))
    temps = _read_temps_c()
    peak = max(temps) if temps else None
    prev_peak = _prev_peak()
    delta_c = round(peak - prev_peak, 2) if peak is not None and prev_peak is not None else 0.0
    level = "ok"
    quota_pct = baseline_quota
    if field_max and baseline_quota < 50:
        quota_pct = 85
    hotspot_advisory = False
    field_switch_safe = True
    wave_shed = "ok"
    if not enabled or peak is None:
        return {
            "schema": "thermal-governor/v1",
            "enabled": enabled,
            "field_max": field_max,
            "no_unexpected_slowdown": no_slowdown,
            "peak_c": peak,
            "prev_peak_c": prev_peak,
            "delta_c": delta_c,
            "level": "unknown" if peak is None else "ok",
            "quota_pct": quota_pct,
            "hotspot_advisory": False,
            "field_switch_safe": True,
            "wave_shed": wave_shed,
            "sensors": len(temps),
        }
    if peak >= crit_c:
        level = "crit"
        quota_pct = max(40 if field_max else 2, quota_pct // 2)
        hotspot_advisory = True
        field_switch_safe = False
        wave_shed = "crit"
    elif peak >= warn_c:
        level = "warn"
        hotspot_advisory = True
        wave_shed = "warn"
        if not no_slowdown:
            floor = 60 if field_max else 3
            quota_pct = max(floor, int(quota_pct * (0.85 if field_max else 0.75)))
    elif delta_c >= hotspot_delta:
        hotspot_advisory = True
        wave_shed = "warn"
    doc = {
        "schema": "thermal-governor/v1",
        "enabled": enabled,
        "field_max": field_max,
        "no_unexpected_slowdown": no_slowdown,
        "peak_c": round(peak, 2),
        "prev_peak_c": prev_peak,
        "delta_c": delta_c,
        "warn_c": warn_c,
        "crit_c": crit_c,
        "level": level,
        "quota_pct": quota_pct,
        "baseline_quota_pct": baseline_quota,
        "hotspot_advisory": hotspot_advisory,
        "field_switch_safe": field_switch_safe,
        "wave_shed": wave_shed,
        "sensors": len(temps),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    ADVISORY.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "cycle", "json"):
        print(json.dumps(evaluate(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: thermal-governor.py [panel|cycle]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
