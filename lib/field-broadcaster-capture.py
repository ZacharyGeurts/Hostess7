#!/usr/bin/env pythong
"""Secure desktop capture — enumerated monitors only, no arbitrary ffmpeg inputs."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc_cap", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE = fcc.STATE
PREVIEW_DIR = STATE / "field-broadcaster-capture-preview"
PREVIEW_RATE = STATE / "field-broadcaster-capture-preview-rate.json"

_MONITOR_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_MIN_PREVIEW_INTERVAL_S = 2.0


def _session_backend() -> str:
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _pipewire_ffmpeg() -> bool:
    ff = shutil.which("ffmpeg")
    if not ff:
        return False
    try:
        proc = subprocess.run(
            [ff, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            timeout=6,
        )
        return "pipewire" in (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return False


def _parse_xrandr() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not os.environ.get("DISPLAY"):
        return out
    try:
        proc = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return out
    geo_re = re.compile(
        r"^(\S+)\s+connected(?:\s+primary)?(?:\s+\d+x\d+\+\d+\+\d+)?\s*"
        r"(?:(\d+)x(\d+)\+(\d+)\+(\d+))?"
    )
    for line in (proc.stdout or "").splitlines():
        m = geo_re.match(line.strip())
        if not m:
            continue
        name, w, h, x, y = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if not _MONITOR_ID_RE.match(name):
            continue
        primary = " primary" in line
        if not w:
            continue
        out.append({
            "id": name,
            "name": f"Desktop · {name}",
            "kind": "desktop_capture",
            "driver": "secure_capture",
            "backend": "x11",
            "capturable": True,
            "primary": primary,
            "geometry": {"width": int(w), "height": int(h), "x": int(x), "y": int(y)},
            "screen": os.environ.get("DISPLAY", ":0").split(".")[0] or ":0",
        })
    return out


def _mss_monitors() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        import mss
        with mss.mss() as sct:
            for idx, mon in enumerate(sct.monitors):
                if idx == 0:
                    continue
                mid = f"mss-{idx}"
                if not _MONITOR_ID_RE.match(mid):
                    continue
                out.append({
                    "id": mid,
                    "name": f"Desktop · monitor {idx}",
                    "kind": "desktop_capture",
                    "driver": "secure_capture",
                    "backend": "mss",
                    "capturable": True,
                    "primary": idx == 1,
                    "geometry": {
                        "width": int(mon["width"]),
                        "height": int(mon["height"]),
                        "x": int(mon["left"]),
                        "y": int(mon["top"]),
                    },
                    "mss_index": idx,
                })
    except Exception:
        pass
    return out


def enumerate_monitors() -> list[dict[str, Any]]:
    """Monitors safe for desktop capture — validated IDs + geometry only."""
    monitors = _parse_xrandr()
    if not monitors:
        monitors = _mss_monitors()
    if not monitors and _session_backend() == "wayland":
        backend = "pipewire" if _pipewire_ffmpeg() else ("grim" if shutil.which("grim") else "mss")
        if backend in ("pipewire", "grim", "mss"):
            monitors.append({
                "id": "wayland-primary",
                "name": "Desktop · Wayland primary",
                "kind": "desktop_capture",
                "driver": "secure_capture",
                "backend": backend,
                "capturable": True,
                "primary": True,
                "geometry": {"width": 1920, "height": 1080, "x": 0, "y": 0},
                "pipewire_node": "0",
                "mss_index": 1,
            })
    elif _session_backend() == "wayland" and _pipewire_ffmpeg():
        for row in monitors:
            if row.get("backend") == "x11":
                row["backend"] = "pipewire"
                row["pipewire_node"] = "0"
    return monitors


def validate_monitor(monitor_id: str) -> dict[str, Any] | None:
    mid = str(monitor_id or "").strip()
    if not mid or not _MONITOR_ID_RE.match(mid):
        return None
    for row in enumerate_monitors():
        if row.get("id") == mid:
            return dict(row)
    return None


def capture_gate() -> dict[str, Any]:
    """Threat + localhost posture before desktop capture is armed."""
    gate: dict[str, Any] = {"ok": True, "localhost_only": True}
    bridge = INSTALL / "lib" / "obs-threat-posterity-bridge.py"
    if bridge.is_file():
        try:
            spec = importlib.util.spec_from_file_location("cap_threat", bridge)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "panel_json"):
                    doc = mod.panel_json()
                    summary = (doc.get("threat_ledger") or {}).get("summary") or doc.get("threat_summary") or {}
                    blocked = int(summary.get("harm_candidate") or summary.get("blocked") or 0)
                    gate["threat_blocked"] = blocked
                    gate["ok"] = blocked == 0
        except Exception as exc:
            gate["threat_error"] = str(exc)
    return gate


def ffmpeg_video_input(source: dict[str, Any]) -> list[str]:
    mid = str(source.get("device") or source.get("id") or "").strip()
    mon = validate_monitor(mid)
    if not mon:
        raise ValueError("invalid_desktop_monitor")
    geo = mon.get("geometry") or {}
    w = int(geo.get("width") or 1920)
    h = int(geo.get("height") or 1080)
    x = int(geo.get("x") or 0)
    y = int(geo.get("y") or 0)
    size = f"{w}x{h}"
    backend = str(mon.get("backend") or "x11")
    if backend == "pipewire" and _pipewire_ffmpeg():
        node = str(mon.get("pipewire_node") or "0")
        return ["-f", "pipewire", "-framerate", "30", "-video_size", size, "-i", node]
    if backend == "mss":
        raise ValueError("mss_desktop_requires_final_eye_or_pipewire")
    if backend == "grim":
        raise ValueError("grim_preview_only_install_pipewire_ffmpeg_for_record")
    screen = str(mon.get("screen") or os.environ.get("DISPLAY", ":0")).split(".")[0]
    offset = f"{screen}+{x},{y}"
    return ["-f", "x11grab", "-framerate", "30", "-video_size", size, "-i", offset]


def _rate_ok(monitor_id: str) -> bool:
    doc = fcc.load(PREVIEW_RATE, {})
    last = float((doc.get(monitor_id) or {}).get("ts") or 0)
    now = time.time()
    if now - last < _MIN_PREVIEW_INTERVAL_S:
        return False
    doc[monitor_id] = {"ts": now}
    try:
        PREVIEW_RATE.parent.mkdir(parents=True, exist_ok=True)
        PREVIEW_RATE.write_text(json.dumps(doc), encoding="utf-8")
    except OSError:
        pass
    return True


def desktop_preview_path(monitor_id: str) -> Path | None:
    mon = validate_monitor(monitor_id)
    if not mon:
        return None
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", monitor_id)[:64]
    return PREVIEW_DIR / f"{safe}.jpg"


def capture_preview_jpeg(monitor_id: str, *, force: bool = False) -> dict[str, Any]:
    gate = capture_gate()
    if not gate.get("ok"):
        return {"ok": False, "error": "threat_blocked", "gate": gate}
    mon = validate_monitor(monitor_id)
    if not mon:
        return {"ok": False, "error": "invalid_desktop_monitor"}
    out = desktop_preview_path(monitor_id)
    if not out:
        return {"ok": False, "error": "preview_path_failed"}
    if out.is_file() and not force and not _rate_ok(monitor_id):
        return {"ok": True, "cached": True, "path": str(out), "monitor": mon}
    backend = str(mon.get("backend") or "x11")
    try:
        if backend == "grim" and shutil.which("grim"):
            proc = subprocess.run(["grim", str(out)], capture_output=True, timeout=10)
            if proc.returncode == 0 and out.is_file():
                return {"ok": True, "path": str(out), "bytes": out.stat().st_size, "monitor": mon, "gate": gate, "backend": "grim"}
        if backend == "mss":
            try:
                import mss
                from PIL import Image
                idx = int(mon.get("mss_index") or 1)
                with mss.mss() as sct:
                    shot = sct.grab(sct.monitors[idx])
                    Image.frombytes("RGB", shot.size, shot.rgb).save(out, format="JPEG", quality=85)
                if out.is_file():
                    return {"ok": True, "path": str(out), "bytes": out.stat().st_size, "monitor": mon, "gate": gate, "backend": "mss"}
            except Exception as exc:
                return {"ok": False, "error": f"mss_preview_failed:{exc}"}
        ff = shutil.which("ffmpeg")
        if not ff:
            return {"ok": False, "error": "ffmpeg_missing"}
        argv = ["ffmpeg", "-y", "-loglevel", "error", "-frames:v", "1"]
        argv.extend(ffmpeg_video_input({"device": monitor_id}))
        argv.append(str(out))
        proc = subprocess.run(argv, capture_output=True, timeout=12)
        if proc.returncode != 0 or not out.is_file():
            return {"ok": False, "error": "preview_capture_failed", "stderr": (proc.stderr or b"").decode()[:200]}
        return {"ok": True, "path": str(out), "bytes": out.stat().st_size, "monitor": mon, "gate": gate}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


def posture() -> dict[str, Any]:
    return {
        "schema": "field-broadcaster-capture/v1",
        "ok": True,
        "backend": _session_backend(),
        "pipewire_ffmpeg": _pipewire_ffmpeg(),
        "monitors": enumerate_monitors(),
        "gate": capture_gate(),
        "preview_interval_s": _MIN_PREVIEW_INTERVAL_S,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "monitors"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "preview" and len(sys.argv) > 2:
        print(json.dumps(capture_preview_jpeg(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-broadcaster-capture.py [json|monitors|preview MONITOR_ID]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())