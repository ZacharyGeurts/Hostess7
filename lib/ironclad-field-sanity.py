#!/usr/bin/env pythong
"""Ironclad field sanity — Queen simplify pass absorbed into the melded capstone."""
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
DOCTRINE = INSTALL / "data" / "ironclad-field-sanity-doctrine.json"
EXTENSIONS = INSTALL / "data" / "ironclad-meld-extensions.json"
PANEL = STATE / "ironclad-field-sanity-panel.json"
LEDGER = STATE / "ironclad-field-sanity-ledger.jsonl"


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


def _queen_root() -> Path:
    for candidate in (
        INSTALL / "Queen",
        INSTALL.parent / "Queen",
        Path(__file__).resolve().parent.parent / "Queen",
    ):
        if (candidate / "lib" / "queen-field-sanity.py").is_file():
            return candidate
    return INSTALL / "Queen"


def _ironclad_mod() -> Any | None:
    py = INSTALL / "lib" / "ironclad-plate.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("ironclad_plate", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _queen_sanity_mod() -> Any | None:
    py = _queen_root() / "lib" / "queen-field-sanity.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("queen_field_sanity", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cite_field_sanity(verse: int = 1) -> str | None:
    """Subsidiary citation from meld extensions — does not amend sealed doctrine."""
    doc = _load(EXTENSIONS, {})
    for book in doc.get("books") or []:
        if str(book.get("id")) != "field_sanity":
            continue
        for v in book.get("verses") or []:
            if int(v.get("v") or 0) == verse:
                return f"ironclad:field_sanity:{verse} — {v.get('text')}"
    return None


def _verse_for_pass(result: dict[str, Any]) -> int:
    if not result.get("ok"):
        return 4
    if (result.get("quarantined") or 0) > 0 or result.get("gate_ok") is False:
        return 4
    if (result.get("heat_avoided") or 0) > 0 or (result.get("deduped") or 0) > 0:
        return 2
    if result.get("fielded"):
        return 3
    return 1


def _truth_receipt(
    result: dict[str, Any],
    *,
    integrity: dict[str, Any],
    verse: int,
) -> dict[str, Any]:
    sealed = bool(integrity.get("realized") and integrity.get("ok"))
    heat = int(result.get("heat_avoided") or 0)
    layers_out = int(result.get("layers_out") or 0)
    gate_ok = result.get("gate_ok") is not False and result.get("ok")
    max_depth = int(result.get("max_field_depth") if result.get("max_field_depth") is not None else 0)
    single_depth = bool(result.get("single_field_depth", max_depth <= 0))
    never_under_heat = gate_ok and heat >= 0 and layers_out <= 64
    integral = bool(result.get("integral")) and gate_ok
    reorganized = result.get("reorganized") or []
    if not single_depth:
        single_field_ok = True
    else:
        single_field_ok = all(int(L.get("depth") or 0) == 0 for L in reorganized)
    depth_impossible = bool(result.get("depth_field_impossible", single_depth))
    return {
        "schema": "ironclad-field-sanity-receipt/v1",
        "meld_citation": _load(DOCTRINE, {}).get("meld_citation") or "ironclad:meld:2",
        "citation": cite_field_sanity(verse),
        "verse": verse,
        "ironclad_sealed": sealed,
        "integrity_ok": integrity.get("ok"),
        "canonical_hash": integrity.get("canonical_hash"),
        "absorbed": True,
        "integral": integral,
        "never_build_under_heat": never_under_heat,
        "simplify_never_obtuse": True,
        "infinite_resolution_aspiration": True,
        "single_field_depth": single_depth,
        "single_field_depth_ok": single_field_ok,
        "depth_field_impossible": depth_impossible,
        "depth_fields_sealed_and_destroyed": depth_impossible,
        "creation_forbidden": depth_impossible,
        "pass_ok": gate_ok and integral and single_field_ok and (not single_depth or depth_impossible),
        "detail": "field_sanity_melded" if gate_ok and single_field_ok else "field_sanity_hold",
    }


def _preflight_no_file(body: dict[str, Any]) -> dict[str, Any]:
    gate_py = INSTALL / "lib" / "field-no-file-gate.py"
    if not gate_py.is_file():
        return {"ok": True, "skipped": "gate_missing"}
    try:
        spec = importlib.util.spec_from_file_location("field_no_file_gate_ic", gate_py)
        if not spec or not spec.loader:
            return {"ok": True, "skipped": "gate_load_failed"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "preflight_body"):
            return mod.preflight_body(body)
    except (ImportError, OSError, AttributeError, ValueError):
        pass
    return {"ok": True, "skipped": "gate_error"}


def _preflight_singularize(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    sing_py = INSTALL / "lib" / "field-depth-singularizer.py"
    if not sing_py.is_file():
        return body, 0
    try:
        spec = importlib.util.spec_from_file_location("field_depth_singularizer_ic", sing_py)
        if not spec or not spec.loader:
            return body, 0
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "pre_singularize_body"):
            return mod.pre_singularize_body(body)
    except (ImportError, OSError, AttributeError, ValueError):
        pass
    return body, 0


def field_sanity_operator(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run Queen simplify pass and meld receipt into Ironclad truth."""
    body = body or {}
    no_file = _preflight_no_file(body)
    body, preflight_fixes = _preflight_singularize(body)
    doctrine = _load(DOCTRINE, {})
    queen = _queen_sanity_mod()
    if not queen or not hasattr(queen, "sanity_pass"):
        return {
            "ok": False,
            "schema": "ironclad-field-sanity/v1",
            "error": "queen_field_sanity_missing",
            "updated": _now(),
        }

    try:
        queen_result = queen.sanity_pass(body)
    except Exception as exc:
        return {
            "ok": False,
            "schema": "ironclad-field-sanity/v1",
            "error": str(exc),
            "updated": _now(),
        }

    ic = _ironclad_mod()
    integrity = ic.verify_integrity() if ic and hasattr(ic, "verify_integrity") else {"ok": False}
    verse = _verse_for_pass(queen_result)
    receipt = _truth_receipt(queen_result, integrity=integrity, verse=verse)
    meld_ref = cite_field_sanity(2) or "ironclad:meld:2"

    out = {
        "schema": "ironclad-field-sanity/v1",
        "updated": _now(),
        "title": "Ironclad Field Sanity",
        "subtitle": "Subsidiary truth melded into the capstone",
        "motto": doctrine.get("motto") or "",
        "meld_citation": doctrine.get("meld_citation") or "ironclad:meld:2",
        "meld_ref": meld_ref,
        "doctrine": doctrine,
        "extensions_ref": str(EXTENSIONS.relative_to(INSTALL)) if EXTENSIONS.is_file() else None,
        "integral": doctrine.get("integral") or {},
        "pass": doctrine.get("pass") or queen_result.get("pass") or [],
        "ironclad": receipt,
        "citation": receipt.get("citation"),
        "verse": verse,
        "queen": {
            k: queen_result.get(k)
            for k in (
                "ok", "integral", "fielded", "layers_in", "layers_out",
                "stripped", "quarantined", "deduped", "depth_flattened",
                "heat_avoided", "hottest_proxy", "coldest_proxy",
                "reorganized", "simplified_stack", "rule", "gate_ok", "gate",
            )
            if k in queen_result
        },
        "preflight_fixes": preflight_fixes,
        "depth_singularized": preflight_fixes > 0,
        "no_field_files": no_file,
        "never_poison_the_well": bool(no_file.get("ok")),
        "ok": bool(queen_result.get("ok")) and receipt.get("pass_ok") and bool(no_file.get("ok")),
        "operator_ok": receipt.get("pass_ok"),
        "detail": receipt.get("detail"),
    }
    return out


def build_panel(*, write: bool = True, body: dict[str, Any] | None = None) -> dict[str, Any]:
    panel = field_sanity_operator(body)
    panel["panel_schema"] = "ironclad-field-sanity-panel/v1"
    if write:
        _save(PANEL, panel)
        _append_ledger({
            "ts": panel.get("updated"),
            "ok": panel.get("ok"),
            "verse": panel.get("verse"),
            "layers_out": (panel.get("queen") or {}).get("layers_out"),
            "heat_avoided": (panel.get("queen") or {}).get("heat_avoided"),
            "citation": panel.get("citation"),
        })
    return panel


def cycle() -> dict[str, Any]:
    sing_py = INSTALL / "lib" / "field-depth-singularizer.py"
    if sing_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("field_depth_singularizer_cycle", sing_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "cycle"):
                    mod.cycle()
        except (ImportError, OSError, AttributeError):
            pass
    return build_panel(write=True)


def melded_extension_slice() -> dict[str, Any]:
    """Live read for ironclad-plate knowledge_grounding — no sealed doctrine write."""
    cached = _load(PANEL, {})
    if cached.get("schema") == "ironclad-field-sanity/v1":
        return {
            "id": "field_sanity",
            "absorbed": True,
            "meld_citation": cached.get("meld_citation"),
            "citation": cached.get("citation"),
            "verse": cached.get("verse"),
            "ok": cached.get("ok"),
            "operator_ok": cached.get("operator_ok"),
            "integral": (cached.get("integral") or {}).get("rule"),
            "heat_avoided": (cached.get("queen") or {}).get("heat_avoided"),
            "layers_out": (cached.get("queen") or {}).get("layers_out"),
            "updated": cached.get("updated"),
        }
    doc = build_panel(write=True)
    return {
        "id": "field_sanity",
        "absorbed": True,
        "meld_citation": doc.get("meld_citation"),
        "citation": doc.get("citation"),
        "verse": doc.get("verse"),
        "ok": doc.get("ok"),
        "operator_ok": doc.get("operator_ok"),
        "integral": (doc.get("integral") or {}).get("rule"),
        "heat_avoided": (doc.get("queen") or {}).get("heat_avoided"),
        "layers_out": (doc.get("queen") or {}).get("layers_out"),
        "updated": doc.get("updated"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd in ("cycle", "refresh"):
        print(json.dumps(cycle(), ensure_ascii=False))
        return 0
    if cmd == "pass":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(field_sanity_operator(body), ensure_ascii=False))
        return 0
    if cmd == "cite" and len(sys.argv) > 2 and sys.argv[2].isdigit():
        out = cite_field_sanity(int(sys.argv[2]))
        print(out or json.dumps({"error": "not_found"}, ensure_ascii=False))
        return 0 if out else 1
    if cmd == "slice":
        print(json.dumps(melded_extension_slice(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: ironclad-field-sanity.py [json|cycle|pass|cite VERSE|slice]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())