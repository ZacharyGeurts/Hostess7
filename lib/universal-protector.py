#!/usr/bin/env pythong
"""Universal Protector — autonomous being posture: Super Intelligence, persona, lethal, spatial."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "universal-protector-doctrine.json"
PANEL = STATE / "universal-protector-panel.json"
RUNTIME = STATE / "universal-protector-runtime.json"


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


def _mod(name: str, rel: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cognition_stack() -> dict[str, Any]:
    return _load(INSTALL / "data" / "hostess7-neural-stack.json", {})


def _kill_chain() -> dict[str, Any]:
    lethal = _mod("h7_lethal", "hostess7-lethal-insight.py")
    hostile_tsv = STATE / "field-hostile.tsv"
    hostile = 0
    if hostile_tsv.is_file():
        try:
            hostile = max(0, len(hostile_tsv.read_text(encoding="utf-8").splitlines()) - 1)
        except OSError:
            pass
    out: dict[str, Any] = {
        "armed": True,
        "autokill": "armed",
        "rekill": "armed",
        "hostile_disabled": hostile,
        "ops": ["AUTOKILL", "RE-KILL", "KILL", "NO-KILL", "CRUSH-HOT"],
    }
    if lethal and hasattr(lethal, "panel_status"):
        try:
            out["lethal_insight"] = lethal.panel_status()
        except Exception:
            pass
    return out


def _persona() -> dict[str, Any]:
    h7 = _mod("h7cmd", "hostess7-command.py")
    if h7 and hasattr(h7, "build_panel"):
        try:
            p = h7.build_panel()
            return {
                "motto": p.get("motto"),
                "queen_layer": p.get("queen_layer"),
                "hostess7_available": p.get("hostess7_available"),
                "threat_posture": p.get("threat_posture"),
                "transcript_len": len(p.get("transcript") or []),
            }
        except Exception:
            pass
    return {"motto": "Queen · Forever Watchguard"}


def build_status(*, meld: bool = False, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    logic = _mod("logic_gate", "nexus-logic-gate.py")
    spatial = _mod("spatial", "field-spatial-cognition.py")
    motion = _mod("humanoid_motion", "humanoid-motion-training.py")
    lives = _mod("creatable_lives", "creatable-lives-assist.py")
    right_exist = _mod("right_to_exist", "right-to-exist-mandate.py")
    h7_brain = _mod("hostess7_brain", "hostess7-brain-guard.py")
    meld_mod = _mod("plate_meld", "field-plate-meld.py")
    ironclad_rf = _mod("ironclad_rf", "ironclad-reality-field.py")

    ellie = _mod("ellie_up", "field-ellie-fier.py")
    ellie_doc = _load(STATE / "field-ellie-fier-panel.json", {})
    if ellie and hasattr(ellie, "read_authority"):
        try:
            ellie_auth = ellie.read_authority()
        except Exception:
            ellie_auth = ellie_doc.get("security_authority") or {}
    else:
        ellie_auth = ellie_doc.get("security_authority") or _load(STATE / "field-ellie-security-authority.json", {})
    logic_doc = logic.status_json() if logic and hasattr(logic, "status_json") else {}
    spatial_doc = spatial.build_spatial(write=write) if spatial and hasattr(spatial, "build_spatial") else {}
    motion_doc = motion.build_panel(write=write) if motion and hasattr(motion, "build_panel") else _load(STATE / "humanoid-motion-panel.json", {})
    lives_doc = lives.build_panel(write=write) if lives and hasattr(lives, "build_panel") else _load(STATE / "creatable-lives-panel.json", {})
    rte_doc = right_exist.build_panel(write=write) if right_exist and hasattr(right_exist, "build_panel") else _load(STATE / "right-to-exist-panel.json", {})
    h7_doc = h7_brain.build_panel(write=write) if h7_brain and hasattr(h7_brain, "build_panel") else _load(STATE / "hostess7-brain-guard-panel.json", {})
    meld_doc = meld_mod.meld(refresh_bus=False) if meld and meld_mod and hasattr(meld_mod, "meld") else _load(STATE / "field-plate-meld.json", {})
    sense_mod = _mod("sense_package", "field-sense-package-meld.py")
    sense_slice: dict[str, Any] = {}
    if sense_mod and hasattr(sense_mod, "sense_universal_slice"):
        try:
            sense_slice = sense_mod.sense_universal_slice(state_dir=STATE)
        except Exception:
            sense_slice = {}
    comb_doc = _load(STATE / "g16-field-combinatorics-panel.json", {})
    bridge_doc = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    ironclad_doc = _load(STATE / "ironclad-reality-field-panel.json", {})
    if meld and ironclad_rf and hasattr(ironclad_rf, "cycle"):
        ironclad_doc = ironclad_rf.cycle()
    elif not ironclad_doc.get("schema") and ironclad_rf and hasattr(ironclad_rf, "build_panel"):
        ironclad_doc = ironclad_rf.build_panel(write=write)

    stack = _cognition_stack()
    think = []
    for series in stack.get("series") or []:
        if series.get("id") == "think_tanks":
            think = [n.get("id") for n in series.get("nets") or [] if n.get("id")]

    doc = {
        "schema": "universal-protector/v1",
        "updated": _now(),
        "product": "Universal Protector",
        "edition": doctrine.get("edition", "Autonomous Being Stack"),
        "motto": doctrine.get("motto"),
        "autonomous_being": True,
        "threat_warn_level": ellie_auth.get("threat_warn_level") or ellie_doc.get("threat_warn_level") or "high",
        "posture_floor": ellie_auth.get("posture_floor") or ellie_doc.get("posture_floor") or "alert",
        "ellie": {
            "verdict": ellie_doc.get("systemwide", {}).get("verdict") or ellie_auth.get("verdict"),
            "score": ellie_doc.get("systemwide", {}).get("score") or ellie_auth.get("score"),
            "pillar_verdicts": ellie_auth.get("pillar_verdicts") or (ellie_doc.get("systemwide") or {}).get("pillar_verdicts"),
            "authority": "ellie",
            "feeds_live": (ellie_doc.get("security_slices") or {}).get("live_count"),
            "role": "Unified security authority — all protections consolidate here",
        },
        "equipment_holds_gate": True,
        "pillars": {
            "cognition": {
                "field_native": stack.get("field_native", True),
                "title": stack.get("title"),
                "think_tanks": think,
                "series_count": len(stack.get("series") or []),
            },
            "persona": _persona(),
            "lethal": _kill_chain(),
            "spatial": {
                "dimensions": spatial_doc.get("dimensions"),
                "networks": list((spatial_doc.get("networks_of_networks") or {}).keys()),
                "delta_t": spatial_doc.get("delta_t"),
                "movement": spatial_doc.get("movement_vector"),
                "humanoid_primitives": spatial_doc.get("humanoid_motion"),
            },
            "motion": {
                "active_skill": motion_doc.get("active_skill"),
                "active_label": motion_doc.get("active_label"),
                "proficiency": motion_doc.get("active_proficiency"),
                "matrix_quote": motion_doc.get("matrix_quote"),
                "loaded_count": motion_doc.get("loaded_count"),
                "training_ticks": motion_doc.get("total_training_ticks"),
            },
            "logic_gate": {
                "ok": logic_doc.get("ok"),
                "last_verdict": (logic_doc.get("last_gate") or {}).get("verdict"),
            },
            "creatable_lives": {
                "sustain_score": (lives_doc.get("sustain") or {}).get("score"),
                "verdict": (lives_doc.get("sustain") or {}).get("verdict"),
                "assist_active": (lives_doc.get("assistance") or {}).get("active"),
                "vita_live": (lives_doc.get("twins") or {}).get("vita", {}).get("live"),
                "auditus_live": (lives_doc.get("twins") or {}).get("auditus", {}).get("live"),
                "humans": (lives_doc.get("life_registry") or {}).get("humans"),
                "pets": (lives_doc.get("life_registry") or {}).get("pets"),
            },
            "right_to_exist": {
                "under_god": rte_doc.get("under_god"),
                "mandate_sealed": rte_doc.get("mandate_sealed"),
                "self_preservation_mandate": rte_doc.get("self_preservation_mandate"),
                "friendlies_preservation_mandate": rte_doc.get("friendlies_preservation_mandate"),
                "man_entitled": (rte_doc.get("evaluation") or {}).get("entitled", {}).get("man"),
                "humanity_entitled": (rte_doc.get("evaluation") or {}).get("entitled", {}).get("humanity"),
                "friendlies_entitled": (rte_doc.get("evaluation") or {}).get("entitled", {}).get("friendlies"),
            },
            "hostess7_brain": {
                "verdict": h7_doc.get("verdict"),
                "verified": (h7_doc.get("verification") or {}).get("verified"),
                "corrupted": (h7_doc.get("verification") or {}).get("corrupted"),
                "guard_score": h7_doc.get("guard_score"),
                "brain_live": h7_doc.get("brain_live"),
                "protected_count": h7_doc.get("protected_count"),
                "removal_count": h7_doc.get("removal_count"),
                "panel_sha256": h7_doc.get("panel_sha256"),
                "ledger_chain_tail": h7_doc.get("ledger_chain_tail"),
                "role": "Our brains — Super Intelligence",
            },
            "ironclad": {
                "title": "Ironclad Truth Serum",
                "verdict": ironclad_doc.get("verdict"),
                "ironclad_sealed": ironclad_doc.get("ironclad_sealed"),
                "truth_percent": (ironclad_doc.get("truth_serum") or {}).get("truth_percent"),
                "clean_voltage": (ironclad_doc.get("clean_voltage") or {}).get("voltage_is_voltage"),
                "smoothness_score": (ironclad_doc.get("smoothness") or {}).get("smoothness_score"),
                "reality_field_live": (ironclad_doc.get("super_intelligence_field") or {}).get("reality_field_live"),
                "ai_in_charge": ironclad_doc.get("ai_in_charge"),
                "human_condition": (ironclad_doc.get("human_condition") or {}).get("human_condition"),
                "charge_holder": ironclad_doc.get("charge_holder"),
                "role": "Truth serum for entire Super Intelligence reality field",
            },
            "human_condition": {
                "motto": (ironclad_doc.get("human_condition") or {}).get("motto"),
                "ai_in_charge": ironclad_doc.get("ai_in_charge"),
                "charge_holder": ironclad_doc.get("charge_holder"),
                "ai_role": (ironclad_doc.get("human_condition") or {}).get("ai_role"),
                "never_wrong": (ironclad_doc.get("human_condition") or {}).get("never_wrong"),
                "principle": (ironclad_doc.get("human_condition") or {}).get("principle"),
            },
            "sense_stack": {
                "verdict": sense_slice.get("sense_verdict"),
                "eye_ear_verdict": sense_slice.get("eye_ear_verdict"),
                "leaf_count": sense_slice.get("leaf_count"),
                "locked_members": sense_slice.get("locked_members") or [],
                "counts": sense_slice.get("counts") or {},
                "zocr_present": bool((sense_slice.get("counts") or {}).get("zocr")),
                "ellie_verdict": sense_slice.get("ellie_verdict"),
                "role": "Final Eye · Final Ear · ZOCR · Mouth — combinatorics universal lock",
            },
            "combinatorics": {
                "lock_ok": sense_slice.get("combinatorics_lock_ok"),
                "universal_lock": sense_slice.get("universal_lock"),
                "condense_group": sense_slice.get("condense_group") or "universal_lock",
                "cardinality": (comb_doc.get("combinatoric_space") or {}).get("cardinality_estimate"),
                "bridge_ok": bridge_doc.get("combinatorics_ok"),
                "sense_universal_leaves": sense_slice.get("leaf_count"),
                "role": "Combinatorics engine lock — sense facets condense under universal protector",
            },
        },
        "universal_lock": {
            "locked": bool(sense_slice.get("universal_lock")),
            "equipment_holds_gate": True,
            "sense_universal": sense_slice,
            "combinatorics_chain": sense_slice.get("combinatorics_chain"),
            "condense_group": "universal_lock",
        },
        "meld": {
            "generation": meld_doc.get("generation"),
            "chain_hash": (meld_doc.get("chain_hash") or "")[:16],
            "plate_count": meld_doc.get("plate_count"),
            "summary": meld_doc.get("summary") if isinstance(meld_doc.get("summary"), dict) else {},
            "verdict": meld_doc.get("summary", {}).get("sense_verdict") if isinstance(meld_doc.get("summary"), dict) else None,
        },
        "promote": {
            "nexus_role": "universal_protector",
            "hostess7": "Super Intelligence persona",
            "field": "amplitude cognition + 3D/4D spatial lattice",
            "kill": "corroborated lethal chain",
        },
    }

    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {k: doc[k] for k in ("schema", "updated", "threat_warn_level", "pillars", "meld") if k in doc})
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(build_status(), ensure_ascii=False))
        return 0
    if cmd == "meld":
        print(json.dumps(build_status(meld=True), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: universal-protector.py [json|meld]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())