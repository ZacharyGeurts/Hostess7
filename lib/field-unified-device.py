#!/usr/bin/env pythong
"""Unified device field — KILROY grants one field across drives, RAM, board, voltage, FCC."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
DOCTRINE = INSTALL / "data" / "field-unified-device-doctrine.json"
PANEL = STATE / "field-unified-device.json"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


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


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kilroy_root() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p.resolve()
    for candidate in (
        INSTALL / "KILROY",
        SG / "KILROY",
        SG / "NewLatest" / "KILROY",
    ):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return INSTALL / "KILROY"


def _kilroy_network_lane() -> dict[str, Any]:
    lane = _load(STATE / "kilroy-net-lane.json", {})
    relayer = _load(STATE / "znetwork-relayer.json", {})
    active = bool(lane.get("active") or relayer.get("active") or relayer.get("running"))
    return {
        "owner": "kilroy_core",
        "absorbed": "znetwork",
        "active": active,
        "mode": lane.get("mode") or relayer.get("mode") or relayer.get("posture") or "unknown",
        "netlink_slots": "16-19",
        "implementation": "lib/znetwork-field.sh",
        "in_field": active or bool(lane) or bool(relayer),
    }


def _kilroy_loopback() -> dict[str, Any]:
    doc = _load(STATE / "kilroy-loopback.json", {})
    if doc:
        return {
            "owner": "kilroy_core",
            "loopback_authority": doc.get("loopback_authority") or "127.0.0.1",
            "transparent": bool(doc.get("transparent", True)),
            "guest_unmodified": bool(doc.get("guest_unmodified", True)),
            "any_computer": bool(doc.get("any_computer", True)),
            "active": bool(doc.get("active")),
            "boons": doc.get("boons") or {},
            "services": doc.get("services") or {},
            "in_field": bool(doc.get("active") or doc),
        }
    loopback_mod = _import_mod("kilroy_loopback", "lib/kilroy-loopback.py")
    if loopback_mod and hasattr(loopback_mod, "posture"):
        try:
            lb = loopback_mod.posture(board=False)
            return {
                "owner": "kilroy_core",
                "loopback_authority": lb.get("loopback_authority") or "127.0.0.1",
                "transparent": True,
                "guest_unmodified": True,
                "any_computer": True,
                "active": bool(lb.get("active")),
                "boons": lb.get("boons") or {},
                "in_field": bool(lb.get("active")),
            }
        except Exception:
            pass
    return {
        "owner": "kilroy_core",
        "loopback_authority": "127.0.0.1",
        "transparent": True,
        "guest_unmodified": True,
        "any_computer": True,
        "motto": "KILROY is 127.0.0.1 — security, speed, storage without bothering the host",
        "in_field": (INSTALL / "lib" / "kilroy-loopback.py").is_file(),
    }


def _kilroy_nexus_c2() -> dict[str, Any]:
    port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477") or "9477")
    c2_doc = _load(STATE / "kilroy-nexus-c2.json", {})
    hook = _load(STATE / "front-hook.json", {})
    up = False
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/field", timeout=2) as resp:
            up = resp.status == 200
    except Exception:
        up = False
    active = up or bool(c2_doc.get("active"))
    return {
        "owner": "kilroy_core",
        "role": "field_tech_monitoring_panel",
        "theme": c2_doc.get("theme") or "black_emerald_rose_2026",
        "palette": c2_doc.get("palette") or "black_green_pink",
        "panel_port": port,
        "panel_url": f"http://127.0.0.1:{port}/field",
        "command_url": f"http://127.0.0.1:{port}/command",
        "module": "lib/threat-panel.sh",
        "monitoring": "all_out_field_tech",
        "panel_up": up,
        "front_hook": bool(hook.get("boarded")),
        "active": active,
        "in_field": active or bool(hook.get("boarded")),
    }


def _kilroy_defense_offense() -> dict[str, Any]:
    doc = _load(STATE / "kilroy-defense-offense.json", {})
    if doc:
        return {
            "owner": doc.get("owner", "kilroy_core"),
            "defense": doc.get("defense") or [],
            "offense": doc.get("offense") or [],
            "guest_cannot_disable": bool(doc.get("guest_cannot_disable", True)),
            "in_field": True,
        }
    return {
        "owner": "kilroy_core",
        "defense": ["self_defensive_field_die", "tamper_verify", "network_lockdown"],
        "offense": ["field_attack_kit", "pest_arsenal", "lethal_enforcement"],
        "guest_cannot_disable": True,
        "in_field": (INSTALL / "lib" / "kilroy-core.sh").is_file(),
    }


def _kilroy_domain() -> dict[str, Any]:
    proc_live = Path("/proc/kilroy_field").is_dir()
    dev_live = Path("/dev/kilroy_field").exists()
    kr = _kilroy_root()
    bz = kr / "build" / "bzImage"
    cfg_die = False
    cfg = kr / "build" / "config"
    if cfg.is_file():
        cfg_die = "CONFIG_RTX_FIELD_DIE=y" in cfg.read_text(encoding="utf-8", errors="replace")
    build_ready = (kr / "scripts" / "build-kilroy.sh").is_file()
    live = proc_live or dev_live
    graft = (not live) and kr.is_dir() and build_ready
    mode = "kernel_live" if live else ("userspace_graft" if graft else "staged")
    network = _kilroy_network_lane()
    loopback = _kilroy_loopback()
    nexus_c2 = _kilroy_nexus_c2()
    defense_offense = _kilroy_defense_offense()
    pc_core = (INSTALL / "lib" / "kilroy-core.sh").is_file() or _load(STATE / "kilroy-core.json", {}).get("role") == "pc_core"
    in_field = (
        live
        or graft
        or network.get("in_field")
        or loopback.get("in_field")
        or nexus_c2.get("in_field")
        or defense_offense.get("in_field")
        or pc_core
    )
    return {
        "role": "pc_core",
        "live": live,
        "proc": proc_live,
        "dev": dev_live,
        "kilroy_root": str(kr),
        "build_ready": build_ready,
        "bzimage": bz.is_file(),
        "config_field_die": cfg_die,
        "mode": mode,
        "grants_field_tech": live or graft,
        "abi": "kilroy-field-1.0",
        "motto": "KILROY is 127.0.0.1 — security, Field Tech speed, storage; guest OS untouched",
        "loopback": loopback,
        "nexus_c2": nexus_c2,
        "network_lane": network,
        "defense_offense": defense_offense,
        "znetwork_absorbed": True,
        "guest_loads_normally": True,
        "in_field": in_field,
    }


def _motherboard_domain() -> dict[str, Any]:
    dmi = Path("/sys/class/dmi/id")
    keys = ("board_vendor", "board_name", "product_name", "sys_vendor", "bios_version")
    board: dict[str, str] = {}
    if dmi.is_dir():
        for key in keys:
            val = _read_text(dmi / key)
            if val:
                board[key] = val
    return {
        "present": bool(board),
        "dmi": board,
        "role": "platform_envelope",
    }


def _ram_domain() -> dict[str, Any]:
    mem_kb = 0
    for line in _read_text(Path("/proc/meminfo")).splitlines():
        if line.startswith("MemTotal:"):
            mem_kb = int(line.split()[1])
            break
    return {
        "mem_total_mb": round(mem_kb / 1024) if mem_kb else None,
        "proc": "/proc/meminfo",
        "in_field": mem_kb > 0,
    }


def _storage_domain() -> dict[str, Any]:
    mounts: list[dict[str, str]] = []
    for line in _read_text(Path("/proc/mounts")).splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        dev, mnt, fst = parts[0], parts[1], parts[2]
        if dev.startswith("/dev/") or "field" in mnt.lower() or "nexus" in mnt.lower():
            mounts.append({"device": dev, "mount": mnt, "fstype": fst})
    mirror = INSTALL / ".nexus-field-drive"
    drives_mod = _import_mod("field_drive_system", "lib/field-drive-system.py")
    drives: list[dict[str, Any]] = []
    if drives_mod and hasattr(drives_mod, "discover_all_drives"):
        try:
            drives = drives_mod.discover_all_drives()
        except Exception:
            drives = []
    return {
        "mounts": mounts[:24],
        "field_mirror": str(mirror) if mirror.is_dir() else "",
        "drives_discovered": len(drives),
        "in_field": bool(mirror.is_dir() or drives),
    }


def _voltage_domain() -> dict[str, Any]:
    mod = _import_mod("field_voltage_regulation", "lib/field-voltage-regulation.py")
    if mod and hasattr(mod, "evaluate"):
        try:
            doc = mod.evaluate(seal=False)
            return {
                "ok": bool(doc.get("ok")),
                "present_rail": bool(doc.get("operate_at_present_rail")),
                "grid_blocked": doc.get("power_company_grid_trust_layer") == "blocked",
                "in_field": bool(doc.get("voltage_is_voltage")),
            }
        except Exception:
            pass
    cached = _load(STATE / "field-voltage-regulation-panel.json", {})
    return {
        "ok": bool(cached.get("ok")),
        "present_rail": bool(cached.get("operate_at_present_rail")),
        "grid_blocked": cached.get("power_company_grid_trust_layer") == "blocked",
        "in_field": bool(cached.get("voltage_is_voltage", True)),
    }


def _fcc_domain() -> dict[str, Any]:
    rf_panel = _load(STATE / "field-rf-sentinel-panel.json", {})
    policy = _load(INSTALL / "data" / "fcc-wireless-policy.json", {})
    permitted = _load(INSTALL / "data" / "fcc-permitted-frequencies.json", {})
    bands = len(permitted.get("bands") or permitted.get("frequencies") or [])
    return {
        "policy_present": policy.get("schema") is not None or bool(policy),
        "permitted_bands": bands,
        "rf_panel": bool(rf_panel),
        "enforcement": "field-rf-sentinel",
        "in_field": bands > 0 or bool(rf_panel) or (INSTALL / "lib" / "field-rf-sentinel.py").is_file(),
    }


def _guest_os_domain() -> dict[str, Any]:
    uname = platform.uname()
    system = (uname.system or "").lower()
    guest = {
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
    }
    if "linux" in system:
        guest["passthrough"] = "linux_abi"
    elif "windows" in system:
        guest["passthrough"] = "windows_native"
    elif "darwin" in system:
        guest["passthrough"] = "macos_native"
    else:
        guest["passthrough"] = "unknown"
    guest["kilroy_guest"] = "kilroy" in (uname.release or "").lower()
    return guest


def posture(*, board: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    boot_order = doctrine.get("boot_order") or [
        "kilroy_kernel", "unified_device_field", "underlay", "guest_os",
    ]
    kilroy = _kilroy_domain()
    domains = {
        "kilroy_kernel": kilroy,
        "storage": _storage_domain(),
        "ram": _ram_domain(),
        "motherboard": _motherboard_domain(),
        "voltage": _voltage_domain(),
        "fcc": _fcc_domain(),
    }
    in_field = sum(1 for d in domains.values() if d.get("in_field") or d.get("grants_field_tech") or d.get("live"))
    total = len(domains)
    guest = _guest_os_domain()
    grant = kilroy.get("grants_field_tech") and in_field >= max(3, total // 2)
    doc: dict[str, Any] = {
        "schema": "field-unified-device/v1",
        "updated": _now(),
        "motto": doctrine.get("motto", ""),
        "boot_order": boot_order,
        "one_field": True,
        "whole_device": True,
        "domains": domains,
        "domains_in_field": in_field,
        "domains_total": total,
        "envelope_ratio": round(in_field / max(total, 1), 3),
        "kilroy_grants_field_tech": kilroy.get("grants_field_tech"),
        "guest_os": guest,
        "guest_field_grant": grant,
        "guest_grant_detail": (
            "KILROY + unified envelope active — field tech applies to guest OS"
            if grant
            else "Partial envelope — userspace graft until KILROY kernel boot"
        ),
        "verdict": "GREEN" if grant and kilroy.get("live") else ("PARTIAL" if grant else "WARN"),
    }
    bus_mod = _import_mod("field_unified_bus", "lib/field-unified-bus.py")
    if bus_mod and hasattr(bus_mod, "bus_runtime"):
        try:
            doc["unified_bus"] = bus_mod.bus_runtime()
        except Exception:
            pass
    if board:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(posture(board=False), ensure_ascii=False, indent=2))
        return 0
    if cmd == "board":
        print(json.dumps(posture(board=True), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-unified-device.py [json|board]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())