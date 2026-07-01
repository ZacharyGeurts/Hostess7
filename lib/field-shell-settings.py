#!/usr/bin/env pythong
"""Field OS shell settings — taskbar, display scale, theme, wallpaper."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SETTINGS = STATE / "field-shell-settings.json"
DOCTRINE = INSTALL / "data" / "field-host-desktop-doctrine.json"

DESKTOP_SCALE_DEFAULT = 125
DESKTOP_SCALE_MIN = 50
DESKTOP_SCALE_MAX = 200

DEFAULTS: dict[str, Any] = {
    "taskbar_auto_hide": False,
    "taskbar_peek": True,
    "desktop_icon_size": 50,
    "ui_scale": DESKTOP_SCALE_DEFAULT,
    "ammoos_theme": "nexus_c2",
    "theme_override": "",
    "wallpaper": "default",
    "sort_desktop": "name",
    "show_desktop_icons": True,
    "fullscreen_programs": True,
    "fullscreen_desktop": True,
    "alt_tab_enabled": True,
    "queen_browser_only": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _display_modes() -> list[dict[str, Any]]:
    script = INSTALL / "lib" / "field-display-open.py"
    if script.is_file():
        try:
            proc = subprocess.run(
                [os.environ.get("PYTHON", "pythong"), str(script), "json"],
                capture_output=True,
                text=True,
                timeout=12,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            if proc.returncode == 0:
                doc = json.loads(proc.stdout or "{}")
                return doc.get("displays") or []
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    return [{"id": "default", "name": "Default display", "backend": "unknown", "connected": True, "primary": True}]


def _hardware_summary() -> dict[str, Any]:
    script = INSTALL / "lib" / "field-hardware-probe.py"
    if not script.is_file():
        return {"ok": False, "error": "hardware_probe_missing"}
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "pythong"), str(script), "json"],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0:
            doc = json.loads(proc.stdout or "{}")
            doc["ok"] = True
            return doc
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"ok": False, "error": "hardware_probe_failed"}


def _version() -> str:
    common = INSTALL / "lib" / "nexus-common.sh"
    if common.is_file():
        try:
            proc = subprocess.run(
                ["bash", "-c", f'source "{common}" && echo -n "$NEXUS_VERSION"'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            ver = (proc.stdout or "").strip()
            if ver:
                return ver
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "0.9.0"


def _doctrine_policy() -> dict[str, Any]:
    return (_load(DOCTRINE, {}).get("policy") or {}) if DOCTRINE.is_file() else {}


def _doctrine_defaults() -> dict[str, Any]:
    policy = _doctrine_policy()
    out: dict[str, Any] = {}
    if "show_desktop_icons" in policy:
        out["show_desktop_icons"] = bool(policy.get("show_desktop_icons"))
    if policy.get("desktop_icons_in_start"):
        out["show_desktop_icons"] = False
    if policy.get("desktop_ui_scale_default") is not None:
        out["ui_scale"] = int(policy["desktop_ui_scale_default"])
    if policy.get("desktop_icon_size_default") is not None:
        out["desktop_icon_size"] = int(policy["desktop_icon_size_default"])
    return out


def desktop_scale_posture(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Unified desktop scale slice — shell, Lock, OBS, control panel."""
    s = {**DEFAULTS, **_doctrine_defaults(), **(settings or {})}
    pct = int(s.get("ui_scale") or DESKTOP_SCALE_DEFAULT)
    pct = max(DESKTOP_SCALE_MIN, min(DESKTOP_SCALE_MAX, pct))
    scale = round(pct / 100.0, 3)
    icon = int(s.get("desktop_icon_size") or 50)
    icon = max(24, min(96, icon))
    return {
        "ui_scale_pct": pct,
        "scale_factor": scale,
        "icon_size_px": icon,
        "min_pct": DESKTOP_SCALE_MIN,
        "max_pct": DESKTOP_SCALE_MAX,
        "default_pct": DESKTOP_SCALE_DEFAULT,
        "quality": True,
    }


def posture() -> dict[str, Any]:
    saved = _load(SETTINGS, {})
    settings = {**DEFAULTS, **_doctrine_defaults(), **{k: v for k, v in saved.items() if k in DEFAULTS}}
    displays = _display_modes()
    hw = _hardware_summary()
    return {
        "schema": "field-shell-settings/v1",
        "ts": _now(),
        "ok": True,
        "settings": settings,
        "defaults": DEFAULTS,
        "desktop_scale": desktop_scale_posture(settings),
        "displays": displays,
        "hardware": hw,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "hostname": platform.node(),
        },
        "version": _version(),
        "control_panel": {
            "display": True,
            "theme": True,
            "themes_index": "/control-panel?tab=themes",
            "hardware": False,
            "system": True,
            "personalization": False,
            "surface_locked": True,
            "operator_only": ["ui_scale", "ammoos_theme", "restart"],
        },
        "sovereignty": _sovereignty_posture(),
    }


def _sovereignty_posture() -> dict[str, Any]:
    script = INSTALL / "lib" / "queen-ammoos-sovereignty.py"
    if not script.is_file():
        script = Path(__file__).resolve().parent / "queen-ammoos-sovereignty.py"
    if not script.is_file():
        return {"ok": False, "skipped": True}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("queen_ammoos_sov_shell", script)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.posture()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _filter_patch(patch: dict[str, Any]) -> dict[str, Any]:
    try:
        import importlib.util

        mod_path = INSTALL / "lib" / "queen-settings-surface.py"
        if not mod_path.is_file():
            mod_path = Path(__file__).resolve().parent / "queen-settings-surface.py"
        if mod_path.is_file():
            spec = importlib.util.spec_from_file_location("queen_settings_surface", mod_path)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            return mod.shell_patch_allowed(patch)
    except Exception:
        pass
    return dict(patch or {})


def apply_patch(patch: dict[str, Any]) -> dict[str, Any]:
    patch = _filter_patch(patch or {})
    current = _load(SETTINGS, {})
    merged = {**DEFAULTS, **{k: v for k, v in current.items() if k in DEFAULTS}}
    for key, val in (patch or {}).items():
        if key not in DEFAULTS:
            continue
        if key == "ui_scale":
            merged[key] = max(DESKTOP_SCALE_MIN, min(DESKTOP_SCALE_MAX, int(val)))
        elif key == "desktop_icon_size":
            merged[key] = max(24, min(96, int(val)))
        elif key == "taskbar_auto_hide":
            merged[key] = bool(val)
        elif key == "taskbar_peek":
            merged[key] = bool(val)
        elif key == "show_desktop_icons":
            merged[key] = bool(val)
        elif key == "fullscreen_programs":
            merged[key] = bool(val)
        elif key == "alt_tab_enabled":
            merged[key] = bool(val)
        elif key in ("ammoos_theme", "theme_override", "wallpaper", "sort_desktop"):
            merged[key] = str(val or "")
    doc = {"schema": "field-shell-settings/v1", "ts": _now(), **merged}
    _save_atomic(SETTINGS, doc)
    out = posture()
    out["applied"] = list(patch.keys()) if patch else []
    return out


def set_resolution(display_id: str, resolution: str) -> dict[str, Any]:
    display_id = (display_id or "").strip()
    resolution = (resolution or "").strip()
    if not resolution or "x" not in resolution:
        return {"ok": False, "error": "invalid_resolution"}
    if not display_id:
        displays = _display_modes()
        primary = next((d for d in displays if d.get("primary")), displays[0] if displays else None)
        display_id = str((primary or {}).get("id") or "default")
    if display_id in ("default", "wayland-primary"):
        return {
            "ok": True,
            "display_id": display_id,
            "resolution": resolution,
            "applied": False,
            "message": "Resolution change recorded — apply via host display settings on Wayland.",
        }
    try:
        proc = subprocess.run(
            ["xrandr", "--output", display_id, "--mode", resolution.split("@", 1)[0]],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "display_id": display_id,
            "resolution": resolution,
            "applied": ok,
            "stderr": (proc.stderr or "").strip()[:400] if not ok else "",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        raw = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[2] if len(sys.argv) > 2 else "{}")
        try:
            patch = json.loads(raw or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "invalid_json"}))
            return 1
        print(json.dumps(apply_patch(patch), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolution" and len(sys.argv) > 3:
        print(json.dumps(set_resolution(sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-shell-settings.py [json|apply|resolution DISPLAY MODE]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())