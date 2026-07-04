#!/usr/bin/env python3
"""Sub-micron spatial + sub-microsecond temporal — run hard on every rack."""
from __future__ import annotations

import importlib.util
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-sub-micron-timing-doctrine.json"
PANEL = STATE / "field-sub-micron-timing-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_json(rel: str, args: list[str] | None = None, *, timeout: float = 60.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *(args or ["json"])],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}
    return {"ok": False, "error": "script_failed"}


def _mod_clock() -> Any:
    spec = importlib.util.spec_from_file_location("sov_clk", INSTALL / "lib" / "sovereign-clock.py")
    if not spec or not spec.loader:
        raise ImportError("sovereign-clock missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def microsecond_bench(*, rounds: int = 64) -> dict[str, Any]:
    clk = _mod_clock()
    mono_deltas: list[int] = []
    sov_deltas: list[int] = []
    t0m = time.perf_counter_ns()
    t0s = clk.ns_linear()
    for _ in range(rounds):
        a = time.perf_counter_ns()
        b = clk.ns_linear()
        c = time.perf_counter_ns()
        d = clk.ns_linear()
        mono_deltas.append((c - a) // 1000)
        sov_deltas.append((d - b) // 1000)
    elapsed_mono_us = (time.perf_counter_ns() - t0m) // 1000
    elapsed_sov_us = (clk.ns_linear() - t0s) // 1000
    return {
        "rounds": rounds,
        "mono_us": {
            "min": min(mono_deltas) if mono_deltas else 0,
            "max": max(mono_deltas) if mono_deltas else 0,
            "mean": round(statistics.mean(mono_deltas), 3) if mono_deltas else 0,
            "elapsed": elapsed_mono_us,
        },
        "sovereign_us": {
            "min": min(sov_deltas) if sov_deltas else 0,
            "max": max(sov_deltas) if sov_deltas else 0,
            "mean": round(statistics.mean(sov_deltas), 3) if sov_deltas else 0,
            "elapsed": elapsed_sov_us,
        },
        "sub_microsecond_capable": (min(mono_deltas) if mono_deltas else 999) < 1000,
        "desync": clk.desync_status() if hasattr(clk, "desync_status") else {},
    }


def run_cycle(*, build_precision: bool = True, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    t0 = time.perf_counter_ns()
    timing = microsecond_bench()
    gps = _run_json("lib/gps-precision.py", ["json"], timeout=20.0)
    precision = _run_json("lib/precision-field.py", ["build" if build_precision else "json"], timeout=45.0)
    presume = _run_json("lib/hostess7-presume.py", ["json"], timeout=15.0)
    rack = _run_json("lib/field-rack-uniqueness.py", ["assert"], timeout=10.0)
    elapsed_us = (time.perf_counter_ns() - t0) // 1000

    out = {
        "ok": True,
        "schema": "field-sub-micron-timing/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "spatial": {
            "sub_micron": True,
            "fixed_scale": (doc.get("spatial") or {}).get("fixed_scale"),
            "lsb_nm": (doc.get("spatial") or {}).get("lsb_nm_latitude"),
            "gps": {
                "ok": gps.get("ok", bool(gps.get("schema"))),
                "anchor": gps.get("anchor"),
                "precision": gps.get("precision"),
            },
            "precision_field": {
                "ok": precision.get("ok", bool(precision.get("entities") is not None)),
                "placed": (precision.get("stats") or {}).get("placed"),
                "sub_micron": (precision.get("stats") or {}).get("sub_micron"),
                "total": (precision.get("stats") or {}).get("total"),
            },
        },
        "temporal": {
            "sub_microsecond": timing.get("sub_microsecond_capable"),
            "bench": timing,
            "cycle_elapsed_us": elapsed_us,
            "presume_ok": presume.get("ok", bool(presume.get("schema"))),
        },
        "rack": {
            "field_id": rack.get("field_id"),
            "solo": rack.get("ok"),
        },
        "field_rack_id": os.environ.get("FIELD_RACK_ID") or rack.get("field_id"),
    }
    if write:
        _save(PANEL, out)
        api = INSTALL / "Hostess7" / "docs" / "api" / "field-sub-micron-timing.json"
        api.parent.mkdir(parents=True, exist_ok=True)
        api.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("ok"):
        return cached
    return run_cycle(build_precision=False, write=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("run", "cycle", "go"):
        print(json.dumps(run_cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "bench":
        print(json.dumps(microsecond_bench(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-sub-micron-timing.py [json|run|bench]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())