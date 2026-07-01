#!/usr/bin/env pythong
"""NEXUS panel plugin registry — unlimited installable plugins with per-tab dock slots."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PLUGINS_DIR = INSTALL / "plugins"
PLUGIN_STATE = STATE / "nexus-plugins.json"
PANEL_JSON = STATE / "threat-panel.json"

VIEW_IDS = (
    "command", "us", "honor", "field-rf", "monitor", "inspect", "library",
    "host-attack", "spiderweb", "dossier", "human-dossier", "research", "settings", "logs",
)


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _plugin_state() -> dict[str, Any]:
    doc = _load_json(PLUGIN_STATE, {"plugins": {}, "updated": ""})
    if not isinstance(doc.get("plugins"), dict):
        doc["plugins"] = {}
    return doc


def _save_plugin_state(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save_json(PLUGIN_STATE, doc)


def _discover_manifests() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not PLUGINS_DIR.is_dir():
        return rows
    for child in sorted(PLUGINS_DIR.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _load_json(manifest_path, {})
        if not manifest.get("id"):
            manifest["id"] = child.name
        manifest["_dir"] = str(child)
        manifest["_manifest"] = str(manifest_path)
        rows.append(manifest)
    return rows


def _load_plugin_module(plugin_dir: Path, entry: str) -> Any | None:
    script = plugin_dir / entry
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"nexus_plugin_{plugin_dir.name}", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plugin_enabled(manifest: dict[str, Any], state: dict[str, Any]) -> bool:
    pid = str(manifest.get("id") or "")
    overrides = state.get("plugins") or {}
    if pid in overrides:
        return bool(overrides[pid].get("enabled"))
    return manifest.get("enabled", True) is not False


def _slots_ok(manifest: dict[str, Any], view_id: str) -> bool:
    slots = manifest.get("slots") or ["*"]
    if "*" in slots or "all" in slots:
        return True
    return view_id in slots


def discover_registry() -> list[dict[str, Any]]:
    state = _plugin_state()
    registry: list[dict[str, Any]] = []
    for manifest in _discover_manifests():
        pid = str(manifest.get("id") or "")
        registry.append({
            "id": pid,
            "name": manifest.get("name") or pid,
            "version": manifest.get("version") or "0.0.0",
            "description": manifest.get("description") or "",
            "author": manifest.get("author") or "",
            "slots": manifest.get("slots") or ["*"],
            "client": manifest.get("client") or "",
            "enabled": _plugin_enabled(manifest, state),
            "builtin": manifest.get("builtin", False),
        })
    return registry


def run_plugin_snapshot(manifest: dict[str, Any], panel_doc: dict[str, Any]) -> dict[str, Any]:
    plugin_dir = Path(manifest.get("_dir") or "")
    entry = str(manifest.get("entry") or "plugin.py")
    mod = _load_plugin_module(plugin_dir, entry)
    if mod and hasattr(mod, "panel_snapshot"):
        try:
            out = mod.panel_snapshot(panel_doc)
            if isinstance(out, dict):
                return out
        except Exception as exc:
            return {"error": str(exc), "views": {}}
    return {"views": {}}


def build_panel_plugins(panel_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    panel_doc = panel_doc if isinstance(panel_doc, dict) else {}
    if not panel_doc and PANEL_JSON.is_file():
        panel_doc = _load_json(PANEL_JSON, {})

    state = _plugin_state()
    registry = discover_registry()
    outputs: dict[str, Any] = {}
    enabled_ids: list[str] = []

    for row in registry:
        if not row.get("enabled"):
            continue
        pid = row["id"]
        manifest = next(
            (m for m in _discover_manifests() if str(m.get("id")) == pid),
            None,
        )
        if not manifest:
            continue
        enabled_ids.append(pid)
        outputs[pid] = run_plugin_snapshot(manifest, panel_doc)

    return {
        "schema": "nexus.plugins/v1",
        "updated": _now(),
        "view_ids": list(VIEW_IDS),
        "registry": registry,
        "enabled": enabled_ids,
        "outputs": outputs,
        "slot": "bottom",
        "unlimited": True,
    }


def merge_into_panel(path: Path | None = None) -> dict[str, Any]:
    path = path or PANEL_JSON
    try:
        raw = path.read_text(encoding="utf-8")
        doc = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(doc, dict):
        return {}
    doc["plugins"] = build_panel_plugins(doc)
    _save_json(path, doc)
    return doc.get("plugins") or {}


def set_plugin_enabled(plugin_id: str, enabled: bool) -> dict[str, Any]:
    state = _plugin_state()
    plugins = state.setdefault("plugins", {})
    plugins[plugin_id] = {"enabled": bool(enabled), "ts": _now()}
    _save_plugin_state(state)
    return {"ok": True, "id": plugin_id, "enabled": bool(enabled)}


def panel_json() -> dict[str, Any]:
    return build_panel_plugins()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "registry":
        print(json.dumps({"registry": discover_registry(), "updated": _now()}, ensure_ascii=False))
        return 0
    if cmd == "merge" and len(sys.argv) >= 3:
        merge_into_panel(Path(sys.argv[2]))
        print(json.dumps({"ok": True, "merged": sys.argv[2]}, ensure_ascii=False))
        return 0
    if cmd == "merge":
        merge_into_panel()
        print(json.dumps({"ok": True, "merged": str(PANEL_JSON)}, ensure_ascii=False))
        return 0
    if cmd == "enable" and len(sys.argv) >= 3:
        en = sys.argv[2].strip().lower() in ("1", "true", "on", "yes")
        pid = sys.argv[3] if len(sys.argv) >= 4 else ""
        if not pid:
            print(json.dumps({"error": "usage: nexus-plugins.py enable on|off PLUGIN_ID"}, ensure_ascii=False))
            return 1
        print(json.dumps(set_plugin_enabled(pid, en), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: nexus-plugins.py [json|registry|merge [path]|enable on|off PLUGIN_ID]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())