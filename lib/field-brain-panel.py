#!/usr/bin/env pythong
"""Field brain + Hostess7 superintelligence — panel slice from field drive."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))


def _import_tie() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("h7_field_drive_tie", INSTALL / "lib" / "h7-field-drive-tie.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _sdf_redata_summary(root: Path) -> dict[str, Any]:
    sdf = root / "brain" / "sdf"
    if not sdf.is_dir():
        return {"available": False}
    segments = list((sdf / "segments").glob("seg-*.json")) if (sdf / "segments").is_dir() else []
    human = list((sdf / "plates").glob("*.human.pgm")) if (sdf / "plates").is_dir() else []
    quarantine = list((sdf / "quarantine").glob("seg-*.json")) if (sdf / "quarantine").is_dir() else []
    truth_log = sdf / "truth_filter.jsonl"
    return {
        "available": True,
        "segments": len(segments),
        "human_plates": len(human),
        "quarantined": len(quarantine),
        "truth_log": truth_log.is_file(),
        "queen_brief": (sdf / "queen_redata_brief.json").is_file(),
        "verify_cmd": "./Hostess7.sh sdf-verify-redata",
    }


def _superintel_summary(root: Path) -> dict[str, Any]:
    si = root / "brain" / "superintel"
    if not si.is_dir():
        return {"available": False}
    ctx = _read_json(si / "context.json")
    lead = _read_json(si / "leadership.json")
    resonance = _read_json(si / "resonance.json")
    outbox_lines = 0
    ob = si / "outbox.jsonl"
    if ob.is_file():
        try:
            outbox_lines = sum(1 for _ in ob.open(encoding="utf-8", errors="replace"))
        except OSError:
            outbox_lines = 0
    return {
        "available": True,
        "arc": ctx.get("arc") or ctx.get("headline"),
        "head": ctx.get("head") or ctx.get("version"),
        "leadership": lead.get("mandate") or lead.get("hostess7_role"),
        "resonance": resonance.get("field_wave") or resonance.get("status"),
        "outbox_lines": outbox_lines,
        "directives": sum(1 for _ in (si / "directives.jsonl").open(encoding="utf-8", errors="replace"))
        if (si / "directives.jsonl").is_file() else 0,
    }


def build_field_brain(*, profile: str | None = None) -> dict[str, Any]:
    tie = _import_tie()
    if not tie:
        return {"schema": "field-brain/v1", "ok": False, "error": "field_tie_missing"}

    root = Path(tie.primary_field_root())
    inventory = tie.field_drive_inventory()
    superintel = _superintel_summary(root)
    sdf_redata = _sdf_redata_summary(root)
    tie_doc = tie.tie_field_drive()

    lib_manifest = root / "brain" / "library" / "manifest.json"
    manifest_doc = _read_json(lib_manifest)

    github_lib = INSTALL / "library" / "dewey"
    github_books = len(list(github_lib.glob("**/book.json"))) if github_lib.is_dir() else 0
    github_brain_dir = INSTALL / "data" / "field-brain"
    github_manifest = {}
    if (github_brain_dir / "manifest.json").is_file():
        github_manifest = _read_json(github_brain_dir / "manifest.json")
    github_ctx = _read_json(github_brain_dir / "context.json") if github_brain_dir.is_dir() else {}
    if github_ctx and not superintel.get("available"):
        superintel = {
            "available": True,
            "arc": github_ctx.get("arc") or github_ctx.get("headline"),
            "head": github_ctx.get("head") or github_ctx.get("version"),
            "source": "github/data/field-brain",
        }

    ruling: dict[str, Any] = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7ruler", INSTALL / "lib" / "hostess7-brain-ruler.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            ruling = mod.build_panel(write=False)
    except Exception:
        ruling = _read_json(STATE / "hostess7-brain-ruler-panel.json")

    return {
        "schema": "field-brain/v1",
        "ok": True,
        "field_root": str(root),
        "hostess7_root": str(HOSTESS7_ROOT),
        "brain_ruler": ruling,
        "superintelligence": superintel,
        "sdf_redata": sdf_redata,
        "inventory": inventory,
        "corpus_books": tie_doc.get("corpus_books") or [],
        "corpus_count": tie_doc.get("corpus_count") or 0,
        "manifest_count": tie_doc.get("manifest_count") or inventory.get("manifest_catalog_count") or 0,
        "manifest_packed": inventory.get("manifest_packed") or 0,
        "brain_corpus_count": inventory.get("brain_corpus_count") or 0,
        "brain_corpora": inventory.get("brain_corpora") or [],
        "bibliography_entries": inventory.get("bibliography_entries") or 0,
        "search_index_entries": inventory.get("search_index_entries") or 0,
        "textbooks_h7": inventory.get("textbooks_h7") or 0,
        "github_library_books": github_books,
        "github_library_path": "library/dewey/",
        "github_field_brain_path": "data/field-brain/",
        "github_manifest_count": github_manifest.get("catalog_count") or len(github_manifest.get("books") or []),
        "library_manifest_ok": bool(manifest_doc.get("books") or github_manifest.get("books")),
        "data_source": "github" if github_books and not inventory.get("manifest_packed") else "field",
        "tracking_total": (tie_doc.get("tracking") or {}).get("total") or 0,
        "zero_cost": True,
        "profile": profile or os.environ.get("NEXUS_LIBRARY_PROFILE", "hostess7"),
    }


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "json"
    if cmd == "json":
        print(json.dumps(build_field_brain(), ensure_ascii=False))
        return 0
    if cmd == "panel":
        doc = build_field_brain()
        out = STATE / "field-brain-panel.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    print("usage: field-brain-panel.py [json|panel]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())