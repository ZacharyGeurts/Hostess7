#!/usr/bin/env pythong
"""Open displays — local Queen browser window + peer device fan-out."""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
REGISTRY = STATE / "field-device-registry.json"
SEED = INSTALL / "data" / "field-device-registry-seed.json"
PANEL = STATE / "field-display-open.json"


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



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_py(script: str, *args: str, timeout: int = 60) -> dict[str, Any]:
    py = INSTALL / "lib" / script
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": script}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "SG_ROOT": str(SG)}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "script": script}


def _host_id() -> str:
    return socket.gethostname().split(".")[0] or "local"


def list_displays() -> list[dict[str, Any]]:
    displays: list[dict[str, Any]] = []
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        displays.append({
            "id": "wayland-primary",
            "name": "Wayland primary",
            "backend": "wayland",
            "connected": True,
            "primary": True,
        })
        return displays
    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        text = proc.stdout or ""
        current = None
        primary_name = None
        for line in text.splitlines():
            if " connected" in line:
                parts = line.split()
                current = parts[0]
                connected = "connected" in line and "disconnected" not in line
                primary = "primary" in line
                res = parts[3] if len(parts) > 3 and "+" in parts[3] else ""
                displays.append({
                    "id": current,
                    "name": current,
                    "backend": "x11",
                    "connected": connected,
                    "primary": primary,
                    "resolution": res,
                })
                if primary:
                    primary_name = current
            elif current and line.strip().startswith(" "):
                m = re.search(r"(\d+x\d+)", line)
                if m and not displays[-1].get("resolution"):
                    displays[-1]["resolution"] = m.group(1)
        if primary_name:
            for d in displays:
                d["primary"] = d["id"] == primary_name
    except (OSError, subprocess.SubprocessError):
        pass
    if not displays:
        displays.append({
            "id": "default",
            "name": "Default display",
            "backend": "unknown",
            "connected": True,
            "primary": True,
        })
    return displays


def device_registry() -> dict[str, Any]:
    doc = _load(REGISTRY, _load(SEED, {"schema": "field-device-registry/v1", "devices": []}))
    host = _host_id()
    for dev in doc.get("devices") or []:
        if dev.get("self"):
            dev["displays"] = list_displays()
            dev["last_seen"] = _now()
    doc["ts"] = _now()
    doc["local_id"] = host
    _write_atomic(REGISTRY, doc)
    return doc


def _peer_url(dev: dict[str, Any], path: str) -> str:
    host = str(dev.get("hostname") or dev.get("host") or dev.get("id") or "127.0.0.1")
    if dev.get("self") or host in (_host_id(), "local", "127.0.0.1", "localhost"):
        host = "127.0.0.1"
    port = int(dev.get("panel_port") or os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    return f"http://{host}:{port}{path}"


def _http_json_post(url: str, body: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip().startswith("{") else {"ok": True}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "url": url}


def open_local_display(*, display_id: str = "", route: str = "") -> dict[str, Any]:
    displays = list_displays()
    target = display_id.strip()
    if not target:
        primary = next((d for d in displays if d.get("primary")), displays[0] if displays else None)
        target = primary.get("id", "default") if primary else "default"
    env = os.environ.copy()
    if target and target not in ("default", "wayland-primary") and os.environ.get("DISPLAY"):
        env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
    browser = _run_py("field-queen-browser-open.py", "open", route, timeout=45)
    doc = {
        "schema": "field-display-open/v1",
        "ts": _now(),
        "display_id": target,
        "displays": displays,
        "browser": browser,
        "ok": browser.get("ok"),
    }
    _write_atomic(PANEL, doc)
    return doc


def open_peer_displays(*, device_ids: list[str] | None = None, all_peers: bool = False) -> dict[str, Any]:
    reg = device_registry()
    results: list[dict[str, Any]] = []
    want = set(device_ids or [])
    for dev in reg.get("devices") or []:
        dev_id = str(dev.get("id") or "")
        if dev.get("self"):
            local = open_local_display()
            results.append({"device": dev_id, "self": True, **local})
            continue
        if not all_peers and want and dev_id not in want:
            continue
        url = _peer_url(dev, "/api/display-open/local")
        rep = _http_json_post(url, {"action": "open_browser", "device_id": dev_id})
        results.append({"device": dev_id, "peer": True, "url": url, **rep})
    ok = all(r.get("ok") for r in results) if results else False
    return {"ok": ok, "results": results, "registry": reg}


def posture() -> dict[str, Any]:
    reg = device_registry()
    return {
        "schema": "field-display-open/v1",
        "ts": _now(),
        "displays": list_displays(),
        "registry": reg,
        "last_open": _load(PANEL, {}),
        "api": "/api/display-open",
    }


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if mode == "json":
        result = posture()
    elif mode == "local":
        display_id = sys.argv[2] if len(sys.argv) > 2 else ""
        route = sys.argv[3] if len(sys.argv) > 3 else ""
        result = open_local_display(display_id=display_id, route=route)
    elif mode == "peers":
        result = open_peer_displays(all_peers=True)
    elif mode == "browser":
        result = open_local_display(route="underlay-f9")
    else:
        print(json.dumps({"error": "usage: field-display-open.py [json|local [display]|peers|browser]"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())