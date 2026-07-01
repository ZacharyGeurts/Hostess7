#!/usr/bin/env pythong
"""Persistent existence identity table — every entity with existence, OCR & vision corroboration."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
REGISTRY_JSON = STATE / "existence-identity-registry.json"
REGISTRY_LEDGER = STATE / "existence-identity.jsonl"
UNIVERSAL_REGISTRY = STATE / "universal-field-registry.json"
PANEL_CACHE = STATE / "existence-identity-panel.json"

VISION_CORPUS_PATHS = (
    HOSTESS7_TEAM_FIELD / "brain" / "vision" / "corpus.json",
    HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "vision" / "corpus.json",
    STATE / "field-storage" / "brain" / "vision" / "corpus.json",
)

SECTION_VISION_TAGS: dict[str, list[str]] = {
    "home": ["vision", "perception", "viewport", "4k"],
    "internet": ["ocr", "text", "screen", "network"],
    "mobile": ["motion", "track", "vision", "camera"],
    "battery": ["action", "power", "energy", "flow"],
    "thermal": ["heat", "energy", "physics", "casimir", "temperature", "ocr"],
}

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        REGISTRY_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRY_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _existence_id(section: str, entity_key: str) -> str:
    blob = f"{section}:{entity_key}".encode("utf-8")
    return "ex_" + hashlib.sha256(blob).hexdigest()[:20]


def _ocr_toolkit() -> dict[str, Any]:
    tess = None
    for candidate in ("tesseract", "/usr/bin/tesseract"):
        try:
            proc = subprocess.run([candidate, "--version"], capture_output=True, timeout=4)
            if proc.returncode == 0:
                tess = candidate
                break
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError):
            continue
    out: dict[str, Any] = {
        "engine": "tesseract" if tess else None,
        "available": bool(tess),
        "vision_pipeline": ["capture", "preprocess", "ocr", "existence_corroborate"],
        "sources": ["field-toolkit", "capture-field-fast"],
    }
    if tess:
        try:
            proc = subprocess.run([tess, "--list-langs"], capture_output=True, text=True, timeout=4)
            langs = [ln.strip() for ln in (proc.stdout or "").splitlines()[1:] if ln.strip()]
            out["languages"] = langs[:12]
        except (OSError, subprocess.TimeoutExpired):
            out["languages"] = ["eng"]
    return out


def _vision_corpus() -> dict[str, Any]:
    for path in VISION_CORPUS_PATHS:
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            domains = doc.get("domains") or []
            return {
                "source": str(path),
                "version": doc.get("version"),
                "domain_count": len(domains),
                "domains": [
                    {
                        "id": d.get("id"),
                        "title": d.get("title"),
                        "tags": d.get("tags") or [],
                        "excerpt": (d.get("body") or "")[:240],
                    }
                    for d in domains
                    if isinstance(d, dict)
                ],
                "mounted": HOSTESS7_TEAM_FIELD.is_dir(),
            }
        except (OSError, json.JSONDecodeError):
            continue
    return {"source": None, "domain_count": 0, "domains": [], "mounted": HOSTESS7_TEAM_FIELD.is_dir()}


def _match_vision_domains(section: str, entity: dict[str, Any], corpus: dict[str, Any]) -> list[str]:
    tags = list(SECTION_VISION_TAGS.get(section) or [])
    label = str(entity.get("label") or "").lower()
    kind = str(entity.get("kind") or "").lower()
    if entity.get("moving"):
        tags.extend(["motion", "track"])
    if entity.get("ip"):
        tags.append("network")
    if "battery" in kind or section == "battery":
        tags.extend(["power", "energy"])
    matched: list[str] = []
    for dom in corpus.get("domains") or []:
        dom_tags = [str(t).lower() for t in (dom.get("tags") or [])]
        if any(t in dom_tags for t in tags):
            matched.append(str(dom.get("id") or dom.get("title") or ""))
        elif any(t in label for t in dom_tags):
            matched.append(str(dom.get("id") or ""))
    return list(dict.fromkeys(m for m in matched if m))[:6]


def _identity_for_entity(section: str, entity: dict[str, Any]) -> dict[str, Any]:
    ip = str(entity.get("ip") or "")
    if not ip and section == "internet":
        ip = str(entity.get("id") or "").replace("inet:", "")
    fp: dict[str, Any] = {}
    if ip and IPV4_RE.match(ip):
        try:
            hi = _mod("host_identity", "host-identity.py")
            fp = hi.fingerprint_from_point_or_dossier(ip, entity)
        except Exception:
            fp = {}
    markers = fp.get("markers") or {}
    return {
        "identity_hash": fp.get("identity_hash") or "",
        "marker_count": fp.get("marker_count") or len(markers),
        "markers": markers,
        "ip": ip or None,
    }


def _entity_row(section: str, entity: dict[str, Any], corpus: dict[str, Any], ocr: dict[str, Any]) -> dict[str, Any]:
    entity_key = str(entity.get("id") or entity.get("ip") or f"{section}_{hash(str(entity))}")
    eid = _existence_id(section, entity_key)
    identity = _identity_for_entity(section, entity)
    vision_domains = _match_vision_domains(section, entity, corpus)
    placed = bool(entity.get("placed"))
    exists = True
    ocr_ok = bool(ocr.get("available") and (placed or identity.get("identity_hash")))
    return {
        "existence_id": eid,
        "entity_key": entity_key,
        "section": section,
        "exists": exists,
        "placed": placed,
        "kind": entity.get("kind") or section,
        "label": entity.get("label") or entity_key,
        "address": entity.get("address") or "",
        "ip": entity.get("ip") or identity.get("ip"),
        "mac": entity.get("mac") or entity.get("bssid") or "",
        "vendor": entity.get("vendor") or entity.get("org") or "",
        "lat": entity.get("lat"),
        "lon": entity.get("lon"),
        "moving": bool(entity.get("moving")),
        "sources": entity.get("sources") or [entity.get("source") or "unknown"],
        "identity_hash": identity.get("identity_hash") or "",
        "marker_count": identity.get("marker_count") or 0,
        "vision_domains": vision_domains,
        "vision_corroborated": len(vision_domains) > 0,
        "ocr_corroborated": ocr_ok,
        "existence_score": round(
            (40 if exists else 0)
            + (20 if placed else 0)
            + (15 if identity.get("identity_hash") else 0)
            + (10 if vision_domains else 0)
            + (10 if ocr_ok else 0)
            + (5 if entity.get("moving") else 0),
            1,
        ),
        "first_seen": _now(),
        "last_seen": _now(),
        "sightings": 1,
    }


def _harvest_entities(registry: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for row in registry.get("homes") or []:
        if isinstance(row, dict):
            out.append(("home", row))
    for row in registry.get("internet") or []:
        if isinstance(row, dict):
            out.append(("internet", row))
    for row in registry.get("mobile") or []:
        if isinstance(row, dict):
            out.append(("mobile", row))
    for row in registry.get("batteries") or []:
        if isinstance(row, dict):
            out.append(("battery", row))
    return out


def build_existence_registry(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    if registry is None:
        registry = _load_json(UNIVERSAL_REGISTRY, {})
    if not registry.get("homes") and not registry.get("internet"):
        try:
            sw = _mod("terror_spiderweb", "terror-spiderweb.py")
            built = sw.build_spiderweb()
            registry = built.get("registry") or registry
        except Exception:
            pass

    prev = _load_json(REGISTRY_JSON, {"entities": {}, "updated": None})
    prev_entities: dict[str, dict[str, Any]] = dict(prev.get("entities") or {})
    corpus = _vision_corpus()
    ocr = _ocr_toolkit()
    current_keys: set[str] = set()
    entities: list[dict[str, Any]] = []

    for section, entity in _harvest_entities(registry):
        row = _entity_row(section, entity, corpus, ocr)
        eid = row["existence_id"]
        current_keys.add(eid)
        prev_row = prev_entities.get(eid)
        if prev_row:
            row["first_seen"] = prev_row.get("first_seen") or row["first_seen"]
            row["sightings"] = int(prev_row.get("sightings") or 0) + 1
            if not row["identity_hash"] and prev_row.get("identity_hash"):
                row["identity_hash"] = prev_row["identity_hash"]
        entities.append(row)
        if not prev_row or prev_row.get("last_seen") != row["last_seen"]:
            _append_ledger({
                "ts": _now(),
                "event": "sighting",
                "existence_id": eid,
                "section": section,
                "entity_key": row["entity_key"],
                "exists": True,
                "existence_score": row["existence_score"],
            })

    for eid, prev_row in prev_entities.items():
        if eid in current_keys:
            continue
        stale = dict(prev_row)
        stale["exists"] = False
        stale["last_seen"] = _now()
        stale["existence_score"] = max(0.0, float(prev_row.get("existence_score") or 0) - 25)
        entities.append(stale)
        _append_ledger({
            "ts": _now(),
            "event": "absence",
            "existence_id": eid,
            "section": prev_row.get("section"),
            "entity_key": prev_row.get("entity_key"),
            "exists": False,
        })

    entities.sort(key=lambda r: (-float(r.get("existence_score") or 0), str(r.get("label") or "")))
    entity_index = {r["existence_id"]: r for r in entities}

    stats = {
        "total": len(entities),
        "existing": sum(1 for r in entities if r.get("exists")),
        "absent": sum(1 for r in entities if not r.get("exists")),
        "placed": sum(1 for r in entities if r.get("exists") and r.get("placed")),
        "vision_corroborated": sum(1 for r in entities if r.get("vision_corroborated")),
        "ocr_corroborated": sum(1 for r in entities if r.get("ocr_corroborated")),
        "with_identity_hash": sum(1 for r in entities if r.get("identity_hash")),
        "homes": sum(1 for r in entities if r.get("section") == "home" and r.get("exists")),
        "internet": sum(1 for r in entities if r.get("section") == "internet" and r.get("exists")),
        "mobile": sum(1 for r in entities if r.get("section") == "mobile" and r.get("exists")),
        "battery": sum(1 for r in entities if r.get("section") == "battery" and r.get("exists")),
    }

    doc = {
        "schema": "existence-identity-registry/v1",
        "updated": _now(),
        "motto": "Persistent identity for everything with existence — OCR, vision, and field corroboration.",
        "toolkit": {
            "ocr": ocr,
            "vision": {
                "corpus_source": corpus.get("source"),
                "domain_count": corpus.get("domain_count", 0),
                "h7_team_mounted": corpus.get("mounted"),
                "pipeline": ["capture", "preprocess", "feature_extract", "identity_match", "existence_score"],
            },
        },
        "entities": entity_index,
        "table": entities,
        "stats": stats,
    }
    _save_json(REGISTRY_JSON, doc)
    return doc


def panel_json() -> dict[str, Any]:
    doc = build_existence_registry()
    _save_json(PANEL_CACHE, doc)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        doc = build_existence_registry()
        _save_json(PANEL_CACHE, doc)
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    if cmd == "table":
        doc = build_existence_registry()
        print(json.dumps({"table": doc.get("table") or [], "stats": doc.get("stats") or {}}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: existence-identity.py [json|build|table]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())