#!/usr/bin/env pythong
"""Open Queen sovereign browser — self-contained shell, no OS wmctrl/xdotool hooks."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))


def _resolve_queen_root() -> Path:
    env = os.environ.get("QUEEN_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p.resolve()
    for candidate in (
        INSTALL / "Queen",
        SG / "Queen",
        SG / "NewLatest" / "Queen",
        Path("/home/default/Desktop/SG/NewLatest/Queen"),
    ):
        if candidate.is_dir() and (candidate / "world").is_dir():
            return candidate.resolve()
    return (INSTALL / "Queen").resolve()


def _load_panel_open() -> Any:
    py = INSTALL / "lib" / "queen-panel-open.py"
    spec = importlib.util.spec_from_file_location("queen_panel_open", py)
    if not spec or not spec.loader:
        raise ImportError("queen-panel-open.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def open_sovereign_browser(*, route: str = "", focus_url: str = "") -> dict[str, Any]:
    """F9 target — Queen world + Webbrowser shell; CHIPS/cores via web (no RTX comp shader)."""
    queen = _resolve_queen_root()
    port = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    c2_url = f"http://127.0.0.1:{panel_port}/field"
    kilroy_home = f"http://127.0.0.1:{port}/world/kilroy-home.html"
    browser_shell = f"http://127.0.0.1:{port}/world/browser.html"
    c2_launch = os.environ.get("NEXUS_C2_DESKTOP_LAUNCH", "0").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    shell_url = os.environ.get("QUEEN_BROWSER_URL", "").strip() or browser_shell
    rtx_bin = queen / "build" / "rtx" / "bin" / "Linux" / "queen-browser"
    rtx_ready = rtx_bin.is_file() and os.access(rtx_bin, os.X_OK)
    skip_rtx = os.environ.get("QUEEN_SKIP_RTX_BOOT", "1" if not rtx_ready else "0")
    if os.environ.get("QUEEN_FORCE_HTTP_SHELL", "0").strip().lower() in ("1", "true", "yes"):
        skip_rtx = "1"
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(queen),
        "QUEEN_SOVEREIGN": "1",
        "NEXUS_QUEEN_SOVEREIGN": "1",
        "QUEEN_INTERNAL_ONLY": "1",
        "QUEEN_INSTANT_BROWSER": "1",
        "QUEEN_BROWSER_STRIPPED": os.environ.get("QUEEN_BROWSER_STRIPPED", "1"),
        "QUEEN_BOOT_OS": os.environ.get("QUEEN_BOOT_OS", "0"),
        "QUEEN_WEB_SHELL": "0" if skip_rtx == "0" else "1",
        "QUEEN_SKIP_RTX_BOOT": skip_rtx,
        "NEXUS_EMBED_PANEL_IN_ENGINE": "0",
        "NEXUS_FIELD_BROWSER_QUEEN": "1",
        "NEXUS_C2_DESKTOP_LAUNCH": "0",
        "NEXUS_C2_KIOSK": os.environ.get("NEXUS_C2_KIOSK", "0"),
        "NEXUS_C2_LAUNCH_URL": os.environ.get("NEXUS_C2_LAUNCH_URL", c2_url),
        "QUEEN_BROWSER_URL": shell_url,
        "QUEEN_BROWSER_START": os.environ.get("QUEEN_BROWSER_START", kilroy_home),
        "QUEEN_BROWSER_HOME": os.environ.get("QUEEN_BROWSER_HOME", kilroy_home),
        "QUEEN_NO_OS_BROWSER": os.environ.get("QUEEN_NO_OS_BROWSER", "1"),
        "AMOURANTHRTX_ROOT": os.environ.get("AMOURANTHRTX_ROOT", str(SG / "AMOURANTHRTX")),
    }
    opener = _load_panel_open()
    world = opener.ensure_queen_world()
    if not world.get("ok"):
        start = queen / "scripts" / "start-world.sh"
        if start.is_file():
            subprocess.run(
                [str(start), "--daemon"],
                cwd=str(queen),
                env=env,
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
            world = opener.ensure_queen_world()
    panel_url = focus_url.strip()
    if not panel_url and route:
        panel_url = opener._panel_field_url(route)  # noqa: SLF001
    if not panel_url:
        panel_url = env.get("QUEEN_BROWSER_START", "").strip() or kilroy_home
    integrated_py = INSTALL / "lib" / "queen-integrated-browser.py"
    if integrated_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(integrated_py), "open"],
                env=env,
                capture_output=True,
                text=True,
                timeout=50,
                check=False,
            )
            display = json.loads(proc.stdout or "{}") if (proc.stdout or "").strip().startswith("{") else {}
        except (subprocess.SubprocessError, json.JSONDecodeError):
            display = opener.launch_queen_display()
    else:
        display = opener.launch_queen_display()
    tab = opener.open_in_queen_tab(panel_url, new_tab=True) if panel_url else None
    return {
        "ok": bool(world.get("ok") or display.get("ok")),
        "engine": "queen-browser",
        "self_contained": True,
        "shell_url": shell_url,
        "world": world,
        "display": display,
        "tab": tab,
        "queen_root": str(queen),
    }


def _http_up(url: str, *, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _resolve_kilroy_root() -> str:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env and (Path(env) / "scripts" / "build-kilroy.sh").is_file():
        return str(Path(env).resolve())
    resolve_sh = INSTALL / "lib" / "kilroy-resolve.sh"
    if not resolve_sh.is_file():
        return ""
    try:
        proc = subprocess.run(
            ["bash", "-c", f'source "{resolve_sh}" && nexus_kilroy_export && printf "%s" "${{KILROY_ROOT:-}}"'],
            capture_output=True,
            text=True,
            timeout=12,
            cwd=str(INSTALL),
            check=False,
        )
        return (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _kilroy_network_active() -> bool:
    lane = STATE / "kilroy-net-lane.json"
    if lane.is_file():
        try:
            doc = json.loads(lane.read_text(encoding="utf-8"))
            if doc.get("active"):
                return True
        except (OSError, json.JSONDecodeError):
            pass
    marker = STATE / "znetwork-running.marker"
    if marker.is_file():
        return True
    status_path = STATE / "znetwork-status.json"
    if not status_path.is_file():
        return False
    try:
        doc = json.loads(status_path.read_text(encoding="utf-8"))
        return bool(doc.get("running") or doc.get("ok"))
    except (OSError, json.JSONDecodeError):
        return False


def _ensure_kilroy_core(env: dict[str, str]) -> dict[str, Any]:
    """KILROY PC core — network lane (ex-ZNetwork) + defense/offense before AmmoOS."""
    sh = INSTALL / "lib" / "kilroy-core.sh"
    if not sh.is_file():
        return {"ok": False, "error": "kilroy-core.sh missing"}
    if _kilroy_network_active():
        return {"ok": True, "skipped": True, "network_lane": True, "owner": "kilroy_core"}
    try:
        proc = subprocess.run(
            [
                "bash",
                "-c",
                f'source "{INSTALL / "lib" / "nexus-common.sh"}" && source "{sh}" && nexus_kilroy_core_board',
            ],
            env=env,
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        for _ in range(24):
            if _kilroy_network_active():
                return {
                    "ok": True,
                    "network_lane": True,
                    "owner": "kilroy_core",
                    "returncode": proc.returncode,
                }
            time.sleep(0.25)
        return {
            "ok": proc.returncode == 0,
            "network_lane": _kilroy_network_active(),
            "owner": "kilroy_core",
            "returncode": proc.returncode,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _install_queen_default_browser(env: dict[str, str]) -> dict[str, Any]:
    """Register queen-browser.desktop and set system default web browser."""
    installer = INSTALL / "lib" / "nexus-host-desktop-install.py"
    if not installer.is_file():
        return {"ok": False, "error": "nexus-host-desktop-install.py missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(installer), "browser"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if (proc.stdout or "").strip().startswith("{"):
            doc = json.loads(proc.stdout)
            return {"ok": bool(doc.get("ok", True)), **doc}
        return {"ok": proc.returncode == 0, "returncode": proc.returncode}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _stack_posture() -> dict[str, bool]:
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    world_port = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    eye_port = int(os.environ.get("FINAL_EYE_PORT", "9479"))
    return {
        "panel": _http_up(f"http://127.0.0.1:{panel_port}/field"),
        "queen": _http_up(f"http://127.0.0.1:{world_port}/api/status?fast=1"),
        "final_eye": _http_up(f"http://127.0.0.1:{eye_port}/api/health"),
        "kilroy_network": _kilroy_network_active(),
    }


def _nexus_c2_url(panel_port: int | None = None) -> str:
    port = panel_port or int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    return f"http://127.0.0.1:{port}/field"


def _ammoos_desktop_url(panel_port: int | None = None) -> str:
    return _nexus_c2_url(panel_port)


def _ensure_kilroy(env: dict[str, str]) -> dict[str, Any]:
    kilroy_root = _resolve_kilroy_root()
    if not kilroy_root:
        return {"ok": False, "error": "kilroy_root_missing"}
    env["KILROY_ROOT"] = kilroy_root
    build = Path(kilroy_root) / "scripts" / "build-kilroy.sh"
    core = _ensure_kilroy_core(env)
    return {
        "ok": True,
        "kilroy_root": kilroy_root,
        "build_script": str(build),
        "ready": build.is_file(),
        "pc_core": True,
        "network_lane": core,
        "znetwork_absorbed": True,
    }


def _ensure_queen_world(env: dict[str, str]) -> dict[str, Any]:
    opener = _load_panel_open()
    world = opener.ensure_queen_world()
    if world.get("ok"):
        return {"ok": True, **world}
    queen = _resolve_queen_root()
    start = queen / "scripts" / "start-world.sh"
    if start.is_file():
        subprocess.run(
            [str(start), "--daemon"],
            cwd=str(queen),
            env=env,
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        world = opener.ensure_queen_world()
    return {"ok": bool(world.get("ok")), **world}


def _launch_ammoos_desktop(env: dict[str, str]) -> dict[str, Any]:
    """Fullscreen AmmoOS desktop (/field) — Queen Browser is operator-launched only."""
    url = _ammoos_desktop_url()
    if not _http_up(url, timeout=4.0):
        return {"ok": False, "error": "field_desktop_unavailable", "url": url}

    profile = INSTALL / "panel" / "profile-ammoos-desktop"
    brand_py = INSTALL / "lib" / "queen-profile-branding.py"
    if brand_py.is_file():
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("queen_profile_branding", brand_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.write_profile(profile, homepage=url)
        except Exception:
            profile.mkdir(parents=True, exist_ok=True)
    else:
        profile.mkdir(parents=True, exist_ok=True)

    launch_env = {
        **env,
        "DISPLAY": env.get("DISPLAY", ":0"),
        "MOZ_DISABLE_SAFE_MODE_KEY": "1",
    }
    for browser in ("firefox", "firefox-esr", "fieldfox"):
        bin_path = shutil.which(browser)
        if not bin_path:
            continue
        try:
            proc = subprocess.Popen(
                [
                    bin_path,
                    "--no-remote",
                    "--profile",
                    str(profile),
                    "--class",
                    "AmmoOSDesktop",
                    "--name",
                    "AmmoOS",
                    "--setpref=general.useragent.override=Mozilla/5.0 (X11; Linux x86_64; rv:128.0) QueenBrowser/2026 AmmoOS/1.0 Gecko/20100101 QueenFieldEngine/128.0",
                    "--kiosk",
                    url,
                ],
                env=launch_env,
                cwd=str(INSTALL),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {
                "ok": True,
                "url": url,
                "engine": browser,
                "mode": "fullscreen_kiosk",
                "pid": proc.pid,
                "profile": str(profile),
            }
        except OSError as exc:
            return {"ok": False, "error": str(exc), "url": url, "engine": browser}
    return {"ok": True, "url": url, "engine": "api_only", "hint": "open /field manually"}


def _kilroy_stack_env() -> dict[str, str]:
    queen = _resolve_queen_root()
    world_port = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    ammoos_desktop = _ammoos_desktop_url(panel_port)
    kilroy_home = f"http://127.0.0.1:{world_port}/world/kilroy-home.html"
    kilroy_root = _resolve_kilroy_root()
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(queen),
        "NEXUS_BOOT_IMPL": "0",
        "NEXUS_C2_DESKTOP_LAUNCH": "0",
        "NEXUS_FIELD_LAUNCH_BROWSER": "0",
        "NEXUS_BOOT_C2_ONLY": "0",
        "NEXUS_AUTO_LAUNCH_QUEEN_BROWSER": "0",
        "QUEEN_WEB_SHELL": "1",
        "QUEEN_SKIP_RTX_BOOT": "1",
        "QUEEN_NO_OS_BROWSER": "1",
        "DISPLAY": os.environ.get("DISPLAY", ":0"),
        "AMMOOS_DESKTOP_URL": ammoos_desktop,
        "NEXUS_C2_LAUNCH_URL": ammoos_desktop,
        "QUEEN_KILROY_HOME": kilroy_home,
        "AMMOOS_SHOW_DESKTOP_ICONS": "1",
    }
    if kilroy_root:
        env["KILROY_ROOT"] = kilroy_root
    return env


def _stamp_f9_sovereign() -> dict[str, Any]:
    marker = STATE / "f9-sovereign-hook.json"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc: dict[str, Any] = {
        "schema": "f9-sovereign-hook/v1",
        "active": True,
        "owner": "kilroy_f9_hook",
        "override": "all_host_shortcuts",
        "policy": "F9 built-in overrides everyone — we got the hook",
        "updated": ts,
    }
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return doc


def _surface_roles(panel_port: int, queen_port: int) -> dict[str, Any]:
    """Queen = web browser. AmmoOS = normal desktop."""
    return {
        "queen": {
            "role": "web_browser",
            "product": "Queen Browser",
            "url": f"http://127.0.0.1:{queen_port}/world/browser.html",
            "not_desktop": True,
        },
        "ammoos": {
            "role": "normal_desktop",
            "product": "AmmoOS",
            "url": f"http://127.0.0.1:{panel_port}/field",
            "f9_surface": True,
        },
    }


def launch_kilroy_stack() -> dict[str, Any]:
    """F9 — sovereign hook → KILROY PC core → AmmoOS normal desktop (Queen = browser only)."""
    env = _kilroy_stack_env()
    for key, val in env.items():
        os.environ[key] = val

    sovereign = _stamp_f9_sovereign()
    ammoos_url = env["AMMOOS_DESKTOP_URL"]
    layers: dict[str, Any] = {}

    kb_py = INSTALL / "lib" / "field-keyboard-sovereign.py"
    if kb_py.is_file():
        subprocess.run(
            [sys.executable, str(kb_py), "engage"],
            env={**env, "F9_SOVEREIGN_HOOK": "1"},
            timeout=10,
            check=False,
        )

    posture = _stack_posture()
    stack_sh = INSTALL / "scripts" / "start-field-stack.sh"
    spawned = False
    log_path = STATE / "f9-kilroy-stack.log"
    stack_keys = ("panel", "queen")
    if stack_sh.is_file() and not all(posture[k] for k in stack_keys):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log_fh:
            subprocess.Popen(
                ["bash", str(stack_sh)],
                env=env,
                cwd=str(INSTALL),
                start_new_session=True,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
            )
        spawned = True
        for _ in range(80):
            posture = _stack_posture()
            if all(posture[k] for k in stack_keys):
                break
            time.sleep(0.25)

    kilroy_layer = _ensure_kilroy(env)
    kilroy_layer["nexus_c2"] = {
        "ok": posture.get("panel", False),
        "url": _nexus_c2_url(),
        "theme": "black_green_pink",
        "monitoring": "all_out_field_tech",
        "inside_kilroy": True,
    }
    layers["kilroy"] = kilroy_layer
    layers["queen_world"] = _ensure_queen_world(env)

    desktop = _launch_ammoos_desktop(env)
    default_browser = _install_queen_default_browser(env)

    stack_ok = all(posture[k] for k in stack_keys)
    queen_port = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    surfaces = _surface_roles(panel_port, queen_port)
    return {
        "ok": bool(desktop.get("ok") and stack_ok),
        "action": "kilroy_stack",
        "product": "AmmoOS",
        "surface": "ammoos_desktop",
        "surfaces": surfaces,
        "queen_role": "web_browser",
        "ammoos_role": "normal_desktop",
        "f9_sovereign_override": True,
        "f9_hook": "lib/field-underlay-hotkey.py",
        "sovereign": sovereign,
        "boot_order": ["kilroy", "ammoos_desktop"],
        "kilroy_includes": ["nexus_c2", "network_lane", "defense_offense", "dns_dhcp_tables"],
        "spawned": spawned,
        "posture": posture,
        "layers": layers,
        "desktop": desktop,
        "default_browser": default_browser,
        "kilroy_root": env.get("KILROY_ROOT", ""),
        "ammoos_url": ammoos_url,
        "queen_browser": {
            "role": "web_browser",
            "auto_launch": False,
            "url": surfaces["queen"]["url"],
            "launch": "operator_from_desktop_not_f9_desktop",
        },
    }


def f9_action() -> dict[str, Any]:
    return launch_kilroy_stack()


def launch_ammoos_desktop() -> dict[str, Any]:
    env = _kilroy_stack_env()
    for key, val in env.items():
        os.environ[key] = val
    return _launch_ammoos_desktop(env)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "open").strip().lower()
    if cmd in ("f9", "hotkey"):
        out = f9_action()
    elif cmd in ("desktop", "ammoos", "c2"):
        out = launch_ammoos_desktop()
    elif cmd == "open":
        route = sys.argv[2] if len(sys.argv) > 2 else ""
        out = open_sovereign_browser(route=route)
    else:
        print(json.dumps({
            "error": "usage",
            "cmds": ["open [route]", "f9", "hotkey", "desktop", "ammoos", "c2"],
        }))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())