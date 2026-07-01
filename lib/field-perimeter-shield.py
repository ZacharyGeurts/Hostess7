#!/usr/bin/env pythong
"""NEXUS Field Perimeter Shield — network, wifi, BT, USB, ethernet, power, physical tamper."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-perimeter-doctrine.json"
PANEL_FILE = STATE / "field-perimeter-panel.json"
STAMP_FILE = STATE / "field-perimeter.stamp"
AUDIT_FILE = STATE / "perimeter-events.jsonl"


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


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run(cmd: list[str], *, timeout: int = 12) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or proc.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _read_sysctl(key: str) -> str | None:
    path = Path("/proc/sys") / key.replace(".", "/")
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    return None


def _audit(event: str, detail: Any) -> None:
    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), "event": event, "detail": detail}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _probe_network_edge() -> dict[str, Any]:
    sysctl_keys = (
        "net.ipv4.conf.all.rp_filter",
        "net.ipv6.conf.all.accept_ra",
        "net.ipv4.conf.all.accept_redirects",
        "net.ipv4.conf.all.send_redirects",
    )
    sysctl: dict[str, str | None] = {k: _read_sysctl(k) for k in sysctl_keys}
    gaps = [k for k, v in sysctl.items() if v not in ("1", "0")]
    sharing_units = (
        "smbd.service", "nmbd.service", "avahi-daemon.service",
        "nfs-server.service", "rpcbind.service",
    )
    sharing_active: list[str] = []
    for unit in sharing_units:
        st = _run(["systemctl", "is-active", unit], timeout=5)
        if st == "active":
            sharing_active.append(unit)
    nft_ok = _run(["nft", "list", "table", "inet", "nexus"], timeout=8).startswith("table")
    perimeter_chain = "perimeter_edge" in _run(["nft", "list", "table", "inet", "nexus"], timeout=8)
    return {
        "ok": len(gaps) == 0 and not sharing_active,
        "sysctl": sysctl,
        "sysctl_gaps": gaps,
        "sharing_active": sharing_active,
        "nftables_nexus": nft_ok,
        "perimeter_chain": perimeter_chain,
    }


def _rfkill_by_type(rtype: str) -> dict[str, Any]:
    text = _run(["rfkill", "list"])
    rows: list[dict[str, str]] = []
    block: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^(\d+):\s+(\S+):\s+(\S+)", line)
        if m:
            if block:
                rows.append(block)
            block = {"index": m.group(1), "name": m.group(2), "type": m.group(3)}
            continue
        for key in ("Soft blocked", "Hard blocked"):
            if key in line:
                block[key.lower().replace(" ", "_")] = line.split(":", 1)[-1].strip()
    if block:
        rows.append(block)
    matched = [r for r in rows if r.get("type", "").lower() == rtype.lower()]
    soft_blocked = any(r.get("soft_blocked", "").lower() == "yes" for r in matched)
    hard_blocked = any(r.get("hard_blocked", "").lower() == "yes" for r in matched)
    return {
        "devices": matched,
        "soft_blocked": soft_blocked,
        "hard_blocked": hard_blocked,
        "present": bool(matched),
    }


def _probe_wifi() -> dict[str, Any]:
    rf = _rfkill_by_type("wlan")
    connected: dict[str, Any] = {"ssid": None, "security": None, "device": None}
    nm = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev", "status"])
    wifi_dev = None
    for line in nm.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
            wifi_dev = parts[0]
            break
    if wifi_dev:
        connected["device"] = wifi_dev
        active = _run(["nmcli", "-t", "-f", "NAME,SSID,SECURITY", "connection", "show", "--active"])
        for line in active.splitlines():
            cols = line.split(":")
            if len(cols) >= 3:
                connected["ssid"] = cols[1] or cols[0]
                connected["security"] = cols[2]
                break
    rf_panel = STATE / "field-rf-panel.json"
    rf_threats = 0
    if rf_panel.is_file():
        try:
            rf_doc = json.loads(rf_panel.read_text(encoding="utf-8"))
            threats = rf_doc.get("threats") or rf_doc.get("active_threats") or []
            if isinstance(threats, list):
                rf_threats = len(threats)
        except (OSError, json.JSONDecodeError):
            pass
    weak_wpa = connected.get("security") in ("", "--", "WEP", "WPA1")
    return {
        "ok": not weak_wpa and rf_threats == 0,
        "rfkill": rf,
        "connected": connected,
        "rf_sentinel_threats": rf_threats,
        "weak_association": weak_wpa,
    }


def _probe_bluetooth() -> dict[str, Any]:
    rf = _rfkill_by_type("bluetooth")
    powered = None
    paired = 0
    if _run(["which", "bluetoothctl"]):
        show = _run(["bluetoothctl", "show"], timeout=10)
        powered = "Powered: yes" in show
        devs = _run(["bluetoothctl", "devices"], timeout=10)
        paired = len([ln for ln in devs.splitlines() if ln.startswith("Device ")])
    return {
        "ok": rf.get("soft_blocked") or not powered,
        "rfkill": rf,
        "powered": powered,
        "paired_devices": paired,
    }


def _probe_ethernet() -> dict[str, Any]:
    ifaces: list[dict[str, Any]] = []
    promisc_any = False
    for entry in sorted(Path("/sys/class/net").glob("*")):
        name = entry.name
        if name == "lo":
            continue
        if not (entry / "device").exists():
            continue
        carrier = None
        promisc = False
        try:
            if (entry / "carrier").is_file():
                carrier = (entry / "carrier").read_text(encoding="utf-8").strip() == "1"
            if (entry / "flags").is_file():
                flags = int((entry / "flags").read_text(encoding="utf-8").strip(), 16)
                promisc = bool(flags & 0x100)
        except (OSError, ValueError):
            pass
        if promisc:
            promisc_any = True
        ifaces.append({"name": name, "carrier": carrier, "promiscuous": promisc})
    return {"ok": not promisc_any, "interfaces": ifaces, "promiscuous_detected": promisc_any}


def _probe_usb() -> dict[str, Any]:
    devices: list[dict[str, str]] = []
    usb_root = Path("/sys/bus/usb/devices")
    if usb_root.is_dir():
        for dev in sorted(usb_root.iterdir()):
            if not re.match(r"^\d", dev.name):
                continue
            row: dict[str, str] = {"id": dev.name}
            for key in ("idVendor", "idProduct", "manufacturer", "product", "bDeviceClass"):
                p = dev / key
                if p.is_file():
                    try:
                        row[key] = p.read_text(encoding="utf-8", errors="replace").strip()
                    except OSError:
                        pass
            devices.append(row)
    storage_class = sum(1 for d in devices if d.get("bDeviceClass") == "08")
    hid_class = sum(1 for d in devices if d.get("bDeviceClass") == "03")
    return {
        "ok": True,
        "device_count": len(devices),
        "mass_storage": storage_class,
        "hid": hid_class,
        "devices_tail": devices[-8:],
    }


def _probe_power_acpi() -> dict[str, Any]:
    ac_online: bool | None = None
    for ac in Path("/sys/class/power_supply").glob("AC*"):
        online = ac / "online"
        try:
            if online.is_file():
                ac_online = online.read_text(encoding="utf-8").strip() == "1"
                break
        except OSError:
            pass
    battery_pct = None
    for bat in Path("/sys/class/power_supply").glob("BAT*"):
        cap = bat / "capacity"
        try:
            if cap.is_file():
                battery_pct = int(float(cap.read_text(encoding="utf-8").strip()))
                break
        except (OSError, ValueError):
            pass
    sleep_states: list[str] = []
    mem_sleep = Path("/sys/power/mem_sleep")
    try:
        if mem_sleep.is_file():
            sleep_states = mem_sleep.read_text(encoding="utf-8", errors="replace").strip().split()
    except OSError:
        pass
    wol_disabled = True
    if _run(["which", "ethtool"]):
        for iface in Path("/sys/class/net").glob("*"):
            if iface.name == "lo" or not (iface / "device").exists():
                continue
            out = _run(["ethtool", iface.name], timeout=6)
            if "Wake-on: d" not in out and "Wake-on:" in out:
                wol_disabled = False
                break
    return {
        "ok": ac_online is not False,
        "ac_online": ac_online,
        "battery_percent": battery_pct,
        "sleep_states": sleep_states,
        "wol_disabled": wol_disabled,
        "power_cord": "connected" if ac_online else ("battery" if battery_pct is not None else "unknown"),
    }


def _probe_physical() -> dict[str, Any]:
    tpm = Path("/sys/class/tpm/tpm0")
    tpm_present = tpm.exists()
    usb_recent = 0
    journal = _run(["journalctl", "-k", "-n", "40", "--no-pager", "-o", "cat"], timeout=10)
    for line in journal.splitlines():
        low = line.lower()
        if "usb" in low and any(tok in low for tok in ("new device", "attach", "disconnect")):
            usb_recent += 1
    return {
        "ok": True,
        "tpm_present": tpm_present,
        "usb_events_recent": usb_recent,
        "tamper_watch": usb_recent > 6,
    }


def _layer_verdict(layer: dict[str, Any]) -> str:
    if layer.get("ok") is True:
        return "GREEN"
    if layer.get("ok") is False:
        return "WARN"
    return "UNKNOWN"


def posture(*, apply: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    layers = {
        "network_edge": _probe_network_edge(),
        "wifi": _probe_wifi(),
        "bluetooth": _probe_bluetooth(),
        "ethernet": _probe_ethernet(),
        "usb": _probe_usb(),
        "power_acpi": _probe_power_acpi(),
        "physical": _probe_physical(),
    }
    if apply and os.geteuid() == 0:
        enforce = INSTALL / "lib" / "field-perimeter-enforce.sh"
        if enforce.is_file():
            env = {**os.environ, "NEXUS_PERIMETER_APPLY": "1", "NEXUS_INSTALL_ROOT": str(INSTALL)}
            subprocess.run(["bash", str(enforce), "apply"], env=env, timeout=60, check=False)
            _audit("apply", {"via": str(enforce)})
        bt = layers.get("bluetooth") or {}
        if bt.get("paired_devices", 0) > 3 and not bt.get("rfkill", {}).get("soft_blocked"):
            _run(["rfkill", "block", "bluetooth"], timeout=8)
            _audit("rfkill_bluetooth", "paired_overflow")
        layers = {
            "network_edge": _probe_network_edge(),
            "wifi": _probe_wifi(),
            "bluetooth": _probe_bluetooth(),
            "ethernet": _probe_ethernet(),
            "usb": _probe_usb(),
            "power_acpi": _probe_power_acpi(),
            "physical": _probe_physical(),
        }
    verdicts = [_layer_verdict(v) for v in layers.values()]
    overall = "GREEN"
    if any(v == "WARN" for v in verdicts):
        overall = "WARN"
    if sum(1 for v in verdicts if v == "UNKNOWN") > 3:
        overall = "WARN"
    return {
        "schema": "field-perimeter/v1",
        "ts": _now(),
        "verdict": overall,
        "doctrine": doctrine.get("title", "field-perimeter"),
        "layers": layers,
        "layer_verdicts": {k: _layer_verdict(v) for k, v in layers.items()},
        "protected_surfaces": [
            "network_edge", "wifi", "bluetooth", "ethernet", "usb", "power_acpi", "physical",
        ],
    }


def board_once(*, apply: bool = False) -> dict[str, Any]:
    doc = posture(apply=apply)
    _save(PANEL_FILE, doc)
    STAMP_FILE.write_text(_now() + "\n", encoding="utf-8")
    return doc


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    apply = os.environ.get("NEXUS_PERIMETER_APPLY", "0") == "1"
    if mode == "board":
        board_once(apply=apply)
        return 0
    if mode == "apply":
        board_once(apply=True)
        return 0
    if mode == "json":
        print(json.dumps(posture(apply=apply), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-perimeter-shield.py [json|board|apply]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())