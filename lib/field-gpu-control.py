#!/usr/bin/env pythong
"""Field GPU Control — detect NVIDIA/AMD/Intel + legacy catalog, fan/temp readouts."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-gpu-control-doctrine.json"
SHELL_DOCK = INSTALL / "data" / "field-shell-dock-doctrine.json"
SETTINGS = STATE / "field-gpu-control-settings.json"
PANEL = STATE / "field-gpu-control-panel.json"
QUEEN_GPU = SG / "NewLatest" / "Queen" / "data" / "gpu-probe.json"
from sg_paths import grok16_root as _grok16_root
RTX_GATE = _grok16_root() / "forge" / "rtx_gate.py"

VENDOR_MAP = {
    "10de": "nvidia",
    "1002": "amd",
    "8086": "intel",
    "1a03": "aspeed",
    "1234": "qemu",
    "1af4": "virtio",
}


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _run_lines(cmd: list[str], *, timeout: int = 10) -> list[str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return []
        return [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return []


def _pci_gpus() -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in _run_lines(["lspci", "-nn"], timeout=8):
        if "VGA" not in line and "3D" not in line and "Display" not in line:
            continue
        m = re.search(r"\[([0-9a-f]{4}):([0-9a-f]{4})\]", line, re.I)
        if not m:
            continue
        vid, did = m.group(1).lower(), m.group(2).lower()
        key = f"{vid}:{did}"
        if key in seen:
            continue
        seen.add(key)
        slot = line.split()[0] if line else ""
        name = re.sub(r"\s*\[[0-9a-f]{4}:[0-9a-f]{4}\].*$", "", line.split(":", 2)[-1]).strip()
        vendor = VENDOR_MAP.get(vid, "unknown")
        gpus.append({
            "id": f"pci_{vid}_{did}_{slot.replace(':', '_')}",
            "source": "pci",
            "pci_slot": slot,
            "vendor_id": vid,
            "device_id": did,
            "vendor": vendor,
            "name": name or f"GPU {vid}:{did}",
            "detected": True,
            "legacy": False,
        })
    if gpus:
        return gpus
    drm = Path("/sys/class/drm")
    if not drm.is_dir():
        return gpus
    for card in sorted(drm.glob("card[0-9]*")):
        if not card.is_dir():
            continue
        dev = card / "device"
        try:
            vid = _read_text(dev / "vendor").lower().replace("0x", "")
            did = _read_text(dev / "device").lower().replace("0x", "")
        except OSError:
            continue
        if not vid:
            continue
        key = f"{vid}:{did}"
        if key in seen:
            continue
        seen.add(key)
        vendor = VENDOR_MAP.get(vid, "unknown")
        gpus.append({
            "id": f"drm_{card.name}_{vid}_{did}",
            "source": "drm",
            "drm_card": card.name,
            "vendor_id": vid,
            "device_id": did,
            "vendor": vendor,
            "name": _read_text(dev / "uevent") or f"GPU {vid}:{did}",
            "detected": True,
            "legacy": False,
        })
    return gpus


def _nvidia_gpus() -> list[dict[str, Any]]:
    fields = [
        "index", "name", "driver_version", "temperature.gpu", "fan.speed",
        "power.draw", "power.limit", "utilization.gpu", "utilization.memory",
        "memory.total", "memory.used", "clocks.gr", "clocks.mem", "clocks.max.gr", "clocks.max.mem",
    ]
    lines = _run_lines(
        ["nvidia-smi", f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"],
        timeout=12,
    )
    gpus: list[dict[str, Any]] = []
    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        def _num(i: int, default: float | None = None) -> float | None:
            if i >= len(parts) or parts[i] in ("", "[N/A]", "N/A"):
                return default
            try:
                return float(parts[i])
            except ValueError:
                return default

        idx = int(parts[0]) if parts[0].isdigit() else len(gpus)
        name = parts[1]
        gpus.append({
            "id": f"nvidia_{idx}",
            "source": "nvidia-smi",
            "index": idx,
            "vendor": "nvidia",
            "name": name,
            "driver": parts[2] if len(parts) > 2 else "",
            "detected": True,
            "legacy": False,
            "rtx": "RTX" in name.upper(),
            "readouts": {
                "temp_c": _num(3),
                "fan_pct": _num(4),
                "power_w": _num(5),
                "power_limit_w": _num(6),
                "gpu_util_pct": _num(7),
                "mem_util_pct": _num(8),
                "vram_total_mb": _num(9),
                "vram_used_mb": _num(10),
                "core_clock_mhz": _num(11),
                "mem_clock_mhz": _num(12),
                "core_clock_max_mhz": _num(13),
                "mem_clock_max_mhz": _num(14),
            },
        })
    return gpus


def _amdgpu_hwmon() -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    hwmon_root = Path("/sys/class/drm")
    idx = 0
    for card in sorted(hwmon_root.glob("card[0-9]*")):
        if not card.is_dir():
            continue
        dev = card / "device"
        try:
            vid = _read_text(dev / "vendor").lower().replace("0x", "")
        except OSError:
            continue
        if vid != "1002":
            continue
        hwmon = None
        for h in sorted(dev.glob("hwmon/hwmon*")):
            if (h / "name").is_file():
                hwmon = h
                break
        temp = fan = power = None
        if hwmon:
            for t in hwmon.glob("temp*_input"):
                raw = _read_text(t)
                if raw.isdigit():
                    temp = round(int(raw) / 1000, 1)
                    break
            for f in hwmon.glob("fan*_input"):
                raw = _read_text(f)
                if raw.isdigit():
                    fan = int(raw)
                    break
            for p in hwmon.glob("power*_average"):
                raw = _read_text(p)
                if raw.isdigit():
                    power = round(int(raw) / 1_000_000, 1)
                    break
        gpus.append({
            "id": f"amd_{idx}",
            "source": "amdgpu-sysfs",
            "index": idx,
            "vendor": "amd",
            "name": f"AMD GPU ({card.name})",
            "detected": True,
            "legacy": False,
            "readouts": {
                "temp_c": temp,
                "fan_rpm": fan,
                "power_w": power,
            },
        })
        idx += 1
    return gpus


def _intel_gpus(pci: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    idx = 0
    for row in pci:
        if row.get("vendor") != "intel":
            continue
        gpus.append({
            "id": f"intel_{idx}",
            "source": "pci-intel",
            "index": idx,
            "vendor": "intel",
            "name": row.get("name") or "Intel GPU",
            "pci_slot": row.get("pci_slot"),
            "detected": True,
            "legacy": False,
            "readouts": {},
        })
        idx += 1
    return gpus


def _merge_detected() -> list[dict[str, Any]]:
    pci = _pci_gpus()
    nvidia = _nvidia_gpus()
    amd = _amdgpu_hwmon()
    intel = _intel_gpus(pci)
    merged: list[dict[str, Any]] = []
    by_vendor: dict[str, list[dict[str, Any]]] = {
        "nvidia": nvidia,
        "amd": amd,
        "intel": intel,
    }
    for vendor, rows in by_vendor.items():
        if rows:
            merged.extend(rows)
            continue
        for row in pci:
            if row.get("vendor") == vendor:
                merged.append({**row, "readouts": row.get("readouts") or {}})
    for row in pci:
        if row.get("vendor") not in ("nvidia", "amd", "intel"):
            merged.append({**row, "readouts": {}})
    if not merged:
        for row in pci:
            merged.append({**row, "readouts": {}})
    return merged


def _legacy_catalog() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    return list(doctrine.get("legacy_catalog") or [])


def _shell_dock_icons() -> list[dict[str, Any]]:
    shell = _load(SHELL_DOCK, {})
    raw = shell.get("dock_icons") or _load(DOCTRINE, {}).get("dock_icons") or []
    return [{**ic, "active": ic.get("id") == "gpu"} for ic in raw]


def _settings() -> dict[str, Any]:
    saved = _load(SETTINGS, {})
    doctrine = _load(DOCTRINE, {})
    default_vendor = saved.get("vendor_filter") or "all"
    default_gpu = saved.get("selected_gpu_id")
    legacy = saved.get("legacy_selection")
    hue = saved.get("unknown_hue", 142)
    return {
        "vendor_filter": default_vendor,
        "selected_gpu_id": default_gpu,
        "legacy_selection": legacy,
        "unknown_hue": hue,
        "dock_icons": _shell_dock_icons(),
    }


def _rtx_status() -> dict[str, Any]:
    if not RTX_GATE.is_file():
        return {"ok": False}
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "pythong"), str(RTX_GATE), "json"],
            capture_output=True, text=True, timeout=12, cwd=str(_grok16_root()),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"ok": False}


def _active_gpu(gpus: list[dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any]:
    sel = settings.get("selected_gpu_id")
    if sel:
        for g in gpus:
            if g.get("id") == sel:
                return g
        for leg in _legacy_catalog():
            if leg.get("id") == sel:
                return {
                    "id": leg["id"],
                    "name": leg.get("name"),
                    "vendor": leg.get("vendor"),
                    "legacy": True,
                    "detected": False,
                    "color_wheel": bool(leg.get("color_wheel")),
                    "color": leg.get("color"),
                    "readouts": {
                        "vram_total_mb": leg.get("vram_mb"),
                        "era": leg.get("era"),
                        "bus": leg.get("bus"),
                    },
                }
    vendor = settings.get("vendor_filter") or "all"
    pool = gpus if vendor == "all" else [g for g in gpus if g.get("vendor") == vendor]
    if pool:
        return pool[0]
    if gpus:
        return gpus[0]
    leg = settings.get("legacy_selection") or "color_wheel"
    for item in _legacy_catalog():
        if item.get("id") == leg:
            return {
                "id": item["id"],
                "name": item.get("name"),
                "vendor": item.get("vendor", "unknown"),
                "legacy": True,
                "detected": False,
                "color_wheel": bool(item.get("color_wheel")),
                "color": item.get("color"),
                "readouts": {},
            }
    return {
        "id": "color_wheel",
        "name": "Unknown GPU",
        "vendor": "unknown",
        "legacy": True,
        "color_wheel": True,
        "detected": False,
        "readouts": {},
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    settings = _settings()
    detected = _merge_detected()
    queen = _load(QUEEN_GPU, {})
    active = _active_gpu(detected, settings)
    vendor_filter = settings.get("vendor_filter") or "all"
    filtered = detected if vendor_filter == "all" else [g for g in detected if g.get("vendor") == vendor_filter]

    doc = {
        "schema": "field-gpu-control/v1",
        "ts": _now(),
        "ok": True,
        "doctrine": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "palette": doctrine.get("palette") or {},
        "vendors": doctrine.get("vendors") or {},
        "detected_count": len(detected),
        "gpus": detected,
        "filtered_gpus": filtered,
        "legacy_catalog": _legacy_catalog(),
        "active_gpu": active,
        "settings": settings,
        "queen_probe": {
            "pci_display": queen.get("pci_display"),
            "nvidia_count": queen.get("nvidia_count"),
            "intel_arc_count": queen.get("intel_arc_count"),
            "ready_rtx": (queen.get("compilers") or {}).get("ready_rtx"),
        },
        "rtx_gate": _rtx_status(),
        "routes": doctrine.get("routes") or {"panel": "/field-gpu", "api": "/api/field-gpu"},
        "poll_ms": (doctrine.get("policy") or {}).get("poll_ms", 1200),
        "posture": (
            f"Field GPU — {len(detected)} detected · active {active.get('name', '?')} · "
            f"filter {vendor_filter}"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"vendor_filter", "selected_gpu_id", "legacy_selection", "unknown_hue"}
    saved = _load(SETTINGS, {})
    for key, val in patch.items():
        if key in allowed:
            saved[key] = val
    _save_atomic(SETTINGS, saved)
    return posture()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-gpu-control.py [json|settings JSON]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())