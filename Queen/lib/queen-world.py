#!/usr/bin/env pythong
"""Queen World — sovereign RTX browser space on one card (loopback HTTP).

Serves world/ SPA + gui/ build deck. APIs: world status, queen-build, queen-eyeball.
Replaces external NEXUS :9477 for Queen sovereign mode.
"""
from __future__ import annotations

import importlib.util
import json
import mimetypes
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
from sg_paths import grok16_root
_LIB = Path(__file__).resolve().parent
WORLD = QUEEN / "world"
GUI = QUEEN / "gui"
HOST = os.environ.get("QUEEN_WORLD_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))

# Seal Grok16 + RTX secure space once per queen-world process (browser load = boot).
_SECURE_BOOT: dict[str, Any] | None = None
_BOOT_HOOK: dict[str, Any] | None = None
_WORLD_FULL_CACHE: dict[str, Any] | None = None
_WORLD_FULL_CACHE_TS: float = 0.0
_PERF_FLYOUT_MOD: Any = None


def _nexus_lib_script(name: str) -> Path:
    for root in (SG / "NewLatest", Path(os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN)))):
        p = root / "lib" / name
        if p.is_file():
            return p
    return SG / "NewLatest" / "lib" / name


def _benchmark_mode_on() -> bool:
    return os.environ.get("QUEEN_BENCHMARK_MODE", "").strip().lower() in ("1", "true", "yes", "on")


def _perf_flyout_sample(*, reset: bool = False) -> dict[str, Any]:
    if _benchmark_mode_on():
        return {
            "schema": "field-performance-flyout/v1",
            "ok": True,
            "benchmark_mode": True,
            "disabled": True,
            "reason": "perf_flyout_off_in_benchmark",
            "cpu_pct": 0,
            "loadavg": [],
            "memory": {"used_pct": 0, "used_kb": 0, "total_kb": 0},
            "energy": {"power_w": 0, "headroom_pct": 100},
            "loopback_only": True,
        }
    global _PERF_FLYOUT_MOD
    script = _nexus_lib_script("field-performance-flyout.py")
    if not script.is_file():
        return {"schema": "field-performance-flyout/v1", "ok": False, "error": "perf_flyout_missing"}
    if _PERF_FLYOUT_MOD is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_performance_flyout_queen", script)
        if not spec or not spec.loader:
            return _run_json(script, "json", timeout=10)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PERF_FLYOUT_MOD = mod
    try:
        return _PERF_FLYOUT_MOD.sample(reset=reset)
    except Exception as exc:
        return {"schema": "field-performance-flyout/v1", "ok": False, "error": str(exc)}


def _boot_hook() -> dict[str, Any]:
    """Board front hook + network metal before host daemons attach."""
    global _BOOT_HOOK
    if _BOOT_HOOK is not None:
        return _BOOT_HOOK
    doc = _run_json(_LIB / "queen-boot-hook.py", "board", timeout=90)
    _BOOT_HOOK = doc if doc.get("boarded") else _run_json(_LIB / "queen-boot-hook.py", "json", timeout=30)
    return _BOOT_HOOK


def _secure_boot() -> dict[str, Any]:
    global _SECURE_BOOT
    if _SECURE_BOOT is not None:
        return _SECURE_BOOT
    _boot_hook()
    doc = _run_json(_LIB / "queen-secure-space.py", "boot", timeout=60)
    _SECURE_BOOT = doc if doc.get("sealed") else _run_json(_LIB / "queen-secure-space.py", "json", timeout=30)
    return _SECURE_BOOT


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _final_eye_root() -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    fe = SG / "Final_Eye"
    return fe if fe.is_dir() else SG / "ZOCR"


def _env() -> dict[str, str]:
    fe = _final_eye_root()
    nexus_root = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(SG / "NewLatest")))
    if not (nexus_root / "lib").is_dir():
        nexus_root = QUEEN
    nexus_state = Path(os.environ.get("NEXUS_STATE_DIR", str(nexus_root / ".nexus-state")))
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "FINAL_EYE_ROOT": str(fe),
        "NEXUS_INSTALL_ROOT": str(nexus_root),
        "NEXUS_STATE_DIR": str(nexus_state),
        "HOSTESS7_ROOT": os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")),
        "GROK16_ROOT": str(grok16_root()),
        "KILROY_ROOT": os.environ.get("KILROY_ROOT", str(SG / "KILROY")),
        "AMOURANTHRTX_ROOT": os.environ.get(
            "AMOURANTHRTX_ROOT", str(SG / "NewLatest" / "AMOURANTHRTX")
        ),
        "QUEEN_INSTANT_BROWSER": os.environ.get("QUEEN_INSTANT_BROWSER", "1"),
        "QUEEN_DISPLAY_REFRESH": os.environ.get("QUEEN_DISPLAY_REFRESH", "120"),
        "NEXUS_FIELD_BROWSER_QUEEN": os.environ.get("NEXUS_FIELD_BROWSER_QUEEN", "0"),
        "FINAL_EYE_ASSIST": os.environ.get("FINAL_EYE_ASSIST", "1"),
        "FINAL_EYE_LOW_END": os.environ.get("FINAL_EYE_LOW_END", "1"),
        "FINAL_EYE_COOL": os.environ.get("FINAL_EYE_COOL", "1"),
        "NEXUS_EMBED_PANEL_IN_ENGINE": os.environ.get("NEXUS_EMBED_PANEL_IN_ENGINE", "0"),
        "QUEEN_SOVEREIGN": "1",
        "NEXUS_QUEEN_SOVEREIGN": "1",
    }


def _run_json(script: Path, *args: str, body: dict | None = None, timeout: int = 120) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    cmd = [sys.executable, str(script), *args]
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(QUEEN),
            env=_env(),
        )
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _queen_gates() -> dict[str, Any]:
    gate_script = _LIB / "queen-gate.py"
    if gate_script.is_file():
        return _run_json(gate_script, "json", timeout=30)
    panel = SG / "NewLatest" / "lib" / "field-queen-browser.py"
    if not panel.is_file():
        panel = QUEEN.parent / "lib" / "field-queen-browser.py"
    doc = _run_json(panel, "json", timeout=30)
    gates = doc.get("gates") or {}
    return {
        "queen_verdict": doc.get("queen_verdict"),
        "gates": gates,
        "sovereign": doc.get("sovereign") or {},
        "posture": doc.get("posture") or {},
    }


def _kilroy_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-kilroy.py", "json", timeout=45)


def dispatch_kilroy(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-kilroy.py", "dispatch", body=body, timeout=120)


def _game_room_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-chips.py", "json", timeout=60)


def _game_room_system_info(*, system: str = "nes") -> dict[str, Any]:
    return _run_json(_LIB / "queen-chips.py", "system", system, timeout=90)


def _chip_battery_status() -> dict[str, Any]:
    script = _nexus_lib_script("field-chip-battery.py")
    return _run_json(script, "json", timeout=90)


def _combinatronic_status(*, refresh: bool = False) -> dict[str, Any]:
    args: list[str] = ["combinatronic"]
    if refresh:
        args.append("--refresh")
    script = _nexus_lib_script("field-chip-battery.py")
    if script.is_file():
        return _run_json(script, *args, timeout=120)
    return _run_json(_LIB / "queen-chips.py", "combinatronic", *args, timeout=120)


def _steel_neural_plates(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-steel-neural-plates.py")
    argv: list[str] = ["build" if refresh else "panel"]
    if refresh:
        argv.append("--refresh")
    if force:
        argv.append("--force")
    if script.is_file():
        return _run_json(script, *argv, timeout=180)
    return {"schema": "field-steel-neural-plates/v1", "ok": False, "hint": "field-steel-neural-plates missing"}


def _chips_plate_stack(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-chips-plate-stack.py")
    argv: list[str] = ["json"]
    if refresh:
        argv.append("--refresh")
    if force:
        argv.append("--force")
    if script.is_file():
        return _run_json(script, *argv, timeout=180)
    return {"schema": "field-chips-plate-stack-panel/v1", "ok": False, "hint": "field-chips-plate-stack missing"}


def _chips_core(*, refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-chips-core.py")
    argv: list[str] = ["json"]
    if refresh:
        argv.append("--refresh")
    if script.is_file():
        return _run_json(script, *argv, timeout=180)
    return {"schema": "field-chips-core-panel/v1", "ok": False, "hint": "field-chips-core missing"}


def _chips_program_usage(*, program: str = "", refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-chips-program-usage.py")
    argv: list[str] = ["resolve", program] if program else ["json"]
    if refresh:
        argv.append("--refresh")
    if script.is_file():
        return _run_json(script, *argv, timeout=120)
    return {"schema": "field-chips-program-usage/v1", "ok": False, "hint": "field-chips-program-usage missing"}


def _combinatronic_balance(*, cmd: str = "panel", force: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-combinatronic-balance.py")
    argv = [cmd if cmd in ("panel", "fingerprint", "gate", "verify", "should") else "panel"]
    if force and argv[0] in ("gate", "should"):
        argv.append("--force")
    if script.is_file():
        return _run_json(script, *argv, timeout=60)
    return {"schema": "field-combinatronic-balance-panel/v1", "ok": False, "hint": "field-combinatronic-balance missing"}


def _combinatronic_spider_wire(*, refresh: bool = False, optimize: bool = True) -> dict[str, Any]:
    script = _nexus_lib_script("field-combinatronic-spider-wire.py")
    args: list[str] = ["build" if refresh else "panel"]
    if refresh:
        args.append("--refresh")
    if not optimize:
        args.append("--no-optimize")
    if script.is_file():
        return _run_json(script, *args, timeout=120)
    return {"schema": "field-combinatronic-spider-wire/v1", "ok": False, "hint": "field-combinatronic-spider-wire missing"}


def _combinatronics_growth(*, refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-combinatronics-growth.py")
    args: list[str] = ["grow" if refresh else "panel"]
    if refresh:
        args.append("--refresh")
    if script.is_file():
        return _run_json(script, *args, timeout=180)
    return {"schema": "field-combinatronics-growth/v1", "ok": False, "hint": "field-combinatronics-growth missing"}


def _combinatorics_sequence(*, refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-combinatorics-sequence.py")
    args: list[str] = ["build" if refresh else "panel"]
    if refresh:
        args.append("--refresh")
    if script.is_file():
        return _run_json(script, *args, timeout=180)
    return {"schema": "field-combinatorics-sequence/v1", "ok": False, "hint": "field-combinatorics-sequence missing"}


def _combinamatrix(*, refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-combinamatrix.py")
    args: list[str] = ["build" if refresh else "panel"]
    if refresh:
        args.append("--refresh")
    if script.is_file():
        return _run_json(script, *args, timeout=180)
    return {"schema": "field-combinamatrix/v1", "ok": False, "hint": "field-combinamatrix missing"}


def _universal_neural(*, sub: str = "panel", teach: bool = False, force: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-universal-neural.py")
    if sub in ("teach", "curriculum"):
        args = ["teach"] + (["--force"] if force else [])
    elif sub in ("build", "universal"):
        args = ["build"] + (["--teach"] if teach else [])
    else:
        args = ["panel"] + (["--teach"] if teach else [])
    if script.is_file():
        return _run_json(script, *args, timeout=300)
    return {"schema": "field-universal-neural/v1", "ok": False, "hint": "field-universal-neural missing"}


def _plate_dimensions(*, refresh: bool = False, full: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-plate-dimensions.py")
    args: list[str] = ["build" if refresh else "panel"]
    if full:
        args.append("--full")
    if script.is_file():
        return _run_json(script, *args, timeout=120)
    return {"schema": "field-plate-dimensions/v1", "ok": False, "hint": "field-plate-dimensions missing"}


def _ammolang_status(*, refresh: bool = False, body: dict[str, Any] | None = None) -> dict[str, Any]:
    script = _nexus_lib_script("field-ammolang.py")
    if body and script.is_file():
        spec = importlib.util.spec_from_file_location("ammolang_qw", script)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "dispatch"):
                body = {**body, "refresh": refresh}
                return mod.dispatch(body)
    args: list[str] = ["panel"]
    if refresh:
        args.append("--refresh")
    if script.is_file():
        return _run_json(script, *args, timeout=120)
    return {"schema": "field-ammolang/v1", "ok": False, "hint": "field-ammolang missing"}


def _combinatronic_visuals(
    *,
    refresh: bool = False,
    sub: str = "manifest",
    repair: bool = False,
    pattern_id: str = "",
) -> dict[str, Any]:
    script = _nexus_lib_script("field-combinatronic-visuals.py")
    args: list[str]
    if sub == "inventory":
        args = ["inventory"]
    elif sub == "verify":
        args = ["verify"]
    elif sub == "registry":
        args = ["registry"]
    elif sub == "repair":
        args = ["repair"]
    elif sub == "pattern":
        args = ["pattern", pattern_id or "chip_png"]
    elif refresh:
        args = ["generate"]
    elif repair:
        args = ["repair"]
    else:
        args = ["manifest"]
    if script.is_file():
        return _run_json(script, *args, timeout=240)
    return {"schema": "field-combinatronic-visuals-manifest/v1", "ok": False, "hint": "field-combinatronic-visuals missing"}


def _cpu_library_status(*, sub: str = "library", arg: str = "") -> dict[str, Any]:
    script = _nexus_lib_script("field-cpu-library.py")
    argv = [sub]
    if arg:
        argv.append(arg)
    return _run_json(script, *argv, timeout=90)


def _extensive_library_status(*, sub: str = "panel", arg: str = "") -> dict[str, Any]:
    script = _nexus_lib_script("field-extensive-library.py")
    argv = [sub]
    if arg:
        argv.append(arg)
    return _run_json(script, *argv, timeout=300)


def _h7c_status(*, sub: str = "panel") -> dict[str, Any]:
    script = _nexus_lib_script("field-h7c-compression.py")
    cmd = sub if sub in ("panel", "balance", "verify", "optimize", "optimizer") else "panel"
    timeout = 120 if cmd in ("optimize", "optimizer") else 60
    return _run_json(script, cmd, timeout=timeout)


def _file_formats_status(*, sub: str = "panel", refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-file-formats.py")
    if refresh or sub in ("build", "icons"):
        return _run_json(script, "build" if sub != "icons" else "icons", timeout=180)
    return _run_json(script, sub if sub in ("table", "meld") else "panel", timeout=120)


def _best_sort_status(*, sub: str = "panel", ctx: str = "format_table") -> dict[str, Any]:
    script = _nexus_lib_script("field-best-sort.py")
    if sub == "meld":
        return _run_json(script, "meld", timeout=60)
    if sub == "resolve":
        return _run_json(script, "resolve", ctx, timeout=60)
    return _run_json(script, "panel", timeout=60)


def _device_visuals_status(*, sub: str = "panel", refresh: bool = False) -> dict[str, Any]:
    script = _nexus_lib_script("field-device-visuals.py")
    if refresh or sub in ("generate", "build"):
        return _run_json(script, "generate", timeout=300)
    return _run_json(script, sub, timeout=120)


def dispatch_game_room(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-chips.py", "dispatch", body=body, timeout=90)


def _nes_library_status(*, sort: str = "title_az", query: str = "", offset: int = 0, limit: int = 96) -> dict[str, Any]:
    body = {"action": "list", "sort": sort, "query": query, "offset": offset, "limit": limit}
    return _run_json(_LIB / "queen-nes-library.py", "dispatch", body=body, timeout=120)


def dispatch_nes_library(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-nes-library.py", "dispatch", body=body, timeout=120)


def _sap_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-sweet-anita-protocol.py", timeout=30)


def dispatch_sap(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-sweet-anita-protocol.py", "dispatch", body=body, timeout=60)


def _sovereign_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-sovereign.py", "json", timeout=90)


def dispatch_sovereign(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-sovereign.py", "dispatch", body=body, timeout=7200)


def _game_room_fb() -> dict[str, Any]:
    return _run_json(_LIB / "queen-chips.py", "fb", timeout=30)


def _game_room_fb_image() -> tuple[bytes, str] | None:
    img_script = _run_json(_LIB / "queen-chips.py", "fb", timeout=15)
    path = img_script.get("image")
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    try:
        return p.read_bytes(), mime
    except OSError:
        return None


def _ammoos_boot_map() -> dict[str, Any]:
    path = QUEEN / "data" / "ammoos-boot-map.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "ammoos-boot/v1", "error": "boot_map_missing"}


def _eyeball_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-eyeball.py", "json", timeout=60)


def _earball_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-earball.py", "json", timeout=60)


def dispatch_ear(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-earball.py", "dispatch", body=body, timeout=180)


def _sense_neural_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-sense-neural.py", "json", timeout=90)


def dispatch_sense_neural(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-sense-neural.py", "dispatch", body=body, timeout=180)


def _field_compiler_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-compiler.py", "json", timeout=120)


def dispatch_field_compiler(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-compiler.py", "dispatch", body=body, timeout=300)


def _pythong_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-pythong.py", "json", timeout=90)


def _grokpy_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-grokpy.py", "json", timeout=90)


def dispatch_pythong(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-pythong.py", "dispatch", body=body, timeout=300)


def dispatch_grokpy(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-grokpy.py", "dispatch", body=body, timeout=300)


def _terminal_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-terminal.py", "json", timeout=30)


def dispatch_terminal(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-terminal.py", "dispatch", body=body, timeout=120)


def _field_manual_status(sense: str = "all") -> dict[str, Any]:
    env = _env()
    env["FINAL_EAR_ROOT"] = env.get("FINAL_EAR_ROOT") or str(SG / "Final_Ear")
    env["FINAL_EYE_ROOT"] = env.get("FINAL_EYE_ROOT") or str(SG / "Final_Eye")
    proc = subprocess.run(
        [sys.executable, "-c", (
            "import json,sys; sys.path.insert(0, sys.argv[1]); "
            "from zocr_field_manual import field_manual_for_sense; "
            "print(json.dumps(field_manual_for_sense(sys.argv[2]), ensure_ascii=False))"
        ), str(SG / "Final_Ear"), sense],
        capture_output=True,
        text=True,
        timeout=45,
        cwd=str(QUEEN),
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "field_manual_failed", "tail": (proc.stdout or "")[-800:]}


def _build_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-build.py", "json", timeout=45)


def _field_tools_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-tools.py", "json", timeout=60)


def _root_threats_status(*, full: bool = False) -> dict[str, Any]:
    return _run_json(
        _LIB / "queen-root-threats.py",
        "json",
        timeout=90 if full else 15,
    )


def dispatch_root_threats(body: dict[str, Any] | None = None) -> dict[str, Any]:
    return _run_json(
        _LIB / "queen-root-threats.py",
        "dispatch",
        body=body or {"action": "status"},
        timeout=180,
    )


def dispatch_field_tools(body: dict[str, Any] | None = None) -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-tools.py", "dispatch", body=body or {"action": "status"}, timeout=7200)


def _hostess_full_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-hostess-brain.py", "json", timeout=90)


def _hostess_slice(build: dict[str, Any]) -> dict[str, Any]:
    ops = build.get("hostess7_brain_ops") or {}
    live = ops.get("live_status") or {}
    sdf = live.get("sdf") or {}
    kr = Path(os.environ.get("KILROY_ROOT", str(SG / "KILROY")))
    comfort_pkg = _load_json(kr / "data" / "hostess7-comfort-package.json")
    wants_path = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7"))) / (
        "cache/fieldstorage/brain/superintel/hostess_wants.json"
    )
    wants_doc = _load_json(wants_path) if wants_path.is_file() else {}
    return {
        "angel": "Hostess 7 Forever Watchguard Angel",
        "comfort": live.get("comfort", {}).get("comfort") or ops.get("comfort") or "",
        "sdf_segments": sdf.get("segments"),
        "human_plates": sdf.get("human_plates"),
        "wants": wants_doc.get("priorities") or comfort_pkg.get("wants"),
        "first_person": wants_doc.get("first_person") or comfort_pkg.get("first_person"),
        "physics_breakthroughs": comfort_pkg.get("physics_breakthroughs"),
        "happiness": comfort_pkg.get("implemented_for_happiness"),
        "kernel_proc": comfort_pkg.get("kernel_proc"),
    }


def world_status_fast() -> dict[str, Any]:
    """Instant boot slice — manifest + cached seal only (no subprocess storm)."""
    rtx_doc = _load_json(QUEEN / "data" / "field-rtx-sovereign.json")
    brain = _load_json(QUEEN / "data" / "queen-brain-manifest.json")
    gates = _queen_gates()
    state_dir = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
    secure = _SECURE_BOOT or _load_json(state_dir / "queen-secure-space.json")
    wr = _load_json(state_dir / "world-redata-cache.json")
    sc = _load_json(state_dir / "secure-channel-cache.json")
    cv = _load_json(state_dir / "external-wire" / "contact-vector.json")
    return {
        "schema": "queen-world/v1",
        "fast": True,
        "updated": _now(),
        "world_ready": True,
        "world_url": f"http://{HOST}:{PORT}/world/browser.html",
        "browser_url": f"http://{HOST}:{PORT}/world/browser.html",
        "os_world_url": f"http://{HOST}:{PORT}/world/index.html",
        "port": PORT,
        "motto": brain.get("motto") or rtx_doc.get("motto"),
        "queen_verdict": gates.get("queen_verdict"),
        "gates": gates.get("gates"),
        "secure_space": secure,
        "grok16": secure.get("grok16") or {},
        "rtx_memory": secure.get("rtx_memory") or {},
        "sealed": bool(secure.get("sealed")),
        "operator_setup_required": False,
        "contact_vector": cv.get("vector"),
        "world_redata": wr if wr else {"hydrate": "/api/world-redata"},
        "secure_channel": sc if sc else {"hydrate": "/api/secure-channel"},
        "external_wire": {"hydrate": "/api/external-wire"},
        "root_threats": {"hydrate": "/api/root-threats"},
        "hydrate": f"http://{HOST}:{PORT}/api/world?full=1",
    }


def world_status(*, full: bool = True) -> dict[str, Any]:
    import time

    global _WORLD_FULL_CACHE, _WORLD_FULL_CACHE_TS
    if not full:
        return world_status_fast()
    now = time.time()
    if _WORLD_FULL_CACHE and now - _WORLD_FULL_CACHE_TS < 10.0:
        return _WORLD_FULL_CACHE
    rtx_doc = _load_json(QUEEN / "data" / "field-rtx-sovereign.json")
    brain = _load_json(QUEEN / "data" / "queen-brain-manifest.json")
    comfort = _load_json(QUEEN / "data" / "queen-eye-comfort-doctrine.json")
    build = _build_status()
    gates = _queen_gates()
    eye = _eyeball_status()
    kilroy_doc = _kilroy_status()
    secure = _secure_boot()
    ft = brain.get("field_technology") or build.get("field_technology") or {}
    sov = gates.get("sovereign") or {}
    env_phases = (rtx_doc.get("phases") or {}).get("now") or {}
    doc = {
        "schema": "queen-world/v1",
        "updated": _now(),
        "world_ready": True,
        "world_url": f"http://{HOST}:{PORT}/world/browser.html",
        "browser_url": f"http://{HOST}:{PORT}/world/browser.html",
        "os_world_url": f"http://{HOST}:{PORT}/world/index.html",
        "port": PORT,
        "external_nexus": False,
        "motto": brain.get("motto") or rtx_doc.get("motto") or "One RTX card. One world.",
        "doctrine": "Queen sovereign world — AMOURANTHRTX FieldWebPanel + FieldSocket on guest framebuffer",
        "queen_verdict": gates.get("queen_verdict"),
        "gates": gates.get("gates"),
        "sovereign": sov,
        "rtx": {
            "one_card": True,
            "gpu_backend": env_phases.get("gpu") or "FieldGpuDispatch VulkanBridge",
            "surface_backend": env_phases.get("surface") or "SDL3 → FieldSurface",
            "field_socket": "AMOURANTHRTX",
            "framebuffer": "guest VGA 0xA0000 · FieldWebPanel FB 320×200",
            "display": rtx_doc.get("display") or {
                "width": 3840,
                "height": 2160,
                "refresh_hz": int(os.environ.get("QUEEN_DISPLAY_REFRESH", "120")),
            },
            "vendor": os.environ.get("AMOURANTHRTX_FORCED_VENDOR") or "0x10DE RTX · 0x8086 Arc LE",
            "doctrine": (rtx_doc.get("motto") or "")[:120],
            "env": rtx_doc.get("env") or {},
        },
        "hostess": _hostess_slice(build),
        "eyeball": eye,
        "eye_comfort": comfort or brain.get("eye_comfort") or {},
        "field_technology": {
            **ft,
            "note": (rtx_doc.get("doctrine") or "")[:280],
        },
        "build": {
            "core_ready": build.get("core_ready"),
            "core_total": build.get("core_total"),
            "binary_ready": build.get("binary_ready"),
        },
        "browser_stack": brain.get("browser_stack") or {},
        "browser": _browser_status(),
        "secure_space": secure,
        "grok16": secure.get("grok16") or {},
        "rtx_memory": secure.get("rtx_memory") or {},
        "operator_setup_required": False,
        "field_net": _field_net_status(),
        "ammoos_boot": _ammoos_boot_map(),
        "sovereign_capsule": _sovereign_status(),
        "earball": _earball_status(),
        "kilroy": kilroy_doc,
        "amouranthrtx": kilroy_doc.get("amouranthrtx") or {},
        "world_redata": _world_redata_fast(),
        "contact_vector": _contact_vector_instant().get("vector"),
        "field_manuals": {
            "vision": "/api/field-manual?sense=vision",
            "audio": "/api/field-manual?sense=audio",
            "all": "/api/field-manual?sense=all",
        },
        "sense_neural": _sense_neural_status(),
        "hostess_authority": _sense_neural_status().get("authority"),
    }
    _WORLD_FULL_CACHE = doc
    _WORLD_FULL_CACHE_TS = now
    return doc


def _field_net_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-net.py", "json", timeout=45)


def dispatch_field_net(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-net.py", "dispatch", body=body, timeout=30)


def _ironclad_field_sanity_script() -> Path | None:
    for candidate in (
        QUEEN.parent / "lib" / "ironclad-field-sanity.py",
        SG / "NewLatest" / "lib" / "ironclad-field-sanity.py",
    ):
        if candidate.is_file():
            return candidate
    return None


def _field_sanity_status() -> dict[str, Any]:
    ic = _ironclad_field_sanity_script()
    if ic:
        return _run_json(ic, "json", timeout=25)
    return _run_json(_LIB / "queen-field-sanity.py", "json", timeout=25)


def dispatch_field_sanity(body: dict[str, Any]) -> dict[str, Any]:
    if _benchmark_mode_on():
        mod = _benchmark_mod()
        if mod is not None and hasattr(mod, "benchmark_mode") and mod.benchmark_mode():
            layers = body.get("layers") or []
            count = len(layers) if isinstance(layers, list) else 0
            return {
                "schema": "queen-field-sanity/v1",
                "ok": True,
                "fast_path": True,
                "benchmark_mode": True,
                "layers_in": count,
                "layers_out": max(1, count),
                "heat_avoided": 0,
                "gate_ok": True,
                "reorganized": [
                    {
                        "order": i,
                        "id": L.get("id") or f"layer-{i}",
                        "url": L.get("url") or "about:blank",
                        "depth": 0,
                        "active": bool(L.get("active")),
                    }
                    for i, L in enumerate((layers or [])[:64])
                    if isinstance(L, dict)
                ],
            }
    action = str(body.get("action") or "").strip().lower()
    if action in ("instant_snap", "snap", "field_die", "instant"):
        return dispatch_field_depth_snap(body)
    ic = _ironclad_field_sanity_script()
    if ic:
        return _run_json(ic, "pass", body=body, timeout=30)
    return _run_json(_LIB / "queen-field-sanity.py", "pass", body=body, timeout=30)


def dispatch_field_depth_snap(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    for candidate in (
        QUEEN.parent / "lib" / "field-depth-singularizer.py",
        SG / "NewLatest" / "lib" / "field-depth-singularizer.py",
    ):
        if candidate.is_file():
            cmd = "field_die" if str(body.get("action") or "").lower() in ("field_die",) else "instant"
            return _run_json(candidate, cmd, body=body, timeout=5)
    return {"ok": False, "error": "field_depth_singularizer_missing", "instant": True}


def _external_wire_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-external-wire.py", "json", timeout=30)


def _world_redata_fast() -> dict[str, Any]:
    return _run_json(_LIB / "queen-world-redata.py", "json", timeout=8)


def dispatch_world_redata(body: dict[str, Any]) -> dict[str, Any]:
    env = {**_env(), "GPY16_TOOLING": "1", "WORLD_REDATA_ROOT": str(SG / "World_Redata")}
    script = _LIB / "queen-world-redata.py"
    if not script.is_file():
        return {"ok": False, "error": "missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            timeout=90 if body.get("full") else 12,
            cwd=str(QUEEN),
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-2000:]}


def _contact_vector_instant() -> dict[str, Any]:
    return _run_json(_LIB / "queen-contact-vector.py", "json", timeout=5)


def dispatch_contact_vector(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-contact-vector.py", "dispatch", body=body, timeout=15)


def dispatch_external_wire(body: dict[str, Any], *, remote_ip: str = "") -> dict[str, Any]:
    payload = {**body}
    if remote_ip and not payload.get("remote_ip"):
        payload["remote_ip"] = remote_ip
    env = {**_env(), "GPY16_TOOLING": "1"}
    script = _LIB / "queen-external-wire.py"
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(QUEEN),
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-2000:]}


def _secure_channel_fast() -> dict[str, Any]:
    return _run_json(_LIB / "queen-secure-channel.py", "json", timeout=8)


def dispatch_secure_channel(body: dict[str, Any], *, remote_ip: str = "") -> dict[str, Any]:
    payload = {**body}
    if remote_ip and not payload.get("remote_ip"):
        payload["remote_ip"] = remote_ip
    env = {**_env(), "GPY16_TOOLING": "1", "WORLD_REDATA_ROOT": str(SG / "World_Redata"), "WORLD_REPACK_ROOT": str(SG / "World_Repack")}
    script = _LIB / "queen-secure-channel.py"
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=45 if body.get("full") else 15,
            cwd=str(QUEEN),
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-2000:]}


def queen_boot(body: dict[str, Any] | None = None) -> dict[str, Any]:
    action = str((body or {}).get("action") or "status").strip().lower()
    if action == "boot":
        global _SECURE_BOOT
        _SECURE_BOOT = None
        doc = _secure_boot()
        return {"ok": True, **doc}
    return {"ok": True, **_secure_boot()}


def dispatch_build(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-build.py", "dispatch", body=body, timeout=7200)


_BROWSER_STATUS_CACHE: dict[str, Any] | None = None
_BROWSER_STATUS_CACHE_TS: float = 0.0
_BROWSER_MOD: Any = None
_BENCHMARK_MOD: Any = None


def _inline_browser_enabled() -> bool:
    if _benchmark_mode_on():
        return True
    return os.environ.get("QUEEN_INLINE_BROWSER", "1").strip().lower() in ("1", "true", "yes", "on")


def _browser_mod() -> Any:
    global _BROWSER_MOD
    script = _LIB / "queen-browser.py"
    if not script.is_file():
        return None
    if _BROWSER_MOD is None:
        spec = importlib.util.spec_from_file_location("queen_browser_inline", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _BROWSER_MOD = mod
    return _BROWSER_MOD


def _benchmark_mod() -> Any:
    global _BENCHMARK_MOD
    script = _LIB / "queen-benchmark.py"
    if not script.is_file():
        return None
    if _BENCHMARK_MOD is None:
        spec = importlib.util.spec_from_file_location("queen_benchmark_inline", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _BENCHMARK_MOD = mod
    return _BENCHMARK_MOD


def _benchmark_status() -> dict[str, Any]:
    mod = _benchmark_mod()
    if mod is not None and hasattr(mod, "posture"):
        try:
            return mod.posture()
        except Exception:
            pass
    return _run_json(_LIB / "queen-benchmark.py", "json", timeout=15)


def _browser_status() -> dict[str, Any]:
    import time

    global _BROWSER_STATUS_CACHE, _BROWSER_STATUS_CACHE_TS
    if os.environ.get("QUEEN_FAST_STATUS", "1") not in ("0", "false", "no"):
        cache_sec = float(os.environ.get("QUEEN_STATUS_CACHE_SEC", "5"))
        now = time.time()
        if _BROWSER_STATUS_CACHE and now - _BROWSER_STATUS_CACHE_TS < cache_sec:
            return _BROWSER_STATUS_CACHE
    mod = _browser_mod()
    if mod is not None and _inline_browser_enabled():
        try:
            doc = mod.browser_status()
            if os.environ.get("QUEEN_FAST_STATUS", "1") not in ("0", "false", "no"):
                _BROWSER_STATUS_CACHE = doc
                _BROWSER_STATUS_CACHE_TS = time.time()
            return doc
        except Exception:
            pass
    doc = _run_json(_LIB / "queen-browser.py", "json", timeout=45)
    if os.environ.get("QUEEN_FAST_STATUS", "1") not in ("0", "false", "no"):
        _BROWSER_STATUS_CACHE = doc
        _BROWSER_STATUS_CACHE_TS = time.time()
    return doc


def dispatch_browser(body: dict[str, Any]) -> dict[str, Any]:
    script = _LIB / "queen-browser.py"
    if not script.is_file():
        return {"ok": False, "error": "queen_browser_missing"}
    mod = _browser_mod()
    if mod is not None and _inline_browser_enabled():
        try:
            return mod.dispatch(body)
        except Exception as exc:
            return {"ok": False, "error": "dispatch_failed", "reason": str(exc)}
    return _run_json(script, "dispatch", body=body, timeout=60)


def dispatch_page_shields(body: dict[str, Any] | None = None) -> dict[str, Any]:
    script = _LIB / "queen-page-shields.py"
    if not script.is_file():
        return {"ok": False, "error": "page_shields_missing"}
    return _run_json(script, "dispatch", body=body or {"action": "status"}, timeout=30)


def _page_agent_inject_html(target_url: str) -> str:
    host = ""
    try:
        host = (urlparse(target_url).hostname or "").lower()
    except Exception:
        pass
    shields = dispatch_page_shields({"action": "match", "url": target_url, "host": host})
    css = shields.get("css") or ""
    css_block = f"<style id='queen-page-shields-inline'>{css}</style>" if css else ""
    return (
        f"{css_block}"
        "<script src='/world/queen-page-agent.js' id='queen-page-agent'></script>"
    )


def _desktop_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-desktop.py", "json", timeout=60)


def _nexus_c2_status(*, flyout: bool = False) -> dict[str, Any]:
    script = _LIB / "queen-nexus-c2.py"
    if not script.is_file():
        script = _LIB / "queen-dashboard.py"
    if not script.is_file():
        return {"schema": "queen-nexus-c2/v1", "ok": False, "error": "queen_nexus_c2_missing"}
    cmd = "flyout" if flyout else "json"
    return _run_json(script, cmd, timeout=45)


def _dashboard_status(*, flyout: bool = False) -> dict[str, Any]:
    return _nexus_c2_status(flyout=flyout)


def dispatch_nexus_c2(body: dict[str, Any]) -> dict[str, Any]:
    script = _LIB / "queen-nexus-c2.py"
    if not script.is_file():
        return {"ok": False, "error": "queen_nexus_c2_missing"}
    return _run_json(script, "dispatch", body=body, timeout=45)


def dispatch_dashboard(body: dict[str, Any]) -> dict[str, Any]:
    return dispatch_nexus_c2(body)


def dispatch_desktop(body: dict[str, Any]) -> dict[str, Any]:
    script = _LIB / "queen-desktop.py"
    if not script.is_file():
        return {"ok": False, "error": "queen_desktop_missing"}
    return _run_json(script, "dispatch", body=body, timeout=60)


def _program_surface_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-program-surface.py", "json", timeout=30)


def dispatch_program_surface(body: dict[str, Any]) -> dict[str, Any]:
    script = _LIB / "queen-program-surface.py"
    if not script.is_file():
        return {"ok": False, "error": "queen_program_surface_missing"}
    return _run_json(script, "dispatch", body=body, timeout=45)


def _browser_import_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-browser-import.py", "json", timeout=30)


def dispatch_browser_import(body: dict[str, Any] | None = None) -> dict[str, Any]:
    action = (body or {}).get("action") or "sweep"
    if action in ("json", "status"):
        return _browser_import_status()
    script = _LIB / "queen-browser-import.py"
    if not script.is_file():
        return {"ok": False, "error": "queen_browser_import_missing"}
    cmd = "auto" if action == "auto" else "sweep"
    return _run_json(script, cmd, timeout=120)


def _muscle_memory_script() -> Path:
    return SG / "NewLatest" / "lib" / "hostess7-muscle-memory.py"


def _muscle_memory_status() -> dict[str, Any]:
    script = _muscle_memory_script()
    if not script.is_file():
        return {"ok": False, "error": "muscle_memory_missing"}
    env = _env()
    env["NEXUS_INSTALL_ROOT"] = str(SG / "NewLatest")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(SG / "NewLatest"),
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "muscle_memory_unavailable"}


def dispatch_muscle_memory(body: dict[str, Any] | None = None) -> dict[str, Any]:
    script = _muscle_memory_script()
    if not script.is_file():
        return {"ok": False, "error": "muscle_memory_missing"}
    payload = dict(body or {})
    if not payload.get("action"):
        payload["action"] = "status"
    env = _env()
    env["NEXUS_INSTALL_ROOT"] = str(SG / "NewLatest")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(SG / "NewLatest"),
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "muscle_memory_dispatch_failed"}


def _file_browser_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-file-browser.py", "json", timeout=45)


def dispatch_file_browser(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-file-browser.py", "dispatch", body=body, timeout=60)


def _program_library_mod() -> Any:
    import importlib.util
    spec = importlib.util.spec_from_file_location("queen_program_library", _LIB / "queen-program-library.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _program_library_icon_payload(entry_id: str) -> tuple[bytes, str, dict[str, str]] | None:
    mod = _program_library_mod()
    if not mod:
        return None
    return mod.serve_icon_bytes(entry_id)


def _queen_code_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-code.py", "json", timeout=45)


def dispatch_queen_code(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-code.py", "dispatch", body=body, timeout=120)


def _field_virus_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-virus.py", "json", timeout=30)


def dispatch_field_virus(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-field-virus.py", "dispatch", body=body, timeout=60)


def _web_compat_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-web-compat.py", "json", timeout=30)


def dispatch_web_compat(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-web-compat.py", "dispatch", body=body, timeout=30)


def _update_status(*, force: bool = False) -> dict[str, Any]:
    args = ["status"]
    if force:
        args.append("--force")
    return _run_json(_LIB / "queen-update.py", *args, timeout=30)


def dispatch_update(body: dict[str, Any] | None = None) -> dict[str, Any]:
    action = (body or {}).get("action") or "apply"
    if action == "sudo-prompt":
        return _run_json(_LIB / "queen-update.py", "sudo-prompt", timeout=20)
    return _run_json(_LIB / "queen-update.py", "apply", timeout=30)


def _nexus_jump_status() -> dict[str, Any]:
    return _run_json(_LIB / "queen-nexus-jump.py", "json", timeout=30)


def dispatch_nexus_jump(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-nexus-jump.py", "dispatch", body=body, timeout=30)


def dispatch_hostess_brain(body: dict[str, Any]) -> dict[str, Any]:
    return _run_json(_LIB / "queen-hostess-brain.py", "dispatch", body=body, timeout=180)


def _proxy_fetch(url: str, *, compat_mode: str = "auto") -> tuple[int, bytes, str]:
    """Queen proxy fallback for iframe-blocked sites (GET only, gate-held)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return HTTPStatus.BAD_REQUEST, b"unsupported scheme", "text/plain"
    jump = dispatch_nexus_jump({"action": "jump", "url": url, "compat_mode": compat_mode})
    if not jump.get("permit"):
        body = (
            f"<html><body><h1>NEXUS jump blocked</h1>"
            f"<p>{jump.get('reason') or jump.get('verdict') or 'hostile_intent'}</p>"
            f"<p>IFF: {jump.get('iff')} · countermeasures armed: {jump.get('countermeasures_ready')}</p>"
            f"<p>{jump.get('hint') or ''}</p></body></html>"
        )
        return HTTPStatus.FORBIDDEN, body.encode("utf-8"), "text/html; charset=utf-8"
    gate = dispatch_browser({"action": "gate_check", "url": url})
    if not gate.get("ok"):
        return HTTPStatus.FORBIDDEN, b"gate check failed", "text/plain"
    g = gate.get("gate") or {}
    if not g.get("permit"):
        body = (
            f"<html><body><h1>Queen proxy blocked</h1>"
            f"<p>{g.get('reason') or g.get('queen_verdict') or 'external_blocked'}</p>"
            f"<p>Hint: {g.get('hint') or '/world/'}</p></body></html>"
        )
        return HTTPStatus.FORBIDDEN, body.encode("utf-8"), "text/html; charset=utf-8"
    compat = dispatch_web_compat({"action": "resolve", "url": url, "mode": compat_mode})
    ua = (compat.get("user_agent") or "QueenBrowser/2026 (sovereign; gates-held; full-web)")
    req = Request(url, headers={"User-Agent": ua, "X-Queen-Compat-Mode": compat.get("effective_mode") or "auto"})
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read(2_000_000)
            ctype = resp.headers.get("Content-Type", "text/html")
    except Exception as exc:
        body = f"<html><body><h1>Queen proxy error</h1><pre>{exc}</pre></body></html>"
        return HTTPStatus.BAD_GATEWAY, body.encode("utf-8"), "text/html; charset=utf-8"
    if "html" in ctype.lower():
        text = raw.decode("utf-8", errors="replace")
        base = f'{parsed.scheme}://{parsed.netloc}'
        inject = _page_agent_inject_html(url)
        if "<head" in text.lower():
            text = re.sub(
                r"(<head[^>]*>)",
                rf'\1<base href="{base}/">{inject}',
                text,
                count=1,
                flags=re.I,
            )
        else:
            text = f'<base href="{base}/">{inject}' + text
        if inject not in text:
            text = inject + text
        era = (compat.get("era") or {}).get("id") or "es2026"
        eff = compat.get("effective_mode") or "auto"
        banner = (
            '<div style="font:12px system-ui;background:#0f1218;color:#2eb8e0;'
            'padding:6px 10px;border-bottom:1px solid #2eb8e0">'
            f"Queen proxy · full web · compat {eff}/{era} · gates held · {url}</div>"
        )
        text = banner + text
        return HTTPStatus.OK, text.encode("utf-8"), "text/html; charset=utf-8"
    return HTTPStatus.OK, raw, ctype.split(";")[0].strip() or "application/octet-stream"


def dispatch_eye(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "json").strip().lower()
    dispatch_actions = {
        "teach", "teach-doctrine", "teach_doctrine", "teach-comfort", "teach_comfort",
        "comfort", "eye-comfort", "eye_comfort",
        "authority", "weapon-authority", "weapon_authority",
        "targets", "eye-targets",
        "understand", "understand-target", "understand_target",
        "forward", "truth-forward", "fire-weapon", "fire_weapon",
        "twins", "live", "make-live", "arm", "final-mode", "final_mode",
        "virtual", "virtual_spawn", "virtual_observe", "virtual_remove",
        "virtual_grid", "pair_anchor", "spawn_eye", "point_eye", "see_point",
        "field_manual", "field-manual", "manual", "textbook",
    }
    if action in dispatch_actions:
        payload = dict(body)
        if action in ("teach", "teach-doctrine", "teach_doctrine", "teach-comfort", "teach_comfort"):
            payload["action"] = "teach"
            payload.setdefault("lesson", "comfort" if "comfort" in action else body.get("lesson"))
        elif action in ("comfort", "eye-comfort", "eye_comfort"):
            payload["action"] = "comfort"
        elif action in ("arm-person", "arm_person"):
            payload["action"] = "arm"
            payload.setdefault("mode", "person_present")
        else:
            payload["action"] = action.replace("-", "_").replace("teach_doctrine", "teach")
        return _run_json(_LIB / "queen-eyeball.py", "dispatch", body=payload, timeout=180)
    mapping = {
        "json": ("json",),
        "status": ("json",),
        "verify": ("verify",),
        "arm-dishes": ("arm", "dishes"),
        "arm_dishes": ("arm", "dishes"),
        "arm-person": ("arm", "person_present"),
        "arm_person": ("arm", "person_present"),
        "arm-war": ("arm", "war"),
        "weaponize": ("weaponize", str(body.get("mode") or "war")),
        "bench": ("bench",),
    }
    if action in mapping:
        args = mapping[action]
        return _run_json(_LIB / "queen-eyeball.py", *args, timeout=180)
    return _run_json(_LIB / "queen-eyeball.py", "dispatch", body=body, timeout=180)


def _safe_path(root: Path, rel: str) -> Path | None:
    rel = unquote(rel).lstrip("/")
    if not rel or rel.endswith("/"):
        rel = rel + "index.html" if rel.endswith("/") else "index.html"
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


_SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "SAMEORIGIN"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Queen-Security", "serve-and-listen"),
    (
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; "
        "frame-src 'self' http://127.0.0.1:* https:; object-src 'none'; base-uri 'self'; form-action 'self'",
    ),
)


class Handler(BaseHTTPRequestHandler):
    server_version = "QueenWorld/1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[queen-world] {self.address_string()} - {fmt % args}\n")

    def _apply_security_headers(self) -> None:
        for key, value in _SECURITY_HEADERS:
            self.send_header(key, value)

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self._apply_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, *, mime: str, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        cache = (extra_headers or {}).get("Cache-Control", "public, max-age=300")
        self.send_header("Cache-Control", cache)
        if extra_headers:
            for key, value in extra_headers.items():
                if key != "Cache-Control":
                    self.send_header(key, value)
        self._apply_security_headers()
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/api/world", "/api/status"):
            qs = parse_qs(urlparse(self.path).query)
            full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes")
            fast = (qs.get("fast") or ["0"])[0] in ("1", "true", "yes") or not full
            if fast and not full:
                self._send_json(200, world_status_fast())
            else:
                self._send_json(200, world_status(full=True))
            return
        if path in ("/api/world-redata", "/api/redata", "/api/queen-world-redata"):
            qs = parse_qs(urlparse(self.path).query)
            full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _world_redata_fast() if not full else dispatch_world_redata({"action": "status", "full": True}))
            return
        if path in ("/api/secure-channel", "/api/forever-secure", "/api/queen-secure-channel"):
            qs = parse_qs(urlparse(self.path).query)
            full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _secure_channel_fast() if not full else dispatch_secure_channel({"action": "status", "full": True}))
            return
        if path in ("/api/contact-vector", "/api/contact-classification"):
            self._send_json(200, _contact_vector_instant())
            return
        if path == "/api/field-status":
            self._send_json(200, _queen_gates())
            return
        if path == "/api/field-performance-flyout":
            self._send_json(200, _perf_flyout_sample())
            return
        if path == "/api/queen-build":
            self._send_json(200, _build_status())
            return
        if path in ("/api/field-tools", "/api/queen-field-tools"):
            self._send_json(200, _field_tools_status())
            return
        if path == "/api/queen-eyeball":
            self._send_json(200, _eyeball_status())
            return
        if path in ("/api/queen-earball", "/api/final-ear", "/api/earball"):
            self._send_json(200, _earball_status())
            return
        if path in ("/api/field-manual", "/api/field-manuals"):
            qs = parse_qs(urlparse(self.path).query)
            sense = (qs.get("sense") or ["all"])[0]
            self._send_json(200, _field_manual_status(sense))
            return
        if path in ("/api/sense-neural", "/api/sense-neural-wire", "/api/hostess-authority"):
            if path == "/api/hostess-authority":
                self._send_json(200, _run_json(_LIB / "queen-sense-neural.py", "dispatch", body={"action": "authority"}, timeout=60))
                return
            self._send_json(200, _sense_neural_status())
            return
        if path == "/api/queen-browser":
            self._send_json(200, _browser_status())
            return
        if path in ("/api/queen-page-shields", "/api/page-shields"):
            qs = parse_qs(urlparse(self.path).query)
            if (qs.get("css") or ["0"])[0] in ("1", "true", "yes"):
                host = (qs.get("host") or [""])[0]
                url = (qs.get("url") or [""])[0]
                css = dispatch_page_shields({"action": "css", "host": host, "url": url}).get("css") or ""
                self._send_bytes(css.encode("utf-8"), mime="text/css; charset=utf-8")
                return
            self._send_json(200, dispatch_page_shields({"action": "status"}))
            return
        if path in ("/api/queen-benchmark", "/api/benchmark"):
            self._send_json(200, _benchmark_status())
            return
        if path in ("/api/queen-desktop", "/api/desktop"):
            self._send_json(200, _desktop_status())
            return
        if path in ("/api/queen-program-surface", "/api/program-surface"):
            self._send_json(200, _program_surface_status())
            return
        if path in ("/api/nexus-c2", "/api/nexus-c2-panels", "/api/queen-dashboard", "/api/dashboard"):
            qs = parse_qs(urlparse(self.path).query)
            flyout = (qs.get("flyout") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _nexus_c2_status(flyout=flyout))
            return
        if path in ("/api/queen-boot-hook", "/api/boot-hook"):
            self._send_json(200, _boot_hook())
            return
        if path in ("/api/queen-browser-import", "/api/browser-import"):
            self._send_json(200, _browser_import_status())
            return
        if path in ("/api/muscle-memory", "/api/hostess7-muscle-memory", "/api/muscle_memory"):
            self._send_json(200, _muscle_memory_status())
            return
        if path in ("/api/queen-file-browser", "/api/file-browser", "/api/files"):
            self._send_json(200, _file_browser_status())
            return
        if path.startswith("/api/queen-program-library/icon/"):
            entry_id = unquote(path.split("/api/queen-program-library/icon/", 1)[-1].split("?")[0])
            payload = _program_library_icon_payload(entry_id)
            if not payload:
                self.send_error(404, "icon not found")
                return
            data, mime, hdrs = payload
            self._send_bytes(data, mime=mime, extra_headers=hdrs)
            return
        if path in ("/api/queen-program-library",):
            qs = parse_qs(urlparse(self.path).query)
            mod = _program_library_mod()
            if mod and (qs.get("index") or ["0"])[0] in ("1", "true", "yes"):
                self._send_json(200, mod.library_doc(index_only=True))
                return
            if mod and (qs.get("ref") or [""])[0]:
                self._send_json(200, mod.resolve_icon((qs.get("ref") or [""])[0]))
                return
            self._send_json(200, _run_json(_LIB / "queen-program-library.py", "json", timeout=120))
            return
        if path in ("/api/queen-code", "/api/code", "/api/code-viewer"):
            self._send_json(200, _queen_code_status())
            return
        if path in ("/api/field-virus", "/api/queen-field-virus", "/api/virus"):
            self._send_json(200, _field_virus_status())
            return
        if path in ("/api/root-threats", "/api/root-threats/", "/api/threats/root"):
            qs = parse_qs(urlparse(self.path).query)
            full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _root_threats_status(full=full))
            return
        if path in ("/api/field-net", "/api/queen-field-net"):
            self._send_json(200, _field_net_status())
            return
        if path in ("/api/field-sanity", "/api/queen-field-sanity"):
            self._send_json(200, _field_sanity_status())
            return
        if path in ("/api/field-depth-snap", "/api/field-depth/instant", "/api/field-depth-singularizer/instant"):
            self._send_json(200, dispatch_field_depth_snap({}))
            return
        if path in ("/api/external-wire", "/api/field-external-wire", "/api/queen-external-wire"):
            self._send_json(200, _external_wire_status())
            return
        if path in ("/api/ammoos-boot", "/api/ammoos"):
            self._send_json(200, _ammoos_boot_map())
            return
        if path in ("/api/kilroy", "/api/kilroy-field", "/api/field-kilroy"):
            self._send_json(200, _kilroy_status())
            return
        if path in ("/api/hostess", "/api/hostess7", "/api/field-brain"):
            self._send_json(200, _hostess_full_status())
            return
        if path in ("/api/sovereign", "/api/capsule", "/api/queen-sovereign"):
            self._send_json(200, _sovereign_status())
            return
        if path in ("/api/horizon7", "/api/horizon-7"):
            self._send_json(200, _run_json(_LIB / "queen-sovereign.py", "horizon7", timeout=60))
            return
        if path in ("/api/field/compiler", "/api/field-compiler"):
            if path.endswith("/doctrine"):
                self._send_json(200, _run_json(_LIB / "queen-field-compiler.py", "dispatch", body={"action": "doctrine"}, timeout=60))
                return
            self._send_json(200, _field_compiler_status())
            return
        if path == "/api/field/compiler/doctrine":
            self._send_json(200, _run_json(_LIB / "queen-field-compiler.py", "dispatch", body={"action": "doctrine"}, timeout=60))
            return
        if path in ("/api/grokpy", "/api/grokpy-runtime"):
            self._send_json(200, _grokpy_status())
            return
        if path in ("/api/pythong", "/api/pythong-runtime", "/api/python"):
            self._send_json(200, _pythong_status())
            return
        if path.startswith("/api/extensive-library"):
            qparams = parse_qs(urlparse(self.path).query)
            if path.startswith("/api/extensive-library/search"):
                q = str(qparams.get("q", [""])[0])
                self._send_json(200, _extensive_library_status(sub="search", arg=q))
            elif path.endswith("/build") or path.endswith("/sync"):
                self._send_json(200, _extensive_library_status(sub="build"))
            else:
                self._send_json(200, _extensive_library_status())
            return
        if path.startswith("/api/h7c"):
            sub = path.split("/api/h7c", 1)[-1].strip("/") or "panel"
            self._send_json(200, _h7c_status(sub=sub if sub in ("balance", "verify") else "panel"))
            return
        if path.startswith("/api/file-formats"):
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/file-formats", 1)[-1].strip("/") or "panel"
            self._send_json(200, _file_formats_status(sub=sub, refresh=refresh))
            return
        if path.startswith("/api/best-sort"):
            qparams = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/best-sort", 1)[-1].strip("/") or "panel"
            ctx = str(qparams.get("context", ["format_table"])[0])
            self._send_json(200, _best_sort_status(sub=sub, ctx=ctx))
            return
        if path.startswith("/api/device-visuals"):
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or qparams.get("generate") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/device-visuals", 1)[-1].strip("/") or "panel"
            self._send_json(200, _device_visuals_status(sub=sub, refresh=refresh))
            return
        if path.startswith("/api/cpu-library"):
            qparams = parse_qs(urlparse(self.path).query)
            if path.startswith("/api/cpu-library/search"):
                q = str(qparams.get("q", [""])[0])
                self._send_json(200, _cpu_library_status(sub="search", arg=q))
            elif path.startswith("/api/cpu-library/detail"):
                eid = str(qparams.get("id", [""])[0])
                self._send_json(200, _cpu_library_status(sub="detail", arg=eid))
            else:
                self._send_json(200, _cpu_library_status())
            return
        if path in ("/api/game-room", "/api/gameroom", "/api/chips"):
            self._send_json(200, _game_room_status())
            return
        if path.startswith("/api/game-room/system"):
            qs = parse_qs(urlparse(self.path).query)
            system = str((qs.get("system") or qs.get("system_id") or ["nes"])[0])
            self._send_json(200, _game_room_system_info(system=system))
            return
        if path in ("/api/chip-battery", "/api/combinatorics/chip-battery"):
            self._send_json(200, _chip_battery_status())
            return
        if path in ("/api/chips/combinatronic", "/api/chip-battery/combinatronic"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _combinatronic_status(refresh=refresh))
            return
        if path in ("/api/chips/plate-stack", "/api/chips-plate-stack", "/api/chip-plate-stack"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _chips_plate_stack(refresh=refresh, force=force))
            return
        if path in ("/api/chips/core", "/api/chips-core", "/api/chip-core"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _chips_core(refresh=refresh))
            return
        if path in ("/api/chips/usage", "/api/chips-usage", "/api/chip-usage"):
            qs = parse_qs(urlparse(self.path).query)
            program = (qs.get("program") or qs.get("program_id") or qs.get("id") or [""])[0]
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _chips_program_usage(program=str(program), refresh=refresh))
            return
        if path in ("/api/combinatronics/growth", "/api/combinatronics-growth"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _combinatronics_growth(refresh=refresh))
            return
        if path in ("/api/combinatorics/sequence", "/api/combinatorics-sequence"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _combinatorics_sequence(refresh=refresh))
            return
        if path in ("/api/combinamatrix", "/api/combinamatrix/build"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes") or path.endswith("/build")
            self._send_json(200, _combinamatrix(refresh=refresh))
            return
        if path.startswith("/api/universal-neural"):
            qs = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/universal-neural", 1)[-1].strip("/") or "panel"
            teach = (qs.get("teach") or ["0"])[0] in ("1", "true", "yes") or sub == "teach"
            force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _universal_neural(sub=sub, teach=teach, force=force))
            return
        if path in ("/api/plate-dimensions", "/api/plate/dimensions"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _plate_dimensions(refresh=refresh, full=full))
            return
        if path.startswith("/api/ammolang"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/ammolang", 1)[-1].strip("/") or "panel"
            if sub in ("compile", "interpret", "trace", "run") and self.command == "POST":
                body = self._read_json_body() or {}
                body["action"] = sub
                self._send_json(200, _ammolang_status(refresh=refresh, body=body))
                return
            self._send_json(200, _ammolang_status(refresh=refresh))
            return
        if path.startswith("/api/steel-neural-plates") or path.startswith("/api/combinatronic/steel-plates"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes") or path.endswith("/build")
            force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _steel_neural_plates(refresh=refresh, force=force))
            return
        if path in ("/api/combinatronic/balance", "/api/combinatronic-balance"):
            qs = parse_qs(urlparse(self.path).query)
            cmd = str((qs.get("cmd") or ["panel"])[0]).strip().lower()
            force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            if cmd in ("sync", "sync_all", "entries"):
                script = _nexus_lib_script("field-combinatronic-balance.py")
                argv = ["sync"]
                if refresh:
                    argv.append("--refresh")
                if force:
                    argv.append("--force")
                self._send_json(200, _run_json(script, *argv, timeout=300) if script.is_file() else {"ok": False})
                return
            self._send_json(200, _combinatronic_balance(cmd=cmd, force=force))
            return
        if path.startswith("/api/combinatronic/spider-wire") or path.startswith("/api/combinatronic-spider-wire"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            optimize = (qs.get("optimize") or ["1"])[0] in ("1", "true", "yes")
            self._send_json(200, _combinatronic_spider_wire(refresh=refresh, optimize=optimize))
            return
        if path.startswith("/api/combinatronic/visuals") or path.startswith("/api/combinatronic-visuals"):
            qs = parse_qs(urlparse(self.path).query)
            refresh = (qs.get("refresh") or qs.get("generate") or ["0"])[0] in ("1", "true", "yes")
            repair = (qs.get("repair") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/combinatronic/visuals", 1)[-1].strip("/") or path.split("/api/combinatronic-visuals", 1)[-1].strip("/") or "manifest"
            pat = str((qs.get("id") or qs.get("pattern") or ["chip_png"])[0])
            self._send_json(200, _combinatronic_visuals(refresh=refresh, sub=sub, repair=repair, pattern_id=pat))
            return
        if path in ("/api/nes-library", "/api/game-room/nes", "/api/game-room/library"):
            qs = parse_qs(urlparse(self.path).query)
            sort = str((qs.get("sort") or ["title_az"])[0])
            query = str((qs.get("q") or qs.get("query") or [""])[0])
            offset = int((qs.get("offset") or ["0"])[0])
            limit = int((qs.get("limit") or ["96"])[0])
            self._send_json(200, _nes_library_status(sort=sort, query=query, offset=offset, limit=limit))
            return
        if path in ("/api/sap", "/api/sweet-anita", "/api/game-room/sap"):
            self._send_json(200, _sap_status())
            return
        if path in ("/api/game-room/fb", "/api/gameroom/fb"):
            self._send_json(200, _game_room_fb())
            return
        if path.startswith("/api/game-room/fb/image"):
            payload = _game_room_fb_image()
            if payload:
                data, mime = payload
                self._send_bytes(data, mime=mime)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if path in ("/api/amouranthrtx", "/api/rtx-engine"):
            doc = _kilroy_status()
            self._send_json(200, doc.get("amouranthrtx") or {})
            return
        if path in ("/api/queen-boot", "/api/queen-secure", "/api/grok16", "/api/queen-rtx"):
            doc = _secure_boot()
            if path == "/api/grok16":
                self._send_json(200, doc.get("grok16") or {})
                return
            if path == "/api/queen-rtx":
                self._send_json(200, doc.get("rtx_memory") or {})
                return
            self._send_json(200, doc)
            return
        if path in ("/api/queen-terminal", "/api/terminal"):
            self._send_json(200, _terminal_status())
            return
        if path in ("/api/queen-web-compat", "/api/web-compat"):
            self._send_json(200, _web_compat_status())
            return
        if path in ("/api/nexus-jump", "/api/queen-nexus-jump"):
            self._send_json(200, _nexus_jump_status())
            return
        if path in ("/api/update/check", "/api/update/status"):
            qs = parse_qs(urlparse(self.path).query)
            force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
            self._send_json(200, _update_status(force=force))
            return
        if path.startswith("/browse/view"):
            qs = parse_qs(urlparse(self.path).query)
            target = (qs.get("url") or [""])[0]
            if not target:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            compat_mode = (qs.get("compat") or qs.get("mode") or ["auto"])[0]
            code, data, mime = _proxy_fetch(unquote(target), compat_mode=compat_mode)
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Queen-Proxy", "1")
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/world" or path == "/world/":
            p = WORLD / "browser.html"
            if p.is_file():
                self._send_bytes(p.read_bytes(), mime="text/html; charset=utf-8")
                return
        if path == "/world/index.html":
            qs = parse_qs(urlparse(self.path).query)
            if (qs.get("os") or [""])[0] not in ("1", "true", "yes"):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", "/world/browser.html")
                self._apply_security_headers()
                self.end_headers()
                return
        if path.startswith("/world/"):
            rel = path[len("/world/") :]
            fp = _safe_path(WORLD, rel)
            if fp:
                mime = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
                self._send_bytes(fp.read_bytes(), mime=mime)
                return
        if path.startswith("/gui/"):
            rel = path[len("/gui/") :]
            fp = _safe_path(GUI, rel)
            if fp:
                mime = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
                self._send_bytes(fp.read_bytes(), mime=mime)
                return
        if path.startswith("/library/"):
            nexus_root = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(SG / "NewLatest")))
            lib_root = nexus_root / "library"
            rel = path[len("/library/") :]
            fp = _safe_path(lib_root, rel)
            if fp and fp.is_file():
                mime = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
                self._send_bytes(fp.read_bytes(), mime=mime)
                return
        if path == "/" or path == "":
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "/world/browser.html")
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json_body()
        if path == "/api/field-performance-flyout":
            reset = bool((body or {}).get("reset"))
            self._send_json(200, _perf_flyout_sample(reset=reset))
            return
        if path == "/api/queen-build":
            self._send_json(200, dispatch_build(body))
            return
        if path == "/api/update/apply":
            result = dispatch_update(body)
            if result.get("update_in_progress") and not result.get("started"):
                code = 409
            elif result.get("started"):
                code = 202
            else:
                code = 200
            self._send_json(code, result)
            return
        if path == "/api/update/sudo-prompt":
            result = dispatch_update({"action": "sudo-prompt"})
            code = 202 if result.get("prompt_started") else 400
            self._send_json(code, result)
            return
        if path in ("/api/field-tools", "/api/queen-field-tools"):
            self._send_json(200, dispatch_field_tools(body))
            return
        if path == "/api/queen-eyeball":
            self._send_json(200, dispatch_eye(body))
            return
        if path in ("/api/queen-earball", "/api/final-ear", "/api/earball"):
            self._send_json(200, dispatch_ear(body))
            return
        if path in ("/api/field-manual", "/api/field-manuals"):
            sense = str(body.get("sense") or "audio")
            if body.get("function"):
                env = _env()
                proc = subprocess.run(
                    [sys.executable, "-c", (
                        "import json,sys; sys.path.insert(0, sys.argv[1]); "
                        "from zocr_field_manual import field_manual_for_function; "
                        "print(json.dumps(field_manual_for_function(sys.argv[2]), ensure_ascii=False))"
                    ), str(SG / "Final_Ear"), str(body["function"])],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    cwd=str(QUEEN),
                    env=env,
                )
                try:
                    self._send_json(200, json.loads(proc.stdout or "{}"))
                except json.JSONDecodeError:
                    self._send_json(500, {"ok": False, "error": "field_manual_failed"})
                return
            self._send_json(200, _field_manual_status(sense))
            return
        if path == "/api/queen-browser":
            self._send_json(200, dispatch_browser(body))
            return
        if path in ("/api/queen-page-shields", "/api/page-shields"):
            self._send_json(200, dispatch_page_shields(body))
            return
        if path in ("/api/queen-desktop", "/api/desktop"):
            self._send_json(200, dispatch_desktop(body))
            return
        if path in ("/api/queen-program-surface", "/api/program-surface"):
            self._send_json(200, dispatch_program_surface(body))
            return
        if path in ("/api/nexus-c2", "/api/nexus-c2-panels", "/api/queen-dashboard", "/api/dashboard"):
            self._send_json(200, dispatch_nexus_c2(body))
            return
        if path in ("/api/queen-boot-hook", "/api/boot-hook"):
            self._send_json(200, _boot_hook())
            return
        if path in ("/api/queen-browser-import", "/api/browser-import"):
            self._send_json(200, dispatch_browser_import(body))
            return
        if path in ("/api/queen-file-browser", "/api/file-browser", "/api/files"):
            self._send_json(200, dispatch_file_browser(body))
            return
        if path in ("/api/queen-code", "/api/code", "/api/code-viewer"):
            self._send_json(200, dispatch_queen_code(body))
            return
        if path in ("/api/field-virus", "/api/queen-field-virus", "/api/virus"):
            self._send_json(200, dispatch_field_virus(body))
            return
        if path in ("/api/root-threats", "/api/root-threats/", "/api/threats/root"):
            self._send_json(200, dispatch_root_threats(body))
            return
        if path in ("/api/queen-boot", "/api/queen-secure"):
            self._send_json(200, queen_boot(body))
            return
        if path in ("/api/field-net", "/api/queen-field-net"):
            self._send_json(200, dispatch_field_net(body))
            return
        if path in ("/api/field-sanity", "/api/queen-field-sanity"):
            self._send_json(200, dispatch_field_sanity(body))
            return
        if path in ("/api/field-depth-snap", "/api/field-depth/instant", "/api/field-depth-singularizer/instant"):
            self._send_json(200, dispatch_field_depth_snap(body))
            return
        if path in ("/api/game-room", "/api/gameroom", "/api/chips"):
            self._send_json(200, dispatch_game_room(body))
            return
        if path.startswith("/api/game-room/system"):
            system = str((body or {}).get("system") or (body or {}).get("system_id") or "nes")
            self._send_json(200, _game_room_system_info(system=system))
            return
        if path in ("/api/nes-library", "/api/game-room/nes", "/api/game-room/library"):
            self._send_json(200, dispatch_nes_library(body))
            return
        if path.startswith("/api/sap") or path in ("/api/sweet-anita", "/api/game-room/sap"):
            self._send_json(200, dispatch_sap(body))
            return
        if path in ("/api/chips/combinatronic", "/api/chip-battery/combinatronic"):
            refresh = bool((body or {}).get("refresh"))
            self._send_json(200, _combinatronic_status(refresh=refresh))
            return
        if path in ("/api/chip-battery", "/api/combinatorics/chip-battery"):
            action = str((body or {}).get("action") or "panel").strip().lower()
            if action in ("combinatronic", "refresh"):
                self._send_json(200, _combinatronic_status(refresh=action == "refresh" or bool((body or {}).get("refresh"))))
                return
            self._send_json(200, _chip_battery_status())
            return
        if path in ("/api/kilroy", "/api/kilroy-field", "/api/field-kilroy", "/api/amouranthrtx"):
            self._send_json(200, dispatch_kilroy(body))
            return
        if path in ("/api/sovereign", "/api/capsule", "/api/queen-sovereign", "/api/horizon7", "/api/horizon-7"):
            self._send_json(200, dispatch_sovereign(body))
            return
        if path in ("/api/sense-neural", "/api/sense-neural-wire", "/api/hostess-authority"):
            self._send_json(200, dispatch_sense_neural(body))
            return
        if path in ("/api/field/compiler", "/api/field-compiler", "/api/field/compiler/probe"):
            if path.endswith("/probe"):
                body = {**body, "action": "probe"}
            self._send_json(200, dispatch_field_compiler(body))
            return
        if path in ("/api/grokpy", "/api/grokpy-runtime", "/api/grokpy/probe"):
            if path.endswith("/probe"):
                body = {**body, "action": "probe"}
            self._send_json(200, dispatch_grokpy(body))
            return
        if path in ("/api/pythong", "/api/pythong-runtime", "/api/python", "/api/pythong/probe"):
            if path.endswith("/probe"):
                body = {**body, "action": "probe"}
            self._send_json(200, dispatch_pythong(body))
            return
        if path in ("/api/queen-terminal", "/api/terminal"):
            self._send_json(200, dispatch_terminal(body))
            return
        if path in ("/api/queen-web-compat", "/api/web-compat"):
            self._send_json(200, dispatch_web_compat(body))
            return
        if path in ("/api/nexus-jump", "/api/queen-nexus-jump"):
            self._send_json(200, dispatch_nexus_jump(body))
            return
        if path in ("/api/hostess", "/api/hostess7", "/api/field-brain"):
            self._send_json(200, dispatch_hostess_brain(body))
            return
        if path in ("/api/external-wire", "/api/field-external-wire", "/api/queen-external-wire"):
            remote = str(body.get("remote_ip") or self.client_address[0] or "")
            self._send_json(200, dispatch_external_wire(body, remote_ip=remote))
            return
        if path in ("/api/world-redata", "/api/redata", "/api/queen-world-redata"):
            self._send_json(200, dispatch_world_redata(body))
            return
        if path in ("/api/secure-channel", "/api/forever-secure", "/api/queen-secure-channel"):
            remote = str(body.get("remote_ip") or self.client_address[0] or "")
            self._send_json(200, dispatch_secure_channel(body, remote_ip=remote))
            return
        if path in ("/api/contact-vector", "/api/contact-classification"):
            self._send_json(200, dispatch_contact_vector(body))
            return
        if path in ("/api/muscle-memory", "/api/hostess7-muscle-memory", "/api/muscle_memory"):
            self._send_json(200, dispatch_muscle_memory(body))
            return
        self.send_error(HTTPStatus.NOT_FOUND)


def port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Queen World HTTP server")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--check", action="store_true", help="exit 0 if world port is listening")
    ap.add_argument("--daemon", action="store_true", help="exit 0 if already running (else start in background)")
    args = ap.parse_args()

    if args.check:
        return 0 if port_open(args.host, args.port) else 1

    if args.daemon:
        if port_open(args.host, args.port):
            print(json.dumps({"ok": True, "already": True, "url": f"http://{args.host}:{args.port}/world/browser.html"}))
            return 0
        pid = os.fork()
        if pid > 0:
            for _ in range(20):
                if port_open(args.host, args.port):
                    print(json.dumps({"ok": True, "spawned": True, "url": f"http://{args.host}:{args.port}/world/browser.html"}))
                    return 0
                import time
                time.sleep(0.2)
            print(json.dumps({"ok": False, "error": "spawn_timeout"}))
            return 1
        if pid == 0:
            os.setsid()
            pid2 = os.fork()
            if pid2 > 0:
                os._exit(0)
            if pid2 == 0:
                os.chdir(str(QUEEN))
                with open(os.devnull, "w") as devnull:
                    os.dup2(devnull.fileno(), sys.stdout.fileno())
                    os.dup2(devnull.fileno(), sys.stderr.fileno())
                # fall through to serve_forever below
            else:
                os._exit(1)
        else:
            print(json.dumps({"ok": False, "error": "fork_failed"}))
            return 1

    if not WORLD.is_dir():
        print(json.dumps({"ok": False, "error": "world_missing", "path": str(WORLD)}), file=sys.stderr)
        return 1

    try:
        hook = _boot_hook()
        print(
            f"[queen-world] boot hook boarded — boot_os={hook.get('boot_os')} network_metal=BIOS",
            flush=True,
        )
        boot = _secure_boot()
        print(
            f"[queen-world] secure space sealed — Grok16 ready={boot.get('grok16', {}).get('ready')}",
            flush=True,
        )
    except Exception as exc:
        print(f"[queen-world] secure boot warn: {exc}", flush=True)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/world/browser.html"
    print(f"Queen World → {url}", flush=True)
    print(f"Build deck → http://{args.host}:{args.port}/gui/queen-build-deck.html", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())