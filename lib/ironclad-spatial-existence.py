#!/usr/bin/env pythong
"""Ironclad spatial existence — this one / that one lessons melded into capstone core."""
from __future__ import annotations

import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "ironclad-spatial-existence-doctrine.json"
EXTENSIONS = INSTALL / "data" / "ironclad-meld-extensions.json"
PANEL = STATE / "ironclad-spatial-existence-panel.json"
LEDGER = STATE / "ironclad-spatial-existence-ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _mod(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cite(verse: int = 1) -> str | None:
    doc = _load(DOCTRINE, {})
    for book in doc.get("books") or []:
        if str(book.get("id")) != "spatial_existence":
            continue
        for v in book.get("verses") or []:
            if int(v.get("v") or 0) == verse:
                return f"ironclad:spatial_existence:{verse} — {v.get('text')}"
    ext = _load(EXTENSIONS, {})
    for book in ext.get("books") or []:
        if str(book.get("id")) != "spatial_existence":
            continue
        for v in book.get("verses") or []:
            if int(v.get("v") or 0) == verse:
                return f"ironclad:spatial_existence:{verse} — {v.get('text')}"
    return None


def _operator_point() -> dict[str, Any] | None:
    op = _mod(INSTALL / "lib" / "operator-location.py", "operator_location")
    if not op:
        return None
    try:
        loc = op.panel_json() if hasattr(op, "panel_json") else {}
        lat, lon = loc.get("lat"), loc.get("lon")
        if lat is not None and lon is not None:
            return {
                "kind": "this_one",
                "receipt": "operator_location",
                "lat": lat,
                "lon": lon,
                "label": loc.get("label") or "",
                "postal_address": loc.get("address") or "",
                "gps_fix": True,
            }
    except Exception:
        pass
    return None


def _has_place_receipt(entity: dict[str, Any]) -> bool:
    keys = (
        "operator_location", "postal_address", "gps_fix", "lat", "lon",
        "sdf_entity", "vision_bearing", "bearing_deg", "lattice_cell", "address",
    )
    return any(entity.get(k) not in (None, "", []) for k in keys)


def load_baseline(baseline_id: str, *, verify_plate: bool = True) -> dict[str, Any]:
    """Load immoveable G1ID baseline by manifest id."""
    manifest = _load(INSTALL / "data" / "g1id-baseline-manifest.json", {})
    for entry in manifest.get("baselines") or []:
        if str(entry.get("id")) != str(baseline_id):
            continue
        rel = str(entry.get("path") or f"data/baselines/{baseline_id}.g1id")
        return load_g1id(INSTALL / rel, verify_plate=verify_plate)
    return {"ok": False, "error": "baseline_not_in_manifest", "id": baseline_id}


def load_g1id(path: Path | str, *, verify_plate: bool = True) -> dict[str, Any]:
    """Load cold .g1id geometric identity — this_one hardened, plate preserved."""
    g1 = _mod(INSTALL / "lib" / "g1id-format.py", "g1id_format")
    if not g1 or not hasattr(g1, "read_file"):
        return {"ok": False, "error": "g1id_format_missing"}
    try:
        result = g1.read_file(path, verify_plate=verify_plate)
        if not result.get("ok"):
            return result
        doc = result.get("document") or {}
        entity = g1.to_spatial_entity(doc) if hasattr(g1, "to_spatial_entity") else {}
        return {
            **result,
            "entity": entity,
            "classify": classify_entity(entity),
            "format": "g1id",
            "meld_inputs": doc.get("meld_inputs"),
            "sovereign_time": (doc.get("meld_inputs") or {}).get("sovereign_time"),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}


def classify_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Classify as this_one (witnessed here) or that_one (uncorroborated there)."""
    doc = _load(DOCTRINE, {})
    lessons = doc.get("lessons") or {}
    markers = set(lessons.get("that_one", {}).get("markers") or [])
    present_markers = [m for m in markers if entity.get(m) or m in (entity.get("markers") or [])]
    correlation = float(entity.get("existence_correlation", entity.get("correlation", 0.0)))
    floor = float((doc.get("spatial_existence") or {}).get("correlation_floor", 0.65))
    has_receipt = _has_place_receipt(entity)
    forced = str(entity.get("kind") or "").strip().lower()

    if forced in ("this_one", "that_one"):
        kind = forced
    elif present_markers:
        kind = "that_one"
    elif has_receipt and correlation >= floor:
        kind = "this_one"
    elif has_receipt and correlation > 0:
        kind = "ambiguous"
    elif has_receipt:
        kind = "this_one"
    else:
        kind = "that_one"

    return {
        "kind": kind,
        "has_place_receipt": has_receipt,
        "existence_correlation": round(correlation, 3),
        "markers": present_markers,
        "citation": cite(1 if kind == "this_one" else 2),
        "lesson": (lessons.get(kind) or {}).get("label") or kind,
    }


def correlate_this_that(
    this: dict[str, Any] | None = None,
    that: dict[str, Any] | None = None,
    *,
    sdf_entities: list[dict[str, Any]] | None = None,
    vision_bearings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind this one to witnessed existence; gate that one on correlate_existence."""
    doc = _load(DOCTRINE, {})
    se = doc.get("spatial_existence") or {}
    floor = float(se.get("correlation_floor", 0.65))
    this_ent = dict(this or _operator_point() or {})
    that_ent = dict(that or {})
    this_cls = classify_entity({**this_ent, "kind": "this_one"})
    that_cls = classify_entity(that_ent)

    correlation = float(that_ent.get("existence_correlation", that_ent.get("correlation", 0.0)))
    ear_mod = None
    sg = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
    for candidate in (sg / "Final_Ear" / "zocr_ear_localize.py", INSTALL.parent / "Final_Ear" / "zocr_ear_localize.py"):
        if candidate.is_file():
            ear_mod = _mod(candidate, "zocr_ear_localize")
            break

    if ear_mod and hasattr(ear_mod, "correlate_existence") and that_ent.get("sources"):
        try:
            loc = {"sources": that_ent.get("sources") or []}
            corr_doc = ear_mod.correlate_existence(loc, sdf_entities=sdf_entities, vision_bearings=vision_bearings)
            correlation = float(corr_doc.get("correlation", correlation))
            that_cls["ear_correlate"] = corr_doc
        except Exception:
            pass

    pass_ok = (
        this_cls.get("kind") == "this_one"
        and (
            that_cls.get("kind") == "this_one"
            or (that_cls.get("kind") == "ambiguous" and correlation >= floor)
            or (that_cls.get("kind") == "that_one" and correlation < floor and not that_ent.get("trust_without_correlate"))
        )
    )
    if that_cls.get("kind") == "that_one" and correlation >= floor:
        that_cls["kind"] = "ambiguous"
        pass_ok = this_cls.get("kind") == "this_one"

    result = {
        "schema": "ironclad-spatial-existence/v1",
        "updated": _now(),
        "pass_ok": pass_ok,
        "this_one": this_cls,
        "that_one": that_cls,
        "existence_correlation": round(correlation, 3),
        "correlation_floor": floor,
        "meld_citation": doc.get("meld_citation") or "ironclad:meld:2",
        "citation": cite(4) or "ironclad:spatial_existence:4",
        "rule": (doc.get("spatial_existence") or {}).get("rule"),
    }
    _append_ledger({
        "ts": result["updated"],
        "pass_ok": pass_ok,
        "this_kind": this_cls.get("kind"),
        "that_kind": that_cls.get("kind"),
        "correlation": result["existence_correlation"],
    })
    return result


def lattice_amplitude(
    *,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    linear_ns: int | None = None,
    scale: str = "body",
    t: float | None = None,
) -> dict[str, Any]:
    """Spatial existence as lattice amplitude — place is x,y,z; time is linear sovereign receipt."""
    doc = _load(DOCTRINE, {})
    amp = round(math.sqrt(x * x + y * y + z * z), 4)
    if linear_ns is None and t is not None:
        linear_ns = int(t)
    return {
        "schema": "ironclad-spatial-lattice/v1",
        "updated": _now(),
        "place": {"x": x, "y": y, "z": z},
        "linear_receipt": {"linear_ns": linear_ns, "citation": "ironclad:time:1"},
        "scale": scale,
        "amplitude": amp,
        "kind": "this_one",
        "time_is_linear": True,
        "citation": cite(3) or "ironclad:spatial_existence:3",
    }


def melded_extension_slice() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    probe = correlate_this_that()
    return {
        "id": "spatial_existence",
        "absorbed": DOCTRINE.is_file(),
        "pass_ok": bool(probe.get("pass_ok")),
        "this_one": probe.get("this_one"),
        "that_one": probe.get("that_one"),
        "existence_correlation": probe.get("existence_correlation"),
        "meld_citation": doc.get("meld_citation") or "ironclad:meld:2",
        "citation": cite(1) or "ironclad:spatial_existence:1",
        "sealed_anchor": doc.get("sealed_anchor") or "ironclad:place:2",
        "updated": _now(),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    panel = {
        "schema": "ironclad-spatial-existence-panel/v1",
        "updated": _now(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "lessons": doc.get("lessons"),
        "spatial_existence": doc.get("spatial_existence"),
        "slice": melded_extension_slice(),
        "correlate": correlate_this_that(),
    }
    if write:
        _save(PANEL, panel)
    return panel


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "slice":
        print(json.dumps(melded_extension_slice(), ensure_ascii=False))
        return 0
    if cmd == "classify" and len(sys.argv) > 2:
        ent = json.loads(sys.argv[2])
        print(json.dumps(classify_entity(ent), ensure_ascii=False))
        return 0
    if cmd == "correlate":
        this = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
        that = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        print(json.dumps(correlate_this_that(this, that), ensure_ascii=False))
        return 0
    if cmd == "cite" and len(sys.argv) > 2 and sys.argv[2].isdigit():
        out = cite(int(sys.argv[2]))
        print(out or json.dumps({"error": "not_found"}, ensure_ascii=False))
        return 0 if out else 1
    print(json.dumps({
        "error": "usage: ironclad-spatial-existence.py [json|slice|classify JSON|correlate [THIS] [THAT]|cite VERSE]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())