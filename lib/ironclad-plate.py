#!/usr/bin/env pythong
"""Ironclad — Melded Plate of Truth. The Bible of AI. Immutable once fully realized."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "ironclad-doctrine.json"
MELD_EXTENSIONS = INSTALL / "data" / "ironclad-meld-extensions.json"
IMAGES_MANIFEST = INSTALL / "data" / "ironclad" / "images" / "manifest.json"
PLATE = STATE / "ironclad-plate.json"
REALIZED = STATE / "ironclad-realized.json"
LEDGER = STATE / "ironclad-ledger.jsonl"


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


def canonical_hash(doc: dict[str, Any]) -> str:
    """Stable hash of doctrine content — excludes realized metadata for pre-realize compute."""
    scrub = {k: v for k, v in doc.items() if k not in ("immutability",)}
    imm = doc.get("immutability") or {}
    scrub["immutability"] = {
        "policy": imm.get("policy"),
        "change_forbidden_after_realized": imm.get("change_forbidden_after_realized"),
        "amendment_forbidden": imm.get("amendment_forbidden"),
    }
    blob = json.dumps(scrub, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def is_realized() -> bool:
    doc = _load(DOCTRINE, {})
    imm = doc.get("immutability") or {}
    if imm.get("realized"):
        return True
    realized = _load(REALIZED, {})
    return bool(realized.get("realized"))


def realize(*, force: bool = False) -> dict[str, Any]:
    """Seal Ironclad forever — immutable Bible of AI."""
    if is_realized() and not force:
        return {"ok": True, "already_realized": True, "plate": _load(PLATE, {})}

    doctrine = _load(DOCTRINE, {})
    if not doctrine:
        return {"ok": False, "error": "doctrine_missing"}

    ch = canonical_hash(doctrine)
    ts = _now()
    imm = doctrine.setdefault("immutability", {})
    imm["realized"] = True
    imm["realized_at"] = ts
    imm["canonical_hash"] = ch

    _save(DOCTRINE, doctrine)

    images = _load(IMAGES_MANIFEST, {})
    plate = {
        "schema": "ironclad-plate/v1",
        "title": "Melded Plate of Truth",
        "subtitle": "The Bible of AI",
        "updated": ts,
        "realized": True,
        "realized_at": ts,
        "canonical_hash": ch,
        "immutable": True,
        "motto": doctrine.get("motto"),
        "universe_bounds": doctrine.get("universe_bounds"),
        "truth_set": doctrine.get("truth_set"),
        "knowledge_rules": doctrine.get("knowledge_rules"),
        "authority": doctrine.get("authority"),
        "books": doctrine.get("books"),
        "gift_images": images.get("images") or [],
        "gift_manifest": str(IMAGES_MANIFEST.relative_to(INSTALL)) if IMAGES_MANIFEST.is_file() else None,
        "citation_prefix": "ironclad",
    }
    _save(PLATE, plate)
    _save(REALIZED, {"schema": "ironclad-realized/v1", "realized": True, "realized_at": ts, "canonical_hash": ch})
    _append_ledger({"ts": ts, "event": "realize", "canonical_hash": ch})
    return {"ok": True, "realized": True, "canonical_hash": ch, "plate": plate}


def verify_integrity() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    realized_doc = _load(REALIZED, {})
    plate = _load(PLATE, {})
    imm = doctrine.get("immutability") or {}
    expected = imm.get("canonical_hash") or realized_doc.get("canonical_hash")
    current = canonical_hash(doctrine) if doctrine else ""
    ok = True
    detail = "ok"
    if imm.get("realized") or realized_doc.get("realized"):
        if expected and current != expected:
            ok = False
            detail = "hash_mismatch_after_realized"
    return {
        "ok": ok,
        "realized": bool(imm.get("realized") or realized_doc.get("realized")),
        "canonical_hash": expected or current,
        "current_hash": current,
        "detail": detail,
        "immutable": bool(plate.get("immutable")),
    }


def _neural_extrapolation_doc() -> dict[str, Any]:
    return _load(DOCTRINE, {}).get("neural_extrapolation") or {}


def _claim_traces_ironclad(claim: str, meta: dict[str, Any] | None = None) -> bool:
    meta = meta or {}
    if meta.get("ironclad_grounded") or meta.get("ironclad_extrapolation"):
        return True
    text = (claim or "").strip()
    if not text:
        return False
    if re.search(r"ironclad:[a-z_]+:\d+", text, re.I):
        return True
    low = text.lower()
    if "ironclad" in low or "melded plate" in low or "bible of ai" in low:
        return True
    doctrine = _load(DOCTRINE, {})
    truth_set = doctrine.get("truth_set") or {}
    tokens: list[str] = []
    for items in truth_set.values():
        if isinstance(items, list):
            tokens.extend(str(x) for x in items)
    for tok in tokens:
        key = tok.replace("_", " ")
        if key in low or tok in low:
            return True
    return False


def neural_extrapolation_confidence(
    claim: str,
    *,
    target_neural: str = "any_intelligence_neural",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ironclad seal — 100% truth confidence on grounded extrapolation to any intelligence neural."""
    meta = meta or {}
    ne = _neural_extrapolation_doc()
    integrity = verify_integrity()
    realized = bool(integrity.get("realized") and integrity.get("ok"))
    traces = _claim_traces_ironclad(claim, meta)
    targets = ne.get("targets") or []
    target = str(meta.get("target_neural") or target_neural or "any_intelligence_neural")
    if target not in targets and target != "any_intelligence_neural":
        target = "any_intelligence_neural"

    if not traces:
        return {
            "ok": False,
            "schema": "ironclad-neural-extrapolation/v1",
            "extrapolation": False,
            "truth_confidence": 0.0,
            "truth_percent": 0.0,
            "truth_score": 0.0,
            "deception_risk": "high",
            "detail": "claim_does_not_trace_ironclad",
            "target_neural": target,
            "realized": realized,
            "integrity_ok": integrity.get("ok"),
        }

    if realized:
        conf = float(ne.get("truth_confidence_when_realized") or 1.0)
        pct = float(ne.get("truth_percent_when_realized") or conf * 100)
    else:
        conf = float(ne.get("truth_confidence_when_pending") or 0.95)
        pct = round(conf * 100, 1)

    sealed = realized and integrity.get("ok")
    return {
        "ok": True,
        "schema": "ironclad-neural-extrapolation/v1",
        "extrapolation": True,
        "ironclad_sealed": sealed,
        "realized": realized,
        "integrity_ok": integrity.get("ok"),
        "truth_confidence": conf,
        "truth_percent": pct,
        "truth_score": pct,
        "deception_risk": "low" if sealed else "medium",
        "adapt_allowed": True,
        "genius_tier": sealed,
        "target_neural": target,
        "citation": cite("neural", 1) or "ironclad:neural:1",
        "assurance": (
            "ironclad sealed — 100% truth confidence on neural extrapolation"
            if sealed
            else "ironclad pending — high truth confidence; realize plate for 100%"
        ),
        "canonical_hash": integrity.get("canonical_hash"),
        "detail": "ironclad_neural_extrapolation",
    }


def _meld_extension_books() -> list[dict[str, Any]]:
    doc = _load(MELD_EXTENSIONS, {})
    return [b for b in (doc.get("books") or []) if isinstance(b, dict)]


def _field_sanity_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "ironclad-field-sanity.py"
    if not py.is_file():
        return {"id": "field_sanity", "absorbed": False, "missing": True}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ironclad_field_sanity", py)
        if not spec or not spec.loader:
            return {"id": "field_sanity", "absorbed": False, "missing": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "melded_extension_slice"):
            return mod.melded_extension_slice()
    except Exception:
        pass
    return {"id": "field_sanity", "absorbed": False, "detail": "slice_unavailable"}


def _spatial_existence_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "ironclad-spatial-existence.py"
    if not py.is_file():
        return {"id": "spatial_existence", "absorbed": False, "missing": True}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ironclad_spatial_existence", py)
        if not spec or not spec.loader:
            return {"id": "spatial_existence", "absorbed": False, "missing": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "melded_extension_slice"):
            return mod.melded_extension_slice()
    except Exception:
        pass
    return {"id": "spatial_existence", "absorbed": False, "detail": "slice_unavailable"}


def _sovereign_time_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "sovereign-time.py"
    if not py.is_file():
        return {"id": "time", "absorbed": False, "missing": True, "declaration": "Time is linear."}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("sovereign_time_plate", py)
        if not spec or not spec.loader:
            return {"id": "time", "absorbed": False, "missing": True, "declaration": "Time is linear."}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "melded_extension_slice"):
            return mod.melded_extension_slice()
    except Exception:
        pass
    return {"id": "time", "absorbed": False, "declaration": "Time is linear.", "detail": "slice_unavailable"}


def _g1id_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "g1id-format.py"
    if not py.is_file():
        return {"id": "g1id", "absorbed": False, "missing": True}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("g1id_format_plate", py)
        if not spec or not spec.loader:
            return {"id": "g1id", "absorbed": False, "missing": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "melded_extension_slice"):
            return mod.melded_extension_slice()
    except Exception:
        pass
    return {"id": "g1id", "absorbed": False, "detail": "slice_unavailable"}


def _g1id_baseline_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "g1id-baseline.py"
    if not py.is_file():
        return {"id": "g1id_baselines", "absorbed": False, "missing": True}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("g1id_baseline_plate", py)
        if not spec or not spec.loader:
            return {"id": "g1id_baselines", "absorbed": False, "missing": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "melded_extension_slice"):
            return mod.melded_extension_slice()
    except Exception:
        pass
    return {"id": "g1id_baselines", "absorbed": False, "detail": "slice_unavailable"}


def _field_io_packet_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-io-packet.py"
    if not py.is_file():
        return {"id": "field_io_packet", "absorbed": False, "missing": True}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_io_packet_plate", py)
        if not spec or not spec.loader:
            return {"id": "field_io_packet", "absorbed": False, "missing": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "melded_extension_slice"):
            return mod.melded_extension_slice()
    except Exception:
        pass
    return {"id": "field_io_packet", "absorbed": False, "detail": "slice_unavailable"}


def cite(book: str, verse: int = 1) -> str | None:
    doctrine = _load(DOCTRINE, {})
    for b in doctrine.get("books") or []:
        if str(b.get("id")) == book:
            for v in b.get("verses") or []:
                if int(v.get("v") or 0) == verse:
                    return f"ironclad:{book}:{verse} — {v.get('text')}"
    for b in _meld_extension_books():
        if str(b.get("id")) == book:
            for v in b.get("verses") or []:
                if int(v.get("v") or 0) == verse:
                    return f"ironclad:{book}:{verse} — {v.get('text')}"
    return None


def knowledge_grounding() -> dict[str, Any]:
    """AI-readable epistemic root — load before any inference."""
    doctrine = _load(DOCTRINE, {})
    plate = _load(PLATE, {})
    if not plate and doctrine:
        plate = {
            "schema": "ironclad-plate/v1",
            "realized": False,
            "motto": doctrine.get("motto"),
            "knowledge_rules": doctrine.get("knowledge_rules"),
            "truth_set": doctrine.get("truth_set"),
            "books": [{k: b.get(k) for k in ("id", "title")} for b in (doctrine.get("books") or [])],
        }
    ne = _neural_extrapolation_doc()
    integrity = verify_integrity()
    sealed = bool(integrity.get("realized") and integrity.get("ok"))
    return {
        "schema": "ironclad-grounding/v1",
        "updated": _now(),
        "bible_of_ai": True,
        "all_knowledge_from": "ironclad",
        "immutable_after_realized": True,
        "integrity": integrity,
        "neural_extrapolation": {
            **ne,
            "active": sealed,
            "truth_percent_when_active": 100.0 if sealed else float(ne.get("truth_confidence_when_pending", 0.95) * 100),
            "targets": ne.get("targets") or [],
        },
        "doctrine": {
            "motto": doctrine.get("motto"),
            "universe_bounds": doctrine.get("universe_bounds"),
            "knowledge_rules": doctrine.get("knowledge_rules"),
            "neural_extrapolation": ne,
            "ai_parse_guide": doctrine.get("ai_parse_guide"),
        },
        "plate": plate,
        "images": _load(IMAGES_MANIFEST, {}),
        "melded_extensions": {
            "policy": "subsidiary_truth_absorbed_without_sealed_amendment",
            "meld_citation": cite("meld", 2) or "ironclad:meld:2",
            "extensions_ref": str(MELD_EXTENSIONS.relative_to(INSTALL)) if MELD_EXTENSIONS.is_file() else None,
            "field_sanity": _field_sanity_slice(),
            "time": _sovereign_time_slice(),
            "spatial_existence": _spatial_existence_slice(),
            "g1id": _g1id_slice(),
            "g1id_baselines": _g1id_baseline_slice(),
            "field_io_packet": _field_io_packet_slice(),
        },
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    grounding = knowledge_grounding()
    panel = {
        "schema": "ironclad-panel/v1",
        "updated": _now(),
        "title": "The Ironclad",
        "subtitle": "Melded Plate of Truth · Bible of AI",
        "motto": grounding.get("doctrine", {}).get("motto") or _load(DOCTRINE, {}).get("motto"),
        "realized": grounding["integrity"].get("realized"),
        "immutable": grounding["integrity"].get("immutable") or grounding["integrity"].get("realized"),
        "canonical_hash": grounding["integrity"].get("canonical_hash"),
        "integrity_ok": grounding["integrity"].get("ok"),
        "gift_images": (grounding.get("images") or {}).get("images") or [],
        "knowledge_rules": grounding.get("doctrine", {}).get("knowledge_rules"),
        "neural_extrapolation": grounding.get("neural_extrapolation"),
        "melded_extensions": grounding.get("melded_extensions"),
        "field_sanity": (grounding.get("melded_extensions") or {}).get("field_sanity"),
        "time": (grounding.get("melded_extensions") or {}).get("time"),
        "time_is_linear": True,
        "spatial_existence": (grounding.get("melded_extensions") or {}).get("spatial_existence"),
        "g1id": (grounding.get("melded_extensions") or {}).get("g1id"),
        "g1id_baselines": (grounding.get("melded_extensions") or {}).get("g1id_baselines"),
        "field_io_packet": (grounding.get("melded_extensions") or {}).get("field_io_packet"),
        "grounding": grounding,
    }
    if write:
        _save(STATE / "ironclad-panel.json", panel)
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "grounding":
        print(json.dumps(knowledge_grounding(), ensure_ascii=False))
        return 0
    if cmd == "realize":
        print(json.dumps(realize(force="--force" in sys.argv), ensure_ascii=False))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_integrity(), ensure_ascii=False))
        return 0
    if cmd == "cite" and len(sys.argv) > 2:
        verse = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 1
        out = cite(sys.argv[2], verse=verse)
        print(out or json.dumps({"error": "not_found"}, ensure_ascii=False))
        return 0 if out else 1
    if cmd in ("extrapolate", "neural", "neural-extrapolation"):
        claim = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "ironclad:neural:1 extrapolation to intelligence neural"
        target = "any_intelligence_neural"
        for i, arg in enumerate(sys.argv[2:], start=2):
            if arg.startswith("--target="):
                target = arg.split("=", 1)[1]
        print(json.dumps(neural_extrapolation_confidence(claim, target_neural=target), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: ironclad-plate.py [json|grounding|realize|verify|extrapolate CLAIM|cite BOOK [VERSE]]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())