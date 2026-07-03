#!/usr/bin/env python3
"""Mechanical auto-learn — Eye camera focal/zoom, Ear eardrum/vibration, Mouth↔Ear smarter."""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
DOCTRINE = INSTALL / "data" / "field-sense-mechanical-learn-doctrine.json"
PANEL = STATE / "field-sense-mechanical-learn-panel.json"
CAMERAS = STATE / "sense-mechanical-cameras.json"
EARS = STATE / "sense-mechanical-ears.json"
QUORUM = STATE / "sense-mouth-ear-quorum.json"

V4L2_CTRL_HINTS = (
    "zoom_absolute", "focus_absolute", "pan_absolute", "tilt_absolute",
    "exposure_auto", "iris_absolute", "zoom_relative", "focus_auto",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(rel: str, name: str) -> Any | None:
    path = INSTALL / rel if not rel.startswith("/") else Path(rel)
    if not path.is_file():
        for base in (SG / "Final_Eye", SG / "Final_Ear", SG / "Final_Mouth"):
            alt = base / Path(rel).name
            if alt.is_file():
                path = alt
                break
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _run(cmd: list[str], *, timeout: int = 12) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (subprocess.TimeoutExpired, OSError) as exc:
        return -1, str(exc)


def _v4l2_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    v4l2 = shutil.which("v4l2-ctl")
    if v4l2:
        rc, out = _run([v4l2, "--list-devices"])
        if rc == 0 and out.strip():
            block: dict[str, Any] = {}
            for line in out.splitlines():
                if not line.strip():
                    if block:
                        devices.append(block)
                        block = {}
                    continue
                if not line.startswith("\t"):
                    if block:
                        devices.append(block)
                    block = {"name": line.strip().rstrip(":"), "nodes": []}
                else:
                    node = line.strip()
                    if node.startswith("/dev/video"):
                        block.setdefault("nodes", []).append(node)
            if block:
                devices.append(block)
    for node in sorted(glob.glob("/dev/video*")):
        if any(node in (d.get("nodes") or []) for d in devices):
            continue
        devices.append({"name": f"video{node.split('video')[-1]}", "nodes": [node], "inferred": True})
    return devices


def _v4l2_controls(device: str) -> dict[str, Any]:
    v4l2 = shutil.which("v4l2-ctl")
    if not v4l2:
        return {"available": False, "controls": []}
    rc, out = _run([v4l2, "-d", device, "--list-ctrls"])
    controls: list[dict[str, Any]] = []
    mechanical = False
    for line in out.splitlines():
        m = re.match(r"^\s*(\w+)\s+.*?(min|max|step|default)=\s*(-?\d+)", line)
        if not m:
            continue
        cid = m.group(1).lower()
        if any(h in cid for h in V4L2_CTRL_HINTS):
            mechanical = True
        controls.append({"id": cid, "line": line.strip()})
    return {
        "available": rc == 0,
        "mechanical": mechanical,
        "has_zoom": any("zoom" in c["id"] for c in controls),
        "has_focus": any("focus" in c["id"] for c in controls),
        "has_pan_tilt": any(x in c["id"] for c in controls for x in ("pan", "tilt")),
        "controls": controls,
    }


def probe_mechanical_cameras() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for dev in _v4l2_devices():
        for node in dev.get("nodes") or []:
            ctrl = _v4l2_controls(node)
            rows.append({
                "device": node,
                "label": dev.get("name"),
                "inferred": dev.get("inferred", False),
                **ctrl,
                "learnable": bool(ctrl.get("mechanical") or ctrl.get("has_zoom") or ctrl.get("has_focus")),
            })
    eye_cap: dict[str, Any] = {}
    fe = SG / "Final_Eye"
    if (fe / "zocr_ai.py").is_file():
        mod = _import_py(str(fe / "zocr_ai.py"), "zocr_ai_cap")
        if mod and hasattr(mod, "capabilities"):
            try:
                eye_cap = mod.capabilities()
            except Exception as exc:
                eye_cap = {"error": str(exc)[:120]}
    return {
        "schema": "sense-mechanical-camera-probe/v1",
        "updated": _utc(),
        "count": len(rows),
        "learnable_count": sum(1 for r in rows if r.get("learnable")),
        "devices": rows,
        "final_eye_capabilities": eye_cap,
        "v4l2_cli": bool(shutil.which("v4l2-ctl")),
    }


def learn_camera(device: str | None = None) -> dict[str, Any]:
    probe = probe_mechanical_cameras()
    target = None
    for row in probe.get("devices") or []:
        if device and row.get("device") != device:
            continue
        if row.get("learnable") or not device:
            target = row
            break
    if not target:
        return {"ok": False, "error": "no_learnable_camera", "probe": probe}
    doc = _load(CAMERAS, {"schema": "sense-mechanical-cameras/v1", "cameras": []})
    cams = [c for c in doc.get("cameras") or [] if c.get("device") != target["device"]]
    profile = {
        "device": target["device"],
        "label": target.get("label"),
        "has_zoom": target.get("has_zoom"),
        "has_focus": target.get("has_focus"),
        "has_pan_tilt": target.get("has_pan_tilt"),
        "controls": target.get("controls") or [],
        "learned_at": _utc(),
        "mechanical": True,
    }
    cams.append(profile)
    doc["cameras"] = cams
    doc["updated"] = _utc()
    doc["active"] = target["device"]
    _save(CAMERAS, doc)
    return {"ok": True, "learned": profile, "total": len(cams)}


def _audio_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    if shutil.which("pactl"):
        _, out = _run(["pactl", "list", "sources", "short"])
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                devices.append({"id": parts[0], "name": parts[1], "kind": "pulse_source"})
    cards = Path("/proc/asound/cards")
    if cards.is_file():
        for line in cards.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*(\d+)\s+\[([^\]]+)\]", line)
            if m:
                devices.append({"id": m.group(1), "name": m.group(2).strip(), "kind": "alsa_card"})
    return devices


def probe_eardrum_vibration() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ear_doc = doctrine.get("ear") or {}
    mechanisms: list[dict[str, Any]] = []
    ve = SG / "Final_Ear" / "zocr_virtual_ear.py"
    if ve.is_file():
        mod = _import_py(str(ve), "zocr_ve")
        if mod and hasattr(mod, "list_mechanisms"):
            try:
                mechanisms = mod.list_mechanisms()
            except Exception:
                pass
    spectrum: dict[str, Any] = {}
    sp = SG / "Final_Ear" / "zocr_ear_spectrum.py"
    if sp.is_file():
        mod = _import_py(str(sp), "zocr_sp")
        if mod and hasattr(mod, "spectrum_doctrine"):
            try:
                spectrum = mod.spectrum_doctrine()
            except Exception:
                pass
    return {
        "schema": "sense-mechanical-ear-probe/v1",
        "updated": _utc(),
        "audio_devices": _audio_devices(),
        "mechanisms": mechanisms,
        "kinetic_eardrum": any(m.get("id") == "kinetic_eardrum" for m in mechanisms),
        "spectrum_doctrine": spectrum,
        "body_vibration": ear_doc.get("body_vibration") or {},
        "spectrum_bands_hz": ear_doc.get("spectrum_bands_hz") or [],
        "color_spectrum_cross": "color_spectrum_cross" in [m.get("id") for m in mechanisms],
    }


def learn_eardrum(*, mechanism: str = "kinetic_eardrum") -> dict[str, Any]:
    probe = probe_eardrum_vibration()
    spawn: dict[str, Any] = {}
    ve = SG / "Final_Ear" / "zocr_virtual_ear.py"
    if ve.is_file():
        mod = _import_py(str(ve), "zocr_ve_learn")
        if mod and hasattr(mod, "spawn_virtual_ear"):
            try:
                spawn = mod.spawn_virtual_ear(mechanism=mechanism, label="auto-learned-eardrum")
            except Exception as exc:
                spawn = {"ok": False, "error": str(exc)[:120]}
    doc = _load(EARS, {"schema": "sense-mechanical-ears/v1", "profiles": []})
    profile = {
        "mechanism": mechanism,
        "probe": {"devices": len(probe.get("audio_devices") or []), "bands": probe.get("spectrum_bands_hz")},
        "body_vibration": probe.get("body_vibration"),
        "virtual_ear": spawn,
        "learned_at": _utc(),
    }
    profiles = [p for p in doc.get("profiles") or [] if p.get("mechanism") != mechanism]
    profiles.append(profile)
    doc["profiles"] = profiles
    doc["updated"] = _utc()
    doc["active_mechanism"] = mechanism
    _save(EARS, doc)
    return {"ok": True, "learned": profile, "probe": probe}


def mouth_ear_smarter(*, encourage: bool = True) -> dict[str, Any]:
    """Cross-train Mouth↔Ear under sense_neural secure path."""
    neural_py = INSTALL / "Queen" / "lib" / "queen-sense-neural.py"
    if not neural_py.is_file():
        neural_py = SG / "Queen" / "lib" / "queen-sense-neural.py"
    fusion: dict[str, Any] = {"ok": False}
    if neural_py.is_file():
        mod = _import_py(str(neural_py), "qsn_fusion")
        if mod and hasattr(mod, "fused_analyze"):
            try:
                fusion = mod.fused_analyze({
                    "secure_path": True,
                    "evidence": {
                        "mouth_correlation": 0.92,
                        "speech_present": True,
                        "fundamental_hz": 440,
                        "music_theory": True,
                        "mechanical_learn": True,
                    },
                    "existence": {"correlation": 0.86},
                })
            except Exception as exc:
                fusion = {"ok": False, "error": str(exc)[:160]}
    quorum_score = 0.0
    if fusion.get("ok"):
        quorum_score = 0.88 if fusion.get("cross_agree") else 0.72
    elif fusion.get("invincible_quorum"):
        quorum_score = 0.95
    doc = {
        "schema": "sense-mouth-ear-quorum/v1",
        "updated": _utc(),
        "quorum_score": quorum_score,
        "smarter": quorum_score >= 0.75,
        "fusion": {k: fusion.get(k) for k in ("ok", "cross_agree", "invincible_quorum", "truth_percent", "citation")},
        "cameras": _load(CAMERAS, {}).get("active"),
        "ear_mechanism": _load(EARS, {}).get("active_mechanism"),
    }
    _save(QUORUM, doc)
    if encourage and quorum_score >= 0.75 and neural_py.is_file():
        mod = _import_py(str(neural_py), "qsn_enc")
        if mod and hasattr(mod, "encourage_both"):
            try:
                doc["encourage"] = mod.encourage_both({
                    "reinforce_triad": True,
                    "mouth_label": "mechanical_learn",
                    "ear_label": "eardrum_spectrum",
                    "eye_label": "mechanical_camera",
                    "evidence": {"mouth_correlation": quorum_score, "mechanical_learn": True},
                })
            except Exception:
                pass
    return {"ok": doc["smarter"], **doc}


def learn_all(*, auto: bool = True) -> dict[str, Any]:
    eye = learn_camera() if auto else {"skipped": True}
    ear = learn_eardrum()
    mouth_ear = mouth_ear_smarter()
    return {
        "ok": bool(
            (eye.get("ok") or eye.get("error") == "no_learnable_camera")
            and ear.get("ok")
            and mouth_ear.get("ok")
        ),
        "schema": "sense-mechanical-learn-all/v1",
        "updated": _utc(),
        "eye": eye,
        "ear": ear,
        "mouth_ear": mouth_ear,
    }


def panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ic = _load(STATE / "ironclad-immediate.json", {})
    doc = {
        "ok": True,
        "schema": "field-sense-mechanical-learn-panel/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "camera_probe": probe_mechanical_cameras(),
        "ear_probe": probe_eardrum_vibration(),
        "learned_cameras": _load(CAMERAS, {}),
        "learned_ears": _load(EARS, {}),
        "mouth_ear_quorum": _load(QUORUM, {}),
        "ironclad_sealed": bool(ic.get("ironclad_sealed")),
        "api": "/api/field-sense-mechanical-learn",
        "secure": doctrine.get("secure") or {},
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps({
            "cameras": probe_mechanical_cameras(),
            "ears": probe_eardrum_vibration(),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "learn-camera":
        dev = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(learn_camera(dev), ensure_ascii=False, indent=2))
        return 0
    if cmd == "learn-ear":
        mech = sys.argv[2] if len(sys.argv) > 2 else "kinetic_eardrum"
        print(json.dumps(learn_eardrum(mechanism=mech), ensure_ascii=False, indent=2))
        return 0
    if cmd == "mouth-ear":
        print(json.dumps(mouth_ear_smarter(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "learn-all":
        print(json.dumps(learn_all(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-sense-mechanical-learn.py [panel|probe|learn-camera|learn-ear|mouth-ear|learn-all]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())