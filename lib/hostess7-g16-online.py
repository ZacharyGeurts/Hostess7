#!/usr/bin/env python3
"""Hostess 7 Grok16 Online — Pages compiler + local g16 bridge for Hostess 7."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-g16-doctrine.json"
PANEL = STATE / "hostess7-g16-online-panel.json"
STAMP = STATE / "hostess7-g16-online.stamp"

ONLINE_PAGES = os.environ.get("GROK16_ONLINE_PAGES", "https://zacharygeurts.github.io/Grok16/").rstrip("/") + "/"
HOSTESS7_G16_PAGES = os.environ.get(
    "HOSTESS7_G16_PAGES",
    "https://zacharygeurts.github.io/Hostess7/g16-build-output/",
).rstrip("/") + "/"
PANEL_PORT = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
PAGES_BASE = os.environ.get("HOSTESS7_PAGES_BASE", "https://zacharygeurts.github.io/Hostess7").rstrip("/")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _http_ok(url: str, timeout: float = 8.0) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Hostess7-G16-Online/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(resp.status) < 400
    except (urllib.error.URLError, OSError, ValueError):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hostess7-G16-Online/1"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return 200 <= int(resp.status) < 400
        except (urllib.error.URLError, OSError, ValueError):
            return False


def _local_g16_panel() -> dict[str, Any]:
    mod = _import_mod("h7g16", "lib/hostess7-g16.py")
    if mod is None or not hasattr(mod, "build_panel"):
        return {"ok": False, "error": "hostess7_g16_missing"}
    try:
        return mod.build_panel(write=False)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def _stack_panel() -> dict[str, Any]:
    mod = _import_mod("g16bridge", "lib/nexus-g16-bridge.py")
    if mod is None or not hasattr(mod, "build_panel"):
        return {"ok": False, "error": "nexus_g16_bridge_missing"}
    try:
        return mod.build_panel(write=False)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def _g16_binary() -> Path | None:
    for root in (
        Path(os.environ.get("GROK16_ROOT", "")),
        INSTALL / "Grok16",
        INSTALL.parent / "Grok16",
    ):
        if not root or not Path(root).is_dir():
            continue
        for rel in ("bin/g16", "g16"):
            p = Path(root) / rel
            if p.is_file():
                return p
    return None


def _probe_local() -> dict[str, Any]:
    g16 = _g16_binary()
    version = ""
    if g16 is not None:
        try:
            proc = subprocess.run(
                [str(g16), "--version"],
                capture_output=True,
                text=True,
                timeout=12,
                cwd=str(INSTALL),
            )
            version = (proc.stdout or proc.stderr or "").strip()[:120]
        except (subprocess.TimeoutExpired, OSError):
            version = ""
    panel = _local_g16_panel()
    stack = _stack_panel()
    return {
        "ok": g16 is not None or bool(panel.get("toolchain_ready")),
        "g16_binary": str(g16) if g16 else None,
        "g16_version": version or panel.get("g16_version"),
        "toolchain_ready": bool(panel.get("toolchain_ready")),
        "fluent": bool(panel.get("fluent")),
        "mastered": bool(panel.get("mastered")),
        "tier": panel.get("tier"),
        "stack": {
            "ok": bool(stack.get("ok", stack.get("g16_ready"))),
            "g16_ready": stack.get("g16_ready"),
        },
        "loopback": {
            "combinatorics": f"http://127.0.0.1:{PANEL_PORT}/combinatorics",
            "g16_build_output": f"http://127.0.0.1:{PANEL_PORT}/g16-build-output",
            "api": f"http://127.0.0.1:{PANEL_PORT}/api/hostess7/g16",
        },
    }


def _probe_online() -> dict[str, Any]:
    return {
        "ok": _http_ok(ONLINE_PAGES) or _http_ok(HOSTESS7_G16_PAGES),
        "grok16_pages": ONLINE_PAGES,
        "grok16_pages_ok": _http_ok(ONLINE_PAGES),
        "hostess7_g16_pages": HOSTESS7_G16_PAGES,
        "hostess7_g16_pages_ok": _http_ok(HOSTESS7_G16_PAGES),
        "https_secure_jump": f"{PAGES_BASE}/bookmark-jump/?id=g16-compiler&https=1",
    }


def ensure_compiler(*, write: bool = True) -> dict[str, Any]:
    local = _probe_local()
    online = _probe_online()
    ok = local.get("ok") or online.get("ok")
    out = {
        "schema": "hostess7-g16-online-ensure/v1",
        "updated": _now(),
        "ok": ok,
        "available": ok,
        "boss": "hostess7",
        "local": local,
        "online": online,
        "prefer": "local" if local.get("ok") else "online",
        "message": (
            "Grok16 local g16 ready — Hostess 7 compiles on loopback."
            if local.get("ok")
            else "Grok16 online Pages ready — loopback panel bridges when up."
            if online.get("ok")
            else "Grok16 offline — start panel or check network."
        ),
    }
    if write:
        try:
            STAMP.write_text(_now() + "\n", encoding="utf-8")
        except OSError:
            pass
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    local = _probe_local()
    online = _probe_online()
    out = {
        "schema": "hostess7-g16-online/v1",
        "updated": _now(),
        "ok": local.get("ok") or online.get("ok"),
        "product": "Hostess 7 Grok16 Online Compiler",
        "motto": "Online Grok16 Pages + local g16 — Hostess 7 is boss of compile.",
        "boss": "hostess7",
        "doctrine_motto": doctrine.get("motto"),
        "local": local,
        "online": online,
        "routes": {
            "panel_api": "/api/hostess7/g16-online",
            "local_g16_api": "/api/hostess7/g16",
            "stack_api": "/api/g16/stack",
            "combinatorics": f"http://127.0.0.1:{PANEL_PORT}/combinatorics",
            "g16_build_output": f"http://127.0.0.1:{PANEL_PORT}/g16-build-output",
            "pages_compiler": HOSTESS7_G16_PAGES,
            "grok16_manual": ONLINE_PAGES,
            "https_secure_bookmark": f"{PAGES_BASE}/bookmark-jump/?id=g16-compiler&https=1",
        },
        "available_to_hostess7": True,
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower().replace("-", "_")
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ensure", "boot", "online"):
        print(json.dumps(ensure_compiler(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps({"local": _probe_local(), "online": _probe_online()}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-g16-online.py [panel|ensure|probe]",
        "api": "/api/hostess7/g16-online",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())