#!/usr/bin/env pythong
"""CHIPS presume pathing — chips ARE truth; direct paths, clock-stop video sync, no loss."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-chips-presume-path-doctrine.json"
PANEL = STATE / "field-chips-presume-path-panel.json"
BATTERY = STATE / "field-chips-presume-path.json"
IRONCLAD_CITE = "ironclad:chips:3"
FAST_PATH_MS = 12


def _now() -> str:
    global _CLOCK
    if _CLOCK is None:
        p = INSTALL / "lib" / "sovereign-clock.py"
        s = importlib.util.spec_from_file_location("sov_clk_pp", p)
        if s and s.loader:
            _CLOCK = importlib.util.module_from_spec(s)
            s.loader.exec_module(_CLOCK)
    if _CLOCK and hasattr(_CLOCK, "utc_z"):
        return _CLOCK.utc_z()
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_CLOCK = None


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _kind(chip: dict[str, Any]) -> str:
    return str(chip.get("kind") or chip.get("family") or "guest_cpu").lower()


def direct_path_for_chip(chip: dict[str, Any], *, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Chip IS the path — route from die truth, never statistical presumption."""
    rules = rules or (_doctrine().get("path_rules") or {})
    cid = str(chip.get("id") or chip.get("chip_id") or "")
    kind = _kind(chip)
    rule = rules.get(kind) or rules.get("guest_cpu") or {}
    suffix = str(rule.get("path_suffix") or "direct_tick")
    family = str(chip.get("family") or kind)
    path_id = f"direct:{family}:{suffix}"
    heat = str(rule.get("heat") or "cool")
    return {
        "chip_id": cid,
        "path_id": path_id,
        "label": chip.get("label") or cid,
        "family": family,
        "kind": kind,
        "presume": False,
        "chip_is_truth": True,
        "direct": True,
        "integrity": "lossless",
        "heat_class": heat,
        "low_heat": heat in ("cool", "low"),
        "clock_stop": bool(rule.get("clock_stop")),
        "ironclad_cite": IRONCLAD_CITE,
    }


def clock_stop_cycle(
    *,
    target_hz: float = 60.0,
    system: str = "",
    phase: str = "frame_boundary",
) -> dict[str, Any]:
    """Pick sovereign clock cycle stop point — sync video/frame on the far end."""
    clock_doc: dict[str, Any] = {}
    if _CLOCK is None:
        _now()
    if _CLOCK and hasattr(_CLOCK, "know"):
        try:
            clock_doc = _CLOCK.know()
        except Exception:
            clock_doc = {}
    cycle = int(clock_doc.get("cycle") or 0)
    ns = int(clock_doc.get("linear_ns") or time.monotonic_ns())
    frame_ns = int(1_000_000_000 / max(1.0, target_hz))
    stop_cycle = cycle + max(1, int(frame_ns / 16_666_667))
    stop_ns = ((ns // frame_ns) + 1) * frame_ns
    return {
        "schema": "field-chips-clock-stop/v1",
        "updated": _now(),
        "target_hz": target_hz,
        "system": system or None,
        "phase": phase,
        "sovereign_cycle": cycle,
        "stop_cycle": stop_cycle,
        "stop_ns": stop_ns,
        "frame_ns": frame_ns,
        "synced": bool(clock_doc.get("synced", True)),
        "integrity": "lossless",
        "motto": "Clock stop at frame boundary — video and CHIPS share one sovereign tick.",
    }


def build_presume_paths(chips: list[dict[str, Any]], *, target_hz: float = 60.0) -> dict[str, Any]:
    """Direct paths for every chip — smaller band, less heat, no guess weights."""
    t0 = time.perf_counter()
    doctrine = _doctrine()
    policy = doctrine.get("policy") or {}
    rules = doctrine.get("path_rules") or {}
    paths: list[dict[str, Any]] = []
    for i, chip in enumerate(chips):
        row = direct_path_for_chip(chip, rules=rules)
        row["slot"] = i
        row["sort_slot"] = i + 1
        if row.get("clock_stop"):
            row["clock_stop_point"] = clock_stop_cycle(target_hz=target_hz, system=str(chip.get("system") or ""))
        paths.append(row)

    band = int(policy.get("narrow_band_width") or 8)
    paths.sort(key=lambda p: (0 if p.get("low_heat") else 1, p.get("sort_slot") or 999))
    for rank, p in enumerate(paths[:band]):
        p["hot_band"] = True
        p["band_rank"] = rank + 1

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    fp = hashlib.sha256(",".join(f"{p['chip_id']}:{p['path_id']}" for p in paths[:256]).encode()).hexdigest()[:20]
    return {
        "schema": "field-chips-presume-path/v1",
        "updated": _now(),
        "ok": True,
        "presume": False,
        "chip_is_truth": True,
        "direct_path_only": True,
        "path_count": len(paths),
        "hot_band_width": band,
        "paths": paths,
        "fingerprint": fp,
        "clock_stop": clock_stop_cycle(target_hz=target_hz),
        "layer_above_ironclad": doctrine.get("layer_above_ironclad"),
        "ironclad_citation": IRONCLAD_CITE,
        "elapsed_ms": elapsed_ms,
        "fast_path": elapsed_ms <= FAST_PATH_MS,
        "motto": doctrine.get("motto"),
    }


def publish_panel(*, write_battery: bool = True) -> dict[str, Any]:
    iron = STATE / "field-ironclad-chips-combinatorics.json"
    chips_doc = _load(iron, {})
    chips = list(chips_doc.get("chips") or [])
    battery = build_presume_paths(chips)
    panel = {
        "schema": "field-chips-presume-path-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok", True),
        "path_count": battery.get("path_count"),
        "hot_band_width": battery.get("hot_band_width"),
        "fingerprint": battery.get("fingerprint"),
        "layer_above_ironclad": battery.get("layer_above_ironclad"),
        "clock_stop": battery.get("clock_stop"),
        "elapsed_ms": battery.get("elapsed_ms"),
        "motto": battery.get("motto"),
    }
    if write_battery:
        _save(BATTERY, battery)
        _save(PANEL, panel)
    return {"ok": True, "panel": panel, "battery": battery}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json"):
        print(json.dumps(publish_panel().get("panel") or {}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("paths", "build"):
        iron = _load(STATE / "field-ironclad-chips-combinatorics.json", {})
        print(json.dumps(build_presume_paths(list(iron.get("chips") or [])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "clock-stop":
        hz = 60.0
        if len(sys.argv) > 2:
            try:
                hz = float(sys.argv[2])
            except ValueError:
                pass
        print(json.dumps(clock_stop_cycle(target_hz=hz), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["panel", "paths", "clock-stop"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())