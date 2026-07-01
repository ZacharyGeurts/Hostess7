#!/usr/bin/env pythong
"""Audio secure bind — ZNetwork localhost layer hooks Pulse/PipeWire to DAC chamber."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE = fcc.STATE
BIND = STATE / "field-audio-secure-bind.json"
PANEL = STATE / "field-audio-secure-bind-panel.json"


def _dac_mod() -> Any | None:
    return fcc.mod("audio_secure_dac", "field-audio-dac-chamber.py")


def probe_hardware() -> dict[str, Any]:
    dac = _dac_mod()
    devs = dac.enumerate_devices() if dac and hasattr(dac, "enumerate_devices") else fcc.enumerate_audio_devices()
    cards = devs.get("alsa_cards") or []
    sinks = devs.get("sinks") or []
    sources = devs.get("sources") or []
    return {
        "ok": True,
        "alsa_cards": len(cards),
        "sinks": len(sinks),
        "sources": len(sources),
        "hdmi": len(devs.get("hdmi") or []),
        "bluetooth": len(devs.get("bluetooth") or []),
        "usb": len(devs.get("usb") or []),
        "default_sink": devs.get("default_sink"),
        "default_source": devs.get("default_source"),
    }


def bind(*, sink_name: str = "", force: bool = False) -> dict[str, Any]:
    """Bind DAC chamber routing through ZNetwork localhost audio layer."""
    dac = _dac_mod()
    if not dac:
        return {"ok": False, "error": "dac_chamber_missing"}
    devs = dac.enumerate_devices() if hasattr(dac, "enumerate_devices") else {}
    sink = sink_name or devs.get("default_sink") or ""
    source = devs.get("default_source") or ""
    if not sink and not force:
        return {"ok": False, "error": "no_sink", "hint": "pass sink_name or --force"}
    settings = dac.load_settings() if hasattr(dac, "load_settings") else {}
    settings["output_device"] = sink or settings.get("output_device", "")
    settings["input_device"] = source or settings.get("input_device", "")
    routed = dac.apply_routing(settings) if hasattr(dac, "apply_routing") else {"ok": False}
    zn = dac.znetwork_hook() if hasattr(dac, "znetwork_hook") else {}
    doc = {
        "schema": "field-audio-secure-bind/v1",
        "updated": fcc.ts(),
        "bound": bool(routed.get("ok")),
        "sink": sink,
        "source": source,
        "localhost_only": True,
        "znetwork_layer": "audio_dac",
        "routing": routed,
        "znetwork": zn,
    }
    fcc.save_atomic(BIND, doc)
    return {"ok": doc["bound"], **doc}


def posture() -> dict[str, Any]:
    link = fcc.load(BIND, {})
    hw = probe_hardware()
    dac = _dac_mod()
    dac_panel = dac.dac_probe() if dac and hasattr(dac, "dac_probe") else {}
    doc = {
        "schema": "field-audio-secure-bind-panel/v1",
        "updated": fcc.ts(),
        "ok": True,
        "bound": bool(link.get("bound")),
        "link": link,
        "hardware": hw,
        "dac": dac_panel,
        "routes": {
            "bind": "/api/field-audio-secure-bind/bind",
            "auto": "/api/field-audio-secure-bind/auto",
            "probe": "/api/field-audio-secure-bind/probe",
            "dac": "/api/field-audio-dac",
        },
        "posture": f"Audio secure bind — {'bound' if link.get('bound') else 'standby'} · {hw.get('sinks', 0)} sinks",
    }
    fcc.save_atomic(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps(probe_hardware(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("bind", "auto"):
        sink = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else ""
        force = "--force" in sys.argv
        print(json.dumps(bind(sink_name=sink, force=force or cmd == "auto"), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-audio-secure-bind.py [json|probe|bind|auto]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())