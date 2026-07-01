#!/usr/bin/env pythong
"""System core — biology, presume, motion tracking, solid brain on every system."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-system-core-doctrine.json"
PANEL = STATE / "hostess7-system-core-panel.json"
LEDGER = STATE / "hostess7-system-core-ledger.jsonl"


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    stem = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(f"{name}_{stem}", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pillar_biology() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    spec = next((p for p in (doc.get("pillars") or []) if p.get("id") == "biology"), {})
    mod_path = INSTALL / str(spec.get("module") or "lib/hostess7-biology.py")
    doctrine_path = INSTALL / str(spec.get("doctrine") or "data/hostess7-biology-doctrine.json")
    ok = mod_path.is_file() and doctrine_path.is_file()
    panel: dict[str, Any] = {}
    bio = _mod("bio", "lib/hostess7-biology.py")
    if bio and hasattr(bio, "build_panel"):
        try:
            panel = bio.build_panel(write=False)
            ok = ok and bool(panel.get("ok", True))
        except Exception as exc:
            panel = {"error": str(exc)[:160]}
            ok = False
    return {
        "id": "biology",
        "ok": ok,
        "module": str(mod_path.relative_to(INSTALL)) if mod_path.is_file() else None,
        "doctrine": doctrine_path.is_file(),
        "panel_ok": bool(panel.get("ok", ok)),
        "tier": panel.get("tier"),
        "fluent": panel.get("fluent"),
    }


def _pillar_presume() -> dict[str, Any]:
    mod_path = INSTALL / "lib/hostess7-presume.py"
    doctrine_path = INSTALL / "data/hostess7-presume-doctrine.json"
    ok = mod_path.is_file() and doctrine_path.is_file()
    panel: dict[str, Any] = {}
    presume = _mod("presume", "lib/hostess7-presume.py")
    probe: dict[str, Any] = {}
    if presume and hasattr(presume, "build_panel"):
        try:
            panel = presume.build_panel(write=False)
        except Exception as exc:
            panel = {"error": str(exc)[:160]}
    commit_probe: dict[str, Any] = {}
    prop: dict[str, Any] = {}
    if presume and hasattr(presume, "presume"):
        try:
            probe = presume.presume(5_000, label="system_core_probe", alternate_id="sovereign_know")
            ok = ok and bool(probe.get("resumed_on_point"))
        except Exception as exc:
            probe = {"error": str(exc)[:160]}
            ok = False
    if presume and hasattr(presume, "decide") and hasattr(presume, "reject_influence"):
        try:
            aid = "system_core_pillar_probe"
            presume.decide(aid, label="pillar_probe", source="hostess7")
            blocked = presume.reject_influence(aid, source="external", reason="pillar_test")
            commit_probe = {"blocked_outside": not blocked.get("allowed", True)}
            if hasattr(presume, "release"):
                presume.release(aid, source="hostess7")
            ok = ok and commit_probe.get("blocked_outside", False)
        except Exception as exc:
            commit_probe = {"error": str(exc)[:160]}
            ok = False
    if presume and hasattr(presume, "propagate"):
        try:
            prop = presume.propagate(write=False)
            ok = ok and bool(prop.get("targets_present", 0) >= 4)
        except Exception as exc:
            prop = {"error": str(exc)[:160]}
    return {
        "id": "presume",
        "ok": ok,
        "precision_us": bool(panel.get("precision_us") or _load(doctrine_path, {}).get("precision_us")),
        "resumed_on_point": bool(probe.get("resumed_on_point")),
        "drift_us": probe.get("drift_us"),
        "line_profile_count": panel.get("line_profile_count", 0),
        "uninterruptable_witness": commit_probe.get("blocked_outside"),
        "propagation": prop,
        "not_go_away": bool(_load(doctrine_path, {}).get("not_go_away", {}).get("resources_remain")),
    }


def _pillar_motion() -> dict[str, Any]:
    mod_path = INSTALL / "lib/humanoid-motion-training.py"
    doctrine_path = INSTALL / "data/humanoid-motion-doctrine.json"
    eye_doc = _load(INSTALL / "data/final-eye-plate-doctrine.json", {})
    motion_track = bool((eye_doc.get("ocr") or {}).get("enhancement_room", {}).get("motion_track"))
    ok = mod_path.is_file() and doctrine_path.is_file()
    doctrine = _load(doctrine_path, {})
    physics = bool(doctrine.get("physics_mode"))
    panel: dict[str, Any] = {}
    motion = _mod("motion", "lib/humanoid-motion-training.py")
    if motion and hasattr(motion, "build_panel"):
        try:
            panel = motion.build_panel(write=False)
            ok = ok and physics and bool(panel.get("ok", True))
        except Exception as exc:
            panel = {"error": str(exc)[:160]}
            ok = False
    resolve_ok = (INSTALL / "lib/iron-plate-motion-resolve.py").is_file()
    secured_ok = False
    secured_slice: dict[str, Any] = {}
    secured_mod = _mod("motion_secured", "lib/humanoid-motion-secured.py")
    if secured_mod and hasattr(secured_mod, "self_protection_status"):
        try:
            secured_slice = secured_mod.self_protection_status()
            secured_ok = bool(secured_slice.get("secured"))
        except Exception:
            secured_ok = False
    return {
        "id": "motion_tracking",
        "ok": ok and motion_track and secured_ok,
        "physics_mode": physics,
        "eye_motion_track": motion_track,
        "motion_secured": secured_ok,
        "protected_by": secured_slice.get("protected_by") or "self",
        "limb_identity_count": (secured_slice.get("components") or []).__len__() if secured_slice else 0,
        "iron_plate_motion_resolve": resolve_ok,
        "skills_loaded": len(
            panel.get("skills")
            or (panel.get("catalog") or {}).get("skills")
            if isinstance(panel.get("catalog"), dict)
            else (panel.get("catalog") or [])
        ),
        "train_gui_ready": panel.get("train_gui_ready"),
    }


def _pillar_brain() -> dict[str, Any]:
    guard_path = INSTALL / "lib/hostess7-brain-guard.py"
    panel_path = INSTALL / "lib/field-brain-panel.py"
    ok = guard_path.is_file() and panel_path.is_file()
    guard_panel = _load(STATE / "hostess7-brain-guard-panel.json", {})
    field_brain = _load(STATE / "field-brain-panel.json", {})
    if not field_brain and panel_path.is_file():
        fb = _mod("fbrain", "lib/field-brain-panel.py")
        if fb and hasattr(fb, "build_field_brain"):
            try:
                field_brain = fb.build_field_brain()
            except Exception:
                pass
    guard = _mod("guard", "lib/hostess7-brain-guard.py")
    verified = False
    if guard and hasattr(guard, "verify_brain"):
        try:
            rep = guard.verify_brain(write_quarantine=False)
            verified = bool(rep.get("verified") and rep.get("critical_ok"))
            guard_panel = guard.build_panel(write=False) if hasattr(guard, "build_panel") else guard_panel
        except Exception:
            verified = bool(guard_panel.get("verdict") == "brain_verified")
    else:
        verified = bool(guard_panel.get("ok") or guard_panel.get("verified"))
    score = guard_panel.get("guard_score") or guard_panel.get("score")
    sdf = INSTALL / "cache" / "fieldstorage" / "brain" / "sdf"
    github_brain = INSTALL / "data" / "field-brain"
    storage_ok = sdf.is_dir() or (INSTALL / "cache" / "fieldstorage" / "brain").is_dir() or github_brain.is_dir()
    field_live = bool(field_brain.get("ok") or field_brain.get("brain_live"))
    verdict = guard_panel.get("verdict") or ("brain_verified" if verified else "brain_hold")
    infrastructure_ok = guard_path.is_file() and panel_path.is_file()
    ok = infrastructure_ok and field_live
    return {
        "id": "brain",
        "ok": ok,
        "infrastructure_ok": infrastructure_ok,
        "brain_verified": verified,
        "guard_score": score,
        "field_brain_live": field_live,
        "sdf_storage": storage_ok,
        "verdict": verdict,
        "runtime_verified": verdict == "brain_verified",
    }


def verify_core(*, write_panel: bool = True) -> dict[str, Any]:
    """Verify all four pillars — every system must pass."""
    pillars = [
        _pillar_biology(),
        _pillar_presume(),
        _pillar_motion(),
        _pillar_brain(),
    ]
    solid = all(p.get("ok") for p in pillars)
    doc = {
        "schema": "hostess7-system-core/v1",
        "updated": _now(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "mandatory_on_every_system": True,
        "solid": solid,
        "pillar_count": len(pillars),
        "pillars_solid": sum(1 for p in pillars if p.get("ok")),
        "pillars": pillars,
        "brain_for_stack": _load(DOCTRINE, {}).get("brain_for_stack"),
    }
    if write_panel:
        _save(PANEL, doc)
    _append({"event": "verify_core", "solid": solid, "pillars_solid": doc["pillars_solid"]})
    return doc


def train_core(*, quick: bool = True) -> dict[str, Any]:
    """Train all four pillars — biology, presume, motion, brain witness."""
    results: dict[str, Any] = {}
    training = _mod("training", "lib/hostess7-training.py")
    if training and hasattr(training, "run_track"):
        for tid in ("biology", "presume", "brain_guard"):
            try:
                results[tid] = training.run_track(tid)
            except Exception as exc:
                results[tid] = {"ok": False, "error": str(exc)[:160]}
    motion = _mod("motion", "lib/humanoid-motion-training.py")
    if motion and hasattr(motion, "train_ticks"):
        try:
            results["humanoid_motion"] = motion.train_ticks("touch_toes", ticks=12 if quick else 30)
        except Exception as exc:
            results["humanoid_motion"] = {"ok": False, "error": str(exc)[:160]}
    secured = _mod("motion_secured_train", "lib/humanoid-motion-secured.py")
    if secured and hasattr(secured, "witness_cycle"):
        try:
            results["motion_secured"] = secured.witness_cycle()
        except Exception as exc:
            results["motion_secured"] = {"ok": False, "error": str(exc)[:160]}
    guard = _mod("guard", "lib/hostess7-brain-guard.py")
    if guard and hasattr(guard, "verify_brain"):
        try:
            results["brain_verify"] = guard.verify_brain(write_quarantine=True)
        except Exception as exc:
            results["brain_verify"] = {"ok": False, "error": str(exc)[:160]}
    fb = _mod("fbrain", "lib/field-brain-panel.py")
    if fb and hasattr(fb, "build_field_brain"):
        try:
            doc = fb.build_field_brain()
            out = STATE / "field-brain-panel.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            results["field_brain_panel"] = doc
        except Exception as exc:
            results["field_brain_panel"] = {"ok": False, "error": str(exc)[:160]}
    ok = all(
        r.get("ok") is not False
        for r in results.values()
        if isinstance(r, dict)
    )
    out = {
        "schema": "hostess7-system-core-train/v1",
        "ok": ok,
        "quick": quick,
        "results": results,
        "verify": verify_core(write_panel=True),
        "utc": _now(),
    }
    _append({"event": "train_core", "ok": ok})
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    return verify_core(write_panel=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status", "verify"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("train", "training"):
        quick = "--full" not in sys.argv
        print(json.dumps(train_core(quick=quick), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {"error": "usage: hostess7-system-core.py [panel|verify|train [--full]]"},
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())