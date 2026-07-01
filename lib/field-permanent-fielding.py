#!/usr/bin/env pythong
"""Permanent fielding — SG + NewLatest field from power input forward (no off switch)."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-permanent-fielding-doctrine.json"

PERMANENT_MARKER = STATE / "permanent-field.marker"
PERMANENT_JSON = STATE / "permanent-field.json"
PERMANENT_ENV = STATE / "permanent-field.env"
SG_MARKER = SG / ".nexus-state" / "permanent-field.marker"
SG_RECEIPT = SG / ".nexus-state" / "permanent-field.json"
RUNTIME = STATE / "field-combinatorics-runtime.json"
UNDERLAY_LOCK = STATE / "field-underlay-lock.json"
DEFIELD_MARKER = STATE / "ammocode-defield.marker"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _py(mod_path: Path, *args: str, timeout: int = 120) -> dict[str, Any]:
    if not mod_path.is_file():
        return {"ok": False, "error": f"missing {mod_path}"}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(mod_path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": (proc.stderr or "empty")[:400]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _import_fc():
    fc_path = SG / "AmmoCode" / "server" / "ammocode-field-control.py"
    if not fc_path.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("ammocode_fc", fc_path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_permanent() -> bool:
    return PERMANENT_MARKER.is_file() or SG_MARKER.is_file()


def _power_witness() -> dict[str, Any]:
    ac_online: int | None = None
    for base in (Path("/sys/class/power_supply"),):
        if not base.is_dir():
            continue
        for psu in sorted(base.iterdir()):
            online = psu / "online"
            if online.is_file():
                try:
                    ac_online = int(online.read_text().strip())
                    break
                except (OSError, ValueError):
                    pass
    boot_id = ""
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        pass
    kilroy_proc = Path("/proc/kilroy_field/status")
    grok_efi = Path("/boot/efi/EFI/BOOT/BOOTX64.EFI")
    kilroy_bz = Path("/boot/efi/boot/kilroy/bzImage")
    build_bz = SG / "KILROY" / "build" / "bzImage"

    def _exists(path: Path) -> bool:
        try:
            return path.is_file()
        except OSError:
            return False

    return {
        "ts": _now(),
        "ac_online": ac_online,
        "boot_id": boot_id,
        "kernel": platform.system(),
        "release": platform.release(),
        "kilroy_proc": _exists(kilroy_proc),
        "kilroy_proc_excerpt": (
            kilroy_proc.read_text(encoding="utf-8", errors="replace")[:500]
            if _exists(kilroy_proc)
            else ""
        ),
        "grok_boot_efi": _exists(grok_efi),
        "kilroy_bzimage_esp": _exists(kilroy_bz),
        "kilroy_bzimage_build": _exists(build_bz),
        "sg_root": str(SG),
        "newlatest_root": str(INSTALL),
    }


def _clear_defield() -> dict[str, Any]:
    fc = _import_fc()
    if fc and hasattr(fc, "clear_defield"):
        return fc.clear_defield()
    removed = []
    for path in (
        DEFIELD_MARKER,
        STATE / "ammocode-defield.json",
        STATE / "ammocode-defield.env",
    ):
        try:
            if path.is_file():
                path.unlink()
                removed.append(path.name)
        except OSError:
            pass
    return {"ok": True, "cleared": removed}


def _commit_underlay() -> dict[str, Any]:
    doc = {
        "schema": "field-underlay-lock/v1",
        "committed": True,
        "committed_at": _now(),
        "permanent": True,
        "off_switch": False,
        "reversible": False,
        "hotkey": "F9",
        "guest_passthrough": True,
        "reboot_target": "KILROY Field",
        "motto": "Permanent fielding — we are always the underlay from power input forward.",
        "source": "field-permanent-fielding",
    }
    env = {**os.environ, "NEXUS_UNDERLAY_FORCE": "1"}
    switch = INSTALL / "lib" / "field-underlay-switch.py"
    if switch.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(switch), "commit"],
                capture_output=True,
                text=True,
                timeout=180,
                env={**env, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "SG_ROOT": str(SG)},
            )
            if proc.stdout.strip():
                out = json.loads(proc.stdout)
                if out.get("ok"):
                    return out
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
            pass
    _save(UNDERLAY_LOCK, doc)
    return {"ok": True, "lock": doc, "direct": True}


def _write_runtime() -> dict[str, Any]:
    doc = {
        "schema": "field-combinatorics-runtime/v1",
        "updated": _now(),
        "permanent": True,
        "field_depth": 0,
        "sg_root": str(SG),
        "nexus_install_root": str(INSTALL),
        "posture": "field",
        "power_chain_active": True,
    }
    _save(RUNTIME, doc)
    return {"ok": True, "runtime": doc}


def _write_env() -> None:
    lines = [
        f"SG_ROOT={SG}",
        f"NEXUS_INSTALL_ROOT={INSTALL}",
        f"NEXUS_STATE_DIR={STATE}",
        "NEXUS_PERMANENT_FIELD=1",
        "NEXUS_FIELD_UNDERLAY_COMMITTED=1",
        "G16_AMMOCODE_RESTING_ON_FIELD=0",
        "G16_AMMOCODE_SURFACE=nexus_field",
        "G16_BELT_PROFILE=belt_2_0",
        "KILROY_ROOT=" + str(SG / "KILROY"),
    ]
    PERMANENT_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sg_env = SG / ".nexus-state" / "permanent-field.env"
    sg_env.parent.mkdir(parents=True, exist_ok=True)
    sg_env.write_text("\n".join(lines) + "\n", encoding="utf-8")


def install(*, force: bool = False) -> dict[str, Any]:
    """Commit permanent fielding for SG + NewLatest from power input forward."""
    if is_permanent() and not force:
        return {"ok": True, "already": True, "status": status()}

    power = _power_witness()
    cleared = _clear_defield()
    underlay = _commit_underlay()
    runtime = _write_runtime()

    ts = _now()
    receipt = {
        "schema": "permanent-field/v1",
        "permanent": True,
        "field": True,
        "off_switch": False,
        "field_depth": 0,
        "no_subfields": True,
        "committed_at": ts,
        "scope": ["SG", "SG/NewLatest"],
        "power_chain": (_load(DOCTRINE, {}).get("power_chain") or []),
        "power_witness": power,
        "cleared_defield": cleared,
        "underlay": underlay,
        "runtime": runtime,
        "motto": "One field from power input forward — KILROY die, SG fabric, NewLatest C2.",
    }
    PERMANENT_MARKER.write_text(f"permanent-field {ts}\n", encoding="utf-8")
    _save(PERMANENT_JSON, receipt)
    SG_MARKER.parent.mkdir(parents=True, exist_ok=True)
    SG_MARKER.write_text(f"permanent-field {ts}\n", encoding="utf-8")
    _save(SG_RECEIPT, receipt)
    _write_env()
    return {"ok": True, "installed": True, "receipt": receipt, "status": status()}


def ensure() -> dict[str, Any]:
    """Boot-cycle witness — re-assert permanent field if marker present."""
    if not is_permanent():
        return {"ok": True, "action": "none", "permanent": False}
    power = _power_witness()
    _clear_defield()
    _write_runtime()
    _write_env()
    doc = _load(PERMANENT_JSON, {"schema": "permanent-field/v1"})
    doc["last_ensure"] = _now()
    doc["power_witness"] = power
    _save(PERMANENT_JSON, doc)
    if SG_RECEIPT.is_file() or SG_MARKER.is_file():
        _save(SG_RECEIPT, doc)
    try:
        _py(INSTALL / "lib" / "field-power-ledger.py", "json", timeout=30)
    except Exception:
        pass
    return {"ok": True, "action": "ensure", "permanent": True, "power_witness": power}


def status() -> dict[str, Any]:
    doc = _load(PERMANENT_JSON, {})
    underlay = _load(UNDERLAY_LOCK, {})
    fc = _import_fc()
    field_status = fc.sg_field_status() if fc and hasattr(fc, "sg_field_status") else {}
    return {
        "schema": "permanent-field-status/v1",
        "ts": _now(),
        "permanent": is_permanent(),
        "field": True if is_permanent() else False,
        "off_switch": False if is_permanent() else None,
        "defield_active": DEFIELD_MARKER.is_file(),
        "underlay_committed": bool(underlay.get("committed")),
        "scope": ["SG", "SG/NewLatest"],
        "sg_root": str(SG),
        "newlatest_root": str(INSTALL),
        "receipt": doc,
        "sg_field_status": field_status,
        "power_witness": _power_witness(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("install", "commit", "enable"):
        out = install(force="--force" in sys.argv)
    elif cmd in ("ensure", "boot"):
        out = ensure()
    elif cmd in ("status", "json"):
        out = status()
    elif cmd == "clear":
        removed = []
        for path in (PERMANENT_MARKER, PERMANENT_JSON, PERMANENT_ENV, SG_MARKER, SG_RECEIPT):
            try:
                if path.is_file():
                    path.unlink()
                    removed.append(str(path))
            except OSError:
                pass
        out = {"ok": True, "cleared": removed}
    else:
        print(json.dumps({"error": "usage", "cmds": ["install", "ensure", "status", "clear"]}))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())