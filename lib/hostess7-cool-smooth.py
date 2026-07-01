#!/usr/bin/env pythong
"""Cool and smooth — important. Thermal headroom + timing + motion smoothness."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-cool-smooth-doctrine.json"
PANEL = STATE / "hostess7-cool-smooth-panel.json"


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"{name}_{path.stem}", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _axis_cool() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    thermal_doc = _load(INSTALL / "data" / "field-thermal-guard-doctrine.json", {})
    eye_doc = _load(INSTALL / "data/final-eye-plate-doctrine.json", {})
    thermal_py = INSTALL / "lib/field-thermal-guard.py"
    governor_py = INSTALL / "lib/thermal-governor.py"
    panel = _load(STATE / "field-thermal-guard-panel.json", {})
    cool_default = bool((eye_doc.get("eyeball") or {}).get("cool_default"))
    incremental = bool((thermal_doc.get("policy") or {}).get("incremental_redata_only"))
    ok = thermal_py.is_file() and incremental
    return {
        "id": "cool",
        "ok": ok,
        "thermal_guard": thermal_py.is_file(),
        "thermal_governor": governor_py.is_file(),
        "incremental_redata_only": incremental,
        "eye_cool_default": cool_default,
        "headroom_hint": (thermal_doc.get("metrics") or {}).get("speed_impact_normal_load"),
        "panel_ok": bool(panel.get("ok", True)) if panel else None,
    }


def _axis_smooth() -> dict[str, Any]:
    presume = _mod("presume", "lib/hostess7-presume.py")
    motion = _mod("motion", "lib/humanoid-motion-training.py")
    probe: dict[str, Any] = {}
    physics = bool(_load(INSTALL / "data/humanoid-motion-doctrine.json", {}).get("physics_mode"))
    if presume and hasattr(presume, "presume"):
        try:
            probe = presume.presume(8_000, label="cool_smooth_probe", alternate_id="sovereign_know")
        except Exception as exc:
            probe = {"error": str(exc)[:120]}
    on_point = bool(probe.get("resumed_on_point"))
    drift = int(probe.get("drift_us") or 0)
    motion_panel: dict[str, Any] = {}
    if motion and hasattr(motion, "build_panel"):
        try:
            motion_panel = motion.build_panel(write=False)
        except Exception:
            pass
    ok = on_point and physics
    return {
        "id": "smooth",
        "ok": ok,
        "presume_on_point": on_point,
        "drift_us": drift,
        "physics_mode": physics,
        "motion_panel_ok": bool(motion_panel.get("ok", True)) if motion_panel else None,
        "no_busy_wait": bool(_load(INSTALL / "data/hostess7-presume-doctrine.json", {}).get("no_busy_wait")),
    }


def verify_cool_smooth(*, write_panel: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    cool = _axis_cool()
    smooth = _axis_smooth()
    rep = {
        "schema": "hostess7-cool-smooth/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "important": True,
        "cool": cool,
        "smooth": smooth,
        "cool_and_smooth": cool.get("ok") and smooth.get("ok"),
        "ok": cool.get("ok") and smooth.get("ok"),
    }
    if write_panel:
        _save(PANEL, rep)
    return rep


def explain_cool_smooth() -> str:
    doc = _load(DOCTRINE, {})
    panel = verify_cool_smooth(write_panel=False)
    lines = [
        str(doc.get("motto") or "Cool and smooth is important."),
        "**Cool** — thermal headroom, incremental redata, backoff before blast, eye cool_default, no busy-wait burn.",
        "**Smooth** — presume resumed_on_point, humanoid physics lattice, parallel panels, calm operator surfaces.",
        f"Status: cool={panel.get('cool', {}).get('ok')} smooth={panel.get('smooth', {}).get('ok')}.",
        "War Soldiers still run cool and smooth — jank and thermal blast are not excused.",
    ]
    return "\n\n".join(lines)


def build_panel(*, write: bool = True) -> dict[str, Any]:
    return verify_cool_smooth(write_panel=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "verify", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("explain", "teach"):
        print(explain_cool_smooth())
        return 0
    print(json.dumps({"error": "usage: hostess7-cool-smooth.py [panel|verify|explain]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())