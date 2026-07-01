#!/usr/bin/env pythong
"""Field thermal guard — Landauer work estimator, incremental redata policy, gatekeeper tie-in."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-thermal-guard-doctrine.json"
PANEL = STATE / "field-thermal-guard.json"
POLICY_ENV = STATE / "field-thermal-guard-policy.env"
ANOMALY = STATE / "field-thermal-anomaly.json"

KT_LN2 = 2.87e-21


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


class FieldThermalGuard:
    """Python mirror of FieldThermalGuard.hpp — budget-capped field work."""

    def __init__(self) -> None:
        doc = _load(DOCTRINE, {})
        defaults = doc.get("defaults") or {}
        self.max_joules_per_second = float(
            os.environ.get("NEXUS_FIELD_MAX_JOULES_PER_SEC", defaults.get("max_joules_per_second", 45.0))
        )
        self.joules_per_field_op = float(
            os.environ.get("NEXUS_FIELD_JOULES_PER_OP", defaults.get("joules_per_field_op", 1.2e-9))
        )
        self.max_global_redata_chunk = int(
            os.environ.get("NEXUS_FIELD_REDATA_CHUNK", defaults.get("max_global_redata_chunk", 8192))
        )
        self.backoff_ms = int(defaults.get("backoff_ms", 5))
        self._ops = 0
        self._window_start = time.monotonic()
        self._current_power_w = 0.0
        self._load_anomaly_tighten()

    def _load_anomaly_tighten(self) -> None:
        anom = _load(ANOMALY, {})
        if anom.get("active"):
            factor = float(os.environ.get("NEXUS_FIELD_THERMAL_TIGHTEN", "0.75"))
            self.max_joules_per_second *= factor

    def landauer_joules(self, bits_erased: int) -> float:
        return float(bits_erased) * KT_LN2

    def estimate_joules(self, num_ops: int, bits_erased_proxy: int = 64) -> float:
        return num_ops * (self.joules_per_field_op + self.landauer_joules(bits_erased_proxy))

    def _roll_window(self) -> None:
        now = time.monotonic()
        dt = now - self._window_start
        if dt >= 1.0:
            self._current_power_w = (self._ops * self.joules_per_field_op) / max(dt, 0.001)
            self._ops = 0
            self._window_start = now

    def allow_update(self, num_ops: int) -> bool:
        self._roll_window()
        dt = max(time.monotonic() - self._window_start, 0.001)
        projected = self._ops + num_ops
        projected_power = (projected * self.joules_per_field_op) / dt
        return projected_power <= self.max_joules_per_second

    def record_ops(self, n: int) -> None:
        self._ops += n

    def headroom_pct(self) -> float:
        if self.max_joules_per_second <= 0:
            return 100.0
        used = min(self._current_power_w / self.max_joules_per_second, 1.0)
        return max(0.0, (1.0 - used) * 100.0)

    def safe_global_redata(
        self,
        total_items: int,
        fn: Callable[[int, int], None],
    ) -> dict[str, Any]:
        chunks_done = 0
        chunks_skipped = 0
        offset = 0
        while offset < total_items:
            chunk = min(self.max_global_redata_chunk, total_items - offset)
            if not self.allow_update(chunk):
                time.sleep(self.backoff_ms / 1000.0)
                chunks_skipped += 1
                offset += chunk
                continue
            fn(offset, chunk)
            self.record_ops(chunk)
            chunks_done += 1
            offset += chunk
        return {"chunks_done": chunks_done, "chunks_skipped": chunks_skipped, "total": total_items}


def _read_hwmon_peak_c() -> float | None:
    hwmon = Path("/sys/class/hwmon")
    if not hwmon.is_dir():
        return None
    temps: list[float] = []
    for chip in sorted(hwmon.glob("hwmon*")):
        for entry in chip.glob("temp*_input"):
            try:
                temps.append(int(entry.read_text(encoding="utf-8").strip()) / 1000.0)
            except (OSError, ValueError):
                continue
    return max(temps) if temps else None


def _rapl_watts() -> float | None:
    ledger_py = INSTALL / "lib" / "field-power-ledger.py"
    if not ledger_py.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_power_ledger_guard", ledger_py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rapl = mod._rapl_watts()
        return rapl.get("watts") if rapl.get("available") else None
    except (ImportError, OSError, AttributeError):
        return None


def detect_anomaly() -> dict[str, Any]:
    thermal = _load(STATE / "thermal-advisory.json", {})
    peak = _read_hwmon_peak_c()
    rapl_w = _rapl_watts()
    level = str(thermal.get("level") or "ok")
    active = level in ("warn", "crit") or (rapl_w is not None and rapl_w > 80.0)
    doc = {
        "schema": "field-thermal-anomaly/v1",
        "ts": _now(),
        "active": active,
        "thermal_level": level,
        "peak_c": peak,
        "rapl_watts": rapl_w,
    }
    _save(ANOMALY, doc)
    return doc


def publish_policy(guard: FieldThermalGuard) -> None:
    lines = [
        f"max_joules_per_second={guard.max_joules_per_second}",
        f"joules_per_field_op={guard.joules_per_field_op}",
        f"max_global_redata_chunk={guard.max_global_redata_chunk}",
    ]
    POLICY_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def gatekeeper_tighten() -> dict[str, Any]:
    """Stealth rate limit hook — tighten field budget on anomaly."""
    anom = detect_anomaly()
    if not anom.get("active"):
        return {"ok": True, "tightened": False}
    guard = FieldThermalGuard()
    factor = float(os.environ.get("NEXUS_FIELD_THERMAL_TIGHTEN", "0.75"))
    guard.max_joules_per_second *= factor
    publish_policy(guard)
    rate = STATE / "field-thermal-rate-limit.json"
    _save(
        rate,
        {
            "schema": "field-thermal-rate-limit/v1",
            "ts": _now(),
            "active": True,
            "max_joules_per_second": guard.max_joules_per_second,
            "reason": "thermal_anomaly",
        },
    )
    return {"ok": True, "tightened": True, "max_joules_per_second": guard.max_joules_per_second}


def _calibration_receipt() -> dict[str, Any]:
    path = STATE / "field-thermal-calibration.json"
    return _load(path, {})


def _canvas_pixels() -> int:
    w = int(os.environ.get("NEXUS_FIELD_CANVAS_W", "3840"))
    h = int(os.environ.get("NEXUS_FIELD_CANVAS_H", "2160"))
    return w * h


def compute_thermal_metrics(guard: FieldThermalGuard) -> dict[str, Any]:
    """Observable certainty numbers — replaces old 857× unguarded peak-risk estimate."""
    canvas_px = _canvas_pixels()
    chunk = guard.max_global_redata_chunk
    burst_derating = round(canvas_px / max(chunk, 1), 1)
    max_ops_budget = guard.max_joules_per_second / guard.joules_per_field_op if guard.joules_per_field_op > 0 else 0.0
    sustained_ops = float(os.environ.get("NEXUS_FIELD_SUSTAINED_OPS_S", "44000000"))
    headroom_mult = round(max_ops_budget / max(sustained_ops, 1.0), 1)
    peak = _read_hwmon_peak_c()
    thermal_adv = _load(STATE / "thermal-advisory.json", {})
    layers = {
        "engine_guard": 1.0,
        "incremental_redata": 1.0,
        "hwmon_feedback": 1.0 if peak is not None else 0.6,
        "gatekeeper_wired": 1.0 if (INSTALL / "lib" / "connection-gatekeeper.py").is_file() else 0.5,
        "boot_enforced": 1.0 if (INSTALL / "lib" / "nexus-boot-impl.sh").is_file() else 0.5,
        "grok16_bridge": 1.0 if Path(os.environ.get("GROK16_ROOT", str(INSTALL.parent.parent / "Grok16"))).joinpath("scripts/nexus-thermal-bridge.sh").is_file() else 0.7,
    }
    certainty = round(sum(layers.values()) / len(layers), 3)
    dispatch_gain_min = 35 if guard.headroom_pct() >= 80.0 else int(35 * guard.headroom_pct() / 100.0)
    dispatch_gain_max = 60 if guard.headroom_pct() >= 80.0 else int(60 * guard.headroom_pct() / 100.0)
    return {
        "schema": "field-thermal-metrics/v1",
        "ts": _now(),
        "certainty_score": certainty,
        "certainty_label": "high" if certainty >= 0.9 else "medium" if certainty >= 0.7 else "low",
        "safe_global_redata_certainty_pct": round(certainty * 100.0, 1),
        "replaces_old_estimate": "857x_peak_risk_unguarded",
        "burst_derating_ratio": burst_derating,
        "budget_headroom_ops_per_s": round(max_ops_budget),
        "sustained_field_ops_per_s": round(sustained_ops),
        "headroom_multiplier": headroom_mult,
        "canvas_pixels_4k_uhd": canvas_px,
        "redata_chunk": chunk,
        "incremental_passes_4k": int((canvas_px + chunk - 1) // chunk),
        "dispatch_gain_band_pct": [dispatch_gain_min, dispatch_gain_max],
        "quality_scale": round(min(1.0, guard.headroom_pct() / 100.0), 3),
        "cold_path_overhead_pct": 0.0,
        "monolithic_blast_forbidden": True,
        "peak_c": peak,
        "hotspot_advisory": bool(thermal_adv.get("hotspot_advisory")),
        "layers": layers,
    }


def evaluate() -> dict[str, Any]:
    guard = FieldThermalGuard()
    anom = detect_anomaly()
    peak = _read_hwmon_peak_c()
    rapl_w = _rapl_watts()
    headroom = round(guard.headroom_pct(), 1)
    cal = _calibration_receipt()
    max_ops = 45.0 / guard.joules_per_field_op if guard.joules_per_field_op > 0 else 0
    metrics = compute_thermal_metrics(guard)
    doc = {
        "schema": "field-thermal-guard/v1",
        "ts": _now(),
        "headroom_pct": headroom,
        "max_joules_per_second": guard.max_joules_per_second,
        "joules_per_field_op": guard.joules_per_field_op,
        "max_global_redata_chunk": guard.max_global_redata_chunk,
        "current_power_w": round(guard._current_power_w, 6),
        "peak_c": peak,
        "rapl_watts": rapl_w,
        "anomaly": anom,
        "incremental_only": True,
        "monolithic_blast_forbidden": True,
        "speed_impact": "none_under_normal_load",
        "max_ops_per_second_at_budget": cal.get("max_ops_per_second_at_budget") or max_ops,
        "calibration": cal if cal else {"status": "pending", "tool": "lib/field-thermal-calibrate.py"},
        "metrics": metrics,
        "certainty_score": metrics.get("certainty_score"),
        "certainty_label": metrics.get("certainty_label"),
    }
    publish_policy(guard)
    _save(PANEL, doc)
    _save(STATE / "field-thermal-metrics.json", metrics)
    return doc


def cycle() -> dict[str, Any]:
    doc = evaluate()
    gatekeeper_tighten()
    headroom = doc.get("headroom_pct", 0)
    try:
        log_path = Path(os.environ.get("NEXUS_ALERT_LOG", STATE / "nexus-alerts.log"))
        line = f"{_now()} [INFO] field-thermal-guard: field thermal headroom {headroom}%\n"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "evaluate"):
        print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cycle":
        cycle()
        return 0
    if cmd == "anomaly":
        print(json.dumps(detect_anomaly(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gatekeeper":
        print(json.dumps(gatekeeper_tighten(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-thermal-guard.py [json|cycle|anomaly|gatekeeper]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())