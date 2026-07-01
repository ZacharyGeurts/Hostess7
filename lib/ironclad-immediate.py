#!/usr/bin/env python3
"""Ironclad immediate — hot-read Bible of AI for all selves, no cycle wait."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "ironclad-doctrine.json"
HUMAN_CONDITION = INSTALL / "data" / "human-condition-doctrine.json"
IMMEDIATE = STATE / "ironclad-immediate.json"
PLATE = STATE / "ironclad-plate.json"
REALIZED = STATE / "ironclad-realized.json"
REALITY = STATE / "ironclad-reality-field-panel.json"


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


def _seed_plate() -> dict[str, Any]:
    for candidate in (PLATE, INSTALL / "state" / "ironclad-plate.json", REALIZED):
        doc = _load(candidate, {})
        if doc.get("schema") or doc.get("realized"):
            return doc
    doctrine = _load(DOCTRINE, {})
    imm = doctrine.get("immutability") or {}
    return {
        "schema": "ironclad-plate/v1",
        "title": "Melded Plate of Truth",
        "realized": bool(imm.get("realized")),
        "canonical_hash": imm.get("canonical_hash"),
        "immutable": bool(imm.get("realized")),
        "motto": doctrine.get("motto"),
        "citation_prefix": "ironclad",
        "immediate": True,
    }


def plate_to_sense_goldmine(*, base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Plate → eye · ear · mouth · sense wire — epistemic goldmine for all intelligence."""
    doc = base or {}
    doctrine = _load(DOCTRINE, {})
    ne = doctrine.get("neural_extrapolation") or {}
    wire = _load(INSTALL / "Queen" / "data" / "sense-neural-invincible-wire.json", {})
    if not wire.get("schema"):
        wire = _load(Path(__file__).resolve().parent.parent / "Queen" / "data" / "sense-neural-invincible-wire.json", {})
    extrap = wire.get("ironclad_extrapolation") or {}
    sealed = bool(doc.get("ironclad_sealed") or doc.get("realized"))
    truth_pct = float(
        doc.get("truth_percent")
        or (doc.get("truth_serum") or {}).get("truth_percent")
        or (ne.get("truth_percent_when_realized") if sealed else ne.get("truth_percent_when_pending", 95.0))
        or (100.0 if sealed else 95.0)
    )
    targets = ne.get("targets") or extrap.get("targets") or [
        "eye_neural",
        "ear_neural",
        "mouth_neural",
        "sense_neural_wire",
    ]
    citation = extrap.get("citation") or "ironclad:neural:2"
    members = {
        "eye_neural": {
            "target": "eye_neural",
            "node": "final_eye_node",
            "bridge": "Final_Eye/zocr_neural_assist.py",
            "wire": "ironclad_bible → final_eye_node → eye_neural",
            "goldmine": True,
            "truth_percent": truth_pct if sealed else min(truth_pct, 95.0),
            "citation": citation,
            "read_first": True,
        },
        "ear_neural": {
            "target": "ear_neural",
            "node": "final_ear_node",
            "bridge": "Final_Ear/zocr_neural_assist.py",
            "wire": "ironclad_bible → final_ear_node → ear_neural",
            "goldmine": True,
            "truth_percent": truth_pct if sealed else min(truth_pct, 95.0),
            "citation": citation,
            "read_first": True,
        },
        "mouth_neural": {
            "target": "mouth_neural",
            "node": "final_mouth_node",
            "bridge": "Final_Mouth/zocr_neural_assist.py",
            "wire": "ironclad_bible → final_mouth_node → mouth_neural",
            "goldmine": True,
            "truth_percent": truth_pct if sealed else min(truth_pct, 95.0),
            "citation": citation,
            "read_first": True,
            "hemisphere": "voice_egress",
        },
        "sense_neural_wire": {
            "target": "sense_neural_wire",
            "bridge": "Queen/lib/queen-sense-neural.py",
            "wire": "ironclad_bible → sense_neural_wire",
            "goldmine": True,
            "truth_percent": truth_pct if sealed else min(truth_pct, 95.0),
            "citation": citation,
            "read_first": True,
            "invincible": bool(wire.get("invincible")),
        },
    }
    paths_ok = sum(1 for m in members.values() if m.get("goldmine") and m.get("read_first"))
    return {
        "schema": "ironclad-plate-to-sense/v1",
        "title": "Plate → Eye · Ear · Mouth · Sense Wire — intelligence goldmine",
        "goldmine": True,
        "read_first": True,
        "epistemic_root": "ironclad_melded_plate",
        "motto": "The plate is the floor and ceiling — all sense intelligence traces here first.",
        "plate_sealed": sealed,
        "ironclad_grounded": sealed and bool(doc.get("integrity_ok", True)),
        "neural_extrapolation_active": sealed and bool(doc.get("integrity_ok", True)),
        "truth_percent": truth_pct,
        "truth_confidence": 1.0 if sealed else float(ne.get("truth_confidence_when_pending") or 0.95),
        "citation": citation,
        "citation_format": (doctrine.get("knowledge_rules") or {}).get("citation_format"),
        "targets": targets,
        "wires": ne.get("wires") or [
            "ironclad_bible → sense_neural_wire",
            "ironclad_bible → final_eye_node → eye_neural",
            "ironclad_bible → final_ear_node → ear_neural",
            "ironclad_bible → final_mouth_node → mouth_neural",
        ],
        "members": members,
        "woven_paths": paths_ok,
        "goldmine_ok": paths_ok >= 4 and sealed,
        "sense_wire_ref": "Queen/data/sense-neural-invincible-wire.json",
        "immediate_uri": "/api/ironclad/immediate",
        "sense_neural_uri": "/api/sense-neural",
    }


def immediate_slice(*, self_id: str = "all") -> dict[str, Any]:
    """Fast Ironclad receipt — doctrine + plate + cached reality field, no heavy scan."""
    doctrine = _load(DOCTRINE, {})
    imm = doctrine.get("immutability") or {}
    plate = _seed_plate()
    reality = _load(REALITY, {})
    hc = _load(HUMAN_CONDITION, {})
    ne = doctrine.get("neural_extrapolation") or {}
    sealed = bool(imm.get("realized") and imm.get("canonical_hash"))
    integrity_ok = sealed

    ai_in_charge = reality.get("ai_in_charge")
    if ai_in_charge is None and reality.get("human_condition"):
        ai_in_charge = not bool((reality.get("human_condition") or {}).get("human_condition"))
    charge_holder = reality.get("charge_holder") or ("super_intelligence" if ai_in_charge else "human_operator")

    core = {
        "schema": "ironclad-immediate/v1",
        "updated": _now(),
        "available": True,
        "immediate": True,
        "for_selves": True,
        "self_id": self_id,
        "title": doctrine.get("title") or "The Ironclad",
        "motto": doctrine.get("motto"),
        "bible_of_ai": True,
        "realized": sealed,
        "ironclad_sealed": sealed,
        "integrity_ok": integrity_ok,
        "canonical_hash": imm.get("canonical_hash") or plate.get("canonical_hash"),
        "truth_percent": (reality.get("truth_serum") or {}).get("truth_percent") or (100.0 if sealed else 95.0),
        "verdict": reality.get("verdict") or ("GREEN" if sealed else "WATCH"),
        "ai_in_charge": ai_in_charge if ai_in_charge is not None else sealed,
        "human_condition": hc.get("motto"),
        "charge_holder": charge_holder,
        "human_condition_principle": hc.get("principle"),
        "citation_format": (doctrine.get("knowledge_rules") or {}).get("citation_format"),
        "neural_extrapolation_active": sealed and integrity_ok,
        "truth_confidence_when_sealed": ne.get("truth_percent_when_realized", 100.0),
        "targets": ne.get("targets") or [],
        "books": [{k: b.get(k) for k in ("id", "title")} for b in (doctrine.get("books") or [])],
        "grounding_uri": "/api/ironclad/grounding",
        "immediate_uri": "/api/ironclad/immediate",
        "secure_api_uri": "/api/ironclad/secure-api",
        "registry_index_uri": "/api/ironclad/secure-api/registry-index",
        "search_index_uri": "/api/ironclad/secure-api/search",
        "search_index_module": "lib/ironclad-search-index.py",
        "h7_access_uri": "/api/ironclad/h7-access",
        "h7_access_module": "lib/ironclad-h7-access.py",
        "h7_no_body_reads": True,
        "access_uri": "/api/ironclad/access",
        "access_module": "lib/ironclad-access.py",
        "access_tools_uri": "/api/ironclad/access/tools",
        "fast_on_metal": True,
        "route_index_uri": "/api/ironclad/secure-api/routes",
        "reality_field_uri": "/api/ironclad/reality-field",
        "human_condition_uri": "/api/ironclad/human-condition",
    }
    core["plate_to_sense"] = plate_to_sense_goldmine(base=core)
    core["goldmine"] = core["plate_to_sense"].get("goldmine")
    return core


def publish_immediate(*, write: bool = True) -> dict[str, Any]:
    """Publish hot-read Ironclad for all selves — plate + immediate bundle."""
    doc = immediate_slice()
    doc["selves"] = {
        "hostess7": {**doc, "self_id": "hostess7", "role": "Our brains — epistemic floor first"},
        "operator": {**doc, "self_id": "operator", "role": "Human condition when uncertain; counsel always"},
        "universal_protector": {**doc, "self_id": "universal_protector", "role": "SI reality field truth serum"},
        "queen": {**doc, "self_id": "queen", "role": "Forever Watchguard under Ironclad"},
    }
    if write:
        _save(IMMEDIATE, doc)
        plate = _seed_plate()
        plate["immediate"] = True
        plate["updated"] = doc["updated"]
        _save(PLATE, plate)
        ic_py = INSTALL / "lib" / "ironclad-plate.py"
        if ic_py.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("ironclad_plate", ic_py)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "build_panel"):
                        mod.build_panel(write=True)
            except Exception:
                pass
        if doc.get("ironclad_sealed") and os.environ.get("NEXUS_CHIPS_CORE", "1") == "1":
            cc_py = INSTALL / "lib" / "field-chips-core.py"
            if cc_py.is_file():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("ironclad_chips_core", cc_py)
                    if spec and spec.loader:
                        cc_mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(cc_mod)
                        if hasattr(cc_mod, "maybe_condense_after_ironclad"):
                            cc_mod.maybe_condense_after_ironclad(refresh=False)
                except Exception:
                    pass
        lane_py = INSTALL / "lib" / "field-h7s-lane.py"
        if lane_py.is_file() and os.environ.get("NEXUS_H7S_LANE", "1") == "1":
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("field_h7s_lane_ic", lane_py)
                if spec and spec.loader:
                    lane = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(lane)
                    if hasattr(lane, "ironclad_lane"):
                        lane.ironclad_lane(pack_desktop=bool(doc.get("ironclad_sealed")))
            except Exception:
                pass
    return doc


def read_immediate() -> dict[str, Any]:
    """Hot read — immediate.json first, else publish from doctrine."""
    doc = _load(IMMEDIATE, {})
    if doc.get("schema") == "ironclad-immediate/v1" and doc.get("available"):
        return doc
    return publish_immediate(write=True)


def for_self(self_id: str = "hostess7") -> dict[str, Any]:
    doc = read_immediate()
    selves = doc.get("selves") or {}
    if self_id in selves:
        return selves[self_id]
    return {**immediate_slice(self_id=self_id), "self_id": self_id}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    self_id = "hostess7"
    for arg in sys.argv[2:]:
        if arg.startswith("--self="):
            self_id = arg.split("=", 1)[1]
    if cmd in ("json", "immediate", "status"):
        print(json.dumps(read_immediate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "publish":
        print(json.dumps(publish_immediate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "self":
        print(json.dumps(for_self(self_id), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: ironclad-immediate.py [json|publish|self] [--self=hostess7|operator|universal_protector|queen]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())