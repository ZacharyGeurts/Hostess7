#!/usr/bin/env python3
"""H7s desktop condenser — deduped blobs + unchanged timestamps; Hostess 7 fast slice read."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import mimetypes
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL / "Queen"))
DOCTRINE = INSTALL / "data" / "field-h7s-desktop-doctrine.json"
BUNDLE_PATH = STATE / "field-desktop.h7s"
MANIFEST_SLICE = "manifest"
SCHEMA = "field-h7s-desktop-condenser/v1"
INNER_KIND = "desktop_condenser"
ICON_EXTS = {".png", ".svg", ".xpm", ".jpg", ".jpeg", ".webp", ".ico"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
TEXT_EXTS = {".txt", ".h7", ".md", ".json"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _elapsed_sec(since_iso: str, until_iso: str | None = None) -> float:
    try:
        since = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        until = datetime.fromisoformat((until_iso or _now()).replace("Z", "+00:00"))
        return max(0.0, (until - since).total_seconds())
    except (ValueError, TypeError):
        return 0.0


def _empty_manifest() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "inner_kind": INNER_KIND,
        "blobs": {},
        "icons": {},
        "ocr": {},
        "updated": _now(),
    }


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


def _import_h7s() -> Any:
    path = INSTALL / "lib" / "field-h7s-format.py"
    spec = importlib.util.spec_from_file_location("field_h7s_desktop", path)
    if not spec or not spec.loader:
        raise ImportError("field-h7s-format.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_progress() -> Any | None:
    path = INSTALL / "lib" / "field-compression-progress.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_compression_progress_desktop", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bundle_path() -> Path:
    doc = _load(DOCTRINE, {})
    rel = str(doc.get("bundle_path") or "field-desktop.h7s")
    if rel.startswith("/"):
        return Path(rel)
    return STATE / rel


def _final_eye_root() -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        sys.path.insert(0, str(INSTALL / "lib"))
        from sg_paths import final_eye_root
        return final_eye_root()
    except Exception:
        return (INSTALL / "Final_Eye").resolve()


def _library_entries() -> dict[str, Any]:
    lib_path = STATE / "queen-program-library.json"
    doc = _load(lib_path, {})
    if not doc.get("entries"):
        qpl = QUEEN / "lib" / "queen-program-library.py"
        if qpl.is_file():
            spec = importlib.util.spec_from_file_location("queen_program_library_desktop", qpl)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "build_library"):
                    built = mod.build_library()
                    return built.get("entries") or {}
    return doc.get("entries") or {}


def _read_manifest_from_bundle(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty_manifest()
    h7s = _import_h7s()
    try:
        blob = path.read_bytes()
        if not h7s.is_h7s_blob(blob):
            return _empty_manifest()
    except OSError:
        return _empty_manifest()
    try:
        raw, _ = h7s.read_slice_bytes(path, slot=0)
        doc = json.loads(raw.decode("utf-8"))
        if isinstance(doc, dict):
            doc.setdefault("blobs", {})
            doc.setdefault("icons", {})
            doc.setdefault("ocr", {})
            return doc
    except Exception:
        pass
    return _empty_manifest()


def _load_blob_bytes(path: Path, manifest: dict[str, Any]) -> dict[str, bytes]:
    """Load unique blob payloads once — keyed by sha256."""
    out: dict[str, bytes] = {}
    h7s = _import_h7s()
    for digest, meta in (manifest.get("blobs") or {}).items():
        slot = meta.get("slot")
        if slot is None:
            continue
        try:
            data, _ = h7s.read_slice_bytes(path, slot=int(slot))
            out[str(digest)] = data
        except Exception:
            continue
    return out


def _image_stamp(sha256: str, at: str) -> dict[str, str]:
    return {"sha256": sha256, "at": at}


def _ref_meta(old_ref: dict[str, Any] | None, digest: str, *, now: str) -> dict[str, Any]:
    """Icon ref — timestamps only when bytes unchanged (same sha256)."""
    if old_ref and str(old_ref.get("sha256") or "") == digest:
        since = str(old_ref.get("unchanged_since") or now)
        return {
            "sha256": digest,
            "unchanged_since": since,
            "last_verified": now,
            "unchanged_sec": round(_elapsed_sec(since, now), 1),
        }
    return {
        "sha256": digest,
        "unchanged_since": now,
        "last_verified": now,
        "unchanged_sec": 0.0,
    }


def _normalize_feed_ref(ref: dict[str, Any] | None) -> dict[str, Any]:
    """Upgrade legacy ocr refs to first_image + last_image + live_feed."""
    if not ref:
        return {}
    if ref.get("first_image") and ref.get("last_image"):
        out = dict(ref)
        if not out.get("live_feed"):
            out["live_feed"] = dict(out["last_image"])
        return out
    sha = str(ref.get("sha256") or "")
    at = str(ref.get("unchanged_since") or ref.get("last_verified") or _now())
    if not sha:
        return dict(ref)
    stamp = _image_stamp(sha, at)
    return {
        **ref,
        "first_image": stamp,
        "last_image": stamp,
        "live_feed": stamp,
        "first_seen": at,
        "last_seen": at,
    }


def _ocr_feed_meta(
    prev: dict[str, Any] | None,
    image_digest: str,
    *,
    now: str,
    captured_at: str | None = None,
    text_digest: str | None = None,
) -> dict[str, Any]:
    """Feed ref — first image frozen; last image / live_feed always current capture."""
    at = captured_at or now
    prev = _normalize_feed_ref(prev)
    if not prev:
        first = _image_stamp(image_digest, at)
        out: dict[str, Any] = {
            "first_image": first,
            "last_image": dict(first),
            "live_feed": dict(first),
            "first_seen": at,
            "last_seen": at,
            "unchanged_since": at,
            "last_verified": now,
            "unchanged_sec": 0.0,
        }
        if text_digest:
            out["text"] = _image_stamp(text_digest, at)
        return out

    first_image = dict(prev.get("first_image") or _image_stamp(image_digest, at))
    old_last_sha = str((prev.get("last_image") or {}).get("sha256") or "")
    if old_last_sha == image_digest:
        unchanged_since = str(prev.get("unchanged_since") or at)
        unchanged_sec = round(_elapsed_sec(unchanged_since, now), 1)
    else:
        unchanged_since = at
        unchanged_sec = 0.0

    last_image = _image_stamp(image_digest, at)
    out = {
        "first_image": first_image,
        "last_image": last_image,
        "live_feed": dict(last_image),
        "first_seen": str(prev.get("first_seen") or first_image.get("at") or at),
        "last_seen": at,
        "unchanged_since": unchanged_since,
        "last_verified": now,
        "unchanged_sec": unchanged_sec,
    }
    if text_digest:
        out["text"] = _image_stamp(text_digest, at)
    elif prev.get("text"):
        out["text"] = prev["text"]
    return out


def _blob_meta(
    old_blob: dict[str, Any] | None,
    digest: str,
    data: bytes,
    mime: str,
    *,
    now: str,
) -> dict[str, Any]:
    if old_blob and str(old_blob.get("sha256") or digest) == digest:
        since = str(old_blob.get("unchanged_since") or now)
        return {
            "sha256": digest,
            "bytes": len(data),
            "mime": mime,
            "unchanged_since": since,
            "last_verified": now,
            "unchanged_sec": round(_elapsed_sec(since, now), 1),
        }
    return {
        "sha256": digest,
        "bytes": len(data),
        "mime": mime,
        "unchanged_since": now,
        "last_verified": now,
        "unchanged_sec": 0.0,
    }


def _scan_icon_candidates(entries: dict[str, Any]) -> list[tuple[str, bytes, str]]:
    out: list[tuple[str, bytes, str]] = []
    for eid, row in entries.items():
        raw = row.get("icon_path") if row else None
        if not raw:
            continue
        path = Path(str(raw))
        if not path.is_file() or path.suffix.lower() not in ICON_EXTS:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        out.append((str(eid), data, mime))
    return out


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError:
        return None


def _scan_ocr_feeds() -> list[dict[str, Any]]:
    """Final Eye + desktop OCR — pair first/last image candidates per feed id."""
    feeds: dict[str, dict[str, Any]] = {}
    root = _final_eye_root()
    out_dir = root / "out"

    def _ensure(feed_id: str) -> dict[str, Any]:
        return feeds.setdefault(feed_id, {
            "feed_id": feed_id,
            "image": None,
            "image_mime": "image/png",
            "text": None,
            "text_mime": "text/plain",
            "captured_at": None,
        })

    if out_dir.is_dir():
        by_stem: dict[str, dict[str, Path]] = {}
        for path in sorted(out_dir.iterdir()):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in IMAGE_EXTS and ext not in TEXT_EXTS and ext != ".h7":
                continue
            by_stem.setdefault(path.stem, {})[ext] = path
        for stem, parts in by_stem.items():
            row = _ensure(stem)
            for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
                if ext in parts:
                    row["image"] = _read_bytes(parts[ext])
                    row["image_mime"] = mimetypes.guess_type(str(parts[ext]))[0] or "image/png"
                    try:
                        row["captured_at"] = time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ",
                            time.gmtime(parts[ext].stat().st_mtime),
                        )
                    except OSError:
                        pass
                    break
            for ext in (".txt", ".h7"):
                if ext in parts:
                    row["text"] = _read_bytes(parts[ext])
                    row["text_mime"] = mimetypes.guess_type(str(parts[ext]))[0] or "text/plain"
                    break

    manifest_jsonl = root / "manifest.jsonl"
    if manifest_jsonl.is_file():
        try:
            for line in manifest_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                fid = str(doc.get("label") or doc.get("id") or Path(str(doc.get("image") or "feed")).stem)
                row = _ensure(fid)
                if doc.get("ts") or doc.get("captured_at"):
                    row["captured_at"] = str(doc.get("captured_at") or doc.get("ts"))
                img_p = doc.get("image")
                if img_p:
                    ip = Path(str(img_p))
                    if ip.is_file():
                        row["image"] = _read_bytes(ip)
                        row["image_mime"] = mimetypes.guess_type(str(ip))[0] or "image/png"
                for key in ("ocr_file", "h7_file"):
                    tp = doc.get(key)
                    if tp:
                        tpath = Path(str(tp))
                        if tpath.is_file():
                            row["text"] = _read_bytes(tpath)
                            row["text_mime"] = mimetypes.guess_type(str(tpath))[0] or "text/plain"
        except (OSError, json.JSONDecodeError):
            pass

    desktop_png = STATE / "ocr-desktop" / "desktop-full.png"
    if desktop_png.is_file():
        row = _ensure("desktop-live")
        row["image"] = _read_bytes(desktop_png)
        row["image_mime"] = "image/png"
        txt = STATE / "ocr-desktop" / "ocr.txt"
        if txt.is_file():
            row["text"] = _read_bytes(txt)
        try:
            row["captured_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(desktop_png.stat().st_mtime),
            )
        except OSError:
            pass

    out: list[dict[str, Any]] = []
    for row in feeds.values():
        if row.get("image") or row.get("text"):
            out.append(row)
    return out


def _ocr_digest_set(ref: dict[str, Any]) -> set[str]:
    ref = _normalize_feed_ref(ref)
    digs: set[str] = set()
    for key in ("first_image", "last_image", "live_feed", "text"):
        stamp = ref.get(key)
        if isinstance(stamp, dict) and stamp.get("sha256"):
            digs.add(str(stamp["sha256"]))
    if ref.get("sha256"):
        digs.add(str(ref["sha256"]))
    return digs


def _gc_blobs(manifest: dict[str, Any], blob_bytes: dict[str, bytes]) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Drop unreferenced blob slices after OCR prune."""
    live: set[str] = set()
    for ref in (manifest.get("icons") or {}).values():
        if ref.get("sha256"):
            live.add(str(ref["sha256"]))
    for ref in (manifest.get("ocr") or {}).values():
        live |= _ocr_digest_set(ref)
    manifest["blobs"] = {d: m for d, m in (manifest.get("blobs") or {}).items() if d in live}
    blob_bytes = {d: b for d, b in blob_bytes.items() if d in live}
    return manifest, blob_bytes


def _carry_ocr_feeds(
    old_ocr: dict[str, Any],
    keep_ids: set[str],
    blob_bytes: dict[str, bytes],
    *,
    now: str,
) -> dict[str, Any]:
    """Preserve selected OCR feeds without rescanning Final_Eye/out."""
    out: dict[str, Any] = {}
    for fid in keep_ids:
        ref = old_ocr.get(fid)
        if ref:
            out[fid] = _normalize_feed_ref(ref)
    return out


def _merge_state(
    old: dict[str, Any],
    icon_rows: list[tuple[str, bytes, str]],
    feed_rows: list[dict[str, Any]],
    existing_bytes: dict[str, bytes],
    *,
    now: str,
    ocr_carry: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, int]]:
    """Dedup by sha256 — new bytes only; feeds keep first + last image timestamps."""
    manifest = _empty_manifest()
    manifest["blobs"] = {}
    manifest["icons"] = {}
    manifest["ocr"] = {}
    new_bytes: dict[str, bytes] = dict(existing_bytes)
    stats = {
        "icons_unchanged": 0, "icons_new": 0, "icons_changed": 0,
        "feeds_unchanged": 0, "feeds_new": 0, "feeds_changed": 0,
        "ocr_unchanged": 0, "ocr_new": 0,
        "blobs_reused": 0, "blobs_added": 0,
    }

    old_blobs = old.get("blobs") or {}
    old_icons = old.get("icons") or {}
    old_ocr = old.get("ocr") or {}

    def _touch_blob(digest: str, data: bytes, mime: str) -> None:
        nonlocal stats
        if digest not in new_bytes:
            new_bytes[digest] = data
            stats["blobs_added"] += 1
        else:
            stats["blobs_reused"] += 1
        manifest["blobs"][digest] = _blob_meta(old_blobs.get(digest), digest, data, mime, now=now)

    for eid, data, mime in icon_rows:
        digest = _sha256(data)
        prev = old_icons.get(eid)
        if prev and str(prev.get("sha256") or "") == digest:
            stats["icons_unchanged"] += 1
        elif prev:
            stats["icons_changed"] += 1
        else:
            stats["icons_new"] += 1
        _touch_blob(digest, data, mime)
        manifest["icons"][eid] = _ref_meta(prev, digest, now=now)

    for feed in feed_rows:
        fid = str(feed.get("feed_id") or "")
        if not fid:
            continue
        image = feed.get("image")
        text = feed.get("text")
        if not image and not text:
            continue
        prev = _normalize_feed_ref(old_ocr.get(fid))
        captured_at = str(feed.get("captured_at") or now)
        image_digest = _sha256(image) if image else ""
        text_digest = _sha256(text) if text else None

        if image:
            old_last = str((prev.get("last_image") or {}).get("sha256") or "")
            if prev and old_last == image_digest:
                stats["feeds_unchanged"] += 1
                stats["ocr_unchanged"] += 1
            elif prev:
                stats["feeds_changed"] += 1
            else:
                stats["feeds_new"] += 1
                stats["ocr_new"] += 1
            _touch_blob(image_digest, image, str(feed.get("image_mime") or "image/png"))
        elif prev:
            image_digest = str((prev.get("last_image") or {}).get("sha256") or "")
            stats["feeds_unchanged"] += 1

        if text and text_digest:
            _touch_blob(text_digest, text, str(feed.get("text_mime") or "text/plain"))

        if image_digest:
            manifest["ocr"][fid] = _ocr_feed_meta(
                prev if prev else None,
                image_digest,
                now=now,
                captured_at=captured_at,
                text_digest=text_digest,
            )
        elif text_digest:
            manifest["ocr"][fid] = _ref_meta(prev if prev else None, text_digest, now=now)

    if ocr_carry:
        for fid, ref in ocr_carry.items():
            if fid not in manifest["ocr"]:
                manifest["ocr"][fid] = ref
                for digest in _ocr_digest_set(ref):
                    if digest in new_bytes:
                        stats["feeds_unchanged"] += 1

    manifest, new_bytes = _gc_blobs(manifest, new_bytes)
    manifest["updated"] = now
    return manifest, new_bytes, stats


def _build_desktop_plan(manifest: dict[str, Any], blob_bytes: dict[str, bytes]) -> dict[str, Any]:
    """One slice per unique sha256 blob — manifest holds refs + unchanged timestamps."""
    slices: list[dict[str, Any]] = []
    slice_blobs: list[bytes] = []
    slot = 0

    manifest_doc = dict(manifest)
    manifest_bytes = json.dumps(manifest_doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    slice_blobs.append(manifest_bytes)
    slices.append({"slot": slot, "byte_count": len(manifest_bytes)})
    slot += 1

    digest_order = sorted((manifest_doc.get("blobs") or {}).keys())
    for digest in digest_order:
        data = blob_bytes.get(digest)
        if data is None:
            continue
        manifest_doc["blobs"][digest]["slot"] = slot
        slice_blobs.append(data)
        slices.append({"slot": slot, "byte_count": len(data)})
        slot += 1

    manifest_bytes = json.dumps(manifest_doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    slice_blobs[0] = manifest_bytes
    slices[0]["byte_count"] = len(manifest_bytes)

    h7s = _import_h7s()
    face = h7s.pick_face_for_source(manifest_bytes, bundle_path())
    return {
        "inner_kind": INNER_KIND,
        "face": face,
        "slices": slices,
        "slice_blobs": slice_blobs,
        "byte_count": sum(len(b) for b in slice_blobs),
        "payload_sha256": _sha256(b"".join(slice_blobs)),
        "counts": {
            "slice_count": len(slices),
            "blob_count": len(digest_order),
            "icon_count": len(manifest_doc.get("icons") or {}),
            "ocr_count": len(manifest_doc.get("ocr") or {}),
        },
        "lossless_restore": True,
        "execute_lane": "desktop_slice",
        "manifest": manifest_doc,
    }


def prune_ocr_feeds(
    keep_ids: set[str] | frozenset[str] | None = None,
    *,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Drop stale OCR feeds — keep live lane only (default desktop-live)."""
    keep = set(keep_ids or {"desktop-live"})
    out_path = dest or bundle_path()
    if not out_path.is_file():
        return {"ok": False, "error": "bundle_missing", "dest": str(out_path)}
    now = _now()
    old = _read_manifest_from_bundle(out_path)
    existing_bytes = _load_blob_bytes(out_path, old)
    ocr_carry = _carry_ocr_feeds(old.get("ocr") or {}, keep, existing_bytes, now=now)
    before = len(old.get("ocr") or {})
    icon_rows = _scan_icon_candidates(_library_entries())
    manifest, blob_bytes, stats = _merge_state(
        old, icon_rows, [], existing_bytes, now=now, ocr_carry=ocr_carry,
    )
    plan = _build_desktop_plan(manifest, blob_bytes)
    h7s = _import_h7s()
    packed = h7s.pack_h7s_bytes(
        plan,
        meta={"original_name": out_path.name, "original_extension": ".h7s", "ocr_pruned": True},
        path=out_path,
    )
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_bytes(packed)
    tmp.replace(out_path)
    after = len((plan.get("manifest") or {}).get("ocr") or {})
    return {
        "ok": True,
        "dest": str(out_path),
        "ocr_before": before,
        "ocr_after": after,
        "kept": sorted(keep),
        "packed_bytes": len(packed),
        "dedup": stats,
        "updated": now,
    }


def pack_desktop_bundle(
    dest: Path | None = None,
    *,
    grow: bool = True,
    include_icons: bool = True,
    include_ocr: bool = True,
    ocr_keep: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """Pack/grow desktop H7s — deduped blobs, unchanged-duration timestamps only."""
    t0 = time.perf_counter()
    out_path = dest or bundle_path()
    now = _now()
    prog_mod = _import_progress()
    progress = prog_mod.start_pack(
        job="pack_desktop_bundle",
        fmt="h7s/1",
        src=str(out_path),
        dest=str(out_path),
        meta={"grow": grow, "inner_kind": INNER_KIND, "dedup": True},
    ) if prog_mod and hasattr(prog_mod, "start_pack") else None

    try:
        old = _read_manifest_from_bundle(out_path) if grow and out_path.is_file() else _empty_manifest()
        existing_bytes = _load_blob_bytes(out_path, old) if grow and out_path.is_file() else {}

        if progress:
            progress.phase("scan", 5.0, f"dedup lane · {len(existing_bytes)} blobs carried")

        icon_rows = _scan_icon_candidates(_library_entries()) if include_icons else []
        feed_rows = _scan_ocr_feeds() if include_ocr else []
        ocr_carry = None
        if not include_ocr and ocr_keep:
            ocr_carry = _carry_ocr_feeds(old.get("ocr") or {}, set(ocr_keep), existing_bytes, now=now)

        if not icon_rows and not feed_rows and not existing_bytes and not ocr_carry:
            out = {"ok": False, "error": "nothing_to_pack", "dest": str(out_path)}
            if progress:
                progress.finish(ok=False, result=out)
            return out

        manifest, blob_bytes, merge_stats = _merge_state(
            old, icon_rows, feed_rows, existing_bytes, now=now, ocr_carry=ocr_carry,
        )

        if progress:
            progress.phase(
                "slice",
                25.0,
                f"{merge_stats['blobs_reused']} reused · {merge_stats['blobs_added']} new blobs",
            )

        plan = _build_desktop_plan(manifest, blob_bytes)
        h7s = _import_h7s()
        if progress:
            progress.phase("pack", 55.0, "H7s desktop condenser")
        packed = h7s.pack_h7s_bytes(
            plan,
            meta={
                "original_name": out_path.name,
                "original_extension": ".h7s",
                "desktop_condenser": True,
                "dedup_by_sha256": True,
                "product": "Hostess7",
            },
            path=out_path,
            progress=progress,
        )
        if progress:
            progress.phase("write", 90.0, f"writing {out_path.name}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_bytes(packed)
        tmp.replace(out_path)

        m = plan.get("manifest") or {}
        result = {
            "ok": True,
            "format": "h7s/1",
            "inner_kind": INNER_KIND,
            "dest": str(out_path),
            "packed_bytes": len(packed),
            "blob_count": len(m.get("blobs") or {}),
            "icon_count": len(m.get("icons") or {}),
            "ocr_count": len(m.get("ocr") or {}),
            "slice_count": len(plan.get("slices") or []),
            "dedup": merge_stats,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "properties": h7s.read_properties(packed),
            "progress_panel": str(prog_mod.panel_path()) if prog_mod and hasattr(prog_mod, "panel_path") else "",
        }
        if progress:
            progress.finish(ok=True, result=result)
        return result
    except Exception as exc:
        if progress:
            progress.finish(ok=False, result={"error": str(exc)})
        raise


def append_feed_capture(
    feed_id: str,
    image: bytes,
    *,
    text: bytes | None = None,
    image_mime: str = "image/png",
    text_mime: str = "text/plain",
    captured_at: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append live feed frame — first image kept; last image / live_feed updated."""
    path = bundle_path()
    now = _now()
    old = _read_manifest_from_bundle(path) if path.is_file() else _empty_manifest()
    existing_bytes = _load_blob_bytes(path, old) if path.is_file() else {}
    feed = {
        "feed_id": feed_id,
        "image": image,
        "image_mime": image_mime,
        "text": text,
        "text_mime": text_mime,
        "captured_at": captured_at or now,
    }
    manifest, blob_bytes, stats = _merge_state(old, [], [feed], existing_bytes, now=now)
    plan = _build_desktop_plan(manifest, blob_bytes)
    h7s = _import_h7s()
    packed = h7s.pack_h7s_bytes(
        plan,
        meta={"original_name": path.name, "original_extension": ".h7s", **(meta or {})},
        path=path,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(packed)
    tmp.replace(path)
    ref = (manifest.get("ocr") or {}).get(feed_id) or {}
    spatial: dict[str, Any] | None = None
    try:
        sp_py = INSTALL / "lib" / "field-look-spatial.py"
        if sp_py.is_file():
            spec = importlib.util.spec_from_file_location("field_look_spatial_capture", sp_py)
            if spec and spec.loader:
                sp = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sp)
                if hasattr(sp, "ingest_capture"):
                    spatial = sp.ingest_capture(
                        feed_id,
                        image,
                        meta=meta,
                        captured_at=captured_at or now,
                    )
    except Exception:
        spatial = None
    return {
        "ok": True,
        "feed_id": feed_id,
        "dest": str(path),
        "packed_bytes": len(packed),
        "live_feed": ref.get("live_feed"),
        "last_image": ref.get("last_image"),
        "first_image": ref.get("first_image"),
        "unchanged_sec": ref.get("unchanged_sec"),
        "dedup": stats,
        "look_spatial": spatial,
    }


def append_ocr(
    ocr_id: str,
    data: bytes,
    *,
    mime: str = "application/octet-stream",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Legacy text append — prefer append_feed_capture for image live feed."""
    if mime.startswith("image/"):
        return append_feed_capture(ocr_id, data, image_mime=mime, meta=meta)
    path = bundle_path()
    now = _now()
    old = _read_manifest_from_bundle(path) if path.is_file() else _empty_manifest()
    existing_bytes = _load_blob_bytes(path, old) if path.is_file() else {}
    feed = {
        "feed_id": ocr_id,
        "image": None,
        "text": data,
        "text_mime": mime,
        "captured_at": now,
    }
    manifest, blob_bytes, _ = _merge_state(old, [], [feed], existing_bytes, now=now)
    plan = _build_desktop_plan(manifest, blob_bytes)
    h7s = _import_h7s()
    packed = h7s.pack_h7s_bytes(plan, meta={"original_name": path.name, **(meta or {})}, path=path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(packed)
    tmp.replace(path)
    return {"ok": True, "ocr_id": ocr_id, "dest": str(path), "packed_bytes": len(packed)}


def _resolve_blob_slot(manifest: dict[str, Any], stamp: dict[str, Any] | None) -> int | None:
    if not stamp:
        return None
    digest = str(stamp.get("sha256") or "")
    blob = (manifest.get("blobs") or {}).get(digest) or {}
    slot = blob.get("slot")
    return int(slot) if slot is not None else None


def _read_blob_by_stamp(bp: Path, manifest: dict[str, Any], stamp: dict[str, Any] | None) -> tuple[bytes, dict[str, Any]] | None:
    slot = _resolve_blob_slot(manifest, stamp)
    if slot is None:
        return None
    h7s = _import_h7s()
    data, ctx = h7s.read_slice_bytes(bp, slot=slot)
    digest = str((stamp or {}).get("sha256") or "")
    return data, {
        "stamp": stamp,
        "blob": (manifest.get("blobs") or {}).get(digest),
        "slice_meta": ctx.get("slice_meta") or {},
    }


def read_manifest(path: Path | None = None) -> dict[str, Any]:
    return _read_manifest_from_bundle(path or bundle_path())


def read_icon(entry_id: str, path: Path | None = None) -> tuple[bytes, dict[str, Any]] | None:
    bp = path or bundle_path()
    if not bp.is_file():
        return None
    manifest = _read_manifest_from_bundle(bp)
    ref = (manifest.get("icons") or {}).get(entry_id)
    slot = _resolve_blob_slot(manifest, ref)
    if slot is None:
        return None
    h7s = _import_h7s()
    data, ctx = h7s.read_slice_bytes(bp, slot=slot)
    return data, {"ref": ref, "blob": (manifest.get("blobs") or {}).get(str(ref.get("sha256"))), "slice_meta": ctx.get("slice_meta") or {}}


def read_live_feed(feed_id: str, path: Path | None = None) -> tuple[bytes, dict[str, Any]] | None:
    """Latest image for feed — live feed lane."""
    bp = path or bundle_path()
    if not bp.is_file():
        return None
    manifest = _read_manifest_from_bundle(bp)
    ref = _normalize_feed_ref((manifest.get("ocr") or {}).get(feed_id))
    stamp = ref.get("live_feed") or ref.get("last_image")
    hit = _read_blob_by_stamp(bp, manifest, stamp)
    if not hit:
        return None
    data, meta = hit
    return data, {"ref": ref, "lane": "live_feed", **meta}


def read_first_image(feed_id: str, path: Path | None = None) -> tuple[bytes, dict[str, Any]] | None:
    """First captured image — frozen at first_seen timestamp."""
    bp = path or bundle_path()
    if not bp.is_file():
        return None
    manifest = _read_manifest_from_bundle(bp)
    ref = _normalize_feed_ref((manifest.get("ocr") or {}).get(feed_id))
    hit = _read_blob_by_stamp(bp, manifest, ref.get("first_image"))
    if not hit:
        return None
    data, meta = hit
    return data, {"ref": ref, "lane": "first_image", **meta}


def read_ocr_text(feed_id: str, path: Path | None = None) -> tuple[bytes, dict[str, Any]] | None:
    """OCR text sidecar if present."""
    bp = path or bundle_path()
    if not bp.is_file():
        return None
    manifest = _read_manifest_from_bundle(bp)
    ref = _normalize_feed_ref((manifest.get("ocr") or {}).get(feed_id))
    hit = _read_blob_by_stamp(bp, manifest, ref.get("text"))
    if hit:
        data, meta = hit
        return data, {"ref": ref, "lane": "text", **meta}
    if ref.get("sha256"):
        return read_icon(feed_id, bp)  # legacy text-only
    return None


def read_ocr(ocr_id: str, path: Path | None = None) -> tuple[bytes, dict[str, Any]] | None:
    """Default OCR read — text if present, else live feed image."""
    hit = read_ocr_text(ocr_id, path)
    if hit:
        return hit
    return read_live_feed(ocr_id, path)


def bundle_status(path: Path | None = None) -> dict[str, Any]:
    bp = path or bundle_path()
    if not bp.is_file():
        return {
            "ok": True,
            "live": False,
            "bundle": str(bp),
            "schema": SCHEMA,
            "blob_count": 0,
            "icon_count": 0,
            "ocr_count": 0,
        }
    h7s = _import_h7s()
    manifest = _read_manifest_from_bundle(bp)
    unchanged_icons = sum(
        1 for r in (manifest.get("icons") or {}).values()
        if float(r.get("unchanged_sec") or 0) > 0
    )
    return {
        "ok": True,
        "live": True,
        "bundle": str(bp),
        "schema": SCHEMA,
        "packed_bytes": bp.stat().st_size,
        "blob_count": len(manifest.get("blobs") or {}),
        "icon_count": len(manifest.get("icons") or {}),
        "ocr_count": len(manifest.get("ocr") or {}),
        "icons_unchanged": unchanged_icons,
        "updated": manifest.get("updated"),
        "properties": h7s.read_properties(bp),
        "manifest_slice": MANIFEST_SLICE,
        "dedup": True,
    }


def ingest_ocr_feed(limit: int = 64) -> list[dict[str, Any]]:
    bp = bundle_path()
    manifest = _read_manifest_from_bundle(bp)
    rows: list[dict[str, Any]] = []
    h7s = _import_h7s()
    for oid, raw_ref in list((manifest.get("ocr") or {}).items())[:limit]:
        try:
            ref = _normalize_feed_ref(raw_ref)
            text_hit = read_ocr_text(oid, bp)
            text = ""
            if text_hit:
                data, _ = text_hit
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = ""
            rows.append({
                "id": oid,
                "source": "field-desktop.h7s",
                "first_image": ref.get("first_image"),
                "last_image": ref.get("last_image"),
                "live_feed": ref.get("live_feed"),
                "first_seen": ref.get("first_seen"),
                "last_seen": ref.get("last_seen"),
                "unchanged_sec": ref.get("unchanged_sec"),
                "last_verified": ref.get("last_verified"),
                "text": text[:8000],
            })
        except Exception as exc:
            rows.append({"id": oid, "error": str(exc)})
    return rows


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "status").lower()
    if cmd in ("status", "properties"):
        print(json.dumps(bundle_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pack":
        grow = "--fresh" not in args
        out = pack_desktop_bundle(grow=grow)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("prune-ocr", "ocr-prune"):
        keep = {"desktop-live"}
        for arg in args[1:]:
            if arg.startswith("--keep="):
                keep = {x.strip() for x in arg.split("=", 1)[1].split(",") if x.strip()}
        out = prune_ocr_feeds(keep)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "manifest":
        print(json.dumps(read_manifest(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "icon" and len(args) >= 2:
        hit = read_icon(args[1])
        if not hit:
            print(json.dumps({"ok": False, "error": "not_found"}, indent=2))
            return 1
        data, meta = hit
        print(json.dumps({"ok": True, "bytes": len(data), **meta}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "ocr-feed":
        print(json.dumps({"ok": True, "rows": ingest_ocr_feed()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "live-feed" and len(args) >= 2:
        hit = read_live_feed(args[1])
        if not hit:
            print(json.dumps({"ok": False, "error": "not_found"}, indent=2))
            return 1
        data, meta = hit
        print(json.dumps({"ok": True, "bytes": len(data), "lane": "live_feed", **meta}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "first-image" and len(args) >= 2:
        hit = read_first_image(args[1])
        if not hit:
            print(json.dumps({"ok": False, "error": "not_found"}, indent=2))
            return 1
        data, meta = hit
        print(json.dumps({"ok": True, "bytes": len(data), "lane": "first_image", **meta}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["status", "pack", "manifest", "icon", "ocr-feed", "live-feed", "first-image"],
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())