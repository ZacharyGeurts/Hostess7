#!/usr/bin/env pythong
"""Open NEXUS / field URLs inside Queen browser tabs — no OS browser fallback."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))


def _resolve_queen_root() -> Path:
    env = os.environ.get("QUEEN_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p.resolve()
    for candidate in (
        INSTALL / "Queen",
        INSTALL.parent / "Queen",
        Path(os.environ.get("SG_ROOT", str(INSTALL.parent))) / "Queen",
        Path(os.environ.get("SG_ROOT", str(INSTALL.parent))) / "NewLatest" / "Queen",
        Path("/home/default/Desktop/SG/Queen"),
        Path("/home/default/Desktop/SG/NewLatest/Queen"),
    ):
        if candidate.is_dir() and ((candidate / "world").is_dir() or (candidate / "lib").is_dir()):
            return candidate.resolve()
    return (INSTALL / "Queen").resolve()


QUEEN = _resolve_queen_root()
WORLD_PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
PANEL_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))


def _world_base() -> str:
    return f"http://127.0.0.1:{WORLD_PORT}"


def _browser_shell_url() -> str:
    custom = os.environ.get("QUEEN_BROWSER_URL", "").strip()
    if custom:
        return custom
    return f"{_world_base()}/world/browser.html"


def _panel_field_url(route: str = "") -> str:
    base = f"http://127.0.0.1:{PANEL_PORT}/field"
    route = (route or "").strip().lstrip("#")
    return f"{base}#{route}" if route else base


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, *, timeout: float = 8.0) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip().startswith("{") else {"ok": True, "raw": raw[:200]}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            doc = json.loads(raw) if raw.strip().startswith("{") else {}
        except (OSError, json.JSONDecodeError):
            doc = {}
        doc.setdefault("ok", False)
        doc.setdefault("http_status", exc.code)
        return doc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def ensure_queen_world() -> dict[str, Any]:
    st = _http_json("GET", f"{_world_base()}/api/status?fast=1", timeout=2.0)
    if st.get("ok") is not False and (st.get("schema") or st.get("port") or st.get("queen_verdict")):
        return {"ok": True, "already": True, "world": _world_base()}
    script = QUEEN / "scripts" / "start-world.sh"
    if script.is_file():
        try:
            subprocess.run(
                [str(script), "--daemon"],
                cwd=str(QUEEN),
                env={**os.environ, "QUEEN_ROOT": str(QUEEN), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    for _ in range(12):
        st = _http_json("GET", f"{_world_base()}/api/status?fast=1", timeout=2.0)
        if st.get("ok") is not False and (st.get("schema") or st.get("port") or st.get("queen_verdict")):
            return {"ok": True, "spawned": True, "world": _world_base()}
    return {"ok": False, "error": "queen_world_unavailable", "world": _world_base()}


def open_in_queen_tab(url: str, *, new_tab: bool = True, tab_id: str = "") -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        return {"ok": False, "error": "url_required"}
    world = ensure_queen_world()
    if not world.get("ok"):
        return world
    jump = _http_json(
        "POST",
        f"{_world_base()}/api/nexus-jump",
        {"action": "jump", "url": url, "tab_id": tab_id, "proc": "queen-browser"},
        timeout=12.0,
    )
    if jump.get("permit") is False or jump.get("ok") is False:
        return {**jump, "ok": False, "phase": "nexus_jump"}
    action = "new_tab" if new_tab else "navigate"
    nav = _http_json(
        "POST",
        f"{_world_base()}/api/queen-browser",
        {"action": action, "url": url, "tab_id": tab_id},
        timeout=12.0,
    )
    return {
        "ok": nav.get("ok") is not False,
        "engine": "queen-browser",
        "world": _world_base(),
        "url": url,
        "tab": nav.get("tab") or nav.get("tabs", [{}])[0] if isinstance(nav.get("tabs"), list) else nav.get("tab"),
        "jump_verdict": jump.get("verdict"),
        "nav": nav,
    }


def _launch_integrated_browser() -> dict[str, Any]:
    """Queen Field Gecko — integrated shell, isolated profile, no OS browser / no comp shader."""
    py = INSTALL / "lib" / "queen-integrated-browser.py"
    if not py.is_file():
        return {
            "ok": True,
            "display": "queen_browser_shell",
            "url": _browser_shell_url(),
            "hint": "queen-integrated-browser.py missing — world daemon only",
        }
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "open"],
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "QUEEN_ROOT": str(QUEEN),
                "QUEEN_NO_OS_BROWSER": "1",
                "QUEEN_WEB_SHELL": "1",
                "QUEEN_SKIP_RTX_BOOT": "1",
            },
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        doc = json.loads(proc.stdout or "{}") if (proc.stdout or "").strip().startswith("{") else {}
        if doc:
            return doc
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"ok": False, "error": "integrated_browser_launch_failed"}


def launch_queen_display(*, focus_url: str = "") -> dict[str, Any]:
    """Open Queen integrated field browser — Webbrowser shell + startup tabs, never comp shader."""
    browser_shell = _browser_shell_url()
    launch_url = browser_shell
    kilroy_home = f"{_world_base()}/world/kilroy-home.html"
    panel_url = (focus_url or kilroy_home).strip()
    world = ensure_queen_world()
    display = _launch_integrated_browser()
    return {
        **display,
        "ok": display.get("ok") is not False and world.get("ok") is not False,
        "world": world,
        "panel_url": panel_url,
        "shell_url": browser_shell,
        "launch_url": launch_url,
        "gecko_url_arg": f"--url={launch_url}",
        "surface": "queen-webbrowser",
        "spawn_rtx": False,
        "comp_shader_boot": False,
    }


def open_nexus_panel(*, route: str = "", new_tab: bool = True, launch_display: bool = True) -> dict[str, Any]:
    url = _panel_field_url(route)
    tab = open_in_queen_tab(url, new_tab=new_tab)
    out = {"ok": tab.get("ok"), "nexus_url": url, "tab": tab}
    if launch_display:
        out["display"] = launch_queen_display()
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "nexus").strip().lower()
    if cmd in ("nexus", "field", "panel"):
        route = sys.argv[2] if len(sys.argv) > 2 else ""
        out = open_nexus_panel(route=route)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "url" and len(sys.argv) > 2:
        out = open_in_queen_tab(" ".join(sys.argv[2:]))
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "ensure":
        print(json.dumps(ensure_queen_world(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: queen-panel-open.py [nexus [route]|url URL|ensure]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())