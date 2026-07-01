#!/usr/bin/env pythong
"""Field plate amplitude — infinite-dimension superposition over plate slices."""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-plate-field-doctrine.json"
RUNTIME = STATE / "field-plate-field-runtime.json"
PANEL = STATE / "field-plate-field-panel.json"

_VERDICT_W = {
    "GREEN": 1.0,
    "LIVE": 1.0,
    "OK": 0.95,
    "WATCH": 0.6,
    "WARN": 0.55,
    "RED": 0.15,
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



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _dimension_phase(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _slice_amplitude(key: str, val: Any, weights: dict[str, float]) -> float:
    if val is None:
        return weights.get("missing", 0.02)
    if isinstance(val, dict):
        if val.get("ok") is False:
            return 0.08
        verdict = str(val.get("verdict") or val.get("status") or "").upper()
        if verdict in weights:
            return float(weights[verdict])
        if val.get("live") or val.get("http_live") or val.get("brain_live"):
            return 0.9
        n = val.get("connection_count")
        if n is None and isinstance(val.get("connections"), list):
            n = len(val["connections"])
        if isinstance(n, int) and n > 0:
            return min(1.0, 0.25 + n / 128.0)
        if val.get("schema") or val.get("generation") is not None:
            return 0.72
        return 0.45 if val else 0.05
    if isinstance(val, list) and val:
        return min(1.0, 0.3 + len(val) / 64.0)
    return 0.35


def amplitude_process(
    slices: dict[str, Any],
    *,
    failed: list[str] | None = None,
) -> dict[str, Any]:
    """Infinite-dimension field: each slice key is a dimension; amplitude = process weight."""
    doctrine = _load(DOCTRINE, {})
    weights = (doctrine.get("amplitude") or {}).get("verdict_weights") or _VERDICT_W
    failed_set = set(failed or [])
    dimensions: list[dict[str, Any]] = []
    sum_sq = 0.0
    for key, val in sorted(slices.items()):
        if key in ("field", "parallel_load", "field_load", "infinite_dimension"):
            continue
        if str(key).startswith("_"):
            continue
        amp = 0.0 if key in failed_set else _slice_amplitude(key, val, weights)
        phase = _dimension_phase(key)
        sum_sq += amp * amp
        dimensions.append({
            "key": key,
            "dimension": phase,
            "amplitude": round(amp, 4),
            "present": key not in failed_set and val is not None,
        })
    norm = math.sqrt(sum_sq) if sum_sq > 0 else 1.0
    for row in dimensions:
        row["normalized"] = round(row["amplitude"] / norm, 4)
    dimensions.sort(key=lambda r: r["amplitude"], reverse=True)
    peak = dimensions[0]["amplitude"] if dimensions else 0.0
    mean = sum(d["amplitude"] for d in dimensions) / len(dimensions) if dimensions else 0.0
    sense = _load(STATE / "field-sense-package-panel.json", {})
    h7 = (sense.get("members") or {}).get("hostess7") or {}
    return {
        "schema": "field-plate-field-runtime/v1",
        "ts": _now(),
        "infinite_dimension": True,
        "amplitude_process": (doctrine.get("amplitude") or {}).get("process") or "superposition_normalize",
        "dimension_count": len(dimensions),
        "field_energy": round(sum_sq, 4),
        "field_norm": round(norm, 4),
        "peak_amplitude": round(peak, 4),
        "mean_amplitude": round(mean, 4),
        "top_dimensions": dimensions[:12],
        "dimensions": dimensions,
        "hostess7_meld": {
            "brain_protected": h7.get("brain_protected"),
            "smart_one": (h7.get("smart_one") or {}).get("label"),
            "system_corrupt": False,
        },
        "failed": list(failed_set),
    }


def write_runtime(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    tmp = RUNTIME.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(RUNTIME)
    PANEL.write_text(payload, encoding="utf-8")


def read_runtime() -> dict[str, Any]:
    return _load(RUNTIME, {})


def panel_json() -> dict[str, Any]:
    doc = read_runtime()
    if doc.get("schema"):
        return doc
    return {"schema": "field-plate-field-runtime/v1", "infinite_dimension": True, "dimensions": []}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-plate-field.py [json|panel]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())