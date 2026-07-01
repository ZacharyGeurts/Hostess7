#!/usr/bin/env pythong
"""NEXUS Hardware Wire — detect and operate hooks for all field hardware; no third-party middlemen."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardware_wire_registry import (
    HARDWARE_CLASSES,
    NEXUS_BLOB_MARKERS,
    WIRE_ALLOWED,
    WIRE_CHAIN,
)
from proc_threat_match import proc_hits_any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_JSON = STATE / "hardware-wire.json"
ALERTS = STATE / "hardware-wire-alerts.jsonl"
SMART_WIRE_JSON = STATE / "smart-wire.json"

# Broad utilities — only middlemen when holding device FDs or capture cmdline markers.
CONDITIONAL_MIDDLEMAN = frozenset({
    "ffmpeg", "ffplay", "gst-launch", "gst-launch-1.0", "python3", "python", "pythong",
    "pw-record", "pw-cat", "sox",
})

CAPTURE_CMD_MARKERS = (
    "alsa", "pulse", "v4l2", "video4linux", "x11grab", "gdigrab", "avfoundation",
    "screen capture", "display capture", "/dev/video", "/dev/snd", "webcam", "camera",
    "record", "grab", "keylog",
)


def _enabled() -> bool:
    env = os.environ.get("NEXUS_HARDWARE_WIRE", os.environ.get("NEXUS_SMART_WIRE", "1"))
    return env not in ("0", "false", "no", "off")


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


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _proc_comm(pid: str) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _proc_cmdline(pid: str) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _proc_fds(pid: str) -> list[str]:
    out: list[str] = []
    fd_dir = Path(f"/proc/{pid}/fd")
    if not fd_dir.is_dir():
        return out
    try:
        links = list(fd_dir.iterdir())
    except OSError:
        return out
    for link in links:
        try:
            out.append(os.readlink(link))
        except OSError:
            continue
    return out


def _is_nexus_stack(comm: str, cmd: str) -> bool:
    if comm in WIRE_ALLOWED:
        return True
    blob = f"{comm} {cmd}".lower()
    return any(m in blob for m in NEXUS_BLOB_MARKERS)


def _classify_proc(
    hw_class: str,
    label: str,
    middleman_procs: frozenset[str],
    fd_markers: tuple[str, ...],
    pid: str,
    comm: str,
    cmd: str,
    fds: list[str],
) -> dict[str, Any] | None:
    marker = proc_hits_any(middleman_procs, comm, cmd)
    if marker:
        if marker in CONDITIONAL_MIDDLEMAN:
            has_fd = bool(fd_markers) and any(any(m in fd for m in fd_markers) for fd in fds)
            has_cmd = any(m in cmd.lower() for m in CAPTURE_CMD_MARKERS)
            if not has_fd and not has_cmd:
                marker = None
        if marker:
            return {
                "pid": pid,
                "comm": comm,
                "class": hw_class,
                "class_label": label,
                "kind": f"{hw_class}_middleman_proc",
                "reason": f"proc:{marker}",
                "iff": "HOSTILE",
            }
    if not fd_markers:
        return None
    for fd in fds:
        if not any(m in fd for m in fd_markers):
            continue
        if _is_nexus_stack(comm, cmd):
            continue
        return {
            "pid": pid,
            "comm": comm,
            "class": hw_class,
            "class_label": label,
            "kind": f"{hw_class}_device_middleman",
            "reason": f"device_fd:{fd}",
            "iff": "HOSTILE",
        }
    return None


def scan_wire(*, hw_class_filter: str | None = None) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    try:
        entries = list(Path("/proc").iterdir())
    except OSError:
        return hits
    classes = HARDWARE_CLASSES
    if hw_class_filter:
        classes = tuple(c for c in HARDWARE_CLASSES if c.id == hw_class_filter)
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = entry.name
        try:
            comm = _proc_comm(pid)
            cmd = _proc_cmdline(pid)
            fds = _proc_fds(pid)
            for hw in classes:
                verdict = _classify_proc(hw.id, hw.label, hw.middleman_procs, hw.fd_markers, pid, comm, cmd, fds)
                if verdict:
                    verdict["ts"] = _now()
                    verdict["enforcement"] = f"INTERDICT — hardware wire ({hw.id}): no middleman"
                    hits.append(verdict)
                    break
        except OSError:
            continue
    return hits


def _hardware_inventory() -> dict[str, Any]:
    probe_py = INSTALL / "lib" / "field-hardware-probe.py"
    if not probe_py.is_file():
        return {"available": False}
    try:
        proc = subprocess.run(
            [sys.executable, str(probe_py), "json"],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ},
        )
        if proc.stdout.strip():
            doc = json.loads(proc.stdout)
            return {
                "available": True,
                "usb_count": len(doc.get("usb") or []),
                "rtl_dongles": len(doc.get("rtl_dongles") or []),
                "net_ifaces": len(doc.get("net") or []),
                "audio_cards": len(doc.get("audio") or []),
                "dongle_present": bool(doc.get("dongle_present")),
            }
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"available": False}


def _log_alert(hit: dict[str, Any]) -> None:
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(hit, ensure_ascii=False) + "\n")


def _publish_smart_wire_compat(hits: list[dict[str, Any]], shield_hits: int) -> None:
    input_hits = [h for h in hits if h.get("class") == "input"]
    doc = {
        "schema": "nexus-smart-wire/v1",
        "updated": _now(),
        "enabled": True,
        "owner": "nexus",
        "middleman_policy": "no_third_party_keyboard_wire",
        "pass_through": os.environ.get("NEXUS_HOOK_PASS_THROUGH", "0") == "1",
        "wire_chain": WIRE_CHAIN,
        "hit_count": len(input_hits),
        "shield_hit_count": shield_hits,
        "hits": input_hits[:48],
        "hardware_wire": True,
        "policy": "Smart wire secured — nobody else is middleman for keyboard",
    }
    _save_json(SMART_WIRE_JSON, doc)


def enforce(*, kill: bool | None = None) -> dict[str, Any]:
    if not _enabled():
        return {"schema": "nexus-hardware-wire/v1", "enabled": False, "hits": []}
    if kill is None:
        kill = os.environ.get("NEXUS_HARDWARE_WIRE_KILL", os.environ.get("NEXUS_SMART_WIRE_KILL", "1")) == "1"
        kill = kill and os.geteuid() == 0
    hits = scan_wire()
    by_class: dict[str, int] = {}
    for hit in hits:
        cls = str(hit.get("class") or "unknown")
        by_class[cls] = by_class.get(cls, 0) + 1
        _log_alert(hit)
        if kill:
            try:
                os.kill(int(hit["pid"]), 9)
                hit["killed"] = True
            except (OSError, ValueError):
                hit["killed"] = False
        else:
            hit["killed"] = False
    shield_hits = 0
    shield_py = INSTALL / "lib" / "admin-window-shield.py"
    if shield_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(shield_py), "enforce"],
                capture_output=True,
                text=True,
                timeout=20,
                env={**os.environ},
            )
            if proc.stdout.strip():
                shield_doc = json.loads(proc.stdout)
                shield_hits = int(shield_doc.get("hit_count") or 0)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    inventory = _hardware_inventory()
    classes_doc = [
        {
            "id": hw.id,
            "label": hw.label,
            "hook_events": list(hw.hook_events),
            "fd_markers": list(hw.fd_markers),
            "middleman_proc_count": len(hw.middleman_procs),
        }
        for hw in HARDWARE_CLASSES
    ]
    doc = {
        "schema": "nexus-hardware-wire/v1",
        "updated": _now(),
        "enabled": True,
        "owner": "nexus",
        "mode": "field_fast_safe",
        "middleman_policy": "no_third_party_hardware_wire",
        "pass_through": os.environ.get("NEXUS_HOOK_PASS_THROUGH", "0") == "1",
        "wire_chain": WIRE_CHAIN,
        "hit_count": len(hits),
        "hits_by_class": by_class,
        "shield_hit_count": shield_hits,
        "hits": hits[:64],
        "hardware_classes": classes_doc,
        "wire_allowed_count": len(WIRE_ALLOWED),
        "inventory": inventory,
        "browser_hooks": {
            "operate": True,
            "block_untrusted": True,
            "dispatch_types": list(__import__("hardware_wire_registry").BROWSER_DISPATCH_TYPES),
        },
        "policy": "Hardware wire secured — NEXUS detects and operates all field hardware hooks",
    }
    _save_json(PANEL_JSON, doc)
    _publish_smart_wire_compat(hits, shield_hits)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_JSON.is_file():
        doc = _load_json(PANEL_JSON, {})
        if doc.get("schema") == "nexus-hardware-wire/v1":
            return doc
    return enforce(kill=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "enforce":
        print(json.dumps(enforce(), ensure_ascii=False))
        return 0
    if cmd == "scan":
        filt = (sys.argv[2] if len(sys.argv) > 2 else "").strip() or None
        print(json.dumps({"hits": scan_wire(hw_class_filter=filt)}, ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "classes":
        print(json.dumps({
            "classes": [
                {"id": hw.id, "label": hw.label, "hook_events": list(hw.hook_events)}
                for hw in HARDWARE_CLASSES
            ],
        }, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hardware-wire.py [json|scan|enforce|classes]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())