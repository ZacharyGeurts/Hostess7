#!/usr/bin/env pythong
"""Field power ledger — draw, shed credits, thermodynamic headroom, grid-export witness."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-power-doctrine.json"
LEDGER_FILE = STATE / "field-power-ledger.json"
LEDGER_LOG = STATE / "field-power-ledger.jsonl"
STAMP = STATE / "field-power-ledger.stamp"
RAPL_SNAP = STATE / ".rapl-snapshot.json"

GRID_HARDWARE = os.environ.get("NEXUS_GRID_EXPORT_HARDWARE", "0") == "1"
GRID_METER_W = float(os.environ.get("NEXUS_GRID_EXPORT_METER_W", "0") or "0")


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _log_event(doc: dict[str, Any]) -> None:
    try:
        with LEDGER_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _rapl_energy_uj() -> dict[str, Any]:
    """Intel/AMD RAPL package energy — best-effort CPU draw witness."""
    zones: dict[str, int] = {}
    base = Path("/sys/class/powercap")
    if not base.is_dir():
        base = Path("/sys/devices/virtual/powercap")
    if not base.is_dir():
        return {"available": False, "zones": {}}
    for zone in sorted(base.glob("intel-rapl:*")) + sorted(base.glob("amd-rapl:*")):
        energy = zone / "energy_uj"
        name = zone / "name"
        if not energy.is_file():
            continue
        try:
            label = name.read_text(encoding="utf-8").strip() if name.is_file() else zone.name
            zones[label] = int(energy.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
    return {"available": bool(zones), "zones": zones, "ts": time.time()}


def _rapl_watts() -> dict[str, Any]:
    cur = _rapl_energy_uj()
    if not cur.get("available"):
        return {"available": False, "watts": None}
    prev = _load(RAPL_SNAP, {})
    _save(RAPL_SNAP, cur)
    if not prev.get("zones") or not prev.get("ts"):
        return {"available": True, "watts": None, "warming": True}
    dt = max(cur["ts"] - float(prev["ts"]), 0.001)
    total_uj = 0
    for label, uj in cur["zones"].items():
        puj = int(prev["zones"].get(label) or uj)
        delta = uj - puj
        if delta < 0:
            delta += 2**32
        total_uj += delta
    watts = (total_uj / 1_000_000.0) / dt
    return {"available": True, "watts": round(watts, 3), "dt_s": round(dt, 3), "uj_delta": total_uj}


def _power_supply() -> dict[str, Any]:
    root = Path("/sys/class/power_supply")
    out: dict[str, Any] = {"ac_online": None, "battery_pct": None, "draw_w": None}
    if not root.is_dir():
        return out
    for ac in root.glob("AC*"):
        online = ac / "online"
        try:
            if online.is_file():
                out["ac_online"] = online.read_text(encoding="utf-8").strip() == "1"
                break
        except OSError:
            pass
    for bat in root.glob("BAT*"):
        for key, field in (("capacity", "battery_pct"), ("power_now", "draw_w")):
            p = bat / key
            try:
                if not p.is_file():
                    continue
                val = int(p.read_text(encoding="utf-8").strip())
                if key == "power_now":
                    out["draw_w"] = round(val / 1_000_000.0, 3)
                else:
                    out["battery_pct"] = val
            except (OSError, ValueError):
                pass
        break
    return out


def _shed_credits() -> dict[str, Any]:
    adv = _load(STATE / "wave-shed-advisory.json", {})
    joules = float(adv.get("potential_energy_shed_joules_proxy") or 0)
    ratio = float(adv.get("strip_wave_ratio") or 0)
    draw_red = adv.get("draw_reduction") or {}
    credit_w = 0.0
    if draw_red.get("capture_halted"):
        credit_w += float(os.environ.get("NEXUS_SHED_CAPTURE_CREDIT_W", "2.5"))
    if draw_red.get("usb_autosuspend"):
        credit_w += float(os.environ.get("NEXUS_SHED_USB_CREDIT_W", "0.8"))
    if draw_red.get("quota_lowered"):
        credit_w += float(os.environ.get("NEXUS_SHED_QUOTA_CREDIT_W", "5.0"))
    if joules > 0:
        credit_w += min(joules * 10.0, 15.0)
    return {
        "joules_proxy_shed": joules,
        "strip_wave_ratio": ratio,
        "credit_watts": round(credit_w, 3),
        "level": adv.get("level"),
        "ts": adv.get("ts"),
    }


def _thermal() -> dict[str, Any]:
    return _load(STATE / "thermal-advisory.json", {})


def _clean_juice() -> dict[str, Any]:
    script = INSTALL / "lib" / "field-clean-juice.py"
    if not script.is_file():
        return {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_clean_juice_ledger", script)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.posture() if hasattr(mod, "posture") else {}
    except Exception:
        return {}


def ledger(*, sample_rapl: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    supply = _power_supply()
    rapl = _rapl_watts() if sample_rapl else {"available": False, "watts": None}
    shed = _shed_credits()
    thermal = _thermal()
    juice = _clean_juice()

    measured_w = rapl.get("watts")
    if measured_w is None and supply.get("draw_w") is not None:
        measured_w = abs(float(supply["draw_w"]))

    credit_w = float(shed.get("credit_watts") or 0)
    net_w = None
    headroom_w = None
    export_equiv_w = None
    if measured_w is not None:
        net_w = round(measured_w - credit_w, 3)
        headroom_w = round(credit_w, 3)
        if net_w < 0:
            export_equiv_w = round(-net_w, 3)

    pool = juice.get("pool") or {}
    available_j = pool.get("available_joules")
    if available_j is not None and headroom_w is not None:
        headroom_w = round(float(headroom_w) + float(available_j), 3)

    grid = {
        "hardware_declared": GRID_HARDWARE,
        "meter_witness_w": GRID_METER_W if GRID_HARDWARE and GRID_METER_W else None,
        "utility_sellback": "requires_inverter_and_net_metering",
        "software_role": "witness_only_no_trust_talk",
        "grid_talk": False,
        "trust_layer": "blocked",
    }

    doc = {
        "schema": "field-power-ledger/v2",
        "ts": _now(),
        "doctrine": doctrine.get("title", "field-power"),
        "clean_juice_primary": bool((doctrine.get("policy") or {}).get("clean_juice_primary", True)),
        "unit_primary": "joules",
        "cord": "connected" if supply.get("ac_online") else ("battery" if supply.get("battery_pct") is not None else "unknown"),
        "measured_draw_w": measured_w,
        "shed_credit_w": credit_w,
        "net_draw_w": net_w,
        "headroom_w": headroom_w,
        "export_equivalent_w": export_equiv_w,
        "can_handle_more_load": (available_j or 0) > 0 or (export_equiv_w is not None and export_equiv_w > 0),
        "clean_juice": {
            "pool_joules": pool.get("available_joules"),
            "charge_joules": pool.get("charge_joules"),
            "no_double_voltage": (juice.get("circuit") or {}).get("no_double_voltage"),
            "bsp_leaves": (juice.get("field_3d") or {}).get("bsp_leaves"),
        },
        "rapl": rapl,
        "power_supply": supply,
        "shed": shed,
        "thermal": {
            "peak_c": thermal.get("peak_c"),
            "quota_pct": thermal.get("quota_pct"),
            "level": thermal.get("level"),
            "wave_shed": thermal.get("wave_shed"),
        },
        "grid": grid,
        "performance": juice.get("performance") or {},
        "verdict": _verdict(net_w, supply, thermal),
    }
    return doc


def _verdict(net_w: float | None, supply: dict[str, Any], thermal: dict[str, Any]) -> str:
    if supply.get("ac_online") is False and (supply.get("battery_pct") or 100) < 20:
        return "WARN"
    if thermal.get("level") == "crit":
        return "WARN"
    if net_w is not None and net_w > 80:
        return "WARN"
    if net_w is not None and net_w < 0:
        return "GREEN"
    return "GREEN"


def board_once() -> dict[str, Any]:
    doc = ledger()
    _save(LEDGER_FILE, doc)
    STAMP.write_text(_now() + "\n", encoding="utf-8")
    _log_event({"event": "board", **{k: doc[k] for k in ("ts", "net_draw_w", "headroom_w", "export_equivalent_w")}})
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "board":
        board_once()
        return 0
    if cmd == "json":
        print(json.dumps(ledger(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "headroom":
        doc = ledger()
        print(json.dumps({
            "headroom_w": doc.get("headroom_w"),
            "export_equivalent_w": doc.get("export_equivalent_w"),
            "can_handle_more_load": doc.get("can_handle_more_load"),
            "net_draw_w": doc.get("net_draw_w"),
        }, ensure_ascii=False, indent=2))
        return 0
    print("usage: field-power-ledger.py [json|board|headroom]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())