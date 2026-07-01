#!/usr/bin/env pythong
"""H7c figure condenser — field plate snap + meld cache + lossless palette PNG."""
from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import zlib
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7c-figure-doctrine.json"
MELD_CACHE = STATE / "field-h7c-figure-meld.json"

# Field manual figure plate — shared across Explaining X / Training X covers and diagrams.
FIELD_PLATE_RGB: tuple[tuple[int, int, int], ...] = (
    (12, 14, 18),
    (14, 16, 22),
    (20, 24, 30),
    (28, 30, 38),
    (32, 48, 42),
    (50, 55, 65),
    (90, 100, 115),
    (100, 110, 125),
    (110, 120, 135),
    (120, 125, 135),
    (140, 150, 165),
    (175, 180, 190),
    (190, 195, 205),
    (200, 205, 215),
    (220, 225, 235),
)

PLATE_KEYS = ("cover", "syntax", "op_map", "memory", "compile", "types")


def _now() -> str:
    import time

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


def _nearest_color(pixel: tuple[int, int, int], palette: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    return min(palette, key=lambda c: sum((a - b) ** 2 for a, b in zip(pixel, c)))


def snap_to_field_plate(
    img: Any,
    *,
    accent: tuple[int, int, int] | None = None,
    extra: list[tuple[int, int, int]] | None = None,
) -> Any:
    """Snap RGBA/RGB figure to field plate palette — canonical plate colors, fast decode."""
    from PIL import Image  # noqa: WPS433

    rgb = img.convert("RGB")
    pal = list(dict.fromkeys(list(FIELD_PLATE_RGB) + ([accent] if accent else []) + (extra or [])))
    pixels = list(rgb.getdata())
    mapped = [_nearest_color(p, pal) for p in pixels]
    out = Image.new("RGB", rgb.size)
    out.putdata(mapped)
    return out


def _lossless_palette_png(img: Any) -> bytes:
    from PIL import Image  # noqa: WPS433

    rgb = img.convert("RGB")
    pixels = list(rgb.getdata())
    unique = len(set(pixels))
    colors = min(max(unique, 2), 256)
    q = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    if list(q.convert("RGB").getdata()) != pixels:
        buf = io.BytesIO()
        rgb.save(buf, format="PNG", optimize=True, compress_level=9)
        return buf.getvalue()
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True, compress_level=9)
    return buf.getvalue()


def zlib_recompress_png(data: bytes) -> bytes:
    """Lossless IDAT recompress — fallback when palette not applicable."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return data
    out = bytearray(data[:8])
    pos = 8
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        crc = data[pos + 8 + length : pos + 12 + length]
        if ctype == b"IDAT":
            try:
                raw = zlib.decompress(chunk)
                chunk = zlib.compress(raw, 9)
                crc = struct.pack(">I", zlib.crc32(ctype + chunk) & 0xFFFFFFFF)
            except zlib.error:
                pass
        out.extend(struct.pack(">I", len(chunk)))
        out.extend(ctype + chunk + crc)
        pos += 12 + length
        if ctype == b"IEND":
            break
    return bytes(out)


def meld_lookup(sha256: str) -> dict[str, Any] | None:
    doc = _load(MELD_CACHE, {"entries": {}})
    return (doc.get("entries") or {}).get(sha256)


def meld_store(sha256: str, meta: dict[str, Any]) -> None:
    doc = _load(MELD_CACHE, {"entries": {}, "hits": 0, "stores": 0})
    entries = doc.setdefault("entries", {})
    if sha256 not in entries:
        doc["stores"] = int(doc.get("stores", 0)) + 1
    entries[sha256] = {**meta, "stored": _now()}
    doc["updated"] = _now()
    _save(MELD_CACHE, doc)


def meld_touch(sha256: str) -> None:
    doc = _load(MELD_CACHE, {"entries": {}})
    if sha256 in (doc.get("entries") or {}):
        doc["hits"] = int(doc.get("hits", 0)) + 1
        _save(MELD_CACHE, doc)


def condense_figure_png(
    data: bytes,
    *,
    plate_key: str = "figure",
    accent: tuple[int, int, int] | None = None,
    use_meld: bool = True,
    use_plate_snap: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    """
    Condense PNG for H7c embed — field plate snap, lossless palette, meld receipt.
    Returns (compressed_bytes, manifest_meta).
    """
    from PIL import Image  # noqa: WPS433

    raw_len = len(data)
    src_sha = hashlib.sha256(data).hexdigest()
    if use_meld:
        hit = meld_lookup(src_sha)
        if hit and hit.get("condensed_sha256"):
            meld_touch(src_sha)
            return data, {
                "plate_key": plate_key,
                "meld": True,
                "meld_hit": True,
                "src_sha256": src_sha,
                "method": hit.get("method", "meld_cache"),
                "src_bytes": raw_len,
                "bytes": raw_len,
            }

    img = Image.open(io.BytesIO(data))
    if use_plate_snap:
        img = snap_to_field_plate(img, accent=accent)
    condensed = _lossless_palette_png(img)
    method = "field_plate_palette"
    if len(condensed) >= len(data):
        recompressed = zlib_recompress_png(data)
        if len(recompressed) < len(condensed):
            condensed = recompressed
            method = "zlib9_idat"
        else:
            condensed = data
            method = "identity"

    out_sha = hashlib.sha256(condensed).hexdigest()
    ratio = round(len(condensed) / raw_len, 4) if raw_len else 1.0
    meta = {
        "plate_key": plate_key,
        "meld": use_meld,
        "meld_hit": False,
        "method": method,
        "plate_snap": use_plate_snap,
        "src_sha256": src_sha,
        "sha256": out_sha,
        "src_bytes": raw_len,
        "bytes": len(condensed),
        "ratio": ratio,
    }
    if use_meld:
        meld_store(
            src_sha,
            {
                "plate_key": plate_key,
                "method": method,
                "condensed_sha256": out_sha,
                "ratio": ratio,
            },
        )
    return condensed, meta


def save_plate_figure(
    img: Any,
    path: Path,
    *,
    plate_key: str = "figure",
    accent: tuple[int, int, int] | None = None,
) -> Path:
    """Save procedural figure — plate snap then lossless palette PNG."""
    snapped = snap_to_field_plate(img, accent=accent)
    payload = _lossless_palette_png(snapped)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def condense_figure_batch(
    figures: dict[str, dict[str, Any]],
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    """Condense figure dict for pack_h7c — meld-dedupe identical blobs across figures."""
    blobs: dict[str, bytes] = {}
    manifest: list[dict[str, Any]] = []
    blob_index: dict[str, str] = {}
    for fig_id, spec in figures.items():
        raw = spec.get("data")
        if raw is None and spec.get("path"):
            try:
                raw = Path(str(spec["path"])).read_bytes()
            except OSError:
                continue
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            continue
        plate_key = str(spec.get("plate_key") or fig_id)
        accent = spec.get("accent")
        accent_t = tuple(accent) if isinstance(accent, (list, tuple)) and len(accent) == 3 else None
        condensed, meta = condense_figure_png(
            bytes(raw),
            plate_key=plate_key,
            accent=accent_t,
            use_meld=True,
            use_plate_snap=spec.get("plate_snap", True),
        )
        sha = meta.get("sha256") or hashlib.sha256(condensed).hexdigest()
        if sha not in blob_index:
            blob_index[sha] = fig_id
            blobs[fig_id] = condensed
        meld_ref = blob_index[sha]
        manifest.append({
            "id": str(fig_id),
            "mime": str(spec.get("mime") or "image/png"),
            "alt": str(spec.get("alt") or fig_id),
            "sha256": sha,
            "bytes": len(condensed),
            "plate_key": plate_key,
            "meld_ref": meld_ref if meld_ref != fig_id else None,
            **meta,
        })
    return blobs, manifest


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else __import__("sys").argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("Usage: field-h7c-figure-compress.py bench PATH [PATH ...]")
        return 0
    if args[0] == "bench":
        rows = []
        for p in args[1:]:
            path = Path(p)
            if not path.is_file():
                continue
            raw = path.read_bytes()
            out, meta = condense_figure_png(raw, plate_key=path.stem)
            rows.append({"path": str(path), "src": len(raw), "out": len(out), **meta})
        print(json.dumps({"ok": True, "rows": rows}, indent=2))
        return 0
    print(json.dumps({"ok": False, "error": "unknown_command"}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())