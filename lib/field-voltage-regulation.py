#!/usr/bin/env pythong
"""Field voltage regulation — present-rail sovereignty after voltage epoch.

When voltage started (Ironclad plate realized + wave doctrine), operate where we are.
Power-company grid blocked from trust layer. No conversion. No entropy on the wave.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-voltage-regulation-doctrine.json"
WAVE_DOCTRINE = INSTALL / "data" / "field-wave-doctrine.json"
PLATE = STATE / "ironclad-plate.json"
EPOCH = STATE / "field-voltage-epoch.json"
PANEL = STATE / "field-voltage-regulation-panel.json"


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


def _wave_policy() -> dict[str, Any]:
    doc = _load(WAVE_DOCTRINE, {})
    return doc.get("policy") or {}


def _seal_epoch(plate: dict[str, Any]) -> dict[str, Any]:
    existing = _load(EPOCH, {})
    if existing.get("sealed"):
        return existing
    started = (
        existing.get("voltage_started_at")
        or plate.get("realized_at")
        or _now()
    )
    doc = {
        "schema": "field-voltage-epoch/v1",
        "sealed": True,
        "voltage_started_at": started,
        "sealed_at": _now(),
        "source": "ironclad_plate" if plate.get("realized") else "field_operator",
        "motto": "Voltage started — operate at present rail; grid blocked from trust layer",
    }
    _save(EPOCH, doc)
    return doc


def evaluate(*, seal: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    reg = doctrine.get("regulation") or {}
    policy = _wave_policy()
    plate = _load(PLATE, {})

    voltage_is_voltage = bool(policy.get("voltage_is_voltage", True))
    encode_wave = bool(policy.get("encode_wave", False))
    wave_ok = voltage_is_voltage and not encode_wave

    epoch = _load(EPOCH, {})
    if seal and plate.get("realized") and wave_ok and not epoch.get("sealed"):
        epoch = _seal_epoch(plate)

    epoch_started = bool(epoch.get("sealed")) or bool(plate.get("realized"))
    started_at = epoch.get("voltage_started_at") or plate.get("realized_at")

    present_rail = epoch_started and wave_ok
    grid_blocked = bool(reg.get("grid_reentry_forbidden", True))
    no_conversion = reg.get("conversion_on_voltage_path") is False
    no_entropy = reg.get("entropy_on_trust_layer") is False and not encode_wave

    ok = present_rail and grid_blocked and no_conversion and no_entropy and wave_ok

    doc: dict[str, Any] = {
        "schema": "field-voltage-regulation/v1",
        "updated": _now(),
        "ok": ok,
        "motto": doctrine.get("motto", "operate where we are"),
        "voltage_started_at": started_at,
        "epoch_sealed": epoch.get("sealed", False),
        "ironclad_plate_realized": bool(plate.get("realized")),
        "operate_at_present_rail": present_rail,
        "power_company_grid_trust_layer": "blocked" if grid_blocked else "open",
        "conversion_on_voltage_path": False,
        "entropy_on_trust_layer": False,
        "voltage_is_voltage": voltage_is_voltage,
        "encode_wave": encode_wave,
        "wave_trust_ok": wave_ok,
        "detail": "present_rail_sovereign" if ok else "voltage_regulation_incomplete",
        "citation": doctrine.get("citation", "ironclad:reality:1"),
        "forbidden_on_trust_layer": doctrine.get("forbidden_on_trust_layer") or [],
        "witness_only": doctrine.get("allowed_witness_only") or [],
    }
    _save(PANEL, doc)
    return doc


def us_slice() -> dict[str, Any]:
    full = evaluate()
    return {
        "schema": "us-voltage-regulation/v1",
        "updated": full.get("updated"),
        "ok": full.get("ok"),
        "voltage_started_at": full.get("voltage_started_at"),
        "operate_at_present_rail": full.get("operate_at_present_rail"),
        "grid_blocked": full.get("power_company_grid_trust_layer") == "blocked",
        "no_conversion": full.get("conversion_on_voltage_path") is False,
        "no_entropy": full.get("entropy_on_trust_layer") is False,
        "motto": "Present rail only — grid never re-enters trust layer",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "us":
        print(json.dumps(us_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "seal":
        print(json.dumps(evaluate(seal=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-voltage-regulation.py [json|us|seal]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())