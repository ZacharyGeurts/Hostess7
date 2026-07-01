#!/usr/bin/env pythong
"""Obscure program tags (MKUltra, Project Monarch, etc.) — merge-only dossier tagging with locations."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "obscure-programs-seed.json"
USER_TAGS = STATE / "program-tags-user.json"
GOV_DOSSIERS = STATE / "gov-dossiers.json"

COORD_RE = re.compile(
    r"^\s*(-?\d{1,3}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$"
)
TAG_SPLIT_RE = re.compile(r"[,;|]+")


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


def _merge_value(existing: Any, new: Any) -> Any:
    if new is None:
        return existing
    if isinstance(new, str) and not new.strip():
        return existing
    if isinstance(new, dict):
        base = dict(existing) if isinstance(existing, dict) else {}
        for k, v in new.items():
            if k in base:
                base[k] = _merge_value(base[k], v)
            else:
                base[k] = v
        return base
    if isinstance(new, list):
        old = list(existing) if isinstance(existing, list) else []
        seen = {json.dumps(x, sort_keys=True, default=str) for x in old}
        for item in new:
            key = json.dumps(item, sort_keys=True, default=str)
            if key not in seen:
                old.append(item)
                seen.add(key)
        return old
    return new


def _program_index() -> dict[str, dict[str, Any]]:
    seed = _load_json(SEED, {"programs": []})
    user = _load_json(USER_TAGS, {"custom_programs": []})
    out: dict[str, dict[str, Any]] = {}
    for row in list(seed.get("programs") or []) + list(user.get("custom_programs") or []):
        pid = str(row.get("id") or "").strip()
        if pid:
            out[pid] = {**row, "source": row.get("source") or ("operator" if pid in {
                str(x.get("id")) for x in user.get("custom_programs") or []
            } else "seed")}
    return out


def _normalize_tag_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        parts = [str(x).strip() for x in raw if str(x).strip()]
    else:
        parts = [p.strip() for p in TAG_SPLIT_RE.split(str(raw)) if p.strip()]
    idx = _program_index()
    resolved: list[str] = []
    for part in parts:
        low = part.lower().replace(" ", "_").replace("-", "_")
        if low in idx:
            resolved.append(low)
            continue
        for pid, prog in idx.items():
            labels = {pid, str(prog.get("label") or "").lower()}
            for alias in prog.get("aliases") or []:
                labels.add(str(alias).lower())
            if part.lower() in labels or low in {a.lower().replace(" ", "_").replace("-", "_") for a in labels}:
                resolved.append(pid)
                break
        else:
            resolved.append(low)
    seen: set[str] = set()
    out: list[str] = []
    for tid in resolved:
        if tid not in seen:
            out.append(tid)
            seen.add(tid)
    return out


def parse_coords(text: str) -> tuple[float | None, float | None]:
    text = (text or "").strip()
    if not text:
        return None, None
    m = COORD_RE.match(text)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            return None, None
    return None, None


def build_location(
    lat: Any = None,
    lon: Any = None,
    coords: str = "",
    place: str = "",
    address: str = "",
    city: str = "",
    country: str = "",
    label: str = "",
    tags: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any] | None:
    clat, clon = parse_coords(coords)
    try:
        flat = float(lat) if lat not in (None, "") else clat
        flon = float(lon) if lon not in (None, "") else clon
    except (TypeError, ValueError):
        flat, flon = clat, clon

    place = str(place or "").strip()
    address = str(address or "").strip()
    city = str(city or "").strip()
    country = str(country or "").strip()
    label = str(label or place or address or "").strip()
    notes = str(notes or "").strip()

    if flat is None and flon is None and not place and not address:
        return None

    loc: dict[str, Any] = {
        "tagged_at": _now(),
        "label": label or place or address or "Pinned location",
    }
    if flat is not None and flon is not None:
        loc["lat"] = round(flat, 6)
        loc["lon"] = round(flon, 6)
    if place:
        loc["place"] = place
    if address:
        loc["address"] = address
    if city:
        loc["city"] = city
    if country:
        loc["country"] = country
    if notes:
        loc["notes"] = notes
    if tags:
        loc["tags"] = tags
    return loc


def _location_key(loc: dict[str, Any]) -> str:
    if loc.get("lat") is not None and loc.get("lon") is not None:
        return f"coord:{loc['lat']},{loc['lon']}:{loc.get('place','')}"
    blob = json.dumps({k: loc.get(k) for k in ("place", "address", "city", "label")}, sort_keys=True)
    return f"place:{hashlib.sha256(blob.encode()).hexdigest()[:16]}"


def list_programs(parent_id: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    idx = _program_index()
    rows = list(idx.values())
    if parent_id:
        rows = [r for r in rows if r.get("parent_id") == parent_id]
    if query:
        q = query.lower()
        rows = [
            r for r in rows
            if q in str(r.get("label") or "").lower()
            or q in str(r.get("id") or "").lower()
            or any(q in str(a).lower() for a in (r.get("aliases") or []))
            or q in str(r.get("description") or "").lower()
        ]
    return sorted(rows, key=lambda r: (r.get("parent_id") or "", r.get("label") or ""))


def program_tree() -> list[dict[str, Any]]:
    idx = _program_index()
    children: dict[str | None, list[dict[str, Any]]] = {}
    for pid, row in idx.items():
        parent = row.get("parent_id") or None
        children.setdefault(parent, []).append({**row, "id": pid})

    def nest(parent: str | None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in sorted(children.get(parent) or [], key=lambda r: r.get("label") or ""):
            node = dict(row)
            subs = nest(row["id"])
            if subs:
                node["children"] = subs
            out.append(node)
        return out

    return nest(None)


def get_program(program_id: str) -> dict[str, Any] | None:
    row = _program_index().get(program_id)
    if not row:
        return None
    kids = list_programs(parent_id=program_id)
    return {**row, "children": kids}


def apply_tags_to_record(
    record_key: str,
    tag_ids: list[str] | None = None,
    location: dict[str, Any] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    if not record_key:
        return {"ok": False, "error": "missing_record_key"}

    tags = _normalize_tag_ids(tag_ids or [])
    gdoc = _load_json(GOV_DOSSIERS, {"records": {}, "updated": None})
    records: dict[str, Any] = gdoc.get("records") or {}
    if not isinstance(records, dict):
        records = {}

    existing = dict(records.get(record_key) or {})
    if not existing:
        existing = {
            "record_key": record_key,
            "agency_id": "program_tags",
            "format_id": "manual_tag",
            "imported_at": _now(),
            "fields": {},
            "program_tags": [],
            "locations": [],
            "images": [],
            "import_history": [],
        }

    prev_tags = list(existing.get("program_tags") or [])
    merged_tags = _merge_value(prev_tags, tags)

    locs = list(existing.get("locations") or [])
    if location:
        lkey = _location_key(location)
        found = False
        for i, old in enumerate(locs):
            if _location_key(old) == lkey:
                locs[i] = _merge_value(old, location)
                found = True
                break
        if not found:
            locs.append(location)

    existing["program_tags"] = merged_tags
    existing["locations"] = locs
    existing["program_tag_updated"] = _now()
    if notes:
        fields = dict(existing.get("fields") or {})
        prev = str(fields.get("program_notes") or "").strip()
        fields["program_notes"] = f"{prev}\n{notes}".strip() if prev else notes
        existing["fields"] = fields

    records[record_key] = existing
    gdoc["records"] = records
    gdoc["record_count"] = len(records)
    gdoc["updated"] = _now()
    _save_json(GOV_DOSSIERS, gdoc)

    return {
        "ok": True,
        "merge_only": True,
        "record_key": record_key,
        "program_tags": merged_tags,
        "location_count": len(locs),
        "reload_panel": True,
    }


def tag_location(
    tag_ids: list[str] | None = None,
    lat: Any = None,
    lon: Any = None,
    coords: str = "",
    place: str = "",
    address: str = "",
    city: str = "",
    country: str = "",
    label: str = "",
    notes: str = "",
    record_key: str = "",
) -> dict[str, Any]:
    tags = _normalize_tag_ids(tag_ids or [])
    loc = build_location(lat, lon, coords, place, address, city, country, label, tags, notes)
    if not loc:
        return {"ok": False, "error": "missing_location"}

    if not record_key:
        if loc.get("lat") is not None and loc.get("lon") is not None:
            record_key = f"program_tag:location:{loc['lat']}:{loc['lon']}"
        else:
            record_key = f"program_tag:place:{hashlib.sha256(_location_key(loc).encode()).hexdigest()[:20]}"

    loc["tags"] = tags
    return apply_tags_to_record(record_key, tags, loc, notes)


def apply_row_tags(record: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Merge program tags and locations from an import row into a dossier record."""
    raw_tags = row.get("program_tags") or row.get("tags") or row.get("programs") or row.get("program")
    tags = _normalize_tag_ids(raw_tags)
    if not tags and not any(row.get(k) for k in ("lat", "lon", "coords", "place", "address", "location")):
        return record

    loc = build_location(
        row.get("lat"),
        row.get("lon"),
        str(row.get("coords") or row.get("coordinates") or ""),
        str(row.get("place") or row.get("location") or row.get("site") or ""),
        str(row.get("address") or ""),
        str(row.get("city") or ""),
        str(row.get("country") or ""),
        str(row.get("location_label") or row.get("label") or ""),
        tags,
        str(row.get("location_notes") or row.get("notes") or ""),
    )

    prev_tags = list(record.get("program_tags") or [])
    record["program_tags"] = _merge_value(prev_tags, tags)
    if loc:
        locs = list(record.get("locations") or [])
        lkey = _location_key(loc)
        found = False
        for i, old in enumerate(locs):
            if _location_key(old) == lkey:
                locs[i] = _merge_value(old, loc)
                found = True
                break
        if not found:
            locs.append(loc)
        record["locations"] = locs
    record["program_tag_updated"] = _now()
    return record


def panel_json() -> dict[str, Any]:
    idx = _program_index()
    gdoc = _load_json(GOV_DOSSIERS, {"records": {}})
    records = gdoc.get("records") or {}
    tagged = 0
    pinned = 0
    recent: list[dict[str, Any]] = []
    if isinstance(records, dict):
        for key, rec in records.items():
            if rec.get("program_tags"):
                tagged += 1
            locs = rec.get("locations") or []
            if locs:
                pinned += len(locs)
            if rec.get("program_tags") or locs:
                recent.append({
                    "record_key": key,
                    "program_tags": rec.get("program_tags") or [],
                    "locations": locs[:3],
                    "updated": rec.get("program_tag_updated") or rec.get("imported_at"),
                })
    recent.sort(key=lambda r: str(r.get("updated") or ""), reverse=True)

    return {
        "motto": _load_json(SEED, {}).get("motto") or "Obscure program tags — MKUltra, sub-projects, precise location pins.",
        "merge_only": True,
        "program_count": len(idx),
        "tagged_record_count": tagged,
        "pinned_location_count": pinned,
        "programs": list(idx.values()),
        "tree": program_tree(),
        "recent_tags": recent[:20],
        "updated": _now(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "get" and len(sys.argv) >= 3:
        row = get_program(sys.argv[2])
        print(json.dumps(row or {"error": "not_found"}, ensure_ascii=False))
        return 0 if row else 1
    if cmd == "list":
        query = None
        parent = None
        for arg in sys.argv[2:]:
            if arg.startswith("--q="):
                query = arg.split("=", 1)[1]
            if arg.startswith("--parent="):
                parent = arg.split("=", 1)[1]
        print(json.dumps({"programs": list_programs(parent, query)}, ensure_ascii=False))
        return 0
    if cmd == "apply-json" and len(sys.argv) >= 3:
        doc = json.loads(sys.argv[2] if sys.argv[2] != "-" else sys.stdin.read())
        if doc.get("record_key"):
            result = apply_tags_to_record(
                str(doc.get("record_key")),
                doc.get("tag_ids") or doc.get("tags"),
                doc.get("location"),
                str(doc.get("notes") or ""),
            )
        else:
            result = tag_location(
                doc.get("tag_ids") or doc.get("tags"),
                doc.get("lat"),
                doc.get("lon"),
                str(doc.get("coords") or ""),
                str(doc.get("place") or ""),
                str(doc.get("address") or ""),
                str(doc.get("city") or ""),
                str(doc.get("country") or ""),
                str(doc.get("label") or ""),
                str(doc.get("notes") or ""),
                str(doc.get("record_key") or ""),
            )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    print(json.dumps({"error": "usage: program-tags-db.py [json|list|get ID|apply-json DOC]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())