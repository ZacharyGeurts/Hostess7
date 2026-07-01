#!/usr/bin/env pythong
"""Queen secure space — Grok16 + RTX FieldSocket memory sealed inside Queen.

Boot once when queen-world starts or when /api/queen-boot is hit from the browser.
No operator-side wiring — page load triggers the seal.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
SEAL_FILE = STATE / "queen-secure-space.json"

# FieldWebPanel + FieldSocket layout (AMOURANTHRTX Pipeline.hpp)
FIELD_SOCKET_BYTES = 4 + 4 + 64 * 4 + 16 * 4 + 4 * 5  # sealed_time, control, buses, floats
FIELD_X86_DIE_BYTES = 64 * 1024 * 1024  # 64 MiB guest die SSBO
VGA_FB_BASE = 0x000A0000
VGA_FB_BYTES = 320 * 200


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def grok16_root() -> Path:
    _SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
    if str(_SG_PATHS_LIB) not in sys.path:
        sys.path.insert(0, str(_SG_PATHS_LIB))
    from sg_paths import grok16_root as _gr
    root = _gr()
    if (root / "bin" / "g16").is_file():
        return root
    prefix = QUEEN / "build" / "g16-prefix"
    return prefix if prefix.is_dir() else root


def _g16_bin(name: str) -> Path | None:
    root = grok16_root()
    for p in (
        root / "bin" / name,
        QUEEN / "build" / "g16-prefix" / "bin" / name,
    ):
        if p.is_file():
            return p
    return None


def grok16_status() -> dict[str, Any]:
    doc = _load_json(QUEEN / "data" / "g16-toolchain.json", {})
    g16 = _g16_bin("g16")
    gxx = _g16_bin("g++16")
    version = ""
    dumpversion = ""
    if g16:
        try:
            proc = subprocess.run(
                [str(g16), "--version"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            version = (proc.stdout or proc.stderr or "").splitlines()[0][:200]
            proc2 = subprocess.run(
                [str(g16), "-dumpversion"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            dumpversion = (proc2.stdout or "").strip()
        except (subprocess.TimeoutExpired, OSError):
            pass
    toolchain = doc.get("toolchain") or {}
    ready = bool(g16 and gxx and (toolchain.get("ready") or dumpversion))
    return {
        "product": "Grok16",
        "g16_version": toolchain.get("g16_version") or doc.get("toolchain", {}).get("g16_version") or "16.1.1",
        "root": str(grok16_root()),
        "g16": str(g16) if g16 else None,
        "g++16": str(gxx) if gxx else None,
        "dumpversion": dumpversion or toolchain.get("dumpversion"),
        "version": version or toolchain.get("version"),
        "profile": toolchain.get("build_profile") or "field_opt",
        "cxx_std": toolchain.get("cxx_std_default") or "gnu++26",
        "ready": ready,
        "in_queen_space": True,
        "mandate": str(QUEEN / "data" / "g16-field-mandate.json"),
    }


def rtx_memory_map() -> dict[str, Any]:
    rtx = _load_json(QUEEN / "data" / "field-rtx-sovereign.json", {})
    gpu = _load_json(QUEEN / "data" / "gpu-probe.json", {})
    return {
        "schema": "queen-rtx-memory/v1",
        "one_card": True,
        "field_socket": {
            "name": "FieldSocket",
            "push_constant_bytes": FIELD_SOCKET_BYTES,
            "data_bus_slots": 64,
            "address_bus_slots": 16,
            "queen_marker_slot": 1,
            "queen_marker_byte": 0x51,
            "boot_surface": "webbrowser",
        },
        "guest_die": {
            "name": "FieldX86Die",
            "ssbo_bytes": FIELD_X86_DIE_BYTES,
            "binding": 1,
        },
        "vga_framebuffer": {
            "base": hex(VGA_FB_BASE),
            "width": 320,
            "height": 200,
            "bytes": VGA_FB_BYTES,
            "panel": "FieldWebPanel",
        },
        "secure_region": {
            "description": "Queen sovereign seal — browser UI + brain + Grok16 toolchain in RTX card memory",
            "total_sealed_bytes": FIELD_SOCKET_BYTES + VGA_FB_BYTES + FIELD_X86_DIE_BYTES,
            "zero_copy_to_host": False,
            "iff": "CIVILIAN · in-process only",
        },
        "gpu": {
            "backend": (rtx.get("phases") or {}).get("now", {}).get("gpu") or "FieldGpuDispatch VulkanBridge",
            "surface": (rtx.get("phases") or {}).get("now", {}).get("surface") or "SDL3 → FieldSurface",
            "env": rtx.get("env") or {},
            "probe": {
                "nvidia_count": gpu.get("nvidia_count"),
                "vulkan": (gpu.get("vulkan_summary") or "").splitlines()[0][:120] if gpu.get("vulkan_summary") else None,
            },
        },
        "doctrine": rtx.get("motto") or "SPIR-V stable ABI. FieldGpuDispatch owns the card.",
    }


def secure_posture() -> dict[str, Any]:
    return {
        "sovereign": True,
        "queen_sovereign": os.environ.get("QUEEN_SOVEREIGN", "1") == "1",
        "field_gpu": os.environ.get("QUEEN_FIELD_GPU", "1") == "1",
        "embed_panel_in_engine": True,
        "no_os_browser_hook": True,
        "no_keyboard_hook": os.environ.get("NEXUS_NO_KEYBOARD_HOOK", "1") == "1",
        "no_screen_capture": os.environ.get("NEXUS_NO_SCREEN_CAPTURE", "1") == "1",
        "admin_window_shield": os.environ.get("NEXUS_ADMIN_WINDOW_SHIELD", "1") == "1",
        "zero_telemetry": True,
        "grok_build_secure": os.environ.get("QUEEN_GROK_BUILD_SECURE", "1") == "1",
        "ai_secure_channel": os.environ.get("NEXUS_AI_SECURE_CHANNEL", "1") == "1",
    }


def boot(*, force: bool = False) -> dict[str, Any]:
    if not force and SEAL_FILE.is_file():
        cached = _load_json(SEAL_FILE, {})
        if cached.get("schema") == "queen-secure-space/v1" and cached.get("sealed"):
            cached["cached"] = True
            return cached

    g16 = grok16_status()
    rtx = rtx_memory_map()
    browser_reset = subprocess.run(
        [sys.executable, str(QUEEN / "lib" / "queen-browser.py"), "reset"],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN), "QUEEN_ROOT": str(QUEEN)},
    )
    browser_ok = browser_reset.returncode == 0

    doc = {
        "schema": "queen-secure-space/v1",
        "sealed": True,
        "updated": _now(),
        "motto": "Grok16 inside. Everything on the RTX card. Browser load = boot.",
        "posture": secure_posture(),
        "grok16": g16,
        "rtx_memory": rtx,
        "browser_reset": browser_ok,
        "world_url": f"http://{os.environ.get('QUEEN_WORLD_HOST', '127.0.0.1')}:{os.environ.get('QUEEN_WORLD_PORT', '9481')}/world/browser.html",
        "boot_from": "page_load",
        "operator_setup_required": False,
        "internal_only": True,
    }
    fn = _run_json_module("queen-field-net.py", "json")
    if fn:
        doc["field_net"] = fn
    _save_json(SEAL_FILE, doc)
    return doc


def _run_json_module(name: str, *args: str) -> dict[str, Any]:
    script = QUEEN / "lib" / name
    if not script.is_file():
        return {}
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(QUEEN),
        env={**os.environ, "QUEEN_ROOT": str(QUEEN), "NEXUS_INSTALL_ROOT": str(QUEEN)},
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def status() -> dict[str, Any]:
    if SEAL_FILE.is_file():
        doc = _load_json(SEAL_FILE, {})
        if doc.get("schema") == "queen-secure-space/v1":
            doc["grok16"] = grok16_status()
            doc["rtx_memory"] = rtx_memory_map()
            return doc
    return boot()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "boot":
        print(json.dumps(boot(force="--force" in sys.argv), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-secure-space.py [json|boot]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())