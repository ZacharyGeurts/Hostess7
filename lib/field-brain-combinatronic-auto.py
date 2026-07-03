#!/usr/bin/env pythong
"""Auto brain combinatronics — snap before brain mirror; full optimal only when map missing."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-brain-combinatronic-auto-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _save_panel(doc: dict[str, Any]) -> None:
    path = PANEL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def auto_brain_combinatronic(*, force: bool = False, context: str = "brain") -> dict[str, Any]:
    """
    Brain-build hook: snap into live map first; fall back to optimal only when required.
    Typical brain mirror build: <25ms snap vs 16+ min full optimal.
    """
    t0 = time.perf_counter()
    live = _import_mod("live_map", "field-combinatronic-live-map.py")
    reb = _import_mod("g16_reb", "g16-combinatronic-rebalance.py")

    snap_out: dict[str, Any] = {"ok": False, "snapped": False}
    if live and hasattr(live, "snap"):
        snap_out = live.snap(force=force)

    if snap_out.get("snapped") and not force:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        out = {
            "schema": "field-brain-combinatronic-auto/v1",
            "updated": _now(),
            "ok": True,
            "context": context,
            "method": "snap",
            "live_combinatronic": True,
            "fast_path": bool(snap_out.get("fast_path")),
            "snap": snap_out,
            "elapsed_ms": elapsed_ms,
            "motto": "Brain combinatronic auto — live map snap, sovereign brain untouched.",
        }
        _save_panel(out)
        return out

    if snap_out.get("needs_full") or force:
        optimal_out: dict[str, Any] = {"ok": False}
        if reb and hasattr(reb, "optimal"):
            optimal_out = reb.optimal(full=force)
        if live and hasattr(live, "capture_placements"):
            live.capture_placements(source="brain_auto_optimal")
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        out = {
            "schema": "field-brain-combinatronic-auto/v1",
            "updated": _now(),
            "ok": bool(optimal_out.get("ok")),
            "context": context,
            "method": "optimal",
            "live_combinatronic": True,
            "snap": snap_out,
            "optimal": {
                "ok": optimal_out.get("ok"),
                "action": optimal_out.get("action"),
                "step_count": len(optimal_out.get("steps") or []),
            },
            "elapsed_ms": elapsed_ms,
            "motto": "Brain combinatronic auto — seeded live map from full optimal.",
        }
        _save_panel(out)
        return out

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    out = {
        "schema": "field-brain-combinatronic-auto/v1",
        "updated": _now(),
        "ok": bool(snap_out.get("ok")),
        "context": context,
        "method": "snap_partial",
        "snap": snap_out,
        "elapsed_ms": elapsed_ms,
    }
    _save_panel(out)
    return out


def panel() -> dict[str, Any]:
    doc = {}
    if PANEL.is_file():
        try:
            doc = json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    live = _import_mod("live_map", "field-combinatronic-live-map.py")
    live_panel = live.panel() if live and hasattr(live, "panel") else {}
    return {
        "schema": "field-brain-combinatronic-auto-panel/v1",
        "updated": _now(),
        "ok": True,
        "last_run": doc,
        "live_map": live_panel,
        "motto": "Auto brain combinatronics — snap first, optimal only when map demands it.",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "auto").strip().lower()
    force = "--force" in sys.argv or "--full" in sys.argv
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("auto", "brain", "run"):
        ctx = "brain"
        for i, a in enumerate(sys.argv[2:], start=2):
            if a == "--context" and i + 1 < len(sys.argv):
                ctx = sys.argv[i + 1]
        print(json.dumps(auto_brain_combinatronic(force=force, context=ctx), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["auto", "panel"], "flags": ["--force", "--full"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())