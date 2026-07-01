#!/usr/bin/env python3
"""Body component wholes — prioritized, independent lanes with last-known + map fallbacks."""
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
DOCTRINE = INSTALL / "data" / "field-body-component-wholes-doctrine.json"
REGISTRY = STATE / "field-body-component-registry.json"
PANEL = STATE / "field-body-component-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(rel: str, name: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _doctrine() -> dict[str, Any]:
    return _load_json(DOCTRINE, {"components": []})


def _empty_registry() -> dict[str, Any]:
    return {"schema": "field-body-component-registry/v1", "components": {}, "updated": _now()}


def _load_registry() -> dict[str, Any]:
    return _load_json(REGISTRY, _empty_registry())


def _visibility_mode(visibility: float, useful: float, hold: float) -> str:
    if visibility >= useful:
        return "live"
    if visibility >= hold:
        return "degraded"
    return "last_known_map"


def update_component(
    component_id: str,
    *,
    live: dict[str, Any] | None = None,
    visibility: float | None = None,
    source: str = "probe",
) -> dict[str, Any]:
    """Store last_known when visibility is useful; always keep map receipt."""
    doc = _doctrine()
    spec = next((c for c in (doc.get("components") or []) if c.get("id") == component_id), None)
    if not spec:
        return {"ok": False, "error": "unknown_component", "id": component_id}

    useful = float(spec.get("useful_visibility") or doc.get("visibility", {}).get("useful_floor") or 0.55)
    hold = float(spec.get("hold_visibility") or doc.get("visibility", {}).get("hold_floor") or 0.35)
    vis = 0.0 if visibility is None else max(0.0, min(1.0, float(visibility)))
    mode = _visibility_mode(vis, useful, hold)

    reg = _load_registry()
    reg.setdefault("components", {})
    row = reg["components"].get(component_id) or {
        "id": component_id,
        "priority": spec.get("priority"),
        "label": spec.get("label"),
        "whole": True,
        "independent": True,
        "last_known": None,
        "map": None,
    }

    map_receipt = {
        "ts": _now(),
        "mode": mode,
        "visibility": round(vis, 3),
        "useful_floor": useful,
        "hold_floor": hold,
        "fallback": spec.get("map_fallback"),
        "source": source,
    }
    if live:
        map_receipt["live_keys"] = sorted(live.keys())[:24]
    row["map"] = map_receipt
    row["live"] = live
    row["visibility"] = round(vis, 3)
    row["mode"] = mode
    row["supportive"] = mode != "last_known_map" or row.get("last_known") is not None

    if mode == "live" and live:
        row["last_known"] = {"ts": _now(), "snapshot": live, "visibility": round(vis, 3)}
    elif mode == "degraded" and live:
        row.setdefault("last_known", {"ts": _now(), "snapshot": live, "visibility": round(vis, 3)})

    reg["components"][component_id] = row
    reg["updated"] = _now()
    _save_json(REGISTRY, reg)
    return {"ok": True, "component": row}


def resolve_component(component_id: str) -> dict[str, Any]:
    """Return live, degraded, or last_known+map — each component whole on its own."""
    reg = _load_registry()
    row = (reg.get("components") or {}).get(component_id)
    doc = _doctrine()
    spec = next((c for c in (doc.get("components") or []) if c.get("id") == component_id), {})
    if not row:
        return {"ok": False, "error": "no_registry_row", "id": component_id, "spec": spec}

    mode = row.get("mode") or "unknown"
    out: dict[str, Any] = {
        "schema": "field-body-component-resolve/v1",
        "ok": True,
        "id": component_id,
        "priority": row.get("priority") or spec.get("priority"),
        "label": row.get("label") or spec.get("label"),
        "whole": True,
        "independent": True,
        "mode": mode,
        "visibility": row.get("visibility"),
        "supportive": row.get("supportive", True),
        "map": row.get("map"),
    }
    if mode == "live":
        out["snapshot"] = row.get("live") or row.get("last_known", {}).get("snapshot")
        out["serving"] = "live"
    elif mode == "degraded":
        out["snapshot"] = row.get("live") or row.get("last_known", {}).get("snapshot")
        out["serving"] = "degraded_live"
        out["last_known"] = row.get("last_known")
    else:
        out["snapshot"] = (row.get("last_known") or {}).get("snapshot")
        out["serving"] = "last_known_map"
        out["last_known"] = row.get("last_known")
    return out


def _probe_eye() -> tuple[dict[str, Any], float]:
    maint = _import_mod("final-eye-maintenance.py", "fbcw_eye_maint")
    if maint and hasattr(maint, "probe_eye_visibility"):
        probe = maint.probe_eye_visibility()
        return probe, float(probe.get("visibility") or 0.5)
    return {"ok": False}, 0.5


def _probe_nav() -> tuple[dict[str, Any], float]:
    nav = _import_mod("final-eye-gps-nav.py", "fbcw_nav")
    if not nav or not hasattr(nav, "nav_snapshot"):
        return {"ok": False}, 0.0
    snap = nav.nav_snapshot()
    if not snap.get("ok"):
        return snap, 0.2
    acc = snap.get("accuracy_m")
    if acc is None:
        vis = 0.65
    else:
        vis = max(0.0, min(1.0, 1.0 - float(acc) / 100.0))
    if snap.get("primary_source") == "gpsd":
        vis = max(vis, 0.75)
    return snap, vis


def _probe_lane(mod_name: str, fn: str, body: dict[str, Any] | None = None, *, timeout_sec: float = 2.5) -> tuple[dict[str, Any], float]:
    import subprocess

    body_line = "body = None" if body is None else f"body = {json.dumps(body)}"
    script = (
        "import importlib.util, json, os, sys\n"
        f"os.environ['NEXUS_INSTALL_ROOT'] = {json.dumps(str(INSTALL))}\n"
        f"os.environ['NEXUS_STATE_DIR'] = {json.dumps(str(STATE))}\n"
        f"path = {json.dumps(str(INSTALL / 'lib' / mod_name))}\n"
        f"fn = {json.dumps(fn)}\n"
        f"{body_line}\n"
        "spec = importlib.util.spec_from_file_location('probe', path)\n"
        "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
        "out = getattr(mod, fn)(body) if body is not None else getattr(mod, fn)()\n"
        "print(json.dumps(out))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(INSTALL),
        )
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or "probe_failed")[:200]}, 0.2
        out = json.loads((proc.stdout or "{}").strip() or "{}")
        ok = bool(out.get("ok", True))
        return out, 0.7 if ok else 0.35
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "timeout": True}, 0.2


def _probe_hostess7() -> tuple[dict[str, Any], float]:
    h7 = _import_mod("hostess7-self-maintenance.py", "fbcw_hostess7")
    if h7 and hasattr(h7, "probe_hostess7"):
        try:
            probe = h7.probe_hostess7()
            vis = float(probe.get("visibility") or probe.get("self_maintenance", {}).get("visibility") or 0.7)
            return probe, vis
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 0.4
    return {"ok": False, "error": "hostess7_self_maintenance_missing"}, 0.3


def refresh_all() -> dict[str, Any]:
    """Probe every prioritized component; update registry with last_known + map."""
    results: list[dict[str, Any]] = []

    h7_live, h7_vis = _probe_hostess7()
    results.append(update_component("hostess7", live=h7_live, visibility=h7_vis, source="hostess7-self-maintenance"))

    eye_live, eye_vis = _probe_eye()
    results.append(update_component("eye", live=eye_live, visibility=eye_vis, source="final-eye-maintenance"))

    nav_live, nav_vis = _probe_nav()
    results.append(update_component("nav", live=nav_live, visibility=nav_vis, source="final-eye-gps-nav"))

    sense_live, sense_vis = _probe_lane("hostess7-sense-core.py", "posture")
    results.append(update_component("ear", live=sense_live, visibility=sense_vis, source="hostess7-sense"))
    results.append(update_component("mouth", live=sense_live, visibility=sense_vis, source="hostess7-sense"))

    motion_live, motion_vis = _probe_lane("hostess7-body-core.py", "body_status")
    results.append(update_component("motion", live=motion_live, visibility=motion_vis, source="hostess7-body"))

    audio_live, audio_vis = _probe_lane("field-audio-dac-chamber.py", "dac_probe")
    results.append(update_component("audio", live=audio_live, visibility=audio_vis, source="audio-dac"))

    spatial_mod = _import_mod("field-look-spatial.py", "fbcw_spatial")
    spatial_live: dict[str, Any] = {"ok": False}
    spatial_vis = 0.4
    if spatial_mod and hasattr(spatial_mod, "status"):
        try:
            spatial_live = spatial_mod.status()
            vc = int(spatial_live.get("view_count") or 0)
            spatial_vis = min(1.0, 0.45 + vc * 0.02)
        except Exception:
            pass
    results.append(update_component("spatial", live=spatial_live, visibility=spatial_vis, source="field-look-spatial"))

    corr_live, corr_vis = _probe_lane("field-body-system.py", "correlate_body", timeout_sec=4.0)
    if corr_live.get("lane_ratio") is not None:
        corr_vis = float(corr_live.get("lane_ratio") or corr_vis)
    results.append(update_component("correlate", live=corr_live, visibility=corr_vis, source="field-body-system"))

    return {"ok": True, "updated": _now(), "components": results}


def advisory_for_truth_gate(*, skip_refresh: bool = False) -> dict[str, Any]:
    """Extra counsel for truth gate — advisory only, never defeats pass_ok."""
    if not skip_refresh:
        refresh_all()
    reg = _load_registry()
    components = reg.get("components") or {}
    resolved = [resolve_component(cid) for cid in sorted(components, key=lambda x: components[x].get("priority", 99))]
    live_count = sum(1 for r in resolved if r.get("mode") == "live")
    mapped_count = sum(1 for r in resolved if r.get("mode") == "last_known_map")
    degraded_count = sum(1 for r in resolved if r.get("mode") == "degraded")
    hostess = resolve_component("hostess7")
    eye = resolve_component("eye")
    nav = resolve_component("nav")
    return {
        "schema": "field-truth-gate-advisory/v1",
        "advisory_only": True,
        "never_defeats_gate": True,
        "ts": _now(),
        "component_count": len(resolved),
        "live_count": live_count,
        "degraded_count": degraded_count,
        "mapped_count": mapped_count,
        "hostess7_priority": hostess.get("priority") or 1,
        "hostess7_self_maintained": (hostess.get("snapshot") or {}).get("self_maintained"),
        "hostess7_self_maintenance_due": (hostess.get("snapshot") or {}).get("self_maintenance", {}).get("due_count"),
        "eye_maintenance_due": (eye.get("snapshot") or {}).get("maintenance", {}).get("due_count"),
        "eye_vision_active": (eye.get("snapshot") or {}).get("maintenance", {}).get("vision_active"),
        "nav_mode": nav.get("mode"),
        "components": resolved,
        "counsel": (
            f"{live_count} lanes live, {degraded_count} degraded, {mapped_count} on last-known map. "
            "Advisory enriches share and counsel — Ironclad gate unchanged."
        ),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    refresh_all()
    doc = _doctrine()
    reg = _load_registry()
    components = sorted(
        (resolve_component(cid) for cid in (reg.get("components") or {})),
        key=lambda x: x.get("priority") or 99,
    )
    panel = {
        "schema": "field-body-component-panel/v1",
        "ok": True,
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "truth_gate_policy": doc.get("truth_gate_policy"),
        "visibility": doc.get("visibility"),
        "components": components,
        "priorities": [{"id": c.get("id"), "priority": c.get("priority"), "mode": c.get("mode")} for c in components],
        "advisory": advisory_for_truth_gate(skip_refresh=True),
        "updated": _now(),
    }
    if write:
        _save_json(PANEL, panel)
    return panel


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "refresh":
        print(json.dumps(refresh_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) >= 3:
        print(json.dumps(resolve_component(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "advisory":
        print(json.dumps(advisory_for_truth_gate(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: field-body-component-wholes.py [status|refresh|resolve ID|advisory]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())