#!/usr/bin/env pythong
"""Calibrate NEXUS_FIELD_JOULES_PER_OP against RAPL (or synthetic fallback).

Run in a quiet VM/host for best results. Writes receipt to state; does not
auto-tighten the live guard unless --apply is passed.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-thermal-guard-doctrine.json"
RECEIPT = STATE / "field-thermal-calibration.json"
POLICY_ENV = STATE / "field-thermal-guard-policy.env"

DEFAULT_OPS = int(os.environ.get("NEXUS_FIELD_CALIB_OPS", "5000000"))
DEFAULT_ROUNDS = int(os.environ.get("NEXUS_FIELD_CALIB_ROUNDS", "3"))


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


def _rapl_module():
    path = INSTALL / "lib" / "field-power-ledger.py"
    spec = importlib.util.spec_from_file_location("field_power_ledger_cal", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _field_ops(n: int) -> None:
    """Light CPU work — proxy for one field op worth of entropy accounting."""
    x = 1
    for i in range(n):
        x = (x * 1664525 + 1013904223 + i) & 0xFFFFFFFF
    if x == 0:
        raise RuntimeError("impossible")


def _rapl_permission_ok(mod: Any) -> tuple[bool, str | None]:
    snap = mod._rapl_energy_uj()
    if not snap.get("available"):
        return False, "rapl_sysfs_missing"
    for label, uj in snap.get("zones", {}).items():
        if uj > 0:
            return True, None
    base = Path("/sys/class/powercap")
    for zone in sorted(base.glob("intel-rapl:*")) + sorted(base.glob("amd-rapl:*")):
        energy = zone / "energy_uj"
        if not energy.is_file():
            continue
        try:
            int(energy.read_text(encoding="utf-8").strip())
            return True, None
        except PermissionError:
            return False, "rapl_permission_denied_run_as_root"
        except (OSError, ValueError):
            continue
    return False, "rapl_zones_empty"


def _sample_rapl(mod: Any, settle_s: float = 0.35) -> dict[str, Any]:
    mod._rapl_watts()
    time.sleep(settle_s)
    return mod._rapl_watts()


def _measure_round(mod: Any, ops: int) -> dict[str, Any]:
    before = _sample_rapl(mod)
    t0 = time.perf_counter()
    _field_ops(ops)
    elapsed = time.perf_counter() - t0
    after = _sample_rapl(mod, settle_s=0.2)
    joules = None
    watts = None
    if before.get("uj_delta") and after.get("uj_delta") and before.get("dt_s") and after.get("dt_s"):
        uj = int(after["uj_delta"])
        joules = uj / 1_000_000.0
        watts = joules / max(elapsed, 0.001)
    elif after.get("watts") is not None:
        watts = float(after["watts"])
        joules = watts * elapsed
    j_per_op = (joules / ops) if joules is not None and ops > 0 else None
    return {
        "ops": ops,
        "elapsed_s": round(elapsed, 4),
        "rapl_joules": round(joules, 6) if joules is not None else None,
        "rapl_watts": round(watts, 3) if watts is not None else None,
        "joules_per_field_op": j_per_op,
        "ops_per_second": round(ops / max(elapsed, 0.001), 0),
    }


def calibrate(*, ops: int = DEFAULT_OPS, rounds: int = DEFAULT_ROUNDS, apply: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    defaults = doctrine.get("defaults") or {}
    fallback = float(defaults.get("joules_per_field_op", 1.2e-9))
    max_jps = float(defaults.get("max_joules_per_second", 45.0))

    mod = _rapl_module()
    rapl_available = False
    rapl_error: str | None = None
    samples: list[dict[str, Any]] = []
    if mod is not None:
        rapl_available, rapl_error = _rapl_permission_ok(mod)
        if rapl_available:
            mod._rapl_watts()
            time.sleep(0.4)
            for _ in range(max(1, rounds)):
                samples.append(_measure_round(mod, ops))

    measured = [s["joules_per_field_op"] for s in samples if s.get("joules_per_field_op")]
    if measured:
        # Use median — robust to one noisy RAPL sample
        measured.sort()
        mid = len(measured) // 2
        calibrated = measured[mid] if len(measured) % 2 else (measured[mid - 1] + measured[mid]) / 2.0
        source = "rapl_median"
    else:
        calibrated = fallback
        source = "doctrine_fallback"

    # Never calibrate tighter than doctrine default — stay conservative
    joules_per_field_op = max(calibrated, fallback)
    max_ops_per_sec = max_jps / joules_per_field_op if joules_per_field_op > 0 else 0
    headroom_note = (
        f"At {max_jps} W budget, guard allows ~{max_ops_per_sec:.3e} field-ops/s before back-off. "
        "Normal dispatch stays at 100% headroom."
    )

    doc = {
        "schema": "field-thermal-calibration/v1",
        "ts": _now(),
        "rapl_available": rapl_available,
        "rapl_error": rapl_error,
        "calibrate_cmd": "sudo NEXUS_INSTALL_ROOT=/path NEXUS_STATE_DIR=/var/lib/nexus-shield pythong lib/field-thermal-calibrate.py calibrate --apply",
        "source": source,
        "joules_per_field_op": joules_per_field_op,
        "joules_per_field_op_raw": calibrated,
        "doctrine_default": fallback,
        "max_joules_per_second": max_jps,
        "max_ops_per_second_at_budget": max_ops_per_sec,
        "headroom_note": headroom_note,
        "speed_impact": "none_under_normal_load",
        "samples": samples,
        "applied": False,
    }

    if apply:
        lines = []
        if POLICY_ENV.is_file():
            for line in POLICY_ENV.read_text(encoding="utf-8").splitlines():
                if line.startswith("joules_per_field_op="):
                    continue
                if line.strip():
                    lines.append(line)
        lines.append(f"joules_per_field_op={joules_per_field_op}")
        POLICY_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
        doc["applied"] = True
        doc["policy_env"] = str(POLICY_ENV)

    _save(RECEIPT, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    apply = "--apply" in sys.argv
    if cmd in ("json", "calibrate", "run"):
        print(json.dumps(calibrate(apply=apply), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-thermal-calibrate.py [json|calibrate] [--apply]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())