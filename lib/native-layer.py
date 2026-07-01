#!/usr/bin/env pythong
"""NEXUS Native Layer — we are THE native down to BIOS witness; no flash; everything lives with us."""
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
def _kilroy_root() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p
    for candidate in (SG.parent / "KILROY", SG / "KILROY", Path.home() / "Desktop" / "KILROY"):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return SG / "KILROY"


KILROY = _kilroy_root()
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "native-layer-doctrine.json"
NATIVE_FILE = STATE / "native-layer.json"
AUDIT_FILE = STATE / "native-firmware-audit.json"


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


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _dmi(key: str) -> str:
    p = Path(f"/sys/class/dmi/id/{key}")
    try:
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    return ""


def firmware_witness() -> dict[str, Any]:
    out: dict[str, Any] = {
        "flash_chip": False,
        "witness_only": True,
        "uefi": Path("/sys/firmware/efi").is_dir(),
        "efi_vars": Path("/sys/firmware/efi/efivars").is_dir(),
        "tpm": Path("/dev/tpm0").exists() or Path("/dev/tpmrm0").exists(),
        "iommu_groups": Path("/sys/kernel/iommu_groups").is_dir(),
        "nx": "nx" in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace") if Path("/proc/cpuinfo").is_file() else False,
        "vendor": _dmi("bios_vendor"),
        "version": _dmi("bios_version"),
        "date": _dmi("bios_date"),
        "board": _dmi("board_name"),
        "product": _dmi("product_name"),
    }
    sb_path = Path("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c")
    if sb_path.is_file():
        try:
            raw = sb_path.read_bytes()
            out["secure_boot"] = raw[-1] == 1 if raw else None
        except OSError:
            out["secure_boot"] = None
    else:
        out["secure_boot"] = None
    return out


def _run_firmware_audit() -> dict[str, Any]:
    script = KILROY / "scripts" / "grok-firmware-audit.sh"
    if not script.is_file():
        return {"ok": False, "error": "audit_script_missing", "path": str(script)}
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(KILROY),
        )
        doc = {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:] if proc.stdout else "",
            "stderr": (proc.stderr or "")[-2000:],
            "updated": _now(),
        }
        _save(AUDIT_FILE, doc)
        return doc
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _layer_live(layer_id: str) -> bool:
    checks = {
        "firmware": lambda: Path("/sys/firmware/efi").is_dir() or _dmi("bios_vendor"),
        "boot": lambda: (KILROY / "boot/grok/grok.conf").is_file() or Path("/run/systemd/system").is_dir(),
        "kernel": lambda: Path("/proc/version").is_file(),
        "firmware_layer": lambda: Path("/var/lib/sg_build/firmware-layer").is_file(),
        "sovereign": lambda: (STATE / "root-sovereign-covenant.json").is_file() or (QUEEN / ".nexus-state/root-sovereign-covenant.json").is_file(),
        "capsule": lambda: (QUEEN / "data/queen-sovereign-capsule.json").is_file(),
        "nexus": lambda: (INSTALL / "lib/nexus-daemon.sh").is_file() or (INSTALL / "lib/threat-panel-http.py").is_file(),
        "surface": lambda: (QUEEN / "scripts/run-queen.sh").is_file() or (INSTALL / "lib/panel-browser.sh").is_file(),
        "cpu_shield": lambda: (INSTALL / "lib/cpu-vulnerability-shield.py").is_file(),
    }
    fn = checks.get(layer_id)
    return bool(fn and fn())


def stack_posture() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    layers = doctrine.get("stack_bottom_up") or []
    out = []
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        lid = str(layer.get("id") or "")
        out.append({
            **layer,
            "live": _layer_live(lid),
            "native_with_us": True,
        })
    return out


def _substrate_takeover_posture() -> dict[str, Any]:
    guard = _probe_guard()
    return guard.run_json_probe(INSTALL, STATE, "field-substrate-takeover.py", timeout=45)


def _field_polkit_posture() -> dict[str, Any]:
    guard = _probe_guard()
    return guard.run_json_probe(INSTALL, STATE, "field-polkit.py", timeout=20)


def _cpu_vulnerability_posture() -> dict[str, Any]:
    guard = _probe_guard()
    return guard.run_json_probe(INSTALL, STATE, "cpu-vulnerability-shield.py", timeout=30)


def _shallow_native_posture() -> dict[str, Any]:
    """Disk-only posture — zero subprocess, prevents probe explosion on json."""
    doctrine = _load(DOCTRINE, {})
    fw = firmware_witness()
    host_kernel = ""
    try:
        host_kernel = Path("/proc/version").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    kilroy_active = "kilroy" in host_kernel.lower() or "KILROY" in platform.system().upper()
    return {
        "schema": "native-layer/v1",
        "updated": _now(),
        "shallow": True,
        "we_are_the_native": True,
        "flash_chip": False,
        "host": {"kernel": host_kernel[:240], "kilroy_active": kilroy_active, "machine": platform.machine()},
        "firmware_witness": fw,
        "stack": stack_posture(),
        "cpu_vulnerability": _load(STATE / "cpu-vulnerability-shield.json", {}),
        "field_polkit": _load(STATE / "field-polkit.json", {}),
        "substrate_takeover": _load(STATE / "field-substrate-takeover.json", {}),
        "field_underlay": _load(STATE / "field-underlay-panel.json", {}),
        "doctrine": doctrine.get("policy") or {},
        "from_cache": False,
        "probe_policy": "shallow_json_no_subprocess",
    }


def native_posture(*, audit: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    fw = firmware_witness()
    audit_doc = _run_firmware_audit() if audit else _load(AUDIT_FILE, {})
    host_kernel = ""
    try:
        host_kernel = Path("/proc/version").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    kilroy_active = "kilroy" in host_kernel.lower() or "KILROY" in platform.system().upper()
    doc = {
        "schema": "native-layer/v1",
        "updated": _now(),
        "we_are_the_native": True,
        "flash_chip": False,
        "flash_policy": "witness_bios_never_write_rom",
        "everything_lives_with_us": True,
        "native_authority": doctrine.get("policy", {}).get("native_authority", "SG/NewLatest"),
        "host": {
            "kernel": host_kernel[:240],
            "kilroy_active": kilroy_active,
            "machine": platform.machine(),
            "node": platform.node(),
        },
        "firmware_witness": fw,
        "firmware_audit": audit_doc if audit_doc else None,
        "stack": stack_posture(),
        "lives_with_us": doctrine.get("lives_with_us") or [],
        "doctrine": doctrine.get("policy") or {},
        "cpu_vulnerability": _cpu_vulnerability_posture(),
        "field_polkit": _field_polkit_posture(),
        "substrate_takeover": _substrate_takeover_posture(),
        "field_underlay": _field_underlay_posture(),
    }
    return doc


def _field_underlay_posture() -> dict[str, Any]:
    guard = _probe_guard()
    return guard.run_json_probe(INSTALL, STATE, "field-underlay.py", timeout=35)


def board_once() -> dict[str, Any]:
    cpu_script = INSTALL / "lib" / "cpu-vulnerability-shield.py"
    if cpu_script.is_file():
        try:
            subprocess.run(
                [sys.executable, str(cpu_script), "board"],
                capture_output=True,
                text=True,
                timeout=45,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                check=False,
            )
        except (subprocess.SubprocessError, OSError):
            pass
    doc = native_posture(audit=True)
    doc["boarded"] = True
    _save(NATIVE_FILE, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "board":
        print(json.dumps(board_once(), ensure_ascii=False))
        return 0
    if cmd == "audit":
        print(json.dumps(_run_firmware_audit(), ensure_ascii=False))
        return 0
    audit = "--audit" in sys.argv
    if not audit and NATIVE_FILE.is_file():
        cached = _load(NATIVE_FILE, {})
        if isinstance(cached, dict) and cached.get("schema"):
            cached = {**cached, "from_cache": True}
            print(json.dumps(cached, ensure_ascii=False))
            return 0
    if not audit and cmd == "json":
        print(json.dumps(_shallow_native_posture(), ensure_ascii=False))
        return 0
    print(json.dumps(native_posture(audit=audit), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())