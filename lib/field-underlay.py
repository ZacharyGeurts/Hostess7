#!/usr/bin/env pythong
"""Field underlay — drop-in OS replacement; guests inside protections; vision assist; bottom-up."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROBE_GUARD: Any = None

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "field-underlay-doctrine.json"
PANEL = STATE / "field-underlay-panel.json"
LOCK = STATE / "field-underlay-lock.json"


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


def _probe_guard() -> Any:
    global _PROBE_GUARD
    if _PROBE_GUARD is not None:
        return _PROBE_GUARD
    py = INSTALL / "lib" / "nexus-probe-guard.py"
    spec = importlib.util.spec_from_file_location("nexus_probe_guard", py)
    if not spec or not spec.loader:
        raise ImportError("nexus-probe-guard.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _PROBE_GUARD = mod
    return mod


def _probe_py(rel: str) -> dict[str, Any]:
    return _probe_guard().run_json_probe(INSTALL, STATE, rel, timeout=30)


def _guest_os() -> dict[str, Any]:
    uname = platform.uname()
    system = uname.system.lower()
    guest = {
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
        "role": "guest_substrate",
    }
    if "linux" in system:
        guest["passthrough"] = "linux_abi"
        guest["mode"] = "host_passthrough_when_kilroy_booted"
    elif "windows" in system or "mingw" in system:
        guest["passthrough"] = "windows_native"
        guest["mode"] = "underlay_aboard_userspace"
    elif "darwin" in system:
        guest["passthrough"] = "macos_native"
        guest["mode"] = "underlay_aboard_userspace"
    else:
        guest["passthrough"] = "unknown"
    guest["kilroy_guest"] = "kilroy" in (uname.release or "").lower()
    return guest


def _underlay_layers() -> dict[str, Any]:
    kilroy_proc = Path("/proc/kilroy_field").is_dir()
    kilroy_dev = Path("/dev/kilroy_field").exists()
    front = _load(STATE / "front-hook.json", {})
    native = _probe_py("native-layer.py")
    substrate = _probe_py("field-substrate-takeover.py")
    return {
        "firmware": {"role": "witness_only", "live": native.get("firmware_witness", {}).get("vendor") is not None},
        "field_die": {"live": kilroy_proc or kilroy_dev, "proc": kilroy_proc},
        "nexus": {"front_hook": front.get("boarded") is True, "human_integration": front.get("human_integration", True)},
        "queen": {"present": QUEEN.is_dir(), "browser": (QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser").is_file()},
        "substrate_takeover": substrate.get("verdict"),
        "we_are_the_native": native.get("we_are_the_native", True),
    }


def _protections() -> dict[str, Any]:
    checks = {
        "gatekeeper": (INSTALL / "lib" / "connection-gatekeeper.py").is_file(),
        "hardware_wire": (INSTALL / "lib" / "hardware-wire.py").is_file(),
        "cpu_shield": (INSTALL / "lib" / "cpu-vulnerability-shield.py").is_file(),
        "field_polkit": (INSTALL / "lib" / "field-polkit.py").is_file(),
        "field_perimeter": (INSTALL / "lib" / "field-perimeter-shield.py").is_file(),
        "root_sovereign": (QUEEN / "lib" / "queen-root-sovereign.py").is_file(),
        "ai_integration": (INSTALL / "lib" / "ai-integration-hook.py").is_file(),
        "nexus_jump": (QUEEN / "lib" / "queen-nexus-jump.py").is_file(),
        "secure_cage": (QUEEN / "lib" / "queen-web-compat.py").is_file(),
        "field_operator": (INSTALL / "lib" / "field-operator.py").is_file(),
    }
    live = sum(1 for v in checks.values() if v)
    return {"checks": checks, "modules_present": live, "envelope_ratio": round(live / max(len(checks), 1), 3)}


def _assist_stack() -> dict[str, Any]:
    eye_root = Path(os.environ.get("FINAL_EYE_ROOT", str(SG / "Final_Eye")))
    ear_root = Path(os.environ.get("FINAL_EAR_ROOT", str(SG / "Final_Ear")))
    eye_port = int(os.environ.get("FINAL_EYE_PORT", "9479") or "9479")
    eye_up = False
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{eye_port}/ops", timeout=2) as resp:
            eye_up = resp.status == 200
    except Exception:
        eye_up = False
    return {
        "final_eye": {"root": str(eye_root), "present": eye_root.is_dir(), "ops_live": eye_up, "port": eye_port},
        "final_ear": {"root": str(ear_root), "present": ear_root.is_dir()},
        "hostess7_vision": (SG / "Hostess7").is_dir(),
        "h7_vision_bridge": (INSTALL / "lib" / "h7-library-bridge.py").is_file(),
        "existence_identity": (INSTALL / "lib" / "existence-identity.py").is_file(),
        "ai_integration": _load(STATE / "ai-integration-panel.json", {}).get("ai_only") is not False,
    }


def _nobody_below(layers: dict[str, Any], guest: dict[str, Any]) -> dict[str, Any]:
    field_die_live = layers.get("field_die", {}).get("live")
    if field_die_live:
        verdict = "GREEN"
        detail = "Field Die owns syscall boundary — guest is inside us"
    elif layers.get("nexus", {}).get("front_hook"):
        verdict = "PARTIAL"
        detail = "Userspace underlay aboard — incumbent kernel still host until KILROY boot"
    else:
        verdict = "WARN"
        detail = "Underlay not boarded — guest OS still native authority"
    return {
        "verdict": verdict,
        "detail": detail,
        "field_die_live": field_die_live,
        "guest_substrate": guest.get("system"),
        "nothing_below_rule": "BIOS witness only — no flash; Field Die target owns syscalls",
    }


def _shallow_posture() -> dict[str, Any]:
    native = _load(STATE / "native-layer.json", {})
    substrate = _load(STATE / "field-substrate-takeover.json", {})
    guest = _guest_os()
    layers = {
        "firmware": {"role": "witness_only", "live": bool(native.get("firmware_witness"))},
        "field_die": {"live": Path("/proc/kilroy_field").is_dir()},
        "nexus": {"front_hook": _load(STATE / "front-hook.json", {}).get("boarded") is True},
        "queen": {"present": QUEEN.is_dir()},
        "substrate_takeover": substrate.get("verdict"),
        "we_are_the_native": native.get("we_are_the_native", True),
    }
    return {
        "schema": "field-underlay/v1",
        "ts": _now(),
        "shallow": True,
        "verdict": substrate.get("verdict", "PARTIAL"),
        "guest_os": guest,
        "underlay_layers": layers,
        "probe_policy": "shallow_json_no_subprocess",
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    guest = _guest_os()
    layers = _underlay_layers()
    protections = _protections()
    assist = _assist_stack()
    nobody = _nobody_below(layers, guest)

    drop_in_ready = (
        protections["envelope_ratio"] >= 0.7
        and layers.get("queen", {}).get("present")
        and assist.get("final_eye", {}).get("present")
    )
    lock = _load(LOCK, {})
    committed = bool(lock.get("committed"))

    unified: dict[str, Any] = {}
    u_py = INSTALL / "lib" / "field-unified-device.py"
    if u_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("field_unified_device", u_py)
            if spec and spec.loader:
                u_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(u_mod)
                if hasattr(u_mod, "posture"):
                    unified = u_mod.posture(board=False)
        except Exception:
            unified = _load(STATE / "field-unified-device.json", {})

    return {
        "schema": "field-underlay/v1",
        "ts": _now(),
        "verdict": "GREEN" if committed else nobody["verdict"],
        "committed": committed,
        "permanent": lock.get("permanent", True) if committed else False,
        "off_switch": False if committed else None,
        "installer": "/tristate-installer",
        "drop_in_replacement_ready": drop_in_ready,
        "doctrine": doctrine.get("title", ""),
        "motto": doctrine.get("motto", ""),
        "guest_os": guest,
        "underlay_layers": layers,
        "protections": protections,
        "assist_stack": assist,
        "nobody_below": nobody,
        "unified_device_field": unified,
        "guest_field_grant": unified.get("guest_field_grant"),
        "boot_order": unified.get("boot_order") or doctrine.get("policy", {}).get("early_boot_order"),
        "model": {
            "underlay": "KILROY + NEXUS + Queen",
            "guest_runs_inside": guest.get("system"),
            "assist_active": assist.get("final_eye", {}).get("ops_live") or assist.get("h7_vision_bridge"),
            "bottom_up": layers.get("we_are_the_native"),
        },
    }


def board_once() -> dict[str, Any]:
    doc = posture()
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    tmp = PANEL.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL)
    return doc


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if mode == "board":
        board_once()
        return 0
    if mode == "json":
        if PANEL.is_file():
            cached = _load(PANEL, {})
            if isinstance(cached, dict) and cached.get("schema"):
                cached = {**cached, "from_cache": True}
                print(json.dumps(cached, ensure_ascii=False, indent=2))
                return 0
        print(json.dumps(_shallow_posture(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-underlay.py [json|board]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())