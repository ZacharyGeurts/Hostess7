#!/usr/bin/env python3
"""H7/7 — universal Hostess 7 container: any file, smaller, self-headered, portable."""
from __future__ import annotations

import errno
import hashlib
import importlib.util
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import zlib
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7-doctrine.json"
SHADOW_REGISTRY = STATE / "h7-shadow-registry.json"
_FIELD_TECH_NO_FIELD = os.environ.get("FIELD_TECH_NO_FIELD", "").strip().lower() in ("1", "true", "yes")
if not _FIELD_TECH_NO_FIELD:
    STATE.mkdir(parents=True, exist_ok=True)

MAGIC = b"H7\x07\x01"
MAGIC_H7E = b"H7E\x01"
FORMAT = "h7/7"
FORMAT_H7E = "h7e/1"
HEADER_SCHEMA = "h7/7-header/v1"
PORTABLE_SCHEMA = "h7/7-portable/v1"
CANONICAL_LAYER = 1
FACE_CAP = 4096
ZLIB_LEVEL = 9
XATTR_FMT = "user.hostess7.format"
XATTR_FACE = "user.hostess7.face"
SKIP_SUFFIXES = {".h7-shadow", ".snap.tmp", ".tmp"}
SKIP_NAMES = {"h7-shadow-registry.json", "field-h7-migrate-manifest.json"}


class H7FormatError(ValueError):
    pass


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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def is_h7_blob(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == MAGIC


def is_h7e_blob(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == MAGIC_H7E


FORMAT_H7S = "h7s/1"
HOSTESS7_CONTAINER_FORMATS = frozenset({FORMAT, FORMAT_H7E, FORMAT_H7S})


def is_h7s_blob(data: bytes) -> bool:
    h7s = _import_mod("field_h7s_blob", "field-h7s-format.py")
    if h7s and hasattr(h7s, "is_h7s_blob"):
        return bool(h7s.is_h7s_blob(data))
    return len(data) >= 4 and data[:4] == b"H7S\x01"


def classify_hostess7_blob(data: bytes) -> dict[str, Any]:
    """Classify H7 family container — h7/7, h7e/1, h7s/1, or native."""
    if is_h7e_blob(data):
        return {"ok": True, "format": FORMAT_H7E, "is_container": True, "magic": "H7E\\x01"}
    if is_h7s_blob(data):
        return {"ok": True, "format": FORMAT_H7S, "is_container": True, "magic": "H7S\\x01"}
    if is_h7_blob(data):
        try:
            header, _, _ = parse_h7(data)
        except H7FormatError:
            header = {}
        return {
            "ok": True,
            "format": FORMAT,
            "is_container": True,
            "magic": "H7\\x07\\x01",
            "inner_format": header.get("inner_format") or header.get("format"),
            "release_kind": header.get("release_kind"),
        }
    return {"ok": True, "format": "native", "is_container": False}


def unwrap_hostess7_bytes(data: bytes) -> tuple[bytes, dict[str, Any]]:
    """Peel one Hostess7 container layer to inner bytes (lossless where supported)."""
    cls = classify_hostess7_blob(data)
    fmt = str(cls.get("format") or "native")
    if fmt == FORMAT_H7E:
        _, raw, _ = decompress_h7e(data, verify=True)
        return raw, {**cls, "unwrapped": True}
    if fmt == FORMAT_H7S:
        h7s = _import_mod("field_h7s_unwrap", "field-h7s-format.py")
        if h7s and hasattr(h7s, "restore_bytes"):
            try:
                props = h7s.read_properties(data) if hasattr(h7s, "read_properties") else {}
                if props.get("lossless_restore", True):
                    return h7s.restore_bytes(data), {**cls, "unwrapped": True}
            except Exception as exc:
                raise H7FormatError(f"H7s unwrap failed: {exc}") from exc
        raise H7FormatError("H7s pack is execute-only (chips_redense) — cannot re-wrap without native source")
    if fmt == FORMAT:
        _, raw, _ = decompress_bytes(data, verify=True)
        return raw, {**cls, "unwrapped": True}
    return data, cls


def guard_pack_source(
    src: Path,
    target_format: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """No double-wrap across H7 / H7e / H7s — unwrap or skip."""
    blob = src.read_bytes()
    cls = classify_hostess7_blob(blob)
    src_fmt = str(cls.get("format") or "native")
    target_format = str(target_format)
    if src_fmt == target_format and not force:
        return {
            "ok": True,
            "skip": True,
            "reason": "never_rewrap_same_format",
            "source_format": src_fmt,
            "target_format": target_format,
            "path": str(src),
        }
    if src_fmt in HOSTESS7_CONTAINER_FORMATS and target_format in HOSTESS7_CONTAINER_FORMATS:
        return {
            "ok": True,
            "skip": False,
            "unwrap": True,
            "reason": "unwrap_before_cross_pack",
            "source_format": src_fmt,
            "target_format": target_format,
            "path": str(src),
        }
    return {
        "ok": True,
        "skip": False,
        "unwrap": src_fmt in HOSTESS7_CONTAINER_FORMATS,
        "source_format": src_fmt,
        "target_format": target_format,
        "path": str(src),
    }


def source_bytes_for_pack(src: Path, target_format: str, *, force: bool = False) -> tuple[bytes, dict[str, Any]]:
    """Resolve pack input — skip signal, native bytes, or guard metadata."""
    guard = guard_pack_source(src, target_format, force=force)
    if guard.get("skip"):
        return b"", guard
    blob = src.read_bytes()
    if guard.get("unwrap"):
        raw, cls = unwrap_hostess7_bytes(blob)
        guard["unwrapped_from"] = cls.get("format")
        return raw, guard
    return blob, guard





def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable_recipe(
    *,
    payload_sha256: str,
    byte_count: int,
    inner_kind: str,
    face: dict[str, Any],
    original_name: str,
    original_extension: str,
) -> dict[str, Any]:
    """Minimal self-contained restore map — stdlib zlib+json+struct only."""
    return {
        "schema": PORTABLE_SCHEMA,
        "magic_hex": "48370701",
        "layout": "magic|u32le hdr_len|hdr_json|u32le face_len|face|zlib(payload)",
        "restore": "zlib.decompress(blob[offset:])",
        "verify": f"sha256:{payload_sha256}",
        "byte_count": byte_count,
        "inner_kind": inner_kind,
        "original_name": original_name,
        "original_extension": original_extension,
        "face_id": face.get("face_format_id"),
        "face_mime": face.get("face_mime"),
        "encoding": "utf-8" if inner_kind == "raw_utf8" else "binary",
        "stdlib": ["zlib", "hashlib", "json", "struct"],
    }


def _format_table() -> list[dict[str, Any]]:
    ff = _import_mod("field_file_formats", "field-file-formats.py")
    if ff and hasattr(ff, "build_table"):
        try:
            return list((ff.build_table() or {}).get("formats") or [])
        except Exception:
            pass
    return []


def _sniff_binary_face(data: bytes, ext: str) -> dict[str, Any]:
    table = _format_table()
    ext = (ext or "").lower()
    magics: tuple[tuple[bytes, str], ...] = (
        (b"\x89PNG\r\n\x1a\n", "png"),
        (b"\xff\xd8\xff", "jpeg"),
        (b"GIF87a", "gif"),
        (b"GIF89a", "gif"),
        (b"%PDF", "pdf"),
        (b"PK\x03\x04", "zip"),
        (b"\x7fELF", "elf"),
        (b"RIFF", "wav"),
    )
    for magic, fid_hint in magics:
        if data[: len(magic)] == magic:
            for row in table:
                if str(row.get("id") or "") == fid_hint:
                    return _face_row(row)
    if ext:
        for row in table:
            exts = [str(e).lower() for e in (row.get("extensions") or [])]
            if ext in exts:
                return _face_row(row)
    return {
        "face_format_id": "octet-stream",
        "face_label": "Binary",
        "face_extension": ext or ".bin",
        "face_mime": "application/octet-stream",
        "face_family": "data",
    }


def pick_face_format(
    *,
    path: Path | None = None,
    data: bytes = b"",
    text: str = "",
    hint_ext: str | None = None,
) -> dict[str, Any]:
    """Best face format from file-format database — BE the native type on read."""
    ext = (hint_ext or (path.suffix if path else "") or ".txt").lower()
    raw = data if data else (text.encode("utf-8") if text else b"")
    if raw and not _looks_text(raw):
        return _sniff_binary_face(raw, ext)

    text_head = (text or raw[:FACE_CAP].decode("utf-8", errors="replace"))[:FACE_CAP]
    stripped = text_head.lstrip()
    table = _format_table()
    library_exts = {".h7", ".h7c", ".h7snap"}

    def _match(fid: str) -> dict[str, Any] | None:
        for row in table:
            if str(row.get("id") or "") == fid:
                return row
        return None

    if stripped.startswith(("{", "[")):
        row = _match("json") or _match("book_json")
        if row:
            return _face_row(row)
    if stripped.startswith("#") or ext in (".md", ".markdown"):
        row = _match("markdown") or _match("md")
        if row:
            return _face_row(row)
    if stripped.lower().startswith("<!doctype") or stripped.startswith("<") or ext == ".html":
        row = _match("html")
        if row:
            return _face_row(row)

    if ext not in library_exts:
        for row in table:
            exts = [str(e).lower() for e in (row.get("extensions") or [])]
            if ext in exts:
                return _face_row(row)

    row = _match("h7b") or _match("h7b_fly")
    if row:
        return _face_row(row)
    return {
        "face_format_id": "plaintext",
        "face_label": "Plain text",
        "face_extension": ext or ".txt",
        "face_mime": "text/plain",
        "face_family": "document",
    }


def _face_row(row: dict[str, Any]) -> dict[str, Any]:
    exts = row.get("extensions") or [row.get("primary_extension") or ".txt"]
    ext = str(exts[0] if exts else ".txt")
    return {
        "face_format_id": str(row.get("id") or "unknown"),
        "face_label": str(row.get("label") or row.get("id") or "unknown"),
        "face_extension": ext,
        "face_mime": row.get("mime") or "application/octet-stream",
        "face_family": row.get("family") or "data",
        "face_magic": row.get("magic"),
    }


def _looks_text(data: bytes) -> bool:
    if not data:
        return True
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _face_prefix_bytes(data: bytes, face: dict[str, Any]) -> bytes:
    cap = min(len(data), FACE_CAP)
    prefix = data[:cap]
    fid = str(face.get("face_format_id") or "")
    if prefix:
        if fid in ("markdown", "md", "plaintext", "json", "html", "h7b", "h7b_fly"):
            return prefix
        if prefix.startswith(b"#") or prefix.lstrip().startswith((b"{", b"[", b"<")):
            return prefix
        return prefix
    if fid == "json":
        return b'{\n  "face": true\n}\n'
    if fid == "html":
        return b"<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>\n"
    return prefix


def _progress_start(
    *,
    job: str,
    fmt: str,
    src: str,
    dest: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[Any | None, Any | None]:
    prog_mod = _import_mod("field_compression_progress", "field-compression-progress.py")
    if not prog_mod or not hasattr(prog_mod, "start_pack"):
        return None, prog_mod
    return prog_mod.start_pack(job=job, fmt=fmt, src=src, dest=dest, meta=meta), prog_mod


def _progress_panel(prog_mod: Any | None) -> str:
    if prog_mod and hasattr(prog_mod, "panel_path"):
        return str(prog_mod.panel_path())
    return ""


def compress_payload(
    data: bytes,
    *,
    progress: Any | None = None,
    pct_lo: float = 20.0,
    pct_hi: float = 85.0,
) -> tuple[bytes, dict[str, Any]]:
    if progress:
        progress.phase("compress", pct_lo, f"zlib level {ZLIB_LEVEL} · {len(data)} bytes")
    compressed = zlib.compress(data, level=ZLIB_LEVEL)
    ratio = round(len(data) / max(1, len(compressed)), 4)
    if progress:
        progress.phase("compress", pct_hi, f"ratio {ratio}x · {len(compressed)} bytes")
    return compressed, {
        "compressor": "zlib",
        "zlib_level": ZLIB_LEVEL,
        "raw_bytes": len(data),
        "packed_bytes": len(compressed),
        "compression_ratio": ratio,
        "portable": True,
    }


def pack_bytes(
    data: bytes,
    meta: dict[str, Any] | None = None,
    *,
    path: Path | None = None,
    hint_ext: str | None = None,
    face: dict[str, Any] | None = None,
    progress: Any | None = None,
) -> bytes:
    """Pack any bytes to H7/7 — zlib payload, portable header, native face disguise."""
    m = dict(meta or {})
    is_text = _looks_text(data)
    inner_kind = "raw_utf8" if is_text else "raw_bytes"
    if progress:
        progress.phase("read", 8.0, f"{len(data)} bytes loaded")
    face = face or pick_face_format(path=path, data=data, hint_ext=hint_ext)
    face_bytes = _face_prefix_bytes(data, face)
    payload, chips_meta = compress_payload(data, progress=progress, pct_lo=25.0, pct_hi=80.0)
    if progress:
        progress.phase("header", 82.0, "H7/7 portable header")

    digest = _sha256(data)
    orig_name = str(m.get("original_name") or (path.name if path else m.get("id") or ""))
    orig_ext = str(m.get("original_extension") or (path.suffix if path else ""))
    header: dict[str, Any] = {
        "schema": HEADER_SCHEMA,
        "format": FORMAT,
        "byte_count": len(data),
        "payload_sha256": digest,
        "lossless": True,
        "field_layer": CANONICAL_LAYER,
        "inner_kind": inner_kind,
        "original_name": orig_name,
        "original_extension": orig_ext,
        "face": {
            "id": face.get("face_format_id"),
            "label": face.get("face_label"),
            "ext": face.get("face_extension"),
            "mime": face.get("face_mime"),
        },
        "compress": chips_meta,
        "portable": _portable_recipe(
            payload_sha256=digest,
            byte_count=len(data),
            inner_kind=inner_kind,
            face=face,
            original_name=orig_name,
            original_extension=orig_ext,
        ),
        "packed_at": _now(),
        **{k: v for k, v in m.items() if k not in ("format", "true_format", "original_name", "original_extension")},
    }
    if is_text:
        header["char_count"] = len(data.decode("utf-8"))
    header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(header_json) > 65535:
        raise H7FormatError("H7/7 header too large")
    return b"".join([
        MAGIC,
        struct.pack("<I", len(header_json)),
        header_json,
        struct.pack("<I", len(face_bytes)),
        face_bytes,
        payload,
    ])


def pack_h7(
    text: str,
    meta: dict[str, Any] | None = None,
    *,
    path: Path | None = None,
    hint_ext: str | None = None,
) -> bytes:
    return pack_bytes(text.encode("utf-8"), meta, path=path, hint_ext=hint_ext)


def parse_h7(data: bytes) -> tuple[dict[str, Any], bytes, bytes]:
    if len(data) < 12 or data[:4] != MAGIC:
        raise H7FormatError("not H7/7 (bad magic)")
    header_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + header_len
    if end + 4 > len(data):
        raise H7FormatError("truncated H7/7 header")
    header = json.loads(data[start:end].decode("utf-8"))
    face_len = struct.unpack("<I", data[end : end + 4])[0]
    face_start = end + 4
    face_end = face_start + face_len
    if face_end > len(data):
        raise H7FormatError("truncated H7/7 face")
    face_bytes = data[face_start:face_end]
    payload = data[face_end:]
    return header, face_bytes, payload


def instant_header(data: bytes | Path) -> dict[str, Any]:
    """Read metadata from header only — no payload decompress."""
    blob = data.read_bytes() if isinstance(data, Path) else data
    if not is_h7_blob(blob):
        return {"ok": False, "error": "not_h7"}
    header, face_bytes, payload = parse_h7(blob)
    return {
        "ok": True,
        "instant": True,
        "format": FORMAT,
        "header": header,
        "face_bytes": len(face_bytes),
        "payload_bytes": len(payload),
        "portable": header.get("portable"),
        "properties": read_properties(blob),
    }


def decompress_bytes(data: bytes, *, verify: bool = True) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    t0 = time.perf_counter()
    header, face_bytes, payload = parse_h7(data)
    try:
        raw = zlib.decompress(payload)
    except zlib.error as exc:
        raise H7FormatError(f"H7/7 payload corrupt: {exc}") from exc

    if verify:
        expect = header.get("payload_sha256") or header.get("text_sha256")
        got = _sha256(raw)
        if expect and got != expect:
            raise H7FormatError("H7/7 integrity check failed (sha256)")

    stats = {
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "format": FORMAT,
        "lossless": True,
        "face_format_id": (header.get("face") or {}).get("id") or (header.get("face") or {}).get("face_format_id"),
        "chips": header.get("compress") or header.get("chips"),
        "properties_only": True,
        "byte_count": len(raw),
        "inner_kind": header.get("inner_kind"),
    }
    return header, raw, stats


def decompress_h7(data: bytes, *, verify: bool = True) -> tuple[dict[str, Any], str, dict[str, Any]]:
    header, raw, stats = decompress_bytes(data, verify=verify)
    kind = header.get("inner_kind") or "raw_utf8"
    if kind == "raw_bytes" and not _looks_text(raw):
        raise H7FormatError("H7/7 payload is binary — use decompress_bytes()")
    text = raw.decode("utf-8")
    stats["char_count"] = len(text)
    return header, text, stats


def read_properties(data: bytes | Path) -> dict[str, Any]:
    """Properties-only reveal — true format H7/7; face format for native disguise."""
    if isinstance(data, Path):
        blob = data.read_bytes()
        path = data
    else:
        blob = data
        path = None
    if not is_h7_blob(blob):
        return {"ok": False, "error": "not_h7", "path": str(path) if path else None}
    header, face_bytes, payload = parse_h7(blob)
    face = header.get("face") or {}
    chips = header.get("compress") or header.get("chips") or {}
    return {
        "ok": True,
        "schema": "field-h7-properties/v1",
        "path": str(path) if path else None,
        "true_format": FORMAT,
        "is_h7": True,
        "properties_only_reveal": True,
        "disguise_identical": True,
        "instant_header": True,
        "face_format_id": face.get("id") or face.get("face_format_id"),
        "face_label": face.get("label") or face.get("face_label"),
        "face_extension": face.get("ext") or face.get("face_extension"),
        "face_mime": face.get("mime") or face.get("face_mime"),
        "face_family": face.get("family") or face.get("face_family"),
        "face_bytes": len(face_bytes),
        "payload_bytes": len(payload),
        "field_layer": header.get("field_layer", CANONICAL_LAYER),
        "ironclad_citation": header.get("ironclad_citation"),
        "lossless": header.get("lossless", True),
        "chips": chips,
        "compression_ratio": chips.get("compression_ratio"),
        "byte_count": header.get("byte_count"),
        "payload_sha256": header.get("payload_sha256"),
        "original_name": header.get("original_name"),
        "original_extension": header.get("original_extension"),
        "portable": header.get("portable"),
        "title": header.get("title"),
        "id": header.get("id"),
    }


def _set_xattr(path: Path, header: dict[str, Any]) -> None:
    face = header.get("face") or {}
    try:
        import xattr  # type: ignore
        xattr.setxattr(str(path), XATTR_FMT, FORMAT.encode("utf-8"))
        fid = face.get("id") or face.get("face_format_id") or ""
        xattr.setxattr(str(path), XATTR_FACE, str(fid).encode("utf-8"))
    except Exception:
        try:
            os.setxattr(str(path), XATTR_FMT, FORMAT.encode("utf-8"))
            fid = face.get("id") or face.get("face_format_id") or ""
            os.setxattr(str(path), XATTR_FACE, str(fid).encode("utf-8"))
        except OSError:
            pass


def _load_shadow_registry() -> dict[str, Any]:
    doc = _load(SHADOW_REGISTRY, {})
    doc.setdefault("schema", "h7-shadow-registry/v1")
    doc.setdefault("entries", [])
    return doc


def _register_shadow(original: Path, shadow: Path, *, reason: str) -> None:
    reg = _load_shadow_registry()
    entries = list(reg.get("entries") or [])
    entries.append({
        "original": str(original),
        "shadow": str(shadow),
        "reason": reason,
        "registered_at": _now(),
        "apply_at": "reboot",
    })
    reg["entries"] = entries[-512:]
    reg["updated"] = _now()
    _save(SHADOW_REGISTRY, reg)


def snap_replace(path: Path, blob: bytes, header: dict[str, Any] | None = None) -> dict[str, Any]:
    """Atomic in-place replace; shadow steal when file is busy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = path.with_suffix(path.suffix + ".snap.tmp")
    snap.write_bytes(blob)
    try:
        snap.replace(path)
        if header:
            _set_xattr(path, header)
        return {"ok": True, "path": str(path), "shadowed": False, "bytes": len(blob)}
    except OSError as exc:
        if exc.errno not in (errno.EBUSY, errno.ETXTBSY, errno.EACCES, errno.EPERM):
            try:
                snap.unlink(missing_ok=True)
            except OSError:
                pass
            raise
    shadow = path.with_suffix(path.suffix + ".h7-shadow")
    shadow.write_bytes(blob)
    try:
        snap.unlink(missing_ok=True)
    except OSError:
        pass
    _register_shadow(path, shadow, reason=str(exc))
    return {
        "ok": True,
        "path": str(path),
        "shadowed": True,
        "shadow": str(shadow),
        "reason": str(exc),
        "apply_at": "reboot",
        "bytes": len(blob),
    }


def write_h7_file(
    path: Path,
    text: str,
    meta: dict[str, Any] | None = None,
    *,
    hint_ext: str | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    raw = data if data is not None else text.encode("utf-8")
    blob = pack_bytes(raw, meta, path=path, hint_ext=hint_ext)
    header, _, _ = parse_h7(blob)
    rep = snap_replace(path, blob, header)
    return {
        **rep,
        "format": FORMAT,
        "properties": read_properties(path),
    }


def _read_legacy_source(path: Path) -> tuple[bytes, dict[str, Any]]:
    blob = path.read_bytes()
    h7s = _import_mod("field_h7s", "field-h7s-format.py")
    if h7s and hasattr(h7s, "is_h7s_blob") and h7s.is_h7s_blob(blob):
        props = h7s.read_properties(blob) if hasattr(h7s, "read_properties") else {"ok": True}
        if props.get("lossless_restore") and hasattr(h7s, "restore_bytes"):
            raw = h7s.restore_bytes(blob)
            return raw, {**props, "is_h7s": True, "is_h7": False, "true_format": "h7s/1"}
        return blob, {**props, "is_h7s": True, "is_h7": False, "true_format": "h7s/1", "execute_only": True}
    if is_h7_blob(blob):
        header, raw, stats = decompress_bytes(blob, verify=True)
        return raw, {**read_properties(blob), "stats": stats, "header": header, "is_h7": True}

    h7c = _import_mod("field_h7c", "field-h7c-compression.py")
    if h7c and blob[:4] in (
        getattr(h7c, "MAGIC_V1", b""),
        getattr(h7c, "MAGIC_V2", b""),
        getattr(h7c, "MAGIC_V3", b""),
        getattr(h7c, "MAGIC_V4", b"H7C\x04"),
    ):
        header, text, stats = h7c.decompress_h7c(
            blob, verify=True, update_balance_table=False, combinatronic_balance=False,
        )
        raw = text.encode("utf-8")
        return raw, {
            "ok": True,
            "true_format": header.get("format"),
            "migrated_from": header.get("format"),
            "is_h7": False,
            "stats": stats,
        }

    h7b_path = INSTALL / "Hostess7" / "scripts" / "field_h7_book.py"
    if h7b_path.is_file():
        spec = importlib.util.spec_from_file_location("field_h7_book", h7b_path)
        if spec and spec.loader:
            h7b = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(h7b)
            if blob[:4] in (getattr(h7b, "MAGIC", b""), getattr(h7b, "MAGIC_FLY", b"")):
                header, text = h7b.unpack_h7(blob, verify=True)
                return text.encode("utf-8"), {
                    "ok": True,
                    "true_format": header.get("format"),
                    "is_h7": False,
                    "header": header,
                }

    return blob, {
        "ok": True,
        "true_format": "native",
        "migrated_from": path.suffix,
        "is_h7": False,
    }


def _read_source(path: Path) -> tuple[bytes, dict[str, Any]]:
    return _read_legacy_source(path)


def open_any_h7_path(path: Path | str) -> tuple[str, dict[str, Any]]:
    raw, props = _read_legacy_source(Path(path))
    if not _looks_text(raw):
        raise H7FormatError("binary payload — use decompress_bytes()")
    return raw.decode("utf-8"), props


def adopt_path(
    src: Path,
    *,
    dest: Path | None = None,
    inplace: bool = True,
    remove_src: bool = True,
    force: bool = False,
    apply_corrects: bool = False,
) -> dict[str, Any]:
    """Adopt any file into H7/7 — smaller, same bytes, native face, in-place snap."""
    src = Path(src)
    if not src.is_file():
        return {"ok": False, "path": str(src), "error": "not_found"}

    blob = src.read_bytes()
    cls = classify_hostess7_blob(blob)
    if cls.get("is_container") and str(cls.get("format")) == FORMAT and not force:
        props = read_properties(blob)
        return {
            "ok": True,
            "path": str(src),
            "skipped": "already_h7",
            "changed": False,
            "properties": props,
        }
    if cls.get("is_container") and str(cls.get("format")) in (FORMAT_H7E, FORMAT_H7S) and not force:
        return {
            "ok": True,
            "path": str(src),
            "skipped": f"already_{cls.get('format', '').replace('/', '_')}",
            "changed": False,
            "source_format": cls.get("format"),
        }

    raw, props = _read_legacy_source(src)
    if apply_corrects and _looks_text(raw):
        corr = _import_mod("field_h7c_correct", "field-h7c-correct.py")
        if corr and hasattr(corr, "correct_text"):
            text, _, _ = corr.correct_text(raw.decode("utf-8"))
            raw = text.encode("utf-8")

    out = dest or src
    if not inplace and dest is None:
        out = src.with_suffix(".h7")

    face = pick_face_format(path=src, data=raw, hint_ext=src.suffix)
    meta = {
        "id": src.stem,
        "title": src.stem.replace("_", " ").title(),
        "source": str(src),
        "original_name": src.name,
        "original_extension": src.suffix,
        "migrated_from": props.get("true_format") or props.get("migrated_from") or src.suffix,
        "adopted_at": _now(),
    }
    book_json = src.parent / "book.json"
    if book_json.is_file():
        bj = _load(book_json, {})
        meta["title"] = bj.get("title") or meta["title"]
        meta["id"] = bj.get("id") or meta["id"]
        meta["dewey"] = bj.get("dewey")
        meta["author"] = bj.get("author")

    progress, prog_mod = _progress_start(
        job="adopt_path",
        fmt=FORMAT,
        src=str(src),
        dest=str(out),
        meta={"inplace": inplace},
    )
    try:
        if progress:
            progress.phase("read", 5.0, f"migrating {src.name}")
        packed = pack_bytes(raw, meta, path=src, hint_ext=face.get("face_extension"), face=face, progress=progress)
        if progress:
            progress.phase("write", 88.0, f"snap {out.name}")
        header, _, _ = parse_h7(packed)
        rep = snap_replace(out, packed, header)
    except Exception as exc:
        if progress:
            progress.finish(ok=False, result={"error": str(exc)})
        raise

    if book_json.is_file():
        bj = _load(book_json, {})
        bj["format"] = FORMAT
        try:
            bj["h7"] = str(out.relative_to(INSTALL))
        except ValueError:
            bj["h7"] = str(out)
        bj.pop("h7c", None)
        bj["face_format"] = face.get("face_format_id")
        bj["properties_only_h7"] = True
        book_json.write_text(json.dumps(bj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if remove_src and src.is_file() and src.resolve() != out.resolve():
        src.unlink()
    elif out.resolve() == src.resolve():
        remove_src = False

    before = len(blob)
    after = len(packed)
    out_doc = {
        **rep,
        "ok": True,
        "changed": True,
        "format": FORMAT,
        "migrated_from": str(src),
        "face": face,
        "bytes_before": before,
        "bytes_after": after,
        "smaller": after < before,
        "properties": read_properties(out),
        "progress_panel": _progress_panel(prog_mod),
    }
    if progress:
        progress.finish(ok=True, result=out_doc)
    return out_doc


def migrate_path_to_h7(
    src: Path,
    *,
    dest: Path | None = None,
    remove_src: bool = True,
    apply_corrects: bool = True,
) -> dict[str, Any]:
    return adopt_path(
        src,
        dest=dest,
        inplace=dest is None,
        remove_src=remove_src,
        apply_corrects=apply_corrects,
    )


def _should_adopt(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name
    if name in SKIP_NAMES:
        return False
    for suf in SKIP_SUFFIXES:
        if name.endswith(suf):
            return False
    if path.suffix == ".h7-shadow":
        return False
    return True


def adopt_tree(
    root: Path,
    *,
    apply: bool = True,
    limit: int = 0,
    extensions: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Walk tree and adopt files to H7/7 in place when seen."""
    paths: list[Path] = []
    if root.is_file():
        paths = [root]
    elif root.is_dir():
        for p in sorted(root.rglob("*")):
            if not _should_adopt(p):
                continue
            if extensions and p.suffix.lower() not in extensions:
                continue
            paths.append(p)
    if limit > 0:
        paths = paths[:limit]

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for i, src in enumerate(paths):
        try:
            if apply:
                row = adopt_path(src, inplace=True, remove_src=False, apply_corrects=False)
            else:
                blob = src.read_bytes()
                if is_h7_blob(blob):
                    row = {"ok": True, "path": str(src), "skipped": "already_h7", "dry_run": True}
                else:
                    row = {
                        "ok": True,
                        "path": str(src),
                        "bytes": len(blob),
                        "would_adopt": True,
                        "dry_run": True,
                    }
        except Exception as exc:
            row = {"ok": False, "path": str(src), "error": str(exc)}
        rows.append(row)
        if not row.get("ok"):
            errors.append(row)
        if (i + 1) % 50 == 0:
            print(f"h7-adopt {i + 1}/{len(paths)} err={len(errors)}", file=sys.stderr, flush=True)

    manifest = {
        "schema": "field-h7-adopt-manifest/v1",
        "updated": _now(),
        "ok": len(errors) == 0,
        "apply": apply,
        "root": str(root),
        "file_count": len(paths),
        "adopted": sum(1 for r in rows if r.get("changed")),
        "skipped": sum(1 for r in rows if r.get("skipped")),
        "shadowed": sum(1 for r in rows if r.get("shadowed")),
        "errors": errors[:24],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
    if apply:
        _save(STATE / "field-h7-adopt-manifest.json", manifest)
    return manifest


def _folder_tar_stats(folder: Path) -> tuple[int, int]:
    files = 0
    total = 0
    for path in folder.rglob("*"):
        if not path.is_file() or path.name.endswith((".tmp", ".pyc")):
            continue
        files += 1
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return files, total


def _tar_folder_bytes(folder: Path, *, progress: Any | None = None) -> tuple[bytes, str]:
    if not folder.is_dir():
        raise H7FormatError(f"not a folder: {folder}")
    root_name = folder.name
    if progress:
        progress.phase("scan", 1.0, f"scanning {root_name}")
    file_count, byte_total = _folder_tar_stats(folder)
    if progress:
        progress.phase("scan", 5.0, f"{file_count} files · {byte_total} bytes", files=file_count, bytes_total=byte_total)
    done_files = 0
    done_bytes = 0
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name.endswith((".tmp", ".pyc")):
                continue
            rel = path.relative_to(folder).as_posix()
            arcname = f"{root_name}/{rel}" if rel else root_name
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            tf.add(path, arcname=arcname, recursive=False)
            done_files += 1
            done_bytes += size
            if progress and byte_total:
                pct = 5.0 + (done_bytes / byte_total) * 55.0
                progress.phase(
                    "tar",
                    pct,
                    f"{done_files}/{file_count} files",
                    files_done=done_files,
                    files_total=file_count,
                    bytes_done=done_bytes,
                    bytes_total=byte_total,
                )
    if progress:
        progress.phase("tar", 60.0, f"tar ready · {done_files} files")
    return buf.getvalue(), root_name


def _tar_bytes_to_folder(tar_bytes: bytes, dest: Path) -> str:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tf:
        names = tf.getnames()
        root = names[0].split("/")[0] if names else ""
        tf.extractall(dest, filter="data")
    return root


def pack_h7e_bytes(
    tar_bytes: bytes,
    *,
    root_name: str = "",
    meta: dict[str, Any] | None = None,
    progress: Any | None = None,
) -> bytes:
    """H7e/1 — extractable folder archive (zlib tar) derived from H7 portable layout."""
    payload, chips_meta = compress_payload(tar_bytes, progress=progress)
    digest = _sha256(tar_bytes)
    m = dict(meta or {})
    header: dict[str, Any] = {
        "schema": "h7e/1-header/v1",
        "format": FORMAT_H7E,
        "byte_count": len(tar_bytes),
        "payload_sha256": digest,
        "lossless": True,
        "field_layer": CANONICAL_LAYER,
        "inner_kind": "tar_folder",
        "extractable": True,
        "extract_to": "cwd",
        "root_folder": root_name or m.get("root_folder") or "",
        "compress": chips_meta,
        "portable": _portable_recipe(
            payload_sha256=digest,
            byte_count=len(tar_bytes),
            inner_kind="tar_folder",
            face={"face_format_id": "octet-stream"},
            original_name=m.get("original_name") or (f"{root_name}.tar" if root_name else "folder.tar"),
            original_extension=".tar",
        ),
        "packed_at": _now(),
        **{k: v for k, v in m.items() if k not in ("format", "root_folder", "original_name")},
    }
    header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(header_json) > 65535:
        raise H7FormatError("H7e header too large")
    return b"".join([
        MAGIC_H7E,
        struct.pack("<I", len(header_json)),
        header_json,
        struct.pack("<I", 0),
        payload,
    ])


def parse_h7e(data: bytes) -> tuple[dict[str, Any], bytes]:
    if len(data) < 12 or data[:4] != MAGIC_H7E:
        raise H7FormatError("not H7e (bad magic)")
    header_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + header_len
    if end + 4 > len(data):
        raise H7FormatError("truncated H7e header")
    header = json.loads(data[start:end].decode("utf-8"))
    face_len = struct.unpack("<I", data[end : end + 4])[0]
    payload = data[end + 4 + face_len :]
    return header, payload


def decompress_h7e(data: bytes, *, verify: bool = True) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    t0 = time.perf_counter()
    header, payload = parse_h7e(data)
    try:
        raw = zlib.decompress(payload)
    except zlib.error as exc:
        raise H7FormatError(f"H7e payload corrupt: {exc}") from exc
    if verify:
        expect = header.get("payload_sha256")
        got = _sha256(raw)
        if expect and got != expect:
            raise H7FormatError("H7e integrity check failed (sha256)")
    stats = {
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "format": FORMAT_H7E,
        "lossless": True,
        "byte_count": len(raw),
        "packed_bytes": len(data),
        "chips": header.get("compress") or {},
    }
    return header, raw, stats


def pack_folder_h7e(folder: Path, dest: Path, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    progress, prog_mod = _progress_start(
        job="pack_folder_h7e",
        fmt=FORMAT_H7E,
        src=str(folder),
        dest=str(dest),
        meta=meta,
    )
    try:
        tar_bytes, root_name = _tar_folder_bytes(folder, progress=progress)
        m = {
            "original_name": f"{root_name}.h7e",
            "root_folder": root_name,
            "source_path": str(folder),
            **(meta or {}),
        }
        packed = pack_h7e_bytes(tar_bytes, root_name=root_name, meta=m, progress=progress)
        if progress:
            progress.phase("write", 90.0, f"writing {dest.name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(packed)
        tmp.replace(dest)
        if progress:
            progress.phase("write", 98.0, "flush complete")
        out = {
            "ok": True,
            "format": FORMAT_H7E,
            "src": str(folder),
            "dest": str(dest),
            "root_folder": root_name,
            "raw_bytes": len(tar_bytes),
            "packed_bytes": len(packed),
            "compression_ratio": round(len(tar_bytes) / max(1, len(packed)), 4),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "progress_panel": _progress_panel(prog_mod),
        }
        if progress:
            progress.finish(ok=True, result=out)
        return out
    except Exception as exc:
        if progress:
            progress.finish(ok=False, result={"error": str(exc)})
        raise


def pack_h7e_file(src: Path, dest: Path, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if src.is_dir():
        return pack_folder_h7e(src, dest, meta=meta)
    if not src.is_file():
        raise H7FormatError(f"missing source: {src}")
    guard = guard_pack_source(src, FORMAT_H7E)
    if guard.get("skip"):
        return {"ok": True, "skipped": guard.get("reason"), "format": FORMAT_H7E, "src": str(src), "dest": str(dest)}
    t0 = time.perf_counter()
    progress, prog_mod = _progress_start(
        job="pack_h7e_file",
        fmt=FORMAT_H7E,
        src=str(src),
        dest=str(dest),
        meta=meta,
    )
    try:
        if progress:
            progress.phase("read", 10.0, f"loading {src.name}")
        data, guard = source_bytes_for_pack(src, FORMAT_H7E)
        m = {
            "schema": "field-h7e-archive/v1",
            "release_kind": "tar",
            "original_name": src.name,
            "original_extension": src.suffix or ".tar",
            **(meta or {}),
        }
        packed = pack_h7e_bytes(data, root_name=src.stem, meta=m, progress=progress)
        if progress:
            progress.phase("write", 90.0, f"writing {dest.name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(packed)
        tmp.replace(dest)
        out = {
            "ok": True,
            "format": FORMAT_H7E,
            "src": str(src),
            "dest": str(dest),
            "raw_bytes": len(data),
            "packed_bytes": len(packed),
            "compression_ratio": round(len(data) / max(1, len(packed)), 4),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "guard": guard,
            "progress_panel": _progress_panel(prog_mod),
        }
        if progress:
            progress.finish(ok=True, result=out)
        return out
    except Exception as exc:
        if progress:
            progress.finish(ok=False, result={"error": str(exc)})
        raise





def extract_h7e_to_cwd(archive: Path, *, dest: Path | None = None) -> dict[str, Any]:
    """Double-click lane — extract folder archive into dest or archive's parent (cwd)."""
    if not archive.is_file():
        raise H7FormatError(f"missing archive: {archive}")
    t0 = time.perf_counter()
    blob = archive.read_bytes()
    if is_h7e_blob(blob):
        header, tar_bytes, _ = decompress_h7e(blob, verify=True)
    elif is_h7_blob(blob):
        h_header, tar_bytes, _ = decompress_bytes(blob, verify=True)
        header = h_header
    elif is_h7s_blob(blob):
        raise H7FormatError("H7s is slice-execute — use field-h7s-format.py restore/execute, not H7e extract")
    else:
        raise H7FormatError("not H7e/H7 extractable archive")
    target = dest or archive.parent
    target = target.resolve()
    root = _tar_bytes_to_folder(tar_bytes, target)
    return {
        "ok": True,
        "archive": str(archive),
        "dest": str(target),
        "root_folder": root or header.get("root_folder") or "",
        "bytes": len(tar_bytes),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def _bench_shell_compress(
    label: str,
    cmd: list[str],
    src: Path,
    out: Path,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        if cmd[:2] in (["gzip", "-9"], ["xz", "-9"], ["bzip2", "-9"]) and "-c" in cmd:
            with out.open("wb") as fh:
                subprocess.run(cmd, check=True, stdout=fh, stderr=subprocess.PIPE)
        else:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {"ok": False, "id": label, "error": str(exc)}
    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    packed = out.stat().st_size if out.is_file() else 0
    return {
        "ok": True,
        "id": label,
        "packed_bytes": packed,
        "elapsed_ms": elapsed,
        "ratio": round(src.stat().st_size / max(1, packed), 4),
        "path": str(out),
    }


def benchmark_compression(
    src: Path,
    *,
    out_dir: Path | None = None,
    skip_external: bool = False,
) -> dict[str, Any]:
    """Field Tech bench — no field generation; compare H7/H7e vs host compressors."""
    if not src.is_file():
        raise H7FormatError(f"bench requires a file corpus: {src}")
    raw_bytes = src.stat().st_size
    bench_dir = out_dir or (Path("/tmp") / f"field-h7-bench-{int(time.time())}")
    bench_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    def _row(fmt_id: str, packed: int, elapsed: float, extra: dict[str, Any] | None = None) -> None:
        rows.append({
            "id": fmt_id,
            "ok": True,
            "raw_bytes": raw_bytes,
            "packed_bytes": packed,
            "elapsed_ms": round(elapsed, 1),
            "ratio": round(raw_bytes / max(1, packed), 4),
            "under_2gib": packed <= 2 * 1024 * 1024 * 1024,
            **(extra or {}),
        })

    t0 = time.perf_counter()
    h7_out = bench_dir / f"{src.stem}.h7"
    pack_archive_file(src, h7_out)
    _row("h7/7", h7_out.stat().st_size, (time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    h7e_out = bench_dir / f"{src.stem}.h7e"
    pack_h7e_file(src, h7e_out)
    _row("h7e/1", h7e_out.stat().st_size, (time.perf_counter() - t0) * 1000)

    if not skip_external:
        ext_map: list[tuple[str, list[str], Path]] = [
            ("gzip", ["gzip", "-9", "-c", str(src)], bench_dir / f"{src.name}.gz"),
            ("zstd", ["zstd", "-19", "-T0", "-o", str(bench_dir / f"{src.name}.zst"), str(src)], bench_dir / f"{src.name}.zst"),
            ("xz", ["xz", "-9", "-c", str(src)], bench_dir / f"{src.name}.xz"),
            ("bzip2", ["bzip2", "-9", "-c", str(src)], bench_dir / f"{src.name}.bz2"),
            ("zip", ["zip", "-9", "-q", str(bench_dir / f"{src.name}.zip"), str(src)], bench_dir / f"{src.name}.zip"),
            ("7z", ["7z", "a", "-mx=9", "-bd", str(bench_dir / f"{src.name}.7z"), str(src)], bench_dir / f"{src.name}.7z"),
        ]
        for label, cmd, outp in ext_map:
            if label == "gzip":
                row = _bench_shell_compress(label, cmd, src, outp)
            elif label == "xz":
                row = _bench_shell_compress(label, cmd, src, outp)
            elif label == "bzip2":
                row = _bench_shell_compress(label, cmd, src, outp)
            else:
                row = _bench_shell_compress(label, cmd, src, outp)
            if row.get("ok"):
                row["raw_bytes"] = raw_bytes
                row["under_2gib"] = row["packed_bytes"] <= 2 * 1024 * 1024 * 1024
                rows.append(row)
            else:
                rows.append(row)

    rows.sort(key=lambda r: r.get("packed_bytes") or (1 << 62))
    best = rows[0] if rows else {}
    return {
        "schema": "field-h7-compression-bench/v1",
        "ok": True,
        "field_tech_no_field": _FIELD_TECH_NO_FIELD,
        "corpus": str(src),
        "raw_bytes": raw_bytes,
        "bench_dir": str(bench_dir),
        "rows": rows,
        "best": best.get("id"),
        "github_fit": [r["id"] for r in rows if r.get("under_2gib")],
    }


def pack_archive_file(
    src: Path,
    dest: Path,
    *,
    meta: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Wrap a release blob (typically tar) in H7/7 — zlib payload, portable header."""
    if not src.is_file():
        raise H7FormatError(f"missing archive source: {src}")
    guard = guard_pack_source(src, FORMAT, force=force)
    if guard.get("skip"):
        if dest.resolve() != src.resolve():
            dest.write_bytes(src.read_bytes())
        return {
            "ok": True,
            "skipped": guard.get("reason"),
            "format": FORMAT,
            "src": str(src),
            "dest": str(dest),
            "guard": guard,
        }
    t0 = time.perf_counter()
    progress, prog_mod = _progress_start(
        job="pack_archive_file",
        fmt=FORMAT,
        src=str(src),
        dest=str(dest),
        meta=meta,
    )
    try:
        if progress:
            progress.phase("read", 5.0, f"loading {src.name}")
        data, guard = source_bytes_for_pack(src, FORMAT, force=force)
        m = {
            "schema": "field-h7-release-archive/v1",
            "release_kind": "tar",
            "release_role": "ammoos_source",
            "original_name": src.name,
            "original_extension": src.suffix or ".tar",
            **(meta or {}),
        }
        packed = pack_bytes(data, m, path=src, hint_ext=src.suffix or ".tar", progress=progress)
        if progress:
            progress.phase("write", 88.0, f"writing {dest.name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(packed)
        tmp.replace(dest)
        ratio = round(len(data) / max(1, len(packed)), 4)
        out = {
            "ok": True,
            "format": FORMAT,
            "src": str(src),
            "dest": str(dest),
            "raw_bytes": len(data),
            "packed_bytes": len(packed),
            "compression_ratio": ratio,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "guard": guard,
            "progress_panel": _progress_panel(prog_mod),
        }
        if progress:
            progress.finish(ok=True, result=out)
        return out
    except Exception as exc:
        if progress:
            progress.finish(ok=False, result={"error": str(exc)})
        raise


def unpack_archive_file(src: Path, dest: Path | None = None) -> dict[str, Any]:
    """Restore inner release blob from H7/7 archive wrapper."""
    if not src.is_file():
        raise H7FormatError(f"missing archive: {src}")
    t0 = time.perf_counter()
    blob = src.read_bytes()
    if is_h7e_blob(blob):
        header, raw, stats = decompress_h7e(blob, verify=True)
    elif is_h7s_blob(blob):
        raise H7FormatError("use field-h7s-format.py restore for .h7s archives")
    elif not is_h7_blob(blob):
        raise H7FormatError("not H7/7 release archive")
    else:
        header, raw, stats = decompress_bytes(blob, verify=True)
    out_path = dest
    if out_path is None:
        orig = str(header.get("original_name") or src.stem)
        if not orig.endswith((".tar", ".tar.gz", ".tgz")):
            orig = f"{orig}.tar"
        out_path = src.with_name(orig)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_bytes(raw)
    tmp.replace(out_path)
    return {
        "ok": True,
        "src": str(src),
        "dest": str(out_path),
        "header": {
            "schema": header.get("schema"),
            "release_kind": header.get("release_kind"),
            "original_name": header.get("original_name"),
            "original_extension": header.get("original_extension"),
        },
        "stats": stats,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def migrate_library(*, apply: bool = True, limit: int = 0) -> dict[str, Any]:
    dewey = INSTALL / "library" / "dewey"
    paths: list[Path] = []
    if dewey.is_dir():
        paths.extend(sorted(dewey.rglob("*.h7c")))
        paths.extend(sorted(p for p in dewey.rglob("*") if p.suffix.lower() in (".h7", ".h7e", ".h7s")))
    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        if p.suffix.lower() in (".h7", ".h7e", ".h7s"):
            head = p.read_bytes()[:4]
            if head in (MAGIC, MAGIC_H7E, b"H7S\x01"):
                continue
        unique.append(p)
    if limit > 0:
        unique = unique[:limit]

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for i, src in enumerate(unique):
        if not src.is_file():
            rows.append({"ok": True, "path": str(src), "skipped": "gone"})
            continue
        try:
            if apply:
                row = adopt_path(src, inplace=(src.suffix.lower() != ".h7c"), dest=src.with_suffix(".h7") if src.suffix.lower() == ".h7c" else None, remove_src=True, apply_corrects=True)
            else:
                blob = src.read_bytes()
                row = {"ok": True, "path": str(src), "bytes": len(blob), "dry_run": True}
        except FileNotFoundError:
            rows.append({"ok": True, "path": str(src), "skipped": "race"})
            continue
        except Exception as exc:
            row = {"ok": False, "path": str(src), "error": str(exc)}
        rows.append(row)
        if not row.get("ok"):
            errors.append(row)
        if (i + 1) % 50 == 0:
            print(f"h7-migrate {i + 1}/{len(unique)} err={len(errors)}", file=sys.stderr, flush=True)

    manifest = {
        "schema": "field-h7-migrate-manifest/v1",
        "updated": _now(),
        "ok": len(errors) == 0,
        "apply": apply,
        "format": FORMAT,
        "book_count": len(unique),
        "migrated": sum(1 for r in rows if r.get("changed")),
        "skipped": sum(1 for r in rows if r.get("skipped")),
        "errors": errors[:24],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
    if apply:
        _save(STATE / "field-h7-migrate-manifest.json", manifest)
    return manifest


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    apply = "--apply" in sys.argv
    limit = 0
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])

    if cmd == "properties" and len(sys.argv) >= 3:
        p = Path(sys.argv[2])
        blob = p.read_bytes()
        h7s = _import_mod("field_h7s_props", "field-h7s-format.py")
        if h7s and hasattr(h7s, "is_h7s_blob") and h7s.is_h7s_blob(blob):
            print(json.dumps(h7s.read_properties(blob), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(read_properties(p), ensure_ascii=False, indent=2))
        return 0
    if cmd == "instant" and len(sys.argv) >= 3:
        print(json.dumps(instant_header(Path(sys.argv[2])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "unpack" and len(sys.argv) >= 3:
        blob = Path(sys.argv[2]).read_bytes()
        if _looks_text(blob[:64]) and not is_h7_blob(blob):
            print(json.dumps({"error": "not_h7"}, indent=2))
            return 1
        header, raw, stats = decompress_bytes(blob, verify=True)
        preview = raw[:240]
        try:
            preview_text = preview.decode("utf-8")
        except UnicodeDecodeError:
            preview_text = preview.hex()[:240]
        print(json.dumps({
            "stats": stats,
            "bytes": len(raw),
            "preview": preview_text,
            "portable": header.get("portable"),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "pack-archive" and len(sys.argv) >= 4:
        out = pack_archive_file(Path(sys.argv[2]), Path(sys.argv[3]))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "unpack-archive" and len(sys.argv) >= 3:
        dest = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
        out = unpack_archive_file(Path(sys.argv[2]), dest)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "pack-h7e" and len(sys.argv) >= 4:
        out = pack_h7e_file(Path(sys.argv[2]), Path(sys.argv[3]))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("compression-progress", "compress-progress") and len(sys.argv) >= 2:
        prog = _import_mod("field_compression_progress", "field-compression-progress.py")
        if prog and hasattr(prog, "read_progress"):
            print(json.dumps(prog.read_progress(), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps({"error": "progress module missing"}, indent=2))
        return 1
    if cmd in ("extract", "extract-h7e") and len(sys.argv) >= 3:
        dest = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
        out = extract_h7e_to_cwd(Path(sys.argv[2]), dest=dest)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("bench", "benchmark"):
        if len(sys.argv) < 3:
            print(json.dumps({"error": "usage", "cmd": "bench <corpus.tar> [--out=DIR]"}, indent=2))
            return 2
        corpus = Path(sys.argv[2])
        out_dir = None
        skip_external = "--field-only" in sys.argv
        for arg in sys.argv[3:]:
            if arg.startswith("--out="):
                out_dir = Path(arg.split("=", 1)[1])
        print(json.dumps(benchmark_compression(corpus, out_dir=out_dir, skip_external=skip_external), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("one", "adopt") and len(sys.argv) >= 3:
        src = Path(sys.argv[2])
        out = adopt_path(src, inplace=True, remove_src=False, apply_corrects=apply)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("migrate", "sweep", "all"):
        out = migrate_library(apply=apply, limit=limit)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "adopt-tree" and len(sys.argv) >= 3:
        out = adopt_tree(Path(sys.argv[2]), apply=apply, limit=limit)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("json", "panel"):
        doc = _load(DOCTRINE, {})
        doc["portable_schema"] = PORTABLE_SCHEMA
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": [
            "migrate [--apply] [--limit=N]",
            "adopt <path> [--apply]",
            "adopt-tree <dir> [--apply]",
            "one <path> [--apply]",
            "properties <path>",
            "instant <path>",
            "unpack <path>",
            "pack-archive <src> <dest.h7>",
            "unpack-archive <src.h7> [dest.tar]",
            "pack-h7e <folder|tar> <dest.h7e>",
            "extract <archive.h7e|.h7> [dest_dir]",
            "bench <corpus.tar> [--out=DIR] [--field-only]",
            "json",
        ],
    }))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())