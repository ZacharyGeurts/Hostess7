#!/usr/bin/env pythong
"""Government / law / police informational database import — merge-only dossier updates.

Never deletes existing dossier fields or records. CSV, TSV, JSON, NDJSON, ICS-205, XML.
Images stored on field drive and linked into dossier records.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
GOV_DOSSIERS = STATE / "gov-dossiers.json"
HUMAN_OVERRIDES = STATE / "human-dossier-overrides.json"
IMAGES_DIR = STATE / "gov-intel-images"
IMPORTS_DIR = STATE / "gov-intel-imports"
USER_DB = STATE / "police-agencies-user.json"

IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]+$")
IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"})


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


def _record_key(row: dict[str, Any], agency_id: str) -> str:
    for field in ("ip", "IP", "ori", "ORI", "id", "record_id", "uuid", "ncic", "badge_id"):
        val = str(row.get(field) or "").strip()
        if val:
            return f"{agency_id}:{field.lower()}:{val.lower()}"
    if row.get("name") and row.get("agency"):
        blob = f"{row.get('agency')}|{row.get('name')}".lower()
        return f"{agency_id}:name:{hashlib.sha256(blob.encode()).hexdigest()[:16]}"
    digest = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()[:20]
    return f"{agency_id}:hash:{digest}"


def _detect_ext(filename: str, fmt_ext: str | None) -> str:
    if fmt_ext:
        return fmt_ext.lower().lstrip(".")
    suf = Path(filename or "").suffix.lower().lstrip(".")
    if suf:
        return suf
    return "csv"


def _parse_tsv(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [dict(row) for row in reader]


def _parse_csv(text: str) -> list[dict[str, str]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _parse_ndjson(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _parse_ics205(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\t|,|;", line)
        if len(parts) < 4:
            continue
        rows.append({
            "channel": parts[0].strip(),
            "function": parts[1].strip() if len(parts) > 1 else "",
            "rx_freq": parts[2].strip() if len(parts) > 2 else "",
            "tx_freq": parts[3].strip() if len(parts) > 3 else "",
            "mode": parts[4].strip() if len(parts) > 4 else "",
            "remarks": parts[5].strip() if len(parts) > 5 else "",
        })
    return rows


def _parse_xml(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return rows
    for child in root:
        if len(child) == 0 and (child.text or "").strip():
            rows.append({root.tag: child.text.strip()})
            continue
        row: dict[str, Any] = {}
        for sub in child:
            key = sub.tag.split("}")[-1]
            row[key] = (sub.text or "").strip()
        if row:
            rows.append(row)
    if not rows and root.tag:
        flat = {c.tag.split("}")[-1]: (c.text or "").strip() for c in root}
        if flat:
            rows.append(flat)
    return rows


def parse_payload(payload: str, ext: str) -> list[dict[str, Any]]:
    ext = (ext or "csv").lower()
    if ext in ("json",):
        doc = json.loads(payload)
        return doc if isinstance(doc, list) else [doc]
    if ext in ("ndjson", "jsonl"):
        return _parse_ndjson(payload)
    if ext == "tsv":
        return _parse_tsv(payload)
    if ext == "ics205":
        return _parse_ics205(payload)
    if ext == "xml":
        return _parse_xml(payload)
    if ext == "csv":
        return _parse_csv(payload)
    # auto: try json then csv
    try:
        doc = json.loads(payload)
        return doc if isinstance(doc, list) else [doc]
    except json.JSONDecodeError:
        return _parse_csv(payload)


def _store_image(record_key: str, filename: str, data_b64: str, caption: str = "") -> dict[str, Any] | None:
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except (ValueError, TypeError):
        return None
    if len(raw) > 8_000_000:
        return None
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename or "image")[:80]
    ext = Path(safe).suffix.lower()
    if ext not in IMAGE_EXTS:
        ext = ".jpg"
        safe = f"{safe}{ext}" if not safe.lower().endswith(ext) else safe
    key_slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", record_key)[:120]
    dest_dir = IMAGES_DIR / key_slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()[:12]
    out_name = f"{digest}_{safe}" if not safe.startswith(digest) else safe
    out_path = dest_dir / out_name
    if not out_path.is_file():
        out_path.write_bytes(raw)
    rel = str(out_path.relative_to(STATE))
    return {
        "path": str(out_path),
        "relative": rel,
        "url": f"/api/gov-intel/image?path={rel}",
        "filename": filename or out_name,
        "caption": caption,
        "size": len(raw),
        "imported_at": _now(),
    }


def _human_ip_from_row(row: dict[str, Any]) -> str | None:
    for field in ("ip", "IP", "remote_ip", "c2_ip", "target_ip"):
        val = str(row.get(field) or "").strip()
        if val and IP_RE.match(val):
            return val
    return None


def _merge_human_dossier(ip: str, row: dict[str, Any], agency_id: str, format_id: str) -> bool:
    overrides = _load_json(HUMAN_OVERRIDES, {"ips": {}, "updated": None})
    ips = overrides.get("ips") or {}
    if not isinstance(ips, dict):
        ips = {}
    existing = dict(ips.get(ip) or {})
    patch: dict[str, Any] = {
        "ip": ip,
        "gov_intel": True,
        "gov_agency_id": agency_id,
        "gov_format_id": format_id,
        "gov_updated_at": _now(),
    }
    for src, dst in (
        ("notes", "notes"), ("remarks", "notes"), ("description", "notes"),
        ("malware", "associated_malware"), ("associated_malware", "associated_malware"),
        ("asn", "asn_org"), ("asn_org", "asn_org"),
        ("city", "geo"), ("country", "geo"), ("lat", "geo"), ("lon", "geo"),
        ("last_seen", "last_seen"), ("first_seen", "first_seen"),
        ("hosting", "hosting_likelihood"), ("hosting_likelihood", "hosting_likelihood"),
    ):
        val = row.get(src)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        if dst == "geo":
            geo = dict(existing.get("geo") or {})
            if src == "city":
                geo["city"] = val
            elif src == "country":
                geo["country_code"] = str(val)[:2].upper()
            elif src in ("lat", "lon"):
                try:
                    geo[src] = float(val)
                except (TypeError, ValueError):
                    pass
            patch["geo"] = geo
        elif dst == "notes":
            note = str(val).strip()
            prev = str(existing.get("notes") or "").strip()
            patch["notes"] = f"{prev}\n[Gov import {agency_id}] {note}".strip() if prev else f"[Gov import {agency_id}] {note}"
        else:
            patch[dst] = val
    merged = _merge_value(existing, patch)
    merged["ip"] = ip
    ips[ip] = merged
    overrides["ips"] = ips
    overrides["updated"] = _now()
    _save_json(HUMAN_OVERRIDES, overrides)

    # Also merge into live human-dossier.json if present
    hd_path = STATE / "human-dossier.json"
    if hd_path.is_file():
        doc = _load_json(hd_path, {})
        rows = list(doc.get("ips") or [])
        idx = next((i for i, r in enumerate(rows) if str(r.get("ip")) == ip), None)
        if idx is not None:
            rows[idx] = _merge_value(rows[idx], merged)
        else:
            rows.append(merged)
        doc["ips"] = rows
        doc["ip_count"] = len(rows)
        doc["gov_merge_updated"] = _now()
        _save_json(hd_path, doc)
    return True


def import_and_merge(
    agency_id: str,
    format_id: str,
    payload: str,
    filename: str = "",
    fmt_ext: str | None = None,
    images: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ext = _detect_ext(filename, fmt_ext)
    try:
        parsed = parse_payload(payload, ext)
    except (json.JSONDecodeError, ET.ParseError, ValueError) as exc:
        return {"ok": False, "error": f"parse_failed: {exc}"}

    if not parsed:
        return {"ok": False, "error": "empty_import"}

    gdoc = _load_json(GOV_DOSSIERS, {"records": {}, "import_log": [], "updated": None})
    records: dict[str, Any] = gdoc.get("records") or {}
    if not isinstance(records, dict):
        records = {}

    merged_count = 0
    created_count = 0
    human_merged = 0
    image_count = 0
    sample_rows: list[dict[str, Any]] = []

    img_queue = list(images or [])
    if _SOVEREIGN_CLOCK_MOD is None:
        _now()
    stamp = _SOVEREIGN_CLOCK_MOD.utc_compact()

    for row in parsed[:2000]:
        if not isinstance(row, dict):
            continue
        key = _record_key(row, agency_id)
        existed = key in records
        existing = dict(records.get(key) or {})
        incoming = {
            "record_key": key,
            "agency_id": agency_id,
            "format_id": format_id,
            "source_filename": filename,
            "imported_at": _now(),
            "fields": dict(row),
            "images": list(existing.get("images") or []),
            "import_history": list(existing.get("import_history") or []),
        }
        incoming["import_history"].append({
            "at": _now(),
            "format_id": format_id,
            "filename": filename,
            "field_count": len(row),
        })
        incoming["import_history"] = incoming["import_history"][-50:]

        merged = _merge_value(existing, incoming)
        try:
            import importlib.util
            pt_spec = importlib.util.spec_from_file_location(
                "program_tags_db", INSTALL / "lib" / "program-tags-db.py"
            )
            pt_mod = importlib.util.module_from_spec(pt_spec)
            pt_spec.loader.exec_module(pt_mod)
            merged = pt_mod.apply_row_tags(merged, row)
        except Exception:
            pass
        records[key] = merged
        if existed:
            merged_count += 1
        else:
            created_count += 1
        if len(sample_rows) < 8:
            sample_rows.append({"key": key, "fields": row})

        ip = _human_ip_from_row(row)
        if ip:
            _merge_human_dossier(ip, row, agency_id, format_id)
            human_merged += 1

        # Attach images tagged for this row or global queue
        row_images = [im for im in img_queue if im.get("record_key") in (key, row.get("id"), row.get("ip"))]
        if not row_images and img_queue and len(parsed) == 1:
            row_images = img_queue[:]
        for im in row_images:
            meta = _store_image(
                key,
                str(im.get("filename") or "image.jpg"),
                str(im.get("data_b64") or im.get("data") or ""),
                str(im.get("caption") or ""),
            )
            if meta:
                merged_imgs = list(records[key].get("images") or [])
                paths = {x.get("path") for x in merged_imgs}
                if meta["path"] not in paths:
                    merged_imgs.append(meta)
                    records[key]["images"] = merged_imgs
                    image_count += 1

    gdoc["records"] = records
    gdoc["record_count"] = len(records)
    gdoc["updated"] = _now()
    log = list(gdoc.get("import_log") or [])
    log.append({
        "agency_id": agency_id,
        "format_id": format_id,
        "filename": filename,
        "row_count": len(parsed),
        "merged": merged_count,
        "created": created_count,
        "human_merged": human_merged,
        "images": image_count,
        "imported_at": _now(),
    })
    gdoc["import_log"] = log[-300:]
    _save_json(GOV_DOSSIERS, gdoc)

    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    import_path = IMPORTS_DIR / f"{agency_id}__{format_id}__{stamp}.json"
    _save_json(import_path, {
        "agency_id": agency_id,
        "format_id": format_id,
        "filename": filename,
        "row_count": len(parsed),
        "merged": merged_count,
        "created": created_count,
        "human_merged": human_merged,
        "images": image_count,
        "rows": parsed[:500],
        "imported_at": _now(),
    })

    udoc = _load_json(USER_DB, {"imports": [], "custom_agencies": [], "updated": None})
    imports = list(udoc.get("imports") or [])
    imports.append({
        "agency_id": agency_id,
        "format_id": format_id,
        "path": str(import_path),
        "row_count": len(parsed),
        "merged": merged_count,
        "created": created_count,
        "human_merged": human_merged,
        "images": image_count,
        "imported_at": _now(),
        "filename": filename,
        "merge_only": True,
    })
    udoc["imports"] = imports[-200:]
    udoc["updated"] = _now()
    _save_json(USER_DB, udoc)

    return {
        "ok": True,
        "merge_only": True,
        "agency_id": agency_id,
        "format_id": format_id,
        "row_count": len(parsed),
        "merged": merged_count,
        "created": created_count,
        "human_merged": human_merged,
        "images_stored": image_count,
        "record_count": len(records),
        "path": str(import_path),
        "sample_rows": sample_rows,
        "reload_panel": True,
    }


def panel_json() -> dict[str, Any]:
    gdoc = _load_json(GOV_DOSSIERS, {"records": {}, "import_log": []})
    overrides = _load_json(HUMAN_OVERRIDES, {"ips": {}})
    records = gdoc.get("records") or {}
    recent = list((gdoc.get("import_log") or [])[-15:])
    return {
        "motto": "Government · law · intelligence databases — merge-only dossier updates, never harm existing data.",
        "merge_only": True,
        "record_count": len(records) if isinstance(records, dict) else 0,
        "human_override_count": len((overrides.get("ips") or {})),
        "import_log": recent,
        "supported_formats": ["csv", "tsv", "json", "ndjson", "jsonl", "ics205", "xml"],
        "image_formats": sorted(IMAGE_EXTS),
        "updated": gdoc.get("updated") or _now(),
    }


def get_image(rel_path: str) -> tuple[bytes, str] | None:
    rel = rel_path.lstrip("/")
    images_root = IMAGES_DIR.resolve()
    try:
        candidate = (STATE / rel).resolve()
        candidate.relative_to(images_root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    ext = candidate.suffix.lower()
    ctype = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }.get(ext, "application/octet-stream")
    return candidate.read_bytes(), ctype


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "import-json" and len(sys.argv) >= 3:
        doc = json.loads(sys.argv[2] if sys.argv[2] != "-" else sys.stdin.read())
        result = import_and_merge(
            str(doc.get("agency_id") or ""),
            str(doc.get("format_id") or ""),
            str(doc.get("payload") or doc.get("data") or ""),
            str(doc.get("filename") or ""),
            doc.get("fmt_ext"),
            doc.get("images"),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    print(json.dumps({"error": "usage: gov-intel-db.py [json|import-json DOC]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())