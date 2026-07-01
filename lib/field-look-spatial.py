#!/usr/bin/env python3
"""Look spatial pairing — different views per place; alarm same view at multiple locations."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-look-spatial-doctrine.json"
REGISTRY = STATE / "field-look-spatial-registry.json"
PANEL = STATE / "field-look-spatial-panel.json"
ALARMS = STATE / "field-look-spatial-alarms.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _append_alarm(row: dict[str, Any]) -> None:
    try:
        with ALARMS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _import_mod(rel: str, name: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _empty_registry() -> dict[str, Any]:
    return {
        "schema": "field-look-spatial-registry/v1",
        "views": {},
        "locations": {},
        "pairs": [],
        "updated": _now(),
    }


def location_id(feed_id: str, meta: dict[str, Any] | None = None) -> str:
    """Stable place key — feed/label plus optional explicit location receipt."""
    meta = meta or {}
    explicit = str(meta.get("location") or meta.get("place_id") or meta.get("window") or "").strip()
    if explicit:
        return f"{feed_id}@{explicit}"
    lat = meta.get("lat")
    lon = meta.get("lon")
    if lat is not None and lon is not None:
        return f"{feed_id}@{lat},{lon}"
    return str(feed_id or "unknown")


def register_look(
    *,
    view_sha256: str,
    feed_id: str,
    location: str | None = None,
    meta: dict[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Record view at location — alarm if same view already seen elsewhere."""
    loc = location or location_id(feed_id, meta)
    view_sha256 = str(view_sha256 or "").strip()
    if not view_sha256:
        return {"ok": False, "error": "missing_view_hash"}

    reg = _load(REGISTRY, _empty_registry())
    reg.setdefault("views", {})
    reg.setdefault("locations", {})
    reg.setdefault("pairs", [])

    view_row = reg["views"].setdefault(view_sha256, {
        "locations": [],
        "feeds": [],
        "first_seen": captured_at or _now(),
        "last_seen": captured_at or _now(),
    })
    locs: list[str] = list(view_row.get("locations") or [])
    feeds: list[str] = list(view_row.get("feeds") or [])

    alarm: dict[str, Any] | None = None
    if loc not in locs:
        other_locs = [x for x in locs if x != loc]
        if other_locs:
            doc = _load(DOCTRINE, {})
            alarm = {
                "schema": "field-look-spatial-alarm/v1",
                "ok": False,
                "alarm": True,
                "id": (doc.get("alarm") or {}).get("id") or "same_view_multi_location",
                "severity": (doc.get("alarm") or {}).get("severity") or "high",
                "view_sha256": view_sha256,
                "location": loc,
                "other_locations": other_locs,
                "feeds": sorted(set(feeds + [feed_id])),
                "citation": (doc.get("alarm") or {}).get("citation"),
                "statement": (doc.get("alarm") or {}).get("statement"),
                "ts": _now(),
            }
            _append_alarm(alarm)
            _notify_alarm(alarm)
        locs.append(loc)
    if feed_id not in feeds:
        feeds.append(feed_id)

    view_row["locations"] = locs
    view_row["feeds"] = feeds
    view_row["last_seen"] = captured_at or _now()

    loc_row = reg["locations"].setdefault(loc, {
        "feed_id": feed_id,
        "views": [],
        "last_view_sha256": view_sha256,
        "updated": captured_at or _now(),
    })
    loc_views: list[str] = list(loc_row.get("views") or [])
    if view_sha256 not in loc_views:
        loc_views.append(view_sha256)
    loc_row["views"] = loc_views[-32:]
    loc_row["last_view_sha256"] = view_sha256
    loc_row["updated"] = captured_at or _now()

    reg["updated"] = _now()
    _save(REGISTRY, reg)

    out: dict[str, Any] = {
        "ok": True,
        "view_sha256": view_sha256,
        "location": loc,
        "feed_id": feed_id,
        "location_count": len(locs),
        "locations": locs,
    }
    if alarm:
        out["alarm"] = alarm
    return out


def pair_locations(
    location_a: str,
    location_b: str,
    *,
    note: str = "",
) -> dict[str, Any]:
    """Pair two places — they should show different looks, not the same view."""
    a, b = str(location_a).strip(), str(location_b).strip()
    if not a or not b or a == b:
        return {"ok": False, "error": "need_two_distinct_locations"}
    reg = _load(REGISTRY, _empty_registry())
    pairs: list[dict[str, Any]] = list(reg.get("pairs") or [])
    key = tuple(sorted((a, b)))
    for row in pairs:
        if tuple(sorted((row.get("a"), row.get("b")))) == key:
            return {"ok": True, "paired": True, "existing": True, "a": a, "b": b}
    pairs.append({"a": a, "b": b, "note": note, "paired_at": _now(), "expect": "different_views"})
    reg["pairs"] = pairs
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    return {"ok": True, "paired": True, "a": a, "b": b, "expect": "different_views"}


def pair_looks(
    feed_a: str,
    feed_b: str,
    *,
    note: str = "",
    meta_a: dict[str, Any] | None = None,
    meta_b: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pair different look lanes — alias for pair_locations on feed ids."""
    return pair_locations(
        location_id(feed_a, meta_a),
        location_id(feed_b, meta_b),
        note=note or f"pair {feed_a} + {feed_b}",
    )


def _notify_alarm(alarm: dict[str, Any]) -> None:
    noti = _import_mod("noti.py", "field_look_spatial_noti")
    if noti and hasattr(noti, "post_message"):
        try:
            locs = ", ".join(alarm.get("other_locations") or [])
            noti.post_message(
                "hostess7",
                person="Final_Eye",
                text=(
                    f"SPATIAL LOOK ALARM: same view at multiple locations "
                    f"({locs} + {alarm.get('location')}). "
                    f"{(alarm.get('statement') or '')[:120]}"
                ),
            )
        except Exception:
            pass
    spatial = _import_mod("ironclad-spatial-existence.py", "field_look_spatial_ic")
    if spatial and hasattr(spatial, "_append_ledger"):
        try:
            spatial._append_ledger({
                "ts": _now(),
                "kind": "look_duplicate_view",
                "alarm": alarm,
            })
        except Exception:
            pass


def ingest_capture(
    feed_id: str,
    image: bytes,
    *,
    meta: dict[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Hook for H7s feed append / zocr write_capture."""
    if not image:
        return {"ok": False, "error": "no_image"}
    digest = _sha256(image)
    return register_look(
        view_sha256=digest,
        feed_id=feed_id,
        meta=meta,
        captured_at=captured_at,
    )


def scan_bundle() -> dict[str, Any]:
    """Scan field-desktop.h7s — alarm feeds sharing the same live view hash."""
    bmod = _import_mod("field-h7s-desktop-bundle.py", "field_look_spatial_bundle")
    if not bmod:
        return {"ok": False, "error": "bundle_module_missing"}
    bp = STATE / "field-desktop.h7s"
    if not bp.is_file():
        return {"ok": True, "live": False, "alarms": []}
    manifest = bmod.read_manifest(bp)
    by_view: dict[str, list[str]] = {}
    for fid, ref in (manifest.get("ocr") or {}).items():
        norm = bmod._normalize_feed_ref(ref) if hasattr(bmod, "_normalize_feed_ref") else ref
        stamp = norm.get("live_feed") or norm.get("last_image") or {}
        digest = str(stamp.get("sha256") or "")
        if digest:
            by_view.setdefault(digest, []).append(str(fid))
    alarms: list[dict[str, Any]] = []
    for digest, feeds in by_view.items():
        if len(feeds) < 2:
            continue
        for fid in feeds:
            hit = register_look(
                view_sha256=digest,
                feed_id=fid,
                location=fid,
                captured_at=str((manifest.get("ocr") or {}).get(fid, {}).get("last_seen") or _now()),
            )
            if hit.get("alarm"):
                alarms.append(hit["alarm"])
    return {
        "ok": True,
        "live": True,
        "feed_count": len(manifest.get("ocr") or {}),
        "duplicate_views": {d: f for d, f in by_view.items() if len(f) > 1},
        "alarms": alarms,
        "alarm_count": len(alarms),
    }


def status() -> dict[str, Any]:
    reg = _load(REGISTRY, _empty_registry())
    multi = [
        {"view_sha256": k[:16], "locations": v.get("locations"), "feeds": v.get("feeds")}
        for k, v in (reg.get("views") or {}).items()
        if len(v.get("locations") or []) > 1
    ]
    recent_alarms: list[dict[str, Any]] = []
    if ALARMS.is_file():
        try:
            for line in ALARMS.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]:
                if line.strip():
                    recent_alarms.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    doc = {
        "schema": "field-look-spatial-panel/v1",
        "ok": True,
        "registry": str(REGISTRY),
        "view_count": len(reg.get("views") or {}),
        "location_count": len(reg.get("locations") or {}),
        "pair_count": len(reg.get("pairs") or []),
        "multi_location_views": multi,
        "recent_alarms": recent_alarms,
        "pairs": reg.get("pairs") or [],
        "updated": reg.get("updated"),
    }
    _save(PANEL, doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "status").lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_bundle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pair" and len(args) >= 3:
        print(json.dumps(pair_looks(args[1], args[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "register" and len(args) >= 3:
        img = Path(args[3]).read_bytes() if len(args) >= 4 and Path(args[3]).is_file() else b""
        if not img:
            print(json.dumps({"ok": False, "error": "image_path_required"}, indent=2))
            return 1
        print(json.dumps(ingest_capture(args[1], img, meta={"location": args[2]}), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["status", "scan", "pair FEED_A FEED_B", "register FEED_ID LOCATION IMAGE"],
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())