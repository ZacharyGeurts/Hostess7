#!/usr/bin/env pythong
"""G16 compiler sense plate — optimize profile from Eye · Ear · Mouth plates."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "g16-compiler-sense-doctrine.json"
PLATE = STATE / "g16-compiler-sense-plate.json"
LEDGER = STATE / "g16-compiler-sense-ledger.jsonl"


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


def _chain_hash(material: Any, prev: str = "") -> str:
    blob = json.dumps(material, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{prev}|{blob}".encode()).hexdigest()


def _sense_members() -> dict[str, Any]:
    sense = _load(STATE / "field-sense-package-panel.json", {})
    members = sense.get("members") or {}
    eye = members.get("final_eye") or {}
    ear = members.get("final_ear") or {}
    mouth = members.get("mouth_neural") or members.get("final_mouth") or {}
    return {"eye": eye, "ear": ear, "mouth": mouth, "sense_verdict": sense.get("verdict")}


def _eye_ear_mouth_plate() -> dict[str, Any]:
    return _load(STATE / "eye-ear-plate.json", {})


def _g16_stack() -> dict[str, Any]:
    return _load(STATE / "nexus-g16-stack-panel.json", {})


def _meld_gen() -> int:
    meld = _load(STATE / "field-plate-meld.json", {})
    return int(meld.get("generation") or 0)


def _member_ok(doc: dict[str, Any]) -> bool:
    if doc.get("ok") is True or doc.get("plated") is True:
        return True
    if str(doc.get("verdict") or "").upper() in ("GREEN", "OK"):
        return True
    if doc.get("ops_live") or doc.get("live"):
        return True
    return False


def _combinatorics_posture() -> dict[str, Any]:
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    posture = bridge.get("exec_posture") or {}
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    return {
        "bridge_ok": bridge.get("ok"),
        "pattern": posture.get("pattern_id"),
        "runner": posture.get("runner"),
        "belt_profile": posture.get("belt_profile"),
        "native_ceiling": posture.get("native_ceiling_ops_per_sec")
        or (comb.get("speed_cap") or {}).get("estimated_cap_ops_per_sec"),
        "free_meld": posture.get("free_meld"),
        "iron_exec": posture.get("iron_exec_recommended"),
    }


def optimize_profile() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    eem = _eye_ear_mouth_plate()
    members = _sense_members()
    stack = _g16_stack()
    meld_gen = _meld_gen()
    comb = _combinatorics_posture()
    eye_ok = bool(eem.get("eye_ok") or _member_ok(members["eye"]))
    ear_ok = bool(eem.get("ear_ok") or _member_ok(members["ear"]))
    mouth_ok = bool(eem.get("mouth_ok") or _member_ok(members["mouth"]))
    iron = (stack.get("ironclad_sanity") or {})
    iron_ok = bool(iron.get("ok"))
    rtx = (stack.get("rtx_gate") or {})
    g16_ready = bool((stack.get("compile") or {}).get("probe", {}).get("g16_ready"))

    profile = "field_opt"
    reason = "default"
    if eye_ok and ear_ok and mouth_ok and iron_ok and g16_ready:
        profile = "heavy" if meld_gen >= 3 else "expert"
        reason = "eye_ear_mouth_green"
        if meld_gen >= 5 and (stack.get("optimized") or stack.get("ok")):
            profile = "forever"
            reason = "meld_stable_heavy"
    elif eye_ok and ear_ok and iron_ok:
        profile = "expert"
        reason = "eye_ear_green"
    elif eye_ok or ear_ok:
        profile = "hostess_secure"
        reason = "sense_watch"
    if profile in ("heavy", "forever") and not rtx.get("satisfied"):
        gated = profile
        if gated in ("queen_rtx", "vulkan_rtx"):
            profile = "field_opt"
            reason = "rtx_gate_fallback"

    belt = str(comb.get("belt_profile") or "belt_1_0")
    if comb.get("iron_exec") and comb.get("bridge_ok") and eye_ok and iron_ok:
        if belt == "belt_2_0" and g16_ready:
            profile = "forever"
            reason = "combinatorics_belt_2_native_bsp"
        elif comb.get("free_meld"):
            profile = "expert" if profile == "hostess_secure" else profile
            reason = f"combinatorics_{comb.get('pattern') or 'iron_exec'}"
        elif (comb.get("native_ceiling") or 0) > 500_000:
            profile = "heavy" if profile in ("field_opt", "hostess_secure") else profile
            reason = "combinatorics_speed_cap"

    weights = doctrine.get("sense_weight") or {}
    score = (
        (weights.get("final_eye", 0.4) if eye_ok else 0.0)
        + (weights.get("final_ear", 0.35) if ear_ok else 0.0)
        + (weights.get("final_mouth", 0.25) if mouth_ok else 0.0)
    )
    return {
        "profile": profile,
        "reason": reason,
        "sense_score": round(score, 3),
        "eye_ok": eye_ok,
        "ear_ok": ear_ok,
        "mouth_ok": mouth_ok,
        "ironclad_ok": iron_ok,
        "g16_ready": g16_ready,
        "meld_generation": meld_gen,
        "rtx_satisfied": bool(rtx.get("satisfied")),
        "combinatorics": comb,
        "belt_profile": belt,
        "emulator": comb.get("runner"),
    }


def build_plate(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    opt = optimize_profile()
    eem = _eye_ear_mouth_plate()
    stack = _g16_stack()
    members = _sense_members()
    prev = str(_load(PLATE, {}).get("chain_hash") or "")
    material = {**opt, "eye_ear_verdict": eem.get("verdict"), "sense_verdict": members.get("sense_verdict")}
    chain = _chain_hash(material, prev)
    plated = bool(opt.get("g16_ready")) and (opt.get("eye_ok") or opt.get("ear_ok") or opt.get("mouth_ok"))
    doc = {
        "schema": "g16-compiler-sense-plate/v1",
        "updated": _now(),
        "title": doctrine.get("title") or "G16 compiler sense plate",
        "motto": doctrine.get("motto") or "",
        "meld_citation": doctrine.get("meld_citation") or "ironclad:meld:2",
        "plate_not_wire": True,
        "ok": plated,
        "plated": plated,
        "verdict": "GREEN" if opt["profile"] in ("expert", "heavy", "forever") else ("WATCH" if plated else "HOLD"),
        "chain_hash": chain,
        "optimize": opt,
        "effective_profile": opt["profile"],
        "profile_reason": opt["reason"],
        "sense_score": opt["sense_score"],
        "eye_ear_plate": {
            "verdict": eem.get("verdict"),
            "chain_hash": eem.get("chain_hash"),
            "eye_ok": eem.get("eye_ok"),
            "ear_ok": eem.get("ear_ok"),
            "mouth_ok": eem.get("mouth_ok"),
        },
        "sense_members": {
            "final_eye": bool(members["eye"]),
            "final_ear": bool(members["ear"]),
            "mouth_neural": bool(members["mouth"]),
        },
        "g16_stack_ok": bool(stack.get("ok") or stack.get("optimized")),
        "grok16_root": str(GROK16) if GROK16.is_dir() else None,
        "profile_ladder": doctrine.get("profile_ladder") or [],
    }
    if write:
        _save(PLATE, doc)
        _append_ledger({
            "ts": doc["updated"],
            "ok": doc.get("ok"),
            "effective_profile": opt["profile"],
            "sense_score": opt["sense_score"],
            "chain_hash": chain,
        })
    return doc


def cycle() -> dict[str, Any]:
    return build_plate(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status", "optimize"):
        print(json.dumps(build_plate(write=cmd != "optimize"), ensure_ascii=False))
        return 0
    if cmd in ("cycle", "plate", "meld"):
        print(json.dumps(cycle(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: g16-compiler-sense-plate.py [json|cycle|optimize]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())