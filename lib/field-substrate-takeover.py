#!/usr/bin/env pythong
"""Field substrate takeover — whole computer inside us; x5–x500 readiness; non-destructive."""
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
def _kilroy_path() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p
    for candidate in (SG.parent / "KILROY", SG / "KILROY", Path.home() / "Desktop" / "KILROY"):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return SG / "KILROY"


KILROY = _kilroy_path()
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "field-substrate-takeover-doctrine.json"
PANEL = STATE / "field-substrate-takeover.json"


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


def _probe_script(rel: str, mode: str = "json") -> dict[str, Any]:
    return _probe_guard().run_json_probe(INSTALL, state_dir(), rel, mode=mode, timeout=35)


def state_dir() -> Path:
    return STATE


def _kilroy_live() -> dict[str, Any]:
    proc_path = Path("/proc/kilroy_field")
    uname = platform.uname()
    kilroy = "kilroy" in (uname.release or "").lower() or "field" in (uname.system or "").lower()
    return {
        "proc_kilroy_field": proc_path.is_dir(),
        "kernel_release": uname.release,
        "kilroy_active": kilroy,
        "bzimage": (KILROY / "build" / "bzImage").is_file(),
        "grok_boot": (KILROY / "boot" / "grok").is_dir() or (SG / "KILROY" / "boot" / "grok").is_dir(),
    }


def _rtx_forefront() -> dict[str, Any]:
    doc = _load(INSTALL / "data" / "field-rtx-sovereign.json", {})
    if not doc:
        doc = _load(QUEEN / "data" / "field-rtx-sovereign.json", {})
    queen_bin = QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser"
    nvidia = Path("/dev/nvidia0").exists() or bool(list(Path("/sys/bus/pci/drivers/nvidia").glob("*"))) if Path("/sys/bus/pci/drivers/nvidia").exists() else Path("/dev/nvidia0").exists()
    return {
        "doctrine": doc.get("title", "field-rtx"),
        "gates_held": doc.get("gates_held", []),
        "queen_browser_built": queen_bin.is_file(),
        "queen_field_gpu_env": os.environ.get("QUEEN_FIELD_GPU", "1") == "1",
        "nvidia_present": nvidia,
        "phase": "now" if doc.get("phases", {}).get("now") else "unknown",
        "forefront_target": "FieldGpuDispatch pure on every RTX",
    }


def _nexus_live() -> dict[str, Any]:
    svc = "unknown"
    try:
        proc = subprocess.run(["systemctl", "is-active", "nexus-genius.service"], capture_output=True, text=True, timeout=5)
        svc = (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    installed = Path("/usr/local/lib/nexus-shield/lib/nexus-daemon.sh").is_file()
    return {"installed": installed, "nexus_genius_service": svc, "dev_tree": str(INSTALL)}


def _ram_witness() -> dict[str, Any]:
    meminfo: dict[str, str] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meminfo[k.strip()] = v.strip()
    except OSError:
        pass
    total_kb = int(meminfo.get("MemTotal", "0 kB").split()[0] or 0)
    avail_kb = int(meminfo.get("MemAvailable", "0 kB").split()[0] or 0)
    return {
        "total_gib": round(total_kb / 1024 / 1024, 2) if total_kb else None,
        "available_gib": round(avail_kb / 1024 / 1024, 2) if avail_kb else None,
        "field_ram_slot": Path("/proc/kilroy_field").is_dir(),
        "capsule": (QUEEN / "data" / "queen-sovereign-capsule.json").is_file(),
        "ownership": "witness" if not Path("/proc/kilroy_field").is_dir() else "field_slot",
    }


def performance_tier(
    *,
    nexus: dict[str, Any],
    kilroy: dict[str, Any],
    rtx: dict[str, Any],
    native: dict[str, Any],
    cpu: dict[str, Any],
) -> dict[str, Any]:
    tier = 0
    label = "substrate_host"
    if nexus.get("nexus_genius_service") == "active" or INSTALL.name == "NewLatest":
        tier = max(tier, 1)
        label = "x5_userspace"
    if rtx.get("queen_browser_built") and rtx.get("queen_field_gpu_env"):
        tier = max(tier, 1)
    if kilroy.get("kilroy_active") or kilroy.get("proc_kilroy_field"):
        tier = 2
        label = "x50_field_die"
    if kilroy.get("bzimage") and cpu.get("verdict") == "GREEN":
        tier = max(tier, 2)
    if rtx.get("gates_held") and "field_gpu_dispatch" in (rtx.get("gates_held") or []):
        if kilroy.get("proc_kilroy_field") and native.get("we_are_the_native"):
            tier = 3
            label = "x500_rtx_forefront_path"
    return {
        "tier": tier,
        "label": label,
        "multiplier_claim": {0: "1x host", 1: "x5 target", 2: "x50 target", 3: "x500 target"}.get(tier, "1x"),
        "honest": "Multipliers are field-path targets when layers are LIVE — not benchmark guarantees on host OS today",
    }


def _shallow_takeover_posture() -> dict[str, Any]:
    """Disk-only json — no subprocess probes."""
    native = _load(STATE / "native-layer.json", {})
    cpu = _load(STATE / "cpu-vulnerability-shield.json", {})
    doctrine = _load(DOCTRINE, {})
    nexus = _nexus_live()
    kilroy = _kilroy_live()
    rtx = _rtx_forefront()
    ram = _ram_witness()
    perf = performance_tier(nexus=nexus, kilroy=kilroy, rtx=rtx, native=native, cpu=cpu)
    blockers: list[str] = []
    if not kilroy.get("kilroy_active"):
        blockers.append("boot_kilroy_field_die — host still runs generic Linux")
    if nexus.get("nexus_genius_service") != "active":
        blockers.append("nexus_genius_service — install-all + integrity fix")
    verdict = "READY" if perf["tier"] >= 3 and not blockers else ("PARTIAL" if perf["tier"] >= 1 else "NOT_READY")
    return {
        "schema": "field-substrate-takeover/v1",
        "ts": _now(),
        "shallow": True,
        "verdict": verdict,
        "performance": perf,
        "layers": {
            "bios": {"status": "witness_only", "flash": False},
            "boot": {"status": "grok_ready" if kilroy.get("grok_boot") else "host_shim"},
            "kernel": {"status": "kilroy" if kilroy.get("kilroy_active") else "linux_substrate_host"},
            "cpu": {"status": cpu.get("verdict", "UNKNOWN")},
            "ram": ram,
            "gpu_rtx": rtx,
            "nexus": nexus,
        },
        "blockers": blockers,
        "probe_policy": "shallow_json_no_subprocess",
    }


def takeover_posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    nexus = _nexus_live()
    kilroy = _kilroy_live()
    rtx = _rtx_forefront()
    ram = _ram_witness()
    native = _probe_script("native-layer.py")
    cpu = _probe_script("cpu-vulnerability-shield.py")
    perf = performance_tier(nexus=nexus, kilroy=kilroy, rtx=rtx, native=native, cpu=cpu)

    layers = {
        "bios": {"status": "witness_only", "flash": False},
        "boot": {"status": "grok_ready" if kilroy.get("grok_boot") else "host_shim", "destructive": False},
        "kernel": {"status": "kilroy" if kilroy.get("kilroy_active") else "linux_substrate_host", "inside_us": kilroy.get("kilroy_active")},
        "cpu": {"status": cpu.get("verdict", "UNKNOWN"), "shield": cpu.get("schema") is not None},
        "ram": ram,
        "gpu_rtx": rtx,
        "nexus": nexus,
        "full_ownership": kilroy.get("kilroy_active") and nexus.get("nexus_genius_service") == "active",
    }

    blockers: list[str] = []
    if not kilroy.get("kilroy_active"):
        blockers.append("boot_kilroy_field_die — host still runs generic Linux")
    if nexus.get("nexus_genius_service") != "active":
        blockers.append("nexus_genius_service — install-all + integrity fix")
    if cpu.get("verdict") == "WARN":
        blockers.append("cpu_sysctl_apply — NEXUS_CPU_VULN_APPLY=1 as root")
    if not rtx.get("queen_browser_built"):
        blockers.append("queen_browser_build — Queen/build/rtx for RTX forefront")
    if ram.get("ownership") == "witness":
        blockers.append("ram_field_slot — needs /proc/kilroy_field (KILROY boot)")

    ready = perf["tier"] >= 2 and len(blockers) <= 2
    verdict = "READY" if perf["tier"] >= 3 and not blockers else ("PARTIAL" if perf["tier"] >= 1 else "NOT_READY")

    return {
        "schema": "field-substrate-takeover/v1",
        "ts": _now(),
        "verdict": verdict,
        "we_are_the_forefront": rtx.get("gates_held", []),
        "permanent_upgrade": True,
        "destructive": False,
        "doctrine": doctrine.get("title", ""),
        "performance": perf,
        "layers": layers,
        "blockers": blockers,
        "next_commands": [
            "./NewLatest/install-all.sh",
            "Queen: ./build-field.sh",
            "KILROY: ./scripts/kilroy-become-substrate.sh && ./scripts/build-kilroy.sh",
            "Grok boot entry — dual-boot, keep existing OS",
            "QUEEN_FIELD_GPU=1 ./Queen/build/rtx/bin/Linux/queen-browser",
        ],
        "move_inside_us": doctrine.get("move_inside_us", []),
    }


def board_once() -> dict[str, Any]:
    doc = takeover_posture()
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
        print(json.dumps(_shallow_takeover_posture(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-substrate-takeover.py [json|board]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())