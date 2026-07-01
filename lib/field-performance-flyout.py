#!/usr/bin/env pythong
"""Field Performance Flyout — live CPU, memory, thermal, energy metrics (loopback)."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _cpu_sample() -> dict[str, Any]:
    try:
        line = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0]
        parts = [int(x) for x in line.split()[1:]]
        idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
        total = sum(parts)
        return {"idle": idle, "total": total, "cores": os.cpu_count() or 1}
    except (OSError, ValueError, IndexError):
        return {"idle": 0, "total": 1, "cores": 1}


def _cpu_pct(prev: dict[str, Any] | None, cur: dict[str, Any]) -> float:
    if not prev or cur["total"] <= prev["total"]:
        return 0.0
    dt = cur["total"] - prev["total"]
    didle = cur["idle"] - prev["idle"]
    return round(max(0.0, min(100.0, 100.0 * (1.0 - didle / dt))), 2)


def _mem_sample() -> dict[str, Any]:
    mem: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            mem[k.strip()] = int(v.strip().split()[0])
    except OSError:
        pass
    total = mem.get("MemTotal", 0)
    avail = mem.get("MemAvailable", mem.get("MemFree", 0))
    used = max(0, total - avail) if total else 0
    pct = round(100.0 * used / total, 2) if total else 0.0
    return {
        "total_kb": total,
        "used_kb": used,
        "available_kb": avail,
        "used_pct": pct,
    }


def _loadavg() -> list[float]:
    try:
        return [round(float(x), 2) for x in os.getloadavg()]
    except OSError:
        return [0.0, 0.0, 0.0]


def _thermal_slice() -> dict[str, Any]:
    doc = _load(STATE / "field-thermal-guard.json", {})
    metrics = _load(STATE / "field-thermal-metrics.json", {})
    if not doc and not metrics:
        return {"available": False}
    return {
        "available": True,
        "headroom_pct": doc.get("headroom_pct"),
        "current_power_w": doc.get("current_power_w"),
        "rapl_watts": doc.get("rapl_watts"),
        "peak_c": doc.get("peak_c"),
        "joules_per_field_op": doc.get("joules_per_field_op"),
        "max_ops_per_second_at_budget": doc.get("max_ops_per_second_at_budget"),
        "certainty_score": doc.get("certainty_score") or metrics.get("certainty_score"),
        "dispatch_gain_band_pct": metrics.get("dispatch_gain_band_pct"),
        "quality_scale": metrics.get("quality_scale"),
    }


def _substrate_slice() -> dict[str, Any]:
    doc = _load(STATE / "field-substrate-takeover.json", {})
    perf = doc.get("performance") or {}
    return {
        "tier": perf.get("tier"),
        "label": perf.get("label"),
        "multiplier": perf.get("multiplier_claim"),
    }


def _wave_seed() -> list[float]:
    """Phase seeds for client waveform — deterministic from thermal headroom."""
    th = _thermal_slice()
    base = float(th.get("headroom_pct") or 50.0) / 100.0
    t = time.time()
    return [round(base * (0.5 + 0.5 * ((t * 0.7 + i * 0.31) % 1.0)), 4) for i in range(32)]


_prev_cpu: dict[str, Any] | None = None


def sample(*, reset: bool = False) -> dict[str, Any]:
    global _prev_cpu
    if reset:
        _prev_cpu = None
    cur = _cpu_sample()
    cpu_pct = _cpu_pct(_prev_cpu, cur)
    _prev_cpu = cur
    mem = _mem_sample()
    thermal = _thermal_slice()
    substrate = _substrate_slice()
    return {
        "schema": "field-performance-flyout/v1",
        "ts": _now(),
        "ok": True,
        "cpu_pct": cpu_pct,
        "cpu_cores": cur.get("cores", 1),
        "loadavg": _loadavg(),
        "memory": mem,
        "thermal": thermal,
        "substrate": substrate,
        "energy": {
            "power_w": thermal.get("current_power_w") or thermal.get("rapl_watts"),
            "headroom_pct": thermal.get("headroom_pct"),
            "peak_c": thermal.get("peak_c"),
        },
        "field_ops": {
            "max_at_budget": thermal.get("max_ops_per_second_at_budget"),
            "joules_per_op": thermal.get("joules_per_field_op"),
        },
        "wave": _wave_seed(),
        "telemetry": False,
        "loopback_only": True,
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "sample", "status"):
        print(json.dumps(sample(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-performance-flyout.py [json|sample]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())