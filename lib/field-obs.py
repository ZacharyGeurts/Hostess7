#!/usr/bin/env pythong
"""Legacy Field OBS shim — delegates to Broadcaster (NEXUS C2 capture)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(__file__).resolve().parent.parent


def _broadcaster() -> Any:
    path = Path(__file__).resolve().parent / "field-broadcaster.py"
    spec = importlib.util.spec_from_file_location("field_broadcaster_shim", path)
    if not spec or not spec.loader:
        raise ImportError("field-broadcaster.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _legacy_map(doc: dict[str, Any]) -> dict[str, Any]:
    if not doc or doc.get("schema", "").startswith("field-obs"):
        return doc
    out = dict(doc)
    out["schema"] = "field-obs/v2"
    out["product"] = "Broadcaster"
    out["legacy_redirect"] = "/field-broadcaster"
    out["routes"] = {"panel": "/field-broadcaster", "api": "/api/field-broadcaster", "legacy": "/field-obs"}
    if "obs" not in out and out.get("engine"):
        out["obs"] = {
            "running": out["engine"].get("running"),
            "field_plugin_installed": out["engine"].get("plugin_installed"),
            "filters": out["engine"].get("filters"),
            "threat_summary": (out.get("scene_guard") or {}).get("threat_summary"),
        }
    return out


def posture() -> dict[str, Any]:
    return _legacy_map(_broadcaster().posture())


def launch(**kwargs: Any) -> dict[str, Any]:
    return _broadcaster().launch(**kwargs)


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    return _legacy_map(_broadcaster().save_settings(patch))


def us_obs_slice() -> dict[str, Any]:
    bc = _broadcaster().us_broadcaster_slice()
    bc["schema"] = "us-obs-field/v3"
    bc["jump"] = "field-broadcaster"
    return bc


def main() -> int:
    bc = _broadcaster()
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "launch":
        print(json.dumps(launch(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "record":
        print(json.dumps(launch(record=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "virtualcam":
        print(json.dumps(launch(virtualcam=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "studio":
        print(json.dumps(launch(studio=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    if cmd == "us":
        print(json.dumps(us_obs_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build":
        print(json.dumps(_legacy_map(bc.posture()), ensure_ascii=False, indent=2))
        return 0
    return bc.main()


if __name__ == "__main__":
    raise SystemExit(main())