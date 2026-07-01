#!/usr/bin/env pythong
"""Police / law / government agency database — global dropdown + merge-only import."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "police-agencies-seed.json"
GOV_SEED = INSTALL / "data" / "gov-databases-seed.json"
USER_DB = STATE / "police-agencies-user.json"
SELECTED = STATE / "police-agency-selected.json"


def _gov_intel():
    spec = importlib.util.spec_from_file_location("gov_intel_db", INSTALL / "lib" / "gov-intel-db.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _program_tags():
    spec = importlib.util.spec_from_file_location("program_tags_db", INSTALL / "lib" / "program-tags-db.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _seed_doc() -> dict[str, Any]:
    police = _load_json(SEED, {"agencies": [], "regions": []})
    gov = _load_json(GOV_SEED, {"agencies": [], "categories": []})
    agencies = list(police.get("agencies") or []) + list(gov.get("agencies") or [])
    regions = list(police.get("regions") or [])
    seen_r = {r.get("id") for r in regions}
    for r in gov.get("regions") or []:
        if r.get("id") not in seen_r:
            regions.append(r)
    categories = list(gov.get("categories") or [])
    return {
        "schema": "nexus-gov-agency-v2",
        "motto": "Police, law, intelligence, and government informational databases — merge-only updates.",
        "default_region": police.get("default_region") or "us",
        "regions": regions,
        "categories": categories,
        "agencies": agencies,
    }


def _user_doc() -> dict[str, Any]:
    return _load_json(USER_DB, {"imports": [], "custom_agencies": [], "updated": None})


def _selected_id() -> str | None:
    doc = _load_json(SELECTED, {"agency_id": None})
    aid = doc.get("agency_id")
    return str(aid) if aid else None


def _agency_index() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _seed_doc().get("agencies") or []:
        aid = str(row.get("id") or "")
        if aid:
            out[aid] = {**row, "source": "seed"}
    for row in _user_doc().get("custom_agencies") or []:
        aid = str(row.get("id") or "")
        if aid:
            out[aid] = {**row, "source": "operator"}
    return out


def list_agencies(region: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
    idx = _agency_index()
    rows = list(idx.values())
    if region:
        rows = [r for r in rows if r.get("region") == region or region == "all"]
    if category:
        rows = [r for r in rows if r.get("category") == category or category == "all"]
    return sorted(rows, key=lambda r: (r.get("category") or "", r.get("country") or "", r.get("name") or ""))


def get_agency(agency_id: str) -> dict[str, Any] | None:
    return _agency_index().get(agency_id)


def surrounding_agencies(agency_id: str) -> list[dict[str, Any]]:
    base = get_agency(agency_id)
    if not base:
        return []
    idx = _agency_index()
    out: list[dict[str, Any]] = []
    for sid in base.get("surrounding") or []:
        row = idx.get(str(sid))
        if row:
            out.append(row)
    return out


def select_agency(agency_id: str) -> bool:
    if not get_agency(agency_id):
        return False
    _save_json(SELECTED, {"agency_id": agency_id, "updated": _now()})
    return True


def import_format(
    agency_id: str,
    format_id: str,
    payload: str,
    filename: str = "",
    images: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    agency = get_agency(agency_id)
    if not agency:
        return {"ok": False, "error": "unknown_agency"}
    fmt = None
    for row in agency.get("formats") or []:
        if str(row.get("id")) == format_id:
            fmt = row
            break
    if not fmt:
        return {"ok": False, "error": "unknown_format"}
    gi = _gov_intel()
    return gi.import_and_merge(
        agency_id,
        format_id,
        payload,
        filename,
        str(fmt.get("ext") or "csv"),
        images,
    )


def panel_json() -> dict[str, Any]:
    seed = _seed_doc()
    sel_id = _selected_id()
    selected = get_agency(sel_id) if sel_id else None
    surrounding = surrounding_agencies(sel_id) if sel_id else []
    udoc = _user_doc()
    regions = seed.get("regions") or []
    agencies = list_agencies()
    gi = _gov_intel()
    gov = gi.panel_json()
    pt = _program_tags()
    programs = pt.panel_json()
    return {
        "motto": seed.get("motto") or "Police, law, and government databases — merge-only dossier updates.",
        "schema": seed.get("schema"),
        "default_region": seed.get("default_region") or "us",
        "regions": regions,
        "categories": seed.get("categories") or [],
        "agencies": agencies,
        "agency_count": len(agencies),
        "selected_id": sel_id,
        "selected": selected,
        "surrounding": surrounding,
        "imports": (udoc.get("imports") or [])[-20:],
        "import_count": len(udoc.get("imports") or []),
        "merge_only": True,
        "gov_intel": gov,
        "supported_formats": gov.get("supported_formats") or [],
        "image_formats": gov.get("image_formats") or [],
        "dossier_record_count": gov.get("record_count", 0),
        "human_override_count": gov.get("human_override_count", 0),
        "program_tags": programs,
        "program_count": programs.get("program_count", 0),
        "tagged_record_count": programs.get("tagged_record_count", 0),
        "pinned_location_count": programs.get("pinned_location_count", 0),
        "updated": _now(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "list":
        region = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        category = None
        for arg in sys.argv[2:]:
            if arg.startswith("--category="):
                category = arg.split("=", 1)[1]
        print(json.dumps({"agencies": list_agencies(region, category)}, ensure_ascii=False))
        return 0
    if cmd == "select" and len(sys.argv) >= 3:
        ok = select_agency(sys.argv[2])
        print(json.dumps({"ok": ok, "agency_id": sys.argv[2]}))
        return 0 if ok else 1
    if cmd == "import" and len(sys.argv) >= 5:
        agency_id = sys.argv[2]
        format_id = sys.argv[3]
        payload = sys.argv[4]
        if payload == "-" and not sys.stdin.isatty():
            payload = sys.stdin.read()
        filename = sys.argv[5] if len(sys.argv) > 5 else ""
        result = import_format(agency_id, format_id, payload, filename)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    if cmd == "import-json":
        raw = sys.argv[2] if len(sys.argv) > 2 else "-"
        doc = json.loads(raw if raw != "-" else sys.stdin.read())
        result = import_format(
            str(doc.get("agency_id") or ""),
            str(doc.get("format_id") or ""),
            str(doc.get("payload") or doc.get("data") or ""),
            str(doc.get("filename") or ""),
            doc.get("images"),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    if cmd == "get" and len(sys.argv) >= 3:
        row = get_agency(sys.argv[2])
        print(json.dumps(row or {"error": "not_found"}, ensure_ascii=False))
        return 0 if row else 1
    print(json.dumps({
        "error": "usage: police-agency-db.py [json|list [region]|select ID|get ID|import ID FORMAT PAYLOAD [filename]]",
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())