#!/usr/bin/env pythong
"""Field hardware probe — read-only sysfs/proc, no sudo. Tools from field drive."""
from __future__ import annotations

import json
import os
import platform
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
TOOLS = Path(os.environ.get("NEXUS_FIELD_TOOLS_DIR", str(INSTALL / "lib" / "bin")))
REGISTRY = INSTALL / "data" / "field-tools-registry.json"

RTL_VIDS = {"0bda"}
RTL_PIDS = {"2838", "2832"}


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def probe_usb() -> list[dict[str, Any]]:
    base = Path("/sys/bus/usb/devices")
    devices: list[dict[str, Any]] = []
    if not base.is_dir():
        return devices
    for dev in sorted(base.iterdir()):
        if dev.name.startswith("."):
            continue
        vid = _read_text(dev / "idVendor").lower()
        pid = _read_text(dev / "idProduct").lower()
        if not vid or not pid:
            continue
        manufacturer = _read_text(dev / "manufacturer")
        product = _read_text(dev / "product")
        row = {
            "usb_id": f"{vid}:{pid}",
            "vendor_id": vid,
            "product_id": pid,
            "manufacturer": manufacturer,
            "product": product,
            "rtl_sdr": vid in RTL_VIDS and pid in RTL_PIDS,
            "path": str(dev),
        }
        devices.append(row)
    return devices


def probe_net() -> list[dict[str, Any]]:
    base = Path("/sys/class/net")
    ifaces: list[dict[str, Any]] = []
    if not base.is_dir():
        return ifaces
    for iface in sorted(base.iterdir()):
        if iface.name == "lo":
            continue
        carrier = _read_text(iface / "carrier")
        operstate = _read_text(iface / "operstate")
        mtu = _read_text(iface / "mtu")
        ifaces.append({
            "name": iface.name,
            "carrier": carrier == "1",
            "operstate": operstate or "unknown",
            "mtu": int(mtu) if mtu.isdigit() else None,
        })
    return ifaces


def probe_audio() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    asound = Path("/proc/asound/cards")
    if not asound.is_file():
        return cards
    for line in _read_text(asound).splitlines():
        m = re.match(r"^\s*(\d+)\s+\[([^\]]*)\]", line)
        if not m:
            continue
        cards.append({"index": int(m.group(1)), "label": m.group(2).strip()})
    return cards


def probe_cpu_mem() -> dict[str, Any]:
    cpu_model = ""
    for line in _read_text(Path("/proc/cpuinfo")).splitlines():
        if line.lower().startswith("model name"):
            cpu_model = line.split(":", 1)[-1].strip()
            break
    mem_total_kb = 0
    for line in _read_text(Path("/proc/meminfo")).splitlines():
        if line.startswith("MemTotal:"):
            mem_total_kb = int(line.split()[1])
            break
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "cpu_model": cpu_model,
        "mem_total_mb": round(mem_total_kb / 1024) if mem_total_kb else None,
        "python": platform.python_version(),
    }


def probe_field_tools() -> dict[str, Any]:
    reg = _load_json(REGISTRY, {"tools": []})
    found: list[dict[str, Any]] = []
    tools_dir = TOOLS if TOOLS.is_dir() else INSTALL / "lib" / "bin"
    for tool in reg.get("tools") or []:
        rel = str(tool.get("bin") or tool.get("id") or "")
        if not rel:
            continue
        path = tools_dir / rel
        ready = path.is_file() and os.access(path, os.X_OK)
        found.append({
            "id": tool.get("id"),
            "label": tool.get("label"),
            "bin": str(path),
            "ready": ready,
            "category": tool.get("category"),
        })
    for name in ("field-wave-fm", "field-wave-play", "field-wave-asm", "field-wave-wav", "field-wave-ppm"):
        path = tools_dir / name
        if path.is_file():
            found.append({
                "id": name,
                "label": name,
                "bin": str(path),
                "ready": os.access(path, os.X_OK),
                "category": "rf",
            })
    return {
        "tools_dir": str(tools_dir),
        "count": len(found),
        "ready_count": sum(1 for t in found if t.get("ready")),
        "tools": found,
    }


def probe_all() -> dict[str, Any]:
    usb = probe_usb()
    rtl = [d for d in usb if d.get("rtl_sdr")]
    tools = probe_field_tools()
    rx = _load_json(INSTALL / "data" / "field-receiver-3fields.json", {})
    fields = list(rx.get("fields") or [])
    return {
        "schema": "field-hardware-probe/v1",
        "updated": _now(),
        "standalone": os.environ.get("NEXUS_FIELD_STANDALONE") == "1",
        "no_sudo": True,
        "engine": "sysfs_proc",
        "host": probe_cpu_mem(),
        "usb": usb,
        "rtl_dongles": rtl,
        "dongle_present": bool(rtl),
        "net": probe_net(),
        "audio": probe_audio(),
        "antenna_fields": len(fields),
        "we_are_the_antenna": len(fields) >= 3,
        "field_tools": tools,
        "state_dir": str(STATE),
        "install_root": str(INSTALL),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(probe_all(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-hardware-probe.py [json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())