#!/usr/bin/env pythong
"""Physics witness — thermals, entropy, isotope shared by every plate and section."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "NewLatest" else INSTALL.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-physics-witness-doctrine.json"
PANEL = STATE / "field-physics-witness.json"


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


def thermal_slice() -> dict[str, Any]:
    guard = _load(STATE / "field-thermal-guard.json", {})
    metrics = _load(STATE / "field-thermal-metrics.json", {})
    advisory = _load(STATE / "thermal-advisory.json", {})
    anomaly = _load(STATE / "field-thermal-anomaly.json", {})
    level = str(advisory.get("level") or guard.get("level") or "ok").lower()
    headroom = float(guard.get("headroom_pct") or 100.0)
    hot = level in ("warn", "crit", "storm") or bool(anomaly.get("active"))
    peak = guard.get("peak_c") or anomaly.get("peak_c") or advisory.get("peak_c")
    return {
        "available": bool(guard or advisory),
        "level": level,
        "hot": hot,
        "cool_ok": not hot and headroom >= 15,
        "headroom_pct": round(headroom, 1),
        "peak_c": peak,
        "rapl_watts": guard.get("rapl_watts") or guard.get("current_power_w"),
        "anomaly_active": bool(anomaly.get("active")),
        "certainty_score": guard.get("certainty_score") or metrics.get("certainty_score"),
        "joules_per_field_op": guard.get("joules_per_field_op"),
        "max_ops_per_second_at_budget": guard.get("max_ops_per_second_at_budget"),
        "never_build_under_heat": True,
    }


def entropy_slice() -> dict[str, Any]:
    voltage = _load(STATE / "field-voltage-regulation-panel.json", {})
    bus = _load(STATE / "field-unified-bus-runtime.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    gate = bridge.get("gate") or {}
    bus_thermal = bus.get("thermal") if isinstance(bus.get("thermal"), dict) else {}
    entropy_on_trust = bool(
        voltage.get("entropy_on_trust_layer")
        or (voltage.get("policy") or {}).get("entropy_on_trust_layer")
    )
    entropy_norm = 0.5
    demod_py = INSTALL / "lib" / "field-spectrum-demod.py"
    if demod_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("fps_demod", demod_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "_field_physics_state"):
                    phys = mod._field_physics_state({"mesh": {"tri_compare": {}}}, {})
                    entropy_norm = float(phys.get("entropy_norm") or 0.5)
        except Exception:
            pass
    shannon_uniform_4 = round(math.log2(4), 4)
    return {
        "available": True,
        "entropy_norm": round(entropy_norm, 4),
        "entropy_on_trust_layer": entropy_on_trust,
        "entropy_ok": bool(gate.get("entropy_ok", not entropy_on_trust)),
        "bus_entropy": bus_thermal.get("entropy"),
        "fabric_slot": "entropy",
        "shannon_uniform_4_bits": shannon_uniform_4,
        "second_law_ok": True,
        "layers": ["shannon_surprise", "field_entropy_norm", "fabric_entropy_slot"],
        "statement": "Entropy is layered — Shannon on files, field norm on mesh, fabric floor at init.",
    }


def isotope_slice() -> dict[str, Any]:
    doctrine_path = GROK16 / "data" / "g16-iron-plate-doctrine.json"
    doctrine = _load(doctrine_path, {})
    twins = doctrine.get("registered_twins") or []
    twin = next((t for t in twins if t.get("stem") == "speed_demo"), twins[0] if twins else {})
    chamber = GROK16 / str(twin.get("chamber") or "examples/speed-demo")
    faces = twin.get("faces") or {}
    present = {k: (chamber / v).is_file() for k, v in faces.items()}
    kernel = list(twin.get("kernel") or [])
    triad = doctrine.get("triad") or {}
    identical = bool((doctrine.get("twin_policy") or {}).get("identical_kernel_required"))
    ok = bool(kernel) and "entropy_fold" in kernel and (not faces or all(present.values()))
    return {
        "available": doctrine_path.is_file(),
        "stem": twin.get("stem") or "speed_demo",
        "identical_kernel_required": identical,
        "faces_present": present,
        "kernel_symbols": kernel,
        "triad": {k: (v or {}).get("statement") or k for k, v in triad.items() if isinstance(v, dict)},
        "ok": ok,
        "statement": "Isotope — identical C/C++/Python twins on one entropy-fold field kernel.",
        "doctrine": str(doctrine_path.relative_to(GROK16)) if doctrine_path.is_file() else None,
    }


def witness(*, sections: bool = True) -> dict[str, Any]:
    thermal = thermal_slice()
    entropy = entropy_slice()
    isotope = isotope_slice()
    doc = {
        "schema": "field-physics-witness/v1",
        "updated": _now(),
        "motto": (_load(DOCTRINE, {}).get("motto") or "We all need to know thermals. We all know entropy and isotope."),
        "meld_citation": "ironclad:meld:2",
        "ok": bool(thermal.get("available")) and bool(entropy.get("available")) and bool(isotope.get("available")),
        "thermal": thermal,
        "entropy": entropy,
        "isotope": isotope,
        "we_all_know": {
            "thermals": True,
            "entropy": True,
            "isotope": True,
        },
    }
    if sections:
        doc["sections"] = {
            "thermal": {"available": thermal.get("available"), "cool_ok": thermal.get("cool_ok"), "consumer": "all_plates"},
            "entropy": {"available": entropy.get("available"), "entropy_ok": entropy.get("entropy_ok"), "consumer": "all_plates"},
            "isotope": {"available": isotope.get("available"), "ok": isotope.get("ok"), "consumer": "all_plates"},
            "panel": {"available": True, "manifest_api": "/api/physics-witness"},
        }
    return doc


def publish(*, write: bool = True) -> dict[str, Any]:
    doc = witness(sections=True)
    if write:
        _save(PANEL, doc)
    return doc


def attach_to_sections(sections: dict[str, Any], *, physics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pass physics witness into every section — we all need thermals."""
    physics = physics or witness(sections=False)
    out: dict[str, Any] = {}
    for sid, row in sections.items():
        merged = dict(row) if isinstance(row, dict) else {"value": row}
        merged["physics"] = {
            "thermal": {
                "level": (physics.get("thermal") or {}).get("level"),
                "cool_ok": (physics.get("thermal") or {}).get("cool_ok"),
                "headroom_pct": (physics.get("thermal") or {}).get("headroom_pct"),
            },
            "entropy": {
                "entropy_ok": (physics.get("entropy") or {}).get("entropy_ok"),
                "entropy_norm": (physics.get("entropy") or {}).get("entropy_norm"),
            },
            "isotope": {
                "ok": (physics.get("isotope") or {}).get("ok"),
                "stem": (physics.get("isotope") or {}).get("stem"),
            },
        }
        out[sid] = merged
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status", "witness"):
        print(json.dumps(publish(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "publish", "refresh"):
        print(json.dumps(publish(write=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-physics-witness.py [json|cycle|witness]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())