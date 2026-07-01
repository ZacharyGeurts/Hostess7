#!/usr/bin/env pythong
"""AmmoOS Image RTX content gate — autodetect GPU, gate RTX-only tools for operator protection."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SG = Path(os.environ.get("SG_ROOT", Path(__file__).resolve().parents[2]))
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
OVERLAY = Path(__file__).resolve().parents[1]
DOCTRINE = OVERLAY / "data" / "field-gimp-doctrine.json"
GATED = OVERLAY / "data" / "rtx-gated-content.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", SG / "NewLatest" / ".nexus-state"))
PANEL = STATE / "ammoos-rtx-gate-panel.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _rtx_gate_mod() -> Any | None:
    script = GROK16 / "forge" / "rtx_gate.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("rtx_gate", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gate_posture(profile: str = "queen_rtx") -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    gated_doc = _load(GATED, {})
    mod = _rtx_gate_mod()
    rtx_status: dict[str, Any] = {"ok": False, "error": "rtx_gate_missing"}
    if mod:
        try:
            rtx_status = mod.gate_status()
        except Exception as exc:
            rtx_status = {"ok": False, "error": str(exc)}
        try:
            allowed = mod.profile_allowed(profile)
            check = {"ok": True, "permit": allowed, "profile": profile}
        except Exception as exc:
            check = {"ok": False, "permit": False, "error": str(exc)}
    else:
        check = {"ok": False, "permit": False, "error": "rtx_gate_missing"}

    permit = bool(check.get("permit") or rtx_status.get("satisfied"))
    fallback = doctrine.get("rtx_policy", {}).get("fallback_profile") or "field_opt"
    active_profile = profile if permit else fallback

    cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ammoos-rtx-gate"
    cache_dir.mkdir(parents=True, exist_ok=True)
    permit_file = cache_dir / "permit"
    if permit:
        permit_file.write_text("1\n", encoding="utf-8")
    elif permit_file.is_file():
        permit_file.unlink()

    doc = {
        "schema": "ammoos-rtx-gate/v1",
        "ts": _now(),
        "ok": True,
        "os_brand": doctrine.get("os_brand") or "AmmoOS",
        "product": doctrine.get("product") or "AmmoOS Image",
        "rtx_detected": bool(rtx_status.get("rtx_count") or rtx_status.get("satisfied")),
        "rtx_gate": rtx_status,
        "profile_requested": profile,
        "profile_active": active_profile,
        "permit_rtx": permit,
        "fallback_profile": fallback,
        "gated_features": gated_doc.get("gated_features") or [],
        "gated_paths": gated_doc.get("gated_paths") or [],
        "operator_banner": None if permit else gated_doc.get("operator_ui", {}).get("banner"),
        "cpu_path_available": True,
        "verdict": "RTX_READY" if permit else "FIELD_OPT_CPU",
    }
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = PANEL.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    profile = sys.argv[2] if len(sys.argv) > 2 else "queen_rtx"
    if cmd in ("json", "status", "posture"):
        print(json.dumps(gate_posture(profile), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: rtx-content-gate.py [json] [profile]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())