#!/usr/bin/env pythong
"""Broadcaster audio chain — echo cancel, static filter, dB shaping before output."""
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
DOCTRINE = INSTALL / "data" / "field-broadcaster-audio-doctrine.json"
SETTINGS = STATE / "field-broadcaster-audio-settings.json"
PANEL = STATE / "field-broadcaster-audio-panel.json"


def _chain_posture(settings: dict[str, Any]) -> list[dict[str, Any]]:
    doctrine = fcc.load(DOCTRINE, {})
    steps = []
    for row in doctrine.get("chain") or []:
        sid = str(row.get("id") or "")
        on = True
        if sid == "echo_cancel":
            on = bool(settings.get("echo_cancel", True))
        elif sid == "noise_gate":
            on = bool(settings.get("noise_gate", True))
        elif sid in ("static_suppress", "highpass"):
            on = bool(settings.get("static_filter", True))
        elif sid == "input_gain_db":
            on = settings.get("input_gain_db", 0) != 0
        elif sid == "output_gain_db":
            on = settings.get("output_gain_db", 0) != 0
        steps.append({
            "id": sid,
            "label": row.get("label"),
            "active": on,
            "physics": row.get("physics"),
            "value": settings.get(sid.replace("_db", "_gain_db"), settings.get(sid)),
        })
    return steps


def _apply_pipewire_echo_cancel(*, enable: bool) -> dict[str, Any]:
    if not enable:
        return {"ok": True, "skipped": "echo_cancel_off"}
    sink = fcc.default_device("sink")
    source = fcc.default_device("source")
    if not sink or not source:
        return {"ok": False, "error": "no_default_devices"}
    return {
        "ok": True,
        "method": "pipewire_echo_cancel",
        "hint": "Load echo-cancel sink/source pair in PipeWire session",
        "sink": sink,
        "source": source,
        "module": (fcc.load(DOCTRINE, {}).get("pipewire_modules") or {}).get("echo_cancel"),
    }


def _passthrough_settings() -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    defaults = doctrine.get("defaults") or {}
    return {
        **defaults,
        "echo_cancel": False,
        "noise_gate": False,
        "static_filter": False,
        "input_gain_db": 0,
        "output_gain_db": 0,
    }


def clear_chain() -> dict[str, Any]:
    """Remove Broadcaster filters — reset saved settings, restore 100% on default devices."""
    merged = _passthrough_settings()
    fcc.save_atomic(SETTINGS, merged)
    backend = fcc.detect_backend()
    sink = fcc.default_device("sink")
    source = fcc.default_device("source")
    results: list[dict[str, Any]] = []
    if backend.get("pactl"):
        if source:
            results.append(fcc.apply_volume_db(source, 0, kind="source"))
        if sink:
            results.append(fcc.apply_volume_db(sink, 0, kind="sink"))
    return {
        "ok": True,
        "cleared": True,
        "passthrough": True,
        "backend": backend,
        "default_sink": sink,
        "default_source": source,
        "settings": merged,
        "chain": _chain_posture(merged),
        "results": results,
    }


def apply_chain(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply Broadcaster audio chain only when filters or gain explicitly enabled."""
    doctrine = fcc.load(DOCTRINE, {})
    defaults = doctrine.get("defaults") or {}
    saved = fcc.load(SETTINGS, {})
    merged = {**defaults, **saved}
    if settings:
        merged.update(settings)
    fcc.save_atomic(SETTINGS, merged)

    filters_on = any(merged.get(k) for k in ("echo_cancel", "noise_gate", "static_filter"))
    gain_on = float(merged.get("input_gain_db", 0)) != 0 or float(merged.get("output_gain_db", 0)) != 0
    if not filters_on and not gain_on:
        return clear_chain()

    backend = fcc.detect_backend()
    sink = merged.get("default_sink") or fcc.default_device("sink")
    source = merged.get("default_source") or fcc.default_device("source")
    results: list[dict[str, Any]] = []

    if backend.get("pactl"):
        in_db = float(merged.get("input_gain_db", 0))
        out_db = float(merged.get("output_gain_db", 0))
        if source and in_db:
            results.append(fcc.apply_volume_db(source, in_db, kind="source"))
        if sink and out_db:
            results.append(fcc.apply_volume_db(sink, out_db, kind="sink"))
        if merged.get("echo_cancel"):
            results.append(_apply_pipewire_echo_cancel(enable=True))

    return {
        "ok": all(r.get("ok", True) for r in results) if results else True,
        "backend": backend,
        "default_sink": sink,
        "default_source": source,
        "settings": merged,
        "chain": _chain_posture(merged),
        "results": results,
    }


def snapshot() -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    settings = fcc.load(SETTINGS, doctrine.get("defaults") or {})
    backend = fcc.detect_backend()
    sink = settings.get("default_sink") or fcc.default_device("sink")
    source = settings.get("default_source") or fcc.default_device("source")
    sink_detail = fcc.parse_pactl_detail("sink", sink) if sink else {}
    src_detail = fcc.parse_pactl_detail("source", source) if source else {}
    return {
        "ok": True,
        "schema": "field-broadcaster-audio/v1",
        "ts": fcc.ts(),
        "backend": backend,
        "default_sink": sink,
        "default_source": source,
        "sink_volume_pct": sink_detail.get("volume_percent"),
        "source_volume_pct": src_detail.get("volume_percent"),
        "settings": settings,
        "chain": _chain_posture(settings),
        "motto": doctrine.get("motto"),
    }


def posture(*, apply: bool = False) -> dict[str, Any]:
    if apply:
        apply_chain(fcc.load(SETTINGS, _passthrough_settings()))
    snap = snapshot()
    doc = {
        **snap,
        "title": "Broadcaster Audio",
        "routes": {"api": "/api/field-broadcaster/audio", "apply": "POST"},
        "posture": (
            f"Audio — {snap.get('backend', {}).get('name', '?')} · "
            f"echo={'on' if (snap.get('settings') or {}).get('echo_cancel') else 'off'} · "
            f"gate={'on' if (snap.get('settings') or {}).get('noise_gate') else 'off'}"
        ),
    }
    fcc.save_atomic(PANEL, doc)
    return doc


def save_settings(patch: dict[str, Any], *, apply: bool = False) -> dict[str, Any]:
    allowed = {
        "echo_cancel", "noise_gate", "static_filter", "input_gain_db", "output_gain_db",
        "default_sink", "default_source", "monitor",
    }
    saved = fcc.load(SETTINGS, {})
    for k, v in patch.items():
        if k in allowed:
            saved[k] = v
    fcc.save_atomic(SETTINGS, saved)
    if apply:
        apply_chain(saved)
    return posture()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        print(json.dumps(apply_chain(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("clear", "clear-filters", "passthrough"):
        print(json.dumps(clear_chain(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-broadcaster-audio.py [json|apply|settings JSON]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())