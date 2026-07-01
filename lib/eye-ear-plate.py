#!/usr/bin/env pythong
"""Eye ↔ Ear ↔ Mouth Plate — fuse vision, hearing, speech on one melded plate (not wire)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
DOCTRINE = INSTALL / "data" / "eye-ear-plate-doctrine.json"
PLATE = STATE / "eye-ear-plate.json"
LEDGER = STATE / "eye-ear-plate-ledger.jsonl"


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _fusion_mod() -> Any | None:
    ear = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear"))
    py = ear / "zocr_eye_ear_fusion.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("zocr_eye_ear_fusion", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    for p in (str(ear), str(SG / "NewLatest" / "Final_Eye"), str(INSTALL / "Final_Eye")):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec.loader.exec_module(mod)
    return mod


def _ironclad_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "ironclad-immediate.py"
    if not py.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("ironclad_immediate", py)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "read_immediate"):
            doc = mod.read_immediate()
            return doc.get("plate_to_sense") or {}
        if hasattr(mod, "plate_to_sense_goldmine"):
            return mod.plate_to_sense_goldmine()
    except Exception:
        pass
    return _load(STATE / "ironclad-immediate.json", {}).get("plate_to_sense") or {}


def _plate_hash(material: dict[str, Any]) -> str:
    blob = json.dumps(material, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _universal_lock_gate() -> dict[str, Any]:
    """Universal Protector + combinatorics lock — sense stack must be sealed before GREEN."""
    sense_py = INSTALL / "lib" / "field-sense-package-meld.py"
    if sense_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("sense_universal_gate", sense_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "sense_universal_slice"):
                    return mod.sense_universal_slice(state_dir=STATE)
        except Exception:
            pass
    universal = _load(STATE / "universal-protector-panel.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    lock_verify = comb.get("combinatorics_lock_verify") or {}
    return {
        "schema": "field-sense-universal-slice/v1",
        "universal_lock": bool(universal.get("equipment_holds_gate")) and bool(lock_verify.get("ok", True)),
        "combinatorics_lock_ok": bool(lock_verify.get("ok", True)),
        "equipment_holds_gate": bool(universal.get("equipment_holds_gate")),
    }


def _mouth_slice() -> dict[str, Any]:
    sense = _load(STATE / "field-sense-package-panel.json", {})
    members = sense.get("members") or {}
    mouth = members.get("mouth_neural") or members.get("final_mouth") or {}
    if mouth:
        return mouth
    iron = _ironclad_slice()
    gold = iron.get("members") or {}
    return gold.get("mouth_neural") or {}


def build_plate(*, evidence: dict[str, Any] | None = None, require_sync: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    fusion = _fusion_mod()
    iron = _ironclad_slice()
    mouth_doc = _mouth_slice()
    fusion_out: dict[str, Any] = {"ok": False, "error": "fusion_missing"}
    if fusion and hasattr(fusion, "secure_neural_path"):
        try:
            fusion_out = fusion.secure_neural_path(
                evidence=evidence or {"mouth_correlation": 0.9, "speech_present": True},
                require_sync=require_sync,
            )
        except Exception as exc:
            fusion_out = {"ok": False, "error": str(exc)[:200]}
    eye_ok = bool((fusion_out.get("eye_neural") or {}).get("ok") or fusion_out.get("ok"))
    ear_ok = bool((fusion_out.get("ear_neural") or {}).get("ok") or fusion_out.get("ok"))
    mouth_ok = bool(
        mouth_doc.get("ok")
        or mouth_doc.get("plated")
        or str(mouth_doc.get("verdict") or "").upper() in ("GREEN", "OK")
        or fusion_out.get("cross_agree")
    )
    lock_gate = _universal_lock_gate()
    plated = fusion_out.get("ok") or (eye_ok and ear_ok and mouth_ok) or (eye_ok and ear_ok)
    universal_lock = bool(lock_gate.get("universal_lock"))
    if plated and not universal_lock and lock_gate.get("combinatorics_lock_ok") is not False:
        plated = eye_ok and ear_ok
    material = {
        "fusion_ok": fusion_out.get("ok"),
        "sync": (fusion_out.get("sync") or {}).get("ok"),
        "cross_agree": fusion_out.get("cross_agree"),
        "eye_ok": eye_ok,
        "ear_ok": ear_ok,
        "mouth_ok": mouth_ok,
    }
    chain = _plate_hash(material)
    return {
        "schema": "eye-ear-plate/v1",
        "updated": _now(),
        "title": doctrine.get("title") or "Eye ↔ Ear ↔ Mouth Plate",
        "motto": doctrine.get("motto") or "",
        "plate_not_wire": True,
        "meld_citation": doctrine.get("meld_citation") or "ironclad:meld:2",
        "ok": plated,
        "plated": plated,
        "verdict": (
            "GREEN"
            if (eye_ok and ear_ok and mouth_ok and universal_lock)
            else ("WATCH" if (eye_ok or ear_ok or mouth_ok) else "HOLD")
        ),
        "universal_lock": universal_lock,
        "combinatorics_lock_ok": lock_gate.get("combinatorics_lock_ok"),
        "chain_hash": chain,
        "products": doctrine.get("products") or ["Final_Eye", "Final_Ear", "Final_Mouth"],
        "mouth": {
            "ok": mouth_ok,
            "verdict": mouth_doc.get("verdict"),
            "bridge": mouth_doc.get("bridge") or "Final_Mouth/zocr_neural_assist.py",
            "truth_percent": mouth_doc.get("truth_percent"),
        },
        "fusion": {
            "schema": fusion_out.get("schema"),
            "ok": fusion_out.get("ok"),
            "sync": fusion_out.get("sync"),
            "signal_id": fusion_out.get("signal_id"),
            "cross_agree": fusion_out.get("cross_agree"),
            "eye_neural": fusion_out.get("eye_neural"),
            "ear_neural": fusion_out.get("ear_neural"),
        },
        "ironclad": {
            "grounded": bool(iron.get("ironclad_grounded")),
            "citation": iron.get("citation") or "ironclad:neural:2",
            "truth_percent": iron.get("truth_percent"),
        },
        "matrix_plates": doctrine.get("matrix_plates") or [],
    }


def build_panel(*, write: bool = True, body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    panel = build_plate(
        evidence=body.get("evidence"),
        require_sync=body.get("require_sync", False) is not False,
    )
    if write:
        _save(PLATE, panel)
        _append_ledger({
            "ts": panel["updated"],
            "ok": panel.get("ok"),
            "verdict": panel.get("verdict"),
            "chain_hash": panel.get("chain_hash"),
        })
    return panel


def cycle() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd in ("cycle", "plate", "meld"):
        print(json.dumps(cycle(), ensure_ascii=False))
        return 0
    if cmd == "pass":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(build_panel(write=False, body=body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: eye-ear-plate.py [json|cycle|pass]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())