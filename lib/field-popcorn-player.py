#!/usr/bin/env pythong
"""Popcorn — media discovery, library, and safe local streaming for the theatre player."""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-popcorn-doctrine.json"
CODEC_DOCTRINE = INSTALL / "data" / "field-media-codec-doctrine.json"
SETTINGS = STATE / "field-popcorn-settings.json"
LIBRARY = STATE / "field-popcorn-library.json"
MEDIA_STATE = STATE / "field-popcorn-media-state.json"
THUMBS_DIR = STATE / "field-popcorn-thumbs"
PANEL = STATE / "field-popcorn-panel.json"
INSPECTOR_DOCTRINE = INSTALL / "data" / "field-media-inspector-doctrine.json"

_INSPECTOR_MOD: Any = None

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".nexus-state", "build", "dist",
    "target", ".cache", "venv", ".venv", "proc", "sys", "dev",
}


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _expand_root(raw: str) -> Path | None:
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("~/"):
        s = str(Path.home() / s[2:])
    s = s.replace("~/SG", str(SG)).replace("~/Desktop/SG", str(SG))
    try:
        p = Path(s).expanduser().resolve()
    except (OSError, RuntimeError):
        return None
    if p.is_dir():
        return p
    return None


def _scan_roots() -> list[Path]:
    doctrine = _load(DOCTRINE, {})
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in doctrine.get("scan_roots") or []:
        p = _expand_root(str(raw))
        if p and str(p) not in seen:
            seen.add(str(p))
            roots.append(p)
    for extra in (
        Path.home() / "Videos",
        Path.home() / "Music",
        Path.home() / "Pictures",
        SG,
        INSTALL,
    ):
        try:
            r = extra.resolve()
            if r.is_dir() and str(r) not in seen:
                seen.add(str(r))
                roots.append(r)
        except OSError:
            pass
    return roots


def _kind_for_ext(ext: str, exts: dict[str, list[str]]) -> str | None:
    e = ext.lower().lstrip(".")
    for kind, items in exts.items():
        if e in items:
            return kind
    return None


def _media_id(path: Path) -> str:
    return hashlib.sha256(str(path).encode()).hexdigest()[:20]


_CODEC_CACHE: dict[str, Any] | None = None


def _codec_doctrine() -> dict[str, Any]:
    global _CODEC_CACHE
    if _CODEC_CACHE is None:
        _CODEC_CACHE = _load(CODEC_DOCTRINE, {})
    return _CODEC_CACHE


def _container_for_ext(ext: str) -> dict[str, Any] | None:
    e = ext.lower().lstrip(".")
    mime_map = _codec_doctrine().get("mime_by_extension") or {}
    mime = mime_map.get(e)
    if not mime:
        return None
    for row in _codec_doctrine().get("containers") or []:
        if e in (row.get("extensions") or []):
            return {**row, "mime": mime}
    return {"id": e, "mime": mime, "browser_native": mime in (_codec_doctrine().get("popcorn_playback") or {}).get("native_tags", [])}


def _mime_for(path: Path, kind: str) -> str:
    ext = path.suffix.lower().lstrip(".")
    mime_map = _codec_doctrine().get("mime_by_extension") or {}
    if ext in mime_map:
        return str(mime_map[ext])
    guess, _ = mimetypes.guess_type(path.name)
    if guess:
        return guess
    return {
        "video": "video/mp4",
        "audio": "audio/mpeg",
        "image": "image/jpeg",
    }.get(kind, "application/octet-stream")


def _inspector_mod() -> Any | None:
    global _INSPECTOR_MOD
    if _INSPECTOR_MOD is not None:
        return _INSPECTOR_MOD
    script = INSTALL / "lib" / "field-media-inspector.py"
    if not script.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_media_inspector", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _INSPECTOR_MOD = mod
    return mod


def _filename_provenance(name: str) -> dict[str, Any]:
    mod = _inspector_mod()
    if mod and hasattr(mod, "_provenance_from_text"):
        sid, conf, _hits = mod._provenance_from_text("", name)
        return {
            "generation_source": sid,
            "generation_confidence": conf,
            "ai_generated": sid not in ("unknown", "camera", ""),
        }
    low = name.lower()
    for sid, markers in (
        ("grok", ("grok", "xai")),
        ("openai", ("dall-e", "dalle", "openai", "chatgpt")),
        ("midjourney", ("midjourney", "mj-")),
        ("stable_diffusion", ("sdxl", "stable-diffusion", "comfyui")),
    ):
        if any(m in low for m in markers):
            return {"generation_source": sid, "generation_confidence": 0.5, "ai_generated": True}
    return {"generation_source": "unknown", "generation_confidence": 0.0, "ai_generated": False}


def _inspect_light(path: Path, kind: str, media_id: str) -> dict[str, Any]:
    mod = _inspector_mod()
    if not mod:
        return _filename_provenance(path.name)
    try:
        row = mod.inspect_light(path, kind, media_id=media_id)
    except Exception:
        return _filename_provenance(path.name)
    gen = row.get("generation") or {}
    ct = row.get("content_threat") or {}
    fd = row.get("file_details") or {}
    return {
        "generation_source": gen.get("generation_source") or "unknown",
        "generation_confidence": gen.get("generation_confidence"),
        "ai_generated": bool(gen.get("ai_generated")),
        "content_threat": ct,
        "file_details": {
            k: fd.get(k)
            for k in (
                "container", "codec", "mime", "width", "height", "sample_rate",
                "channels", "bit_depth", "encoding_issues", "bitrate_est",
            )
            if fd.get(k) is not None
        },
    }


def inspect_media(media_id: str, *, deep: bool = True) -> dict[str, Any]:
    item = resolve_media(media_id)
    if not item:
        return {"ok": False, "error": "media_not_found"}
    mod = _inspector_mod()
    if not mod:
        return {"ok": False, "error": "inspector_missing"}
    path = Path(str(item["path"]))
    kind = str(item.get("kind") or "image")
    try:
        if deep:
            row = mod.inspect_deep(path, kind, media_id=media_id)
        else:
            row = mod.inspect_light(path, kind, media_id=media_id)
    except Exception as exc:
        return {"ok": False, "error": "inspect_failed", "detail": str(exc)[:200]}
    return {"ok": True, "item": item, "inspect": row}


def file_details(media_id: str) -> dict[str, Any]:
    cached = None
    mod = _inspector_mod()
    if mod and hasattr(mod, "inspect_cached"):
        cached = mod.inspect_cached(media_id)
    if cached:
        return {"ok": True, "media_id": media_id, "inspect": cached, "cached": True}
    out = inspect_media(media_id, deep=True)
    if not out.get("ok"):
        return out
    return {"ok": True, "media_id": media_id, "inspect": out.get("inspect"), "cached": False}


def _playback_hint(path: Path, kind: str, mime: str) -> dict[str, Any]:
    native_tags = (_codec_doctrine().get("popcorn_playback") or {}).get("native_tags") or []
    container = _container_for_ext(path.suffix)
    browser_native = mime in native_tags or bool(container and container.get("browser_native") is True)
    templates = (_codec_doctrine().get("popcorn_playback") or {}).get("can_play_type_templates") or {}
    can_play = None
    if kind == "video":
        ext = path.suffix.lower().lstrip(".")
        if ext in ("webm",):
            can_play = templates.get("vp9_opus_webm")
        elif ext in ("mp4", "m4v"):
            can_play = templates.get("h264_aac_mp4")
    return {
        "mime": mime,
        "browser_native": browser_native,
        "ffmpeg_fallback": not browser_native and bool(container and container.get("ffmpeg")),
        "can_play_type": can_play,
        "container": (container or {}).get("id"),
    }


def scan_library(*, force: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    exts = doctrine.get("extensions") or {}
    max_files = int(policy.get("max_files") or 4000)
    max_depth = int(policy.get("max_depth") or 10)
    follow = bool(policy.get("follow_symlinks"))

    if not force and LIBRARY.is_file():
        cached = _load(LIBRARY, {})
        if cached.get("items") and cached.get("scanned"):
            return cached

    items: list[dict[str, Any]] = []
    roots = _scan_roots()
    for root in roots:
        if len(items) >= max_files:
            break
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=follow):
                depth = Path(dirpath).relative_to(root).parts
                if len(depth) > max_depth:
                    dirnames.clear()
                    continue
                dirnames[:] = [
                    d for d in dirnames
                    if d not in _SKIP_DIRS and not d.startswith(".")
                ]
                for name in filenames:
                    if len(items) >= max_files:
                        break
                    if name.startswith("."):
                        continue
                    path = Path(dirpath) / name
                    try:
                        if not path.is_file():
                            continue
                        st = path.stat()
                    except OSError:
                        continue
                    kind = _kind_for_ext(path.suffix, exts)
                    if not kind:
                        continue
                    mid = _media_id(path)
                    mime = _mime_for(path, kind)
                    row = {
                        "id": mid,
                        "name": name,
                        "path": str(path),
                        "kind": kind,
                        "ext": path.suffix.lower().lstrip("."),
                        "size": st.st_size,
                        "mtime": int(st.st_mtime),
                        "root": str(root),
                        "mime": mime,
                        "playback": _playback_hint(path, kind, mime),
                    }
                    policy = doctrine.get("policy") or {}
                    insp_doc = _load(INSPECTOR_DOCTRINE, {})
                    if policy.get("scan_on_open", True) and insp_doc.get("policy", {}).get("scan_light_on_library", True):
                        row.update(_filename_provenance(name))
                    items.append(row)
        except OSError:
            continue

    items.sort(key=lambda x: (-(x.get("mtime") or 0), x.get("name") or ""))
    doc = {
        "scanned": _now(),
        "count": len(items),
        "roots": [str(r) for r in roots],
        "items": items,
        "by_kind": {
            "video": sum(1 for i in items if i["kind"] == "video"),
            "audio": sum(1 for i in items if i["kind"] == "audio"),
            "image": sum(1 for i in items if i["kind"] == "image"),
        },
    }
    _save_atomic(LIBRARY, doc)
    return doc


def resolve_media(media_id: str) -> dict[str, Any] | None:
    lib = _load(LIBRARY, {})
    for item in lib.get("items") or []:
        if item.get("id") == media_id:
            path = Path(str(item["path"]))
            try:
                real = path.resolve()
            except OSError:
                return None
            if not real.is_file():
                return None
            return {**item, "path": str(real)}
    return None


def read_range(path: Path, start: int, end: int) -> bytes:
    with path.open("rb") as fh:
        fh.seek(start)
        return fh.read(end - start + 1)


def parse_range_header(header: str, size: int) -> tuple[int, int] | None:
    if not header or not header.strip().lower().startswith("bytes="):
        return None
    spec = header.strip()[6:].split(",")[0].strip()
    if "-" not in spec:
        return None
    left, right = spec.split("-", 1)
    try:
        if left == "":
            suffix = int(right)
            if suffix <= 0:
                return None
            start = max(0, size - suffix)
            return start, size - 1
        start = int(left)
        end = int(right) if right else size - 1
        end = min(end, size - 1)
        if start > end or start < 0:
            return None
        return start, end
    except ValueError:
        return None


def _media_states() -> dict[str, Any]:
    doc = _load(MEDIA_STATE, {})
    return doc.get("items") if isinstance(doc.get("items"), dict) else {}


def _save_media_states(items: dict[str, Any]) -> None:
    _save_atomic(MEDIA_STATE, {"updated": _now(), "items": items})


def _thumb_file(media_id: str, mode: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", media_id)[:40]
    return THUMBS_DIR / f"{safe}-{mode}.jpg"


def thumb_exists(media_id: str, mode: str) -> bool:
    return _thumb_file(media_id, mode).is_file()


def thumb_read(media_id: str, mode: str) -> bytes | None:
    if mode not in ("viewing", "custom"):
        return None
    path = _thumb_file(media_id, mode)
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError:
        return None


def media_meta(media_id: str) -> dict[str, Any]:
    items = _media_states()
    meta = dict(items.get(media_id) or {})
    mode = meta.get("thumb_mode") or "viewing"
    if mode == "custom" and not thumb_exists(media_id, "custom"):
        mode = "viewing" if thumb_exists(media_id, "viewing") else "viewing"
    active = mode if thumb_exists(media_id, mode) else (
        "custom" if thumb_exists(media_id, "custom") else (
            "viewing" if thumb_exists(media_id, "viewing") else None
        )
    )
    return {
        "thumb_mode": meta.get("thumb_mode") or "viewing",
        "active_thumb": active,
        "aspect_ratio": meta.get("aspect_ratio"),
        "resume_sec": float(meta.get("resume_sec") or 0),
        "viewing": meta.get("viewing") or {},
        "custom": meta.get("custom") or {},
        "has_viewing": thumb_exists(media_id, "viewing"),
        "has_custom": thumb_exists(media_id, "custom"),
        "thumb_url": f"/api/field-popcorn/thumb?id={media_id}&mode={active}" if active else None,
        "viewing_url": f"/api/field-popcorn/thumb?id={media_id}&mode=viewing" if thumb_exists(media_id, "viewing") else None,
        "custom_url": f"/api/field-popcorn/thumb?id={media_id}&mode=custom" if thumb_exists(media_id, "custom") else None,
    }


def _decode_data_url(data_url: str) -> bytes | None:
    raw = str(data_url or "").strip()
    if not raw.startswith("data:"):
        return None
    try:
        _hdr, b64 = raw.split(",", 1)
        return base64.b64decode(b64, validate=False)
    except (ValueError, base64.binascii.Error):
        return None


def save_thumb(
    media_id: str,
    mode: str,
    data_url: str,
    *,
    aspect_ratio: float | None = None,
    time_sec: float | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    if mode not in ("viewing", "custom"):
        return {"ok": False, "error": "bad_thumb_mode"}
    blob = _decode_data_url(data_url)
    if not blob:
        return {"ok": False, "error": "thumb_decode_failed"}
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _thumb_file(media_id, mode)
    dest.write_bytes(blob)
    items = _media_states()
    meta = dict(items.get(media_id) or {})
    stamp = _now()
    slot = {
        "updated": stamp,
        "time_sec": round(float(time_sec or 0), 3),
        "title": (title or "").strip()[:200] or None,
        "aspect_ratio": aspect_ratio,
    }
    meta[mode] = {k: v for k, v in slot.items() if v is not None}
    if aspect_ratio:
        meta["aspect_ratio"] = aspect_ratio
    if mode == "custom":
        meta["thumb_mode"] = "custom"
    items[media_id] = meta
    _save_media_states(items)
    return {"ok": True, "media_id": media_id, "mode": mode, "meta": media_meta(media_id)}


def set_thumb_mode(media_id: str, mode: str) -> dict[str, Any]:
    if mode not in ("viewing", "custom"):
        return {"ok": False, "error": "bad_thumb_mode"}
    if mode == "custom" and not thumb_exists(media_id, "custom"):
        return {"ok": False, "error": "custom_thumb_missing"}
    items = _media_states()
    meta = dict(items.get(media_id) or {})
    meta["thumb_mode"] = mode
    items[media_id] = meta
    _save_media_states(items)
    return {"ok": True, "meta": media_meta(media_id)}


def save_position(media_id: str, position_sec: float) -> dict[str, Any]:
    items = _media_states()
    meta = dict(items.get(media_id) or {})
    meta["resume_sec"] = max(0.0, float(position_sec))
    meta["resume_updated"] = _now()
    items[media_id] = meta
    _save_media_states(items)
    return {"ok": True, "resume_sec": meta["resume_sec"], "meta": media_meta(media_id)}


def all_media_meta() -> dict[str, Any]:
    return {mid: media_meta(mid) for mid in _media_states().keys()}


def _enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    mid = str(item.get("id") or "")
    meta = media_meta(mid)
    out = {**item, **meta}
    if item.get("kind") == "image" and not meta.get("has_viewing"):
        out["thumb_url"] = f"/api/field-popcorn/stream?id={mid}"
        out["active_thumb"] = "stream"
    return out


def _settings() -> dict[str, Any]:
    saved = _load(SETTINGS, {})
    doctrine = _load(DOCTRINE, {})
    return {
        "filter": saved.get("filter") or "all",
        "last_media_id": saved.get("last_media_id"),
        "volume": float(saved.get("volume", 1.0)),
        "playback_rate": float(saved.get("playback_rate", 1.0)),
        "rotation": saved.get("rotation") or "auto",
        "zoom": float(saved.get("zoom", 1.0)),
    }


def posture(*, rescan: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    if rescan or policy.get("scan_on_open", True):
        lib = scan_library(force=rescan)
    else:
        lib = _load(LIBRARY, {}) or scan_library()
    settings = _settings()
    doc = {
        "schema": "field-popcorn/v1",
        "ts": _now(),
        "ok": True,
        "title": "Popcorn",
        "doctrine": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "palette": doctrine.get("palette") or {},
        "policy": policy,
        "library": {
            "scanned": lib.get("scanned"),
            "count": lib.get("count", 0),
            "by_kind": lib.get("by_kind") or {},
            "roots": lib.get("roots") or [],
        },
        "settings": settings,
        "routes": doctrine.get("routes") or {},
        "controls": doctrine.get("controls") or {},
        "codec_doctrine": doctrine.get("codec_doctrine") or "field-media-codec-doctrine.json",
        "codec_tree": {
            "containers": len((_codec_doctrine().get("containers") or [])),
            "video_codecs": len((_codec_doctrine().get("video_codecs") or [])),
            "audio_codecs": len((_codec_doctrine().get("audio_codecs") or [])),
        },
        "inspector": {
            "doctrine": doctrine.get("inspector") or "field-media-inspector-doctrine.json",
            "generation_sources": doctrine.get("generation_sources") or [],
            "detail_formats": (_load(INSPECTOR_DOCTRINE, {}).get("file_detail_formats") or []),
            "summary": (_inspector_mod().cache_summary() if _inspector_mod() else {}),
        },
        "ellie_fier": {
            "doctrine": doctrine.get("ellie_fier") or "field-ellie-fier-doctrine.json",
            "route": (doctrine.get("routes") or {}).get("ellie_fier") or "/api/field-ellie-fier",
        },
        "posture": (
            f"Popcorn — {lib.get('count', 0)} items · "
            f"V{lib.get('by_kind', {}).get('video', 0)} "
            f"A{lib.get('by_kind', {}).get('audio', 0)} "
            f"I{lib.get('by_kind', {}).get('image', 0)}"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def library(kind: str | None = None, query: str | None = None) -> dict[str, Any]:
    lib = _load(LIBRARY, {}) or scan_library()
    items = [_enrich_item(i) for i in list(lib.get("items") or [])]
    if kind and kind != "all":
        items = [i for i in items if i.get("kind") == kind]
    if query:
        q = query.lower().strip()
        items = [i for i in items if q in (i.get("name") or "").lower()]
    return {
        "ok": True,
        "count": len(items),
        "items": items,
        "scanned": lib.get("scanned"),
    }


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"filter", "last_media_id", "volume", "playback_rate", "rotation", "zoom"}
    saved = _load(SETTINGS, {})
    for k, v in patch.items():
        if k in allowed:
            saved[k] = v
    _save_atomic(SETTINGS, saved)
    return posture()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        rescan = "--rescan" in sys.argv[2:]
        print(json.dumps(posture(rescan=rescan), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_library(force=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "library":
        kind = sys.argv[2] if len(sys.argv) > 2 else None
        q = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(library(kind, q), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) > 2:
        item = resolve_media(sys.argv[2])
        print(json.dumps({"ok": bool(item), "item": item}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    if cmd == "thumb" and len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(
            save_thumb(
                str(payload.get("media_id") or ""),
                str(payload.get("mode") or "viewing"),
                str(payload.get("data_url") or ""),
                aspect_ratio=payload.get("aspect_ratio"),
                time_sec=payload.get("time_sec"),
                title=payload.get("title"),
            ),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "thumb-mode" and len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(
            set_thumb_mode(str(payload.get("media_id") or ""), str(payload.get("mode") or "viewing")),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "position" and len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(
            save_position(str(payload.get("media_id") or ""), float(payload.get("position_sec") or 0)),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "meta" and len(sys.argv) > 2:
        print(json.dumps({"ok": True, "meta": media_meta(sys.argv[2])}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "inspect" and len(sys.argv) > 2:
        deep = "--light" not in sys.argv[3:]
        print(json.dumps(inspect_media(sys.argv[2], deep=deep), ensure_ascii=False, indent=2))
        return 0
    if cmd == "details" and len(sys.argv) > 2:
        print(json.dumps(file_details(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(
        "usage: field-popcorn-player.py [json|scan|library|inspect ID|details ID|thumb JSON|thumb-mode JSON|position JSON|meta ID]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())