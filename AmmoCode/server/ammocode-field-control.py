#!/usr/bin/env python3
"""AmmoCode + SG field control — detect fielded posture and defield safely."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT.parent
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
NEWLATEST = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEWLATEST / ".nexus-state"))

DEFIELD_MARKER = STATE / "ammocode-defield.marker"
DEFIELD_JSON = STATE / "ammocode-defield.json"
PERMANENT_MARKER = STATE / "permanent-field.marker"
PERMANENT_SG_MARKER = SG / ".nexus-state" / "permanent-field.marker"
FIELD_RUNTIME = STATE / "field-combinatorics-runtime.json"
ZNET_MARKER = STATE / "znetwork-running.marker"
ZNET_SOCK = STATE / "znetwork-field.sock"
FIELD_DRIVE = NEWLATEST / ".nexus-field-drive"


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def is_permanent_fielded() -> bool:
    return PERMANENT_MARKER.is_file() or PERMANENT_SG_MARKER.is_file()


def is_defielded() -> bool:
    if is_permanent_fielded():
        return False
    return DEFIELD_MARKER.is_file()


def _grok16_posture(surface: str = "plain") -> dict[str, Any]:
    instill = GROK16 / "lib" / "g16-ammocode-field-instill.py"
    if not instill.is_file():
        return {"posture": "unknown", "field": False}
    env = os.environ.copy()
    if is_defielded():
        env["G16_AMMOCODE_RESTING_ON_FIELD"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(instill), "posture", surface or "plain"],
            capture_output=True, text=True, timeout=8, env=env,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"posture": "unknown", "field": False}


def _defield_posture(*, reason: str = "defield_active") -> dict[str, Any]:
    return {
        "posture": "defield",
        "field": False,
        "no_subfields": True,
        "resting_on_field": True,
        "defield_active": True,
        "reason": reason,
    }


def _permanent_field_posture() -> dict[str, Any]:
    return {
        "posture": "field",
        "field": True,
        "no_subfields": True,
        "permanent": True,
        "resting_on_field": False,
        "defield_active": False,
        "reason": "permanent_field_power_chain",
        "scope": ["SG", "SG/NewLatest"],
    }


def ammocode_posture(surface: str = "plain") -> dict[str, Any]:
    """Effective AmmoCode runtime posture — permanent field wins; defield marker next."""
    if is_permanent_fielded():
        return _permanent_field_posture()
    if is_defielded():
        return _defield_posture()
    pos = _grok16_posture(surface)
    doc = _load_json(ROOT / "data" / "ammocode-field-doctrine.json", {})
    pol = doc.get("policy") or {}
    surf = str(surface or "plain").lower()
    resting = surf in set((doc.get("surfaces") or {}).get("field") or [])
    if resting and pol.get("defield_if_resting_on_field", True):
        return _defield_posture(reason="resting_on_field")
    return pos


def ammocode_is_fielded(surface: str = "plain") -> bool:
    if is_defielded():
        return False
    pos = ammocode_posture(surface)
    return bool(pos.get("field")) and str(pos.get("posture") or "") == "field"


def sg_field_status() -> dict[str, Any]:
    """Detect whether SG / Grok16 / NEXUS or AmmoCode itself is actively fielded."""
    signals: list[dict[str, Any]] = []
    sg_fielded = False

    if ZNET_MARKER.is_file():
        sg_fielded = True
        signals.append({"id": "znetwork_running_marker", "active": True})
    if ZNET_SOCK.exists():
        sg_fielded = True
        signals.append({"id": "znetwork_field_sock", "active": True})

    attach = _load_json(STATE / "ammocode-znetwork-attach.json", {})
    if attach.get("znetwork_running"):
        sg_fielded = True
        signals.append({"id": "ammocode_znetwork_running", "active": True})
    if attach.get("detail") == "startup_with_us" and attach.get("interfered"):
        signals.append({"id": "ammocode_field_startup_attempt", "active": True, "fielded_hint": True})

    rt = _load_json(FIELD_RUNTIME, {})
    if rt.get("updated"):
        signals.append({"id": "field_combinatorics_runtime", "active": True, "updated": rt.get("updated")})
        sg_fielded = True

    if FIELD_DRIVE.is_dir() and any(FIELD_DRIVE.rglob("nexus-field")):
        signals.append({"id": "nexus_field_drive_mirror", "active": True})
        sg_fielded = True

    instill = _grok16_posture()
    ac_posture = ammocode_posture()
    ammocode_fielded = ammocode_is_fielded()
    fielded = sg_fielded or ammocode_fielded
    if ammocode_fielded:
        signals.append({"id": "ammocode_posture_field", "active": True, "posture": ac_posture.get("posture")})
    elif instill.get("field") and instill.get("posture") == "field":
        signals.append({"id": "grok16_instill_field", "active": True, "fielded_hint": True})

    defield_active = DEFIELD_MARKER.is_file()
    doc = _load_json(DEFIELD_JSON, {})

    return {
        "ok": True,
        "fielded": fielded and not defield_active,
        "ammocode_fielded": ammocode_fielded and not defield_active,
        "sg_fielded": sg_fielded and not defield_active,
        "defield_active": defield_active,
        "signals": signals,
        "ammocode_posture": ac_posture,
        "grok16_posture": instill,
        "defield": doc,
        "motto": "AmmoCode or SG fielded → defield. No subfields.",
    }


def defield_sg(*, reason: str = "operator_request", force: bool = False) -> dict[str, Any]:
    """Defield NewLatest/Grok16 and AmmoCode runtime — stop field-on-field until cleared."""
    before = sg_field_status()
    needs = before.get("fielded") or before.get("ammocode_fielded")
    if not force and not needs and before.get("defield_active"):
        return {"ok": True, "already_defielded": True, "status": before}

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc = {
        "schema": "ammocode-defield/v1",
        "defielded": True,
        "field": False,
        "posture": "defield",
        "no_subfields": True,
        "resting_on_field": True,
        "ammocode_defielded": True,
        "sg_defielded": True,
        "reason": reason,
        "ts": ts,
        "signals_before": before.get("signals") or [],
        "ammocode_was_fielded": before.get("ammocode_fielded"),
    }
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        DEFIELD_MARKER.write_text(f"ammocode-defield {ts}\n", encoding="utf-8")
        _save_json(DEFIELD_JSON, doc)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}

    cleared: list[str] = []
    for path in (ZNET_MARKER, STATE / "ammocode-shield-active.marker"):
        try:
            if path.is_file():
                path.unlink()
                cleared.append(path.name)
        except OSError:
            pass

    env_hint = STATE / "ammocode-defield.env"
    try:
        env_hint.write_text("G16_AMMOCODE_RESTING_ON_FIELD=1\nAMMOCODE_NO_ZNETWORK=1\n", encoding="utf-8")
    except OSError:
        pass

    after = sg_field_status()
    return {
        "ok": True,
        "defielded": True,
        "cleared_markers": cleared,
        "before": before,
        "after": after,
        "receipt": doc,
    }


def field_sg(*, reason: str = "operator_request") -> dict[str, Any]:
    """Enable permanent SG/NewLatest fielding from power input forward."""
    mod = NEWLATEST / "lib" / "field-permanent-fielding.py"
    if not mod.is_file():
        return {"ok": False, "error": "field-permanent-fielding.py missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(mod), "install"],
            capture_output=True,
            text=True,
            timeout=180,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(NEWLATEST),
                "NEXUS_STATE_DIR": str(STATE),
                "SG_ROOT": str(SG),
            },
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": (proc.stderr or "install_failed")[:400]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def clear_defield() -> dict[str, Any]:
    removed = []
    for path in (DEFIELD_MARKER, DEFIELD_JSON, STATE / "ammocode-defield.env"):
        try:
            if path.is_file():
                path.unlink()
                removed.append(path.name)
        except OSError:
            pass
    return {"ok": True, "cleared": removed, "status": sg_field_status()}


def auto_defield_if_fielded() -> dict[str, Any]:
    st = sg_field_status()
    if st.get("fielded") or st.get("ammocode_fielded"):
        return defield_sg(reason="auto_on_ammocode_boot", force=True)
    return {"ok": True, "action": "none", "fielded": False, "ammocode_fielded": False, "status": st}


def field_posture_for_api(surface: str = "plain") -> dict[str, Any]:
    return ammocode_posture(surface)