#!/usr/bin/env pythong
"""OBS Studio engine — binary resolve, portable harden, launch (used by Broadcaster)."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
FIELD = Path(os.environ.get("OBS_FIELD_ROOT", os.environ.get("BROADCASTER_FIELD_ROOT", SG / "OBS-Field")))
DOCTRINE = FIELD / "data" / "field-obs-doctrine.json"
TIERS = FIELD / "data" / "field-obs-ui-tiers.json"
G16_TOOLCHAIN = FIELD / "data" / "g16-field-obs-toolchain.json"
HARDEN = FIELD / "forge" / "field-obs-harden.py"
BUILD_SCRIPT = FIELD / "build-field-obs.sh"
PANEL = STATE / "field-obs-panel.json"
PORTABLE = Path(os.environ.get("FIELD_BROADCASTER_PORTABLE_DIR", os.environ.get("FIELD_OBS_PORTABLE_DIR", str(STATE / "field-obs-portable"))))
SETTINGS = STATE / "field-obs-settings.json"
RECORDINGS = PORTABLE / "recordings"
from sg_paths import grok16_root

GROK16 = grok16_root()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _guest_os() -> str:
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system:
        return "darwin"
    return "linux"


def _display_size() -> tuple[int, int]:
    try:
        proc = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            for line in (proc.stdout or "").splitlines():
                if "*" in line:
                    parts = line.split()[0]
                    if "x" in parts:
                        w, h = parts.split("x", 1)
                        return int(w), int(h)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return 1920, 1080


def _rtx_detected() -> bool:
    gate = GROK16 / "forge" / "rtx_gate.py"
    if gate.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(gate), "json", "queen_rtx"],
                capture_output=True, text=True, timeout=12, cwd=str(GROK16),
            )
            if proc.returncode == 0 and '"permit":true' in (proc.stdout or "").replace(" ", ""):
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=6,
        )
        if proc.returncode == 0 and "RTX" in (proc.stdout or "").upper():
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def _panel_shell_ui_scale() -> int | None:
    shell_path = STATE / "field-shell-settings.json"
    try:
        shell = json.loads(shell_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = shell.get("ui_scale")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _tier(width: int) -> dict[str, Any]:
    for tier in (_load(TIERS, {}).get("tiers") or []):
        if tier.get("min_width", 0) <= width <= tier.get("max_width", 99999):
            return tier
    return {"id": "fhd", "scale": 1.1, "font_pt": 12, "dock_icon_px": 24}


def ui_posture(*, width: int | None = None, ui_scale_pct: int | None = None, rtx_reduce: bool | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ui_doc = doctrine.get("ui") or {}
    saved = _load(SETTINGS, {})
    w, _h = _display_size() if width is None else (width, 1080)
    pct = ui_scale_pct if ui_scale_pct is not None else int(
        saved.get("ui_scale_pct") or _panel_shell_ui_scale() or ui_doc.get("default_ui_scale_pct") or 125
    )
    rtx = _rtx_detected()
    reduce = rtx_reduce if rtx_reduce is not None else bool(saved.get("rtx_reduce", ui_doc.get("rtx_reduce_default", True)) and rtx)
    tier = _tier(w)
    scale = float(tier.get("scale", 1.1)) * (pct / 100.0)
    if reduce:
        scale *= float(ui_doc.get("rtx_reduce_factor", 0.92))
    scale = round(min(float(ui_doc.get("max_ui_scale_pct", 200)) / 100.0, max(float(ui_doc.get("min_ui_scale_pct", 85)) / 100.0, scale)), 3)
    return {
        "width": w,
        "tier": tier.get("id"),
        "ui_scale_pct": pct,
        "qt_scale_factor": scale,
        "font_pt": tier.get("font_pt"),
        "dock_icon_px": tier.get("dock_icon_px"),
        "rtx_detected": rtx,
        "rtx_reduce": reduce,
        "nvenc": rtx,
    }


def _g16_probe() -> dict[str, Any]:
    doc = _load(G16_TOOLCHAIN, {})
    g16_bin = GROK16 / "bin" / "g16"
    prefix_bin = FIELD / (doc.get("prefix") or "prefix") / "bin" / "obs"
    if not prefix_bin.is_file():
        build_bin = FIELD / (doc.get("build", {}).get("binary") or "prefix/bin/obs")
        if build_bin.is_file():
            prefix_bin = build_bin
    ready = g16_bin.is_file() and os.access(g16_bin, os.X_OK)
    return {
        "ok": ready,
        "g16": str(g16_bin) if ready else None,
        "profile": doc.get("default_profile", "field_opt"),
        "prefix_binary": str(prefix_bin) if prefix_bin.is_file() else None,
    }


def _resolve_binary() -> str | None:
    doctrine = _load(DOCTRINE, {})
    g16 = _g16_probe()
    if g16.get("prefix_binary"):
        return g16["prefix_binary"]
    for rel in ((doctrine.get("build") or {}).get("binary"), "prefix/bin/obs"):
        if rel:
            candidate = FIELD / str(rel)
            if candidate.is_file():
                return str(candidate)
    return shutil.which("obs")


def _obs_running() -> bool:
    try:
        proc = subprocess.run(["pgrep", "-x", "obs"], capture_output=True, timeout=2)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _obs_plugin_home() -> Path:
    return Path.home() / ".config/obs-studio/plugins/obs-field-voice-filter"


def _obs_plugin_installed() -> bool:
    return (_obs_plugin_home() / "bin/64bit/obs-field-voice-filter.so").is_file()


def _obs_stack_doc() -> dict[str, Any]:
    for p in (
        _obs_plugin_home() / "data/field-obs-stack.json",
        SG / "OBS-FieldVoiceFilter/data/field-obs-stack.json",
    ):
        doc = _load(p, {})
        if doc:
            doc["_path"] = str(p)
            return doc
    return {}


def _posterity_bridge() -> dict[str, Any]:
    try:
        import importlib.util
        bridge_py = INSTALL / "lib" / "obs-threat-posterity-bridge.py"
        spec = importlib.util.spec_from_file_location("obs_threat_posterity_bridge", bridge_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.panel_json()
    except Exception:
        pass
    return _load(STATE / "obs-threat-posterity-panel.json", {})


def _harden_portable(ui: dict[str, Any]) -> dict[str, Any]:
    env = {
        **os.environ,
        "OBS_FIELD_ROOT": str(FIELD),
        "NEXUS_STATE_DIR": str(STATE),
        "FIELD_OBS_PORTABLE_DIR": str(PORTABLE),
        "FIELD_BROADCASTER_PORTABLE_DIR": str(PORTABLE),
        "FIELD_OBS_WIDTH": str(ui.get("width", 1920)),
        "FIELD_OBS_UI_SCALE": str(ui.get("ui_scale_pct", 110)),
        "FIELD_OBS_RTX_REDUCE": "1" if ui.get("rtx_reduce") else "0",
    }
    if HARDEN.is_file():
        proc = subprocess.run(
            [sys.executable, str(HARDEN), "json"],
            capture_output=True, text=True, timeout=45, env=env,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                pass
    return {"ok": False, "portable": str(PORTABLE)}


def _launch_env(ui: dict[str, Any]) -> dict[str, str]:
    return {
        **os.environ,
        "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
        "QT_SCALE_FACTOR": str(ui.get("qt_scale_factor", 1.1)),
        "QT_FONT_DPI": str(int(96 * float(ui.get("qt_scale_factor", 1.1)))),
    }


def _launch_argv(*, record: bool = False, virtualcam: bool = False, studio: bool = False) -> list[str]:
    doctrine = _load(FIELD / "data" / "field-broadcaster-doctrine.json", {}) or _load(DOCTRINE, {})
    capture = doctrine.get("capture") or {}
    binary = _resolve_binary()
    if not binary:
        return []
    profile = capture.get("default_profile", "Field")
    collection = capture.get("default_collection", "Field-Queen")
    if binary.startswith("flatpak "):
        argv = binary.split()
    else:
        argv = [binary]
    argv += [
        "--portable", "--disable-updater", "--only-bundled-plugins",
        "--profile", profile, "--collection", collection,
        "--disable-missing-files-check",
    ]
    if record:
        argv.append("--startrecording")
    if virtualcam:
        argv.append("--startvirtualcam")
    if studio:
        argv.append("--studio-mode")
    return argv


def list_recordings() -> list[dict[str, Any]]:
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for p in sorted(RECORDINGS.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file() and p.suffix.lower() in (".mkv", ".mp4", ".mov", ".flv", ".webm"):
            out.append({"name": p.name, "path": str(p), "bytes": p.stat().st_size})
    return out[:24]


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ui = ui_posture()
    binary = _resolve_binary()
    hardened = _harden_portable(ui) if binary else {}
    stack = _obs_stack_doc()
    posterity = _posterity_bridge()
    g16 = _g16_probe()
    threat = (posterity.get("threat_ledger") or {}).get("summary") or {}
    doc = {
        "schema": "field-obs-engine/v1",
        "ts": _now(),
        "ok": bool(binary),
        "binary": binary,
        "platform": _guest_os(),
        "g16": g16,
        "ui": ui,
        "portable": hardened.get("portable") or str(PORTABLE),
        "recordings_dir": str(RECORDINGS),
        "profile": hardened.get("profile") or "Field",
        "collection": hardened.get("collection") or "Field-Queen",
        "encoder": hardened.get("encoder"),
        "recordings": list_recordings(),
        "obs": {
            "running": _obs_running(),
            "field_plugin_installed": _obs_plugin_installed(),
            "plugin_home": str(_obs_plugin_home()),
            "stack": stack,
            "filters": (stack.get("filters") or []) if stack else [],
            "security": posterity.get("security") or stack.get("security") or {},
            "posterity": posterity.get("posterity") or {},
            "threat_summary": threat,
        },
    }
    _save_atomic(PANEL, doc)
    return doc


def launch(*, record: bool = False, virtualcam: bool = False, studio: bool = False) -> dict[str, Any]:
    binary = _resolve_binary()
    if not binary:
        return {"ok": False, "error": "obs_missing"}
    ui = ui_posture()
    hardened = _harden_portable(ui)
    argv = _launch_argv(record=record, virtualcam=virtualcam, studio=studio)
    env = _launch_env(ui)
    try:
        proc = subprocess.Popen(
            argv, env=env, cwd=str(PORTABLE),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        return {"ok": True, "pid": proc.pid, "binary": binary, "argv": argv, "portable": hardened.get("portable"), "ui": ui}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "argv": argv}


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"ui_scale_pct", "rtx_reduce", "tier_override", "studio_mode_default"}
    saved = _load(SETTINGS, {})
    for key, val in patch.items():
        if key in allowed:
            saved[key] = val
    _save_atomic(SETTINGS, saved)
    return posture()