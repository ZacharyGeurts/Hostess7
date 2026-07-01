#!/usr/bin/env pythong
"""Queen integrated field browser — Webbrowser shell + startup tabs, no comp shader / no OS browser."""
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


QUEEN = _resolve_queen_root()
WORLD_PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
PANEL_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
FIELD_GECKO = QUEEN / "field-gecko"
LAUNCH_SH = FIELD_GECKO / "bin" / "launch-field-gecko.sh"
AMMOOS_FIELD = os.environ.get(
    "AMMOOS_DESKTOP_URL",
    f"http://127.0.0.1:{PANEL_PORT}/field",
).strip() or f"http://127.0.0.1:{PANEL_PORT}/field"
QUEEN_SHELL = f"http://127.0.0.1:{WORLD_PORT}/world/browser.html"
KILROY_HOME = os.environ.get("QUEEN_BROWSER_HOME", AMMOOS_FIELD).strip() or AMMOOS_FIELD


def _world_base() -> str:
    return f"http://127.0.0.1:{WORLD_PORT}"


def _c2_field_url() -> str:
    return f"http://127.0.0.1:{PANEL_PORT}/field"


def _shell_url() -> str:
    custom = os.environ.get("QUEEN_BROWSER_URL", "").strip()
    if custom:
        return custom
    if os.environ.get("NEXUS_C2_DESKTOP_LAUNCH", "0").strip().lower() not in ("0", "false", "no", "off"):
        return _c2_field_url()
    custom = os.environ.get("QUEEN_BROWSER_URL", "").strip()
    if custom:
        return custom
    return f"{_world_base()}/world/browser.html"


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, *, timeout: float = 12.0) -> dict[str, Any]:
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
                timeout=25,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    for _ in range(16):
        st = _http_json("GET", f"{_world_base()}/api/status?fast=1", timeout=2.0)
        if st.get("ok") is not False and (st.get("schema") or st.get("port") or st.get("queen_verdict")):
            return {"ok": True, "spawned": True, "world": _world_base()}
    return {"ok": False, "error": "queen_world_unavailable", "world": _world_base()}


def _resolve_tab_url(spec: dict[str, Any]) -> str:
    env_key = str(spec.get("url_env") or "").strip()
    if env_key and os.environ.get(env_key, "").strip():
        return os.environ.get(env_key, "").strip()
    url = str(spec.get("url") or "").strip()
    if url.startswith("queen://"):
        return url
    if url.startswith("/"):
        return f"{_world_base()}{url}"
    return url or _shell_url()


def startup_tab_specs() -> list[dict[str, Any]]:
    manifest = FIELD_GECKO / "manifest.json"
    if manifest.is_file():
        try:
            doc = json.loads(manifest.read_text(encoding="utf-8"))
            tabs = doc.get("startup_tabs") or []
            if tabs:
                return list(tabs)
        except (OSError, json.JSONDecodeError):
            pass
    return [
        {"role": "ammoos_desktop", "title": "AmmoOS", "url": AMMOOS_FIELD, "url_env": "AMMOOS_DESKTOP_URL", "pinned": True},
    ]


def _seed_profile_branding() -> dict[str, Any]:
    import importlib.util

    brand_py = INSTALL / "lib" / "queen-profile-branding.py"
    if not brand_py.is_file():
        brand_py = QUEEN / "lib" / "queen-profile-branding.py"
    if not brand_py.is_file():
        return {"ok": False, "skipped": True}
    try:
        spec = importlib.util.spec_from_file_location("queen_profile_branding", brand_py)
        if not spec or not spec.loader:
            return {"ok": False, "skipped": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.seed_all(homepage=AMMOOS_FIELD)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def seed_startup_tabs() -> dict[str, Any]:
    branding = _seed_profile_branding()
    world = ensure_queen_world()
    if not world.get("ok"):
        return world
    opened: list[dict[str, Any]] = []
    for i, spec in enumerate(startup_tab_specs()):
        url = _resolve_tab_url(spec)
        jump = _http_json(
            "POST",
            f"{_world_base()}/api/nexus-jump",
            {"action": "jump", "url": url, "proc": "queen-browser"},
            timeout=15.0,
        )
        if jump.get("permit") is False or jump.get("ok") is False:
            opened.append({"url": url, "ok": False, "phase": "nexus_jump", "jump": jump})
            continue
        action = "navigate" if i == 0 else "new_tab"
        nav = _http_json(
            "POST",
            f"{_world_base()}/api/queen-browser",
            {
                "action": action,
                "url": url,
                "title": spec.get("title", ""),
                "pinned": spec.get("role") in ("start", "files"),
            },
            timeout=15.0,
        )
        opened.append({"url": url, "ok": nav.get("ok") is not False, "action": action, "tab": nav.get("tab")})
    return {
        "ok": True,
        "world": world,
        "tabs": opened,
        "surface": "queen-webbrowser",
        "branding": branding,
        "ammoos_desktop": AMMOOS_FIELD,
        "queen_browser": QUEEN_SHELL,
    }


def launch_integrated_display() -> dict[str, Any]:
    """Queen Field Gecko window — isolated profile, never operator default browser."""
    if os.environ.get("QUEEN_NO_OS_BROWSER", "1") not in ("1", "true", "yes"):
        return {
            "ok": False,
            "error": "os_browser_disabled",
            "hint": "Set QUEEN_NO_OS_BROWSER=1 — Queen integrated shell only",
        }
    world = ensure_queen_world()
    seed = seed_startup_tabs()
    shell = _shell_url()
    if not LAUNCH_SH.is_file():
        return {
            "ok": bool(world.get("ok")),
            "engine": "queen-webbrowser",
            "display": "world_daemon_only",
            "shell_url": shell,
            "world": world,
            "seed": seed,
            "hint": "field-gecko launcher missing — open shell via Queen world",
        }
    c2_url = _c2_field_url()
    env = {
        **os.environ,
        "QUEEN_ROOT": str(QUEEN),
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "SG_ROOT": str(SG),
        "QUEEN_WEB_SHELL": "1",
        "QUEEN_SKIP_RTX_BOOT": "1",
        "QUEEN_NO_OS_BROWSER": "1",
        "NEXUS_EMBED_PANEL_IN_ENGINE": "0",
        "NEXUS_C2_DESKTOP_LAUNCH": os.environ.get("NEXUS_C2_DESKTOP_LAUNCH", "0"),
        "NEXUS_C2_KIOSK": os.environ.get("NEXUS_C2_KIOSK", "0"),
        "NEXUS_C2_LAUNCH_URL": os.environ.get("NEXUS_C2_LAUNCH_URL", c2_url),
        "QUEEN_BROWSER_URL": shell,
        "QUEEN_BROWSER_START": os.environ.get("QUEEN_BROWSER_START", KILROY_HOME),
        "QUEEN_BROWSER_HOME": os.environ.get("QUEEN_BROWSER_HOME", KILROY_HOME),
    }
    try:
        subprocess.Popen(
            ["bash", str(LAUNCH_SH)],
            env=env,
            cwd=str(FIELD_GECKO),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "ok": True,
            "engine": "queen-field-gecko",
            "display": "integrated",
            "shell_url": shell,
            "profile": str(FIELD_GECKO / "profile"),
            "comp_shader_boot": False,
            "world": world,
            "seed": seed,
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc), "launcher": str(LAUNCH_SH)}


def open_integrated(*, seed_only: bool = False) -> dict[str, Any]:
    if seed_only:
        return seed_startup_tabs()
    return launch_integrated_display()


def close_integrated(*, stop_world: bool = False) -> dict[str, Any]:
    """Close AmmoOS / Queen field browser window — never host poweroff."""
    profile = str((FIELD_GECKO / "profile").resolve())
    killed: list[str] = []
    patterns = (
        f"firefox.*{profile}",
        f"firefox-esr.*{profile}",
        f"fieldfox.*{profile}",
        "AmmoOS",
        "QueenFieldBrowser",
        "Mozilla Firefox.*AmmoOS",
        "QueenBrowser",
    )
    for pat in patterns:
        try:
            proc = subprocess.run(
                ["pkill", "-f", pat],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                killed.append(pat)
        except (OSError, subprocess.TimeoutExpired):
            pass
    world_stopped = False
    if stop_world:
        for pat in ("queen-world.py", "queen-browser"):
            try:
                proc = subprocess.run(["pkill", "-f", pat], capture_output=True, timeout=5)
                if proc.returncode == 0:
                    killed.append(pat)
                    world_stopped = True
            except (OSError, subprocess.TimeoutExpired):
                pass
    return {
        "ok": True,
        "action": "close_os",
        "message": "AmmoOS closed — host stays running",
        "killed": killed,
        "world_stopped": world_stopped,
        "host_poweroff": False,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "open").strip().lower()
    if cmd in ("open", "launch", "start"):
        out = open_integrated()
    elif cmd == "seed":
        out = open_integrated(seed_only=True)
    elif cmd in ("close", "close-os", "quit", "exit"):
        out = close_integrated(stop_world=os.environ.get("AMMOOS_CLOSE_STOP_WORLD", "0") in ("1", "true", "yes"))
    elif cmd == "ensure":
        out = ensure_queen_world()
    else:
        print(json.dumps({
            "error": "usage: queen-integrated-browser.py [open|seed|close|ensure]",
        }, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())