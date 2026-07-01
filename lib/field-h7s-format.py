#!/usr/bin/env python3
"""H7s — universal speedup format: any file, native face identity, execute without decompress.

Structural slice index (or CHIPS redense for JSON batteries). Hot path reads header +
one slice — faster than parsing full uncompressed source. Identifies as the source file
type via field-file-formats face disguise (properties-only reveal of h7s/1).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
_FIELD_TECH_NO_FIELD = os.environ.get("FIELD_TECH_NO_FIELD", "").strip().lower() in ("1", "true", "yes")
if not _FIELD_TECH_NO_FIELD:
    STATE.mkdir(parents=True, exist_ok=True)

MAGIC = b"H7S\x01"
FORMAT = "h7s/1"
HEADER_SCHEMA = "h7s/1-header/v1"
FACE_CAP = 4096
DEFAULT_CHUNK = 256 * 1024
CHIPS_MARKERS = frozenset({
    "field-chips-core/v1",
    "field-chips-plate-stack/v1",
    "field-ironclad-chips-combinatorics/v1",
})


class H7sError(ValueError):
    pass


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def is_h7s_blob(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == MAGIC


def _h7_helpers() -> Any | None:
    return _import_mod("field_h7_format_h7s", "field-h7-format.py")


def pick_face_for_source(data: bytes, path: Path | None = None) -> dict[str, Any]:
    ext = (path.suffix if path else "").lower()
    ff = _import_mod("field_file_formats", "field-file-formats.py")
    if ext and ff and hasattr(ff, "build_table"):
        for row in (ff.build_table() or {}).get("formats") or []:
            exts = [str(e).lower() for e in (row.get("extensions") or [])]
            if ext in exts:
                return {
                    "face_format_id": str(row.get("id") or "unknown"),
                    "face_label": str(row.get("label") or row.get("id") or "unknown"),
                    "face_extension": ext,
                    "face_mime": row.get("mime") or "application/octet-stream",
                    "face_family": row.get("family") or "data",
                }
    h7 = _h7_helpers()
    if h7 and hasattr(h7, "pick_face_format"):
        return h7.pick_face_format(path=path, data=data, hint_ext=ext or None)
    return {
        "face_format_id": "octet-stream",
        "face_label": "Binary",
        "face_extension": ext or ".bin",
        "face_mime": "application/octet-stream",
        "face_family": "data",
    }


def _face_prefix_bytes(data: bytes, face: dict[str, Any]) -> bytes:
    h7 = _h7_helpers()
    if h7 and hasattr(h7, "_face_prefix_bytes"):
        return h7._face_prefix_bytes(data, face)
    return data[: min(len(data), FACE_CAP)]


def _looks_text(data: bytes) -> bool:
    h7 = _h7_helpers()
    if h7 and hasattr(h7, "_looks_text"):
        return h7._looks_text(data)
    if not data or b"\x00" in data[:4096]:
        return False
    try:
        data[:4096].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def redense_stacked_chips(doc: dict[str, Any]) -> dict[str, Any]:
    """Fold stacked CHIPS layers into executable slices — drop duplicate chip arrays."""
    modules = list(doc.get("core_modules") or doc.get("modules") or [])
    leaves = list(doc.get("core_leaves") or doc.get("combinatorics_leaves") or [])
    chips = list(doc.get("chips") or [])
    if not modules and chips:
        by_family: dict[str, list[dict[str, Any]]] = {}
        for chip in chips:
            fam = str(chip.get("family") or "unknown")
            by_family.setdefault(fam, []).append(chip)
        modules = [
            {
                "id": f"chips_core:{fam}",
                "family": fam,
                "chip_count": len(fam_chips),
                "leaves": [{"id": c.get("combinatorics_leaf") or c.get("id"), "chip_id": c.get("id")} for c in fam_chips[:64]],
            }
            for fam, fam_chips in sorted(by_family.items())
        ]
    slices: list[dict[str, Any]] = []
    for i, mod in enumerate(modules):
        mid = str(mod.get("id") or mod.get("core_id") or f"slice:{i}")
        slices.append({
            "id": mid,
            "family": mod.get("family"),
            "slot": mod.get("slot", i),
            "chip_count": mod.get("chip_count") or mod.get("indexed_chips"),
            "path_pct": mod.get("path_pct"),
            "bsp_model": mod.get("bsp_model"),
            "combinatorics_leaf": mod.get("combinatorics_leaf"),
            "leaf_ids": [
                str(l.get("id") or l.get("chip_id") or "")
                for l in (mod.get("leaves") or [])[:64]
                if isinstance(l, dict)
            ],
        })
    return {
        "schema": "field-h7s-redense/v1",
        "format": FORMAT,
        "inner_kind": "chips_redense",
        "slice_count": len(slices),
        "slices": slices,
        "counts": {
            "source_chips": len(chips),
            "source_leaves": len(leaves),
            "source_modules": len(modules),
            "redensed_slices": len(slices),
        },
    }


def _is_chips_battery(doc: dict[str, Any]) -> bool:
    schema = str(doc.get("schema") or "")
    if schema in CHIPS_MARKERS:
        return True
    return bool(doc.get("chips") and (doc.get("modules") or doc.get("core_modules")))


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


def slice_plan_for_bytes(data: bytes, path: Path | None = None, *, progress: Any | None = None) -> dict[str, Any]:
    """Build slice plan for any file — CHIPS redense, else lossless byte chunks."""
    face = pick_face_for_source(data, path)
    inner_kind = "raw_bytes"
    slices: list[dict[str, Any]] = []
    slice_blobs: list[bytes] = []

    if _looks_text(data):
        try:
            doc = json.loads(data.decode("utf-8"))
            if isinstance(doc, dict) and _is_chips_battery(doc):
                if progress:
                    progress.phase("redense", 15.0, "CHIPS battery structural slice")
                redensed = redense_stacked_chips(doc)
                rows = list(redensed.get("slices") or [])
                for i, row in enumerate(rows):
                    blob = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    slice_blobs.append(blob)
                    slices.append({
                        "id": row.get("id"),
                        "slot": row.get("slot"),
                        "byte_count": len(blob),
                        "kind": "chips_module",
                    })
                    if progress and rows:
                        pct = 15.0 + ((i + 1) / len(rows)) * 35.0
                        progress.phase("redense", pct, f"slice {i + 1}/{len(rows)}")
                if progress:
                    progress.phase("slice", 52.0, f"{len(slices)} CHIPS slices")
                return {
                    "inner_kind": "chips_redense",
                    "face": face,
                    "slices": slices,
                    "slice_blobs": slice_blobs,
                    "byte_count": len(data),
                    "payload_sha256": _sha256(b"".join(slice_blobs)),
                    "counts": redensed.get("counts") or {},
                    "lossless_restore": False,
                    "execute_lane": "chips_module",
                }
            inner_kind = "json_utf8"
        except (json.JSONDecodeError, UnicodeDecodeError):
            inner_kind = "raw_utf8" if _looks_text(data) else "raw_bytes"
    else:
        inner_kind = "raw_bytes"

    chunk = DEFAULT_CHUNK
    if progress:
        progress.phase("slice", 12.0, f"byte chunks · {len(data)} bytes")
    if len(data) <= chunk:
        slice_blobs = [data]
        slices = [{"id": "slice:0", "slot": 0, "byte_count": len(data), "kind": "whole"}]
    else:
        pos = 0
        idx = 0
        total = len(data)
        while pos < len(data):
            part = data[pos : pos + chunk]
            slice_blobs.append(part)
            slices.append({
                "id": f"slice:{idx}",
                "slot": idx,
                "byte_count": len(part),
                "kind": "chunk",
                "offset_src": pos,
            })
            pos += len(part)
            idx += 1
            if progress and total:
                pct = 12.0 + (pos / total) * 38.0
                progress.phase("slice", pct, f"chunk {idx} · {pos}/{total} bytes")

    joined = b"".join(slice_blobs)
    if progress:
        progress.phase("slice", 52.0, f"{len(slices)} slices ready")
    return {
        "inner_kind": inner_kind,
        "face": face,
        "slices": slices,
        "slice_blobs": slice_blobs,
        "byte_count": len(data),
        "payload_sha256": _sha256(data),
        "source_sha256": _sha256(data),
        "counts": {"slice_count": len(slices), "chunk_bytes": chunk},
        "lossless_restore": True,
        "execute_lane": "byte_slice",
    }


def pack_h7s_bytes(
    plan: dict[str, Any],
    *,
    meta: dict[str, Any] | None = None,
    path: Path | None = None,
    progress: Any | None = None,
) -> bytes:
    """Pack slice plan — face disguise + slice table + payload, no zlib."""
    if progress:
        progress.phase("pack", 55.0, "H7s header + slice table")
    slice_blobs = list(plan.get("slice_blobs") or [])
    index_rows = list(plan.get("slices") or [])
    face = plan.get("face") or pick_face_for_source(b"", path)
    payload = b"".join(slice_blobs)
    orig_name = str((meta or {}).get("original_name") or (path.name if path else ""))
    orig_ext = str((meta or {}).get("original_extension") or (path.suffix if path else ""))
    face_bytes = _face_prefix_bytes(payload[:FACE_CAP] if payload else b"", face)
    header: dict[str, Any] = {
        "schema": HEADER_SCHEMA,
        "format": FORMAT,
        "execute_without_decompress": True,
        "speedup_lane": True,
        "compression_kind": "structural_slice",
        "inner_kind": plan.get("inner_kind") or "raw_bytes",
        "execute_lane": plan.get("execute_lane") or "byte_slice",
        "lossless_restore": bool(plan.get("lossless_restore", True)),
        "slice_count": len(index_rows),
        "slices": index_rows,
        "face": {
            "id": face.get("face_format_id"),
            "label": face.get("face_label"),
            "ext": face.get("face_extension"),
            "mime": face.get("face_mime"),
            "family": face.get("face_family"),
        },
        "original_name": orig_name,
        "original_extension": orig_ext,
        "byte_count": plan.get("byte_count") or len(payload),
        "source_sha256": plan.get("source_sha256") or plan.get("payload_sha256"),
        "payload_sha256": _sha256(payload),
        "counts": plan.get("counts") or {},
        "packed_at": _now(),
        **{k: v for k, v in (meta or {}).items() if k not in ("original_name", "original_extension")},
    }
    header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(header_json) > 65535:
        raise H7sError("H7s header too large")
    data_offset = 4 + 4 + len(header_json) + 4 + len(face_bytes) + 4 + 8 * len(slice_blobs)
    table_parts: list[bytes] = []
    pos = data_offset
    for blob in slice_blobs:
        table_parts.append(struct.pack("<II", pos, len(blob)))
        pos += len(blob)
    blob = b"".join([
        MAGIC,
        struct.pack("<I", len(header_json)),
        header_json,
        struct.pack("<I", len(face_bytes)),
        face_bytes,
        struct.pack("<I", len(slice_blobs)),
        *table_parts,
        payload,
    ])
    if progress:
        progress.phase("pack", 78.0, f"H7s blob · {len(blob)} bytes")
    return blob


def parse_h7s(data: bytes) -> tuple[dict[str, Any], bytes, list[tuple[int, int]], bytes]:
    if len(data) < 16 or data[:4] != MAGIC:
        raise H7sError("not H7s (bad magic)")
    hdr_len = struct.unpack("<I", data[4:8])[0]
    hdr_end = 8 + hdr_len
    if hdr_end + 4 > len(data):
        raise H7sError("truncated H7s header")
    header = json.loads(data[8:hdr_end].decode("utf-8"))
    face_len = struct.unpack("<I", data[hdr_end : hdr_end + 4])[0]
    face_start = hdr_end + 4
    face_end = face_start + face_len
    if face_end + 4 > len(data):
        raise H7sError("truncated H7s face")
    face_bytes = data[face_start:face_end]
    slice_count = struct.unpack("<I", data[face_end : face_end + 4])[0]
    table_start = face_end + 4
    table_end = table_start + slice_count * 8
    if table_end > len(data):
        raise H7sError("truncated H7s slice table")
    entries: list[tuple[int, int]] = []
    for i in range(slice_count):
        off = table_start + i * 8
        offset, length = struct.unpack("<II", data[off : off + 8])
        entries.append((offset, length))
    return header, face_bytes, entries, data


def read_properties(data: bytes | Path) -> dict[str, Any]:
    """Properties-only reveal — true format h7s/1; face shows native source type."""
    blob = data.read_bytes() if isinstance(data, Path) else data
    path = data if isinstance(data, Path) else None
    if not is_h7s_blob(blob):
        return {"ok": False, "error": "not_h7s", "path": str(path) if path else None}
    header, face_bytes, entries, _ = parse_h7s(blob)
    face = header.get("face") or {}
    return {
        "ok": True,
        "schema": "field-h7s-properties/v1",
        "path": str(path) if path else None,
        "true_format": FORMAT,
        "is_h7s": True,
        "properties_only_reveal": True,
        "disguise_identical": True,
        "instant_header": True,
        "execute_without_decompress": True,
        "face_format_id": face.get("id"),
        "face_label": face.get("label"),
        "face_extension": face.get("ext"),
        "face_mime": face.get("mime"),
        "face_family": face.get("family"),
        "face_bytes": len(face_bytes),
        "slice_count": len(entries),
        "inner_kind": header.get("inner_kind"),
        "execute_lane": header.get("execute_lane"),
        "lossless_restore": header.get("lossless_restore"),
        "byte_count": header.get("byte_count"),
        "source_sha256": header.get("source_sha256"),
        "original_name": header.get("original_name"),
        "original_extension": header.get("original_extension"),
    }


def identify(path: Path) -> dict[str, Any]:
    """Identify any path — H7s reveals as native face type."""
    if not path.is_file():
        return {"ok": False, "error": "not_found", "path": str(path)}
    blob = path.read_bytes()
    if is_h7s_blob(blob):
        props = read_properties(blob)
        props["identifies_as"] = props.get("face_format_id") or "unknown"
        props["canonical_format"] = FORMAT
        return props
    face = pick_face_for_source(blob, path)
    return {
        "ok": True,
        "path": str(path),
        "is_h7s": False,
        "true_format": "native",
        "identifies_as": face.get("face_format_id"),
        "face_extension": face.get("face_extension"),
        "face_mime": face.get("face_mime"),
    }


def read_slice_bytes(
    data: bytes | Path,
    *,
    slice_id: str | None = None,
    slot: int | None = None,
    slice_index: int | None = None,
) -> tuple[bytes, dict[str, Any]]:
    blob = data.read_bytes() if isinstance(data, Path) else data
    header, _, entries, raw = parse_h7s(blob)
    slices_meta = list(header.get("slices") or [])
    pick = slice_index if slice_index is not None else 0
    if slice_id:
        for i, row in enumerate(slices_meta):
            if str(row.get("id") or "") == slice_id:
                pick = i
                break
    elif slot is not None:
        for i, row in enumerate(slices_meta):
            if int(row.get("slot") or -1) == slot:
                pick = i
                break
    if pick >= len(entries):
        pick = 0
    offset, length = entries[pick]
    return raw[offset : offset + length], {"header": header, "slice_index": pick, "slice_meta": slices_meta[pick] if pick < len(slices_meta) else {}}


def instant_execute(
    data: bytes | Path,
    *,
    slice_id: str | None = None,
    slot: int | None = None,
    slice_index: int | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    slice_bytes, ctx = read_slice_bytes(data, slice_id=slice_id, slot=slot, slice_index=slice_index)
    header = ctx.get("header") or {}
    inner = header.get("inner_kind") or "raw_bytes"
    parsed: Any = None
    if inner in ("chips_redense", "json_utf8") or ctx.get("slice_meta", {}).get("kind") == "chips_module":
        try:
            parsed = json.loads(slice_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed = None
    return {
        "ok": True,
        "format": FORMAT,
        "instant": True,
        "execute_without_decompress": True,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "slice_index": ctx.get("slice_index"),
        "slice_bytes": len(slice_bytes),
        "slice": parsed,
        "slice_raw": slice_bytes.decode("utf-8", errors="replace")[:240] if parsed is None and _looks_text(slice_bytes) else None,
        "properties": {
            "face_format_id": (header.get("face") or {}).get("id"),
            "original_extension": header.get("original_extension"),
        },
        "header_counts": header.get("counts"),
    }


def restore_bytes(data: bytes | Path) -> bytes:
    """Lossless restore — concatenate byte slices (non-CHIPS-redense packs)."""
    blob = data.read_bytes() if isinstance(data, Path) else data
    header, _, entries, raw = parse_h7s(blob)
    if not header.get("lossless_restore", True):
        raise H7sError("H7s pack is chips_redense — use instant_execute per module")
    parts: list[bytes] = []
    for offset, length in entries:
        parts.append(raw[offset : offset + length])
    out = b"".join(parts)
    expect = header.get("source_sha256")
    if expect and _sha256(out) != expect:
        raise H7sError("H7s restore integrity failed")
    return out


def _h7_family() -> Any | None:
    return _import_mod("field_h7_family", "field-h7-format.py")


def pack_any_file(
    src: Path,
    dest: Path | None = None,
    *,
    meta: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    if not src.is_file():
        raise H7sError(f"missing source: {src}")
    out_path = dest or src
    progress, prog_mod = _progress_start(
        job="pack_any_file",
        fmt=FORMAT,
        src=str(src),
        dest=str(out_path),
        meta=meta,
    )
    try:
        h7 = _h7_family()
        if h7 and hasattr(h7, "guard_pack_source"):
            guard = h7.guard_pack_source(src, FORMAT, force=force)
            if guard.get("skip"):
                return {
                    "ok": True,
                    "skipped": guard.get("reason"),
                    "format": FORMAT,
                    "src": str(src),
                    "dest": str(out_path),
                    "guard": guard,
                }
            if progress:
                progress.phase("read", 5.0, f"loading {src.name}")
            if hasattr(h7, "source_bytes_for_pack"):
                data, guard = h7.source_bytes_for_pack(src, FORMAT, force=force)
            else:
                data, guard = src.read_bytes(), {}
        else:
            if progress:
                progress.phase("read", 5.0, f"loading {src.name}")
            data, guard = src.read_bytes(), {}
        plan = slice_plan_for_bytes(data, src, progress=progress)
        packed = pack_h7s_bytes(
            plan,
            meta={
                "original_name": src.name,
                "original_extension": src.suffix,
                **(meta or {}),
            },
            path=src,
            progress=progress,
        )
        if progress:
            progress.phase("write", 88.0, f"writing {out_path.name}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_bytes(packed)
        tmp.replace(out_path)
        out = {
            "ok": True,
            "format": FORMAT,
            "src": str(src),
            "dest": str(out_path),
            "face_format_id": (plan.get("face") or {}).get("face_format_id"),
            "face_extension": (plan.get("face") or {}).get("face_extension"),
            "inner_kind": plan.get("inner_kind"),
            "execute_lane": plan.get("execute_lane"),
            "raw_bytes": len(data),
            "packed_bytes": len(packed),
            "ratio": round(len(data) / max(1, len(packed)), 4),
            "slice_count": len(plan.get("slices") or []),
            "lossless_restore": plan.get("lossless_restore"),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "properties": read_properties(packed),
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


def pack_chips_battery_h7s(src: Path, dest: Path, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return pack_any_file(src, dest, meta=meta)


def benchmark_speedup(src: Path, *, repeats: int = 24, slice_index: int = 0) -> dict[str, Any]:
    if not src.is_file():
        raise H7sError(f"missing: {src}")
    raw = src.read_bytes()
    h7s_path = src.with_suffix(src.suffix + ".bench.h7s")
    pack_any_file(src, h7s_path)
    h7s_blob = h7s_path.read_bytes()

    def _time_raw() -> float:
        t0 = time.perf_counter()
        if _looks_text(raw):
            try:
                doc = json.loads(raw.decode("utf-8"))
                if isinstance(doc, dict):
                    _ = doc.get("core_modules") or doc.get("modules") or doc
            except json.JSONDecodeError:
                _ = raw[:4096]
        else:
            _ = raw[:4096]
        return (time.perf_counter() - t0) * 1000

    def _time_h7s() -> float:
        t0 = time.perf_counter()
        instant_execute(h7s_blob, slice_index=slice_index)
        return (time.perf_counter() - t0) * 1000

    raw_times = [_time_raw() for _ in range(repeats)]
    h7s_times = [_time_h7s() for _ in range(repeats)]
    raw_avg = sum(raw_times) / len(raw_times)
    h7s_avg = sum(h7s_times) / len(h7s_times)
    return {
        "schema": "field-h7s-speedup-bench/v1",
        "ok": True,
        "field_tech_no_field": _FIELD_TECH_NO_FIELD,
        "corpus": str(src),
        "identify": identify(src),
        "raw_bytes": len(raw),
        "h7s_bytes": len(h7s_blob),
        "size_ratio": round(len(raw) / max(1, len(h7s_blob)), 4),
        "raw_parse_ms_avg": round(raw_avg, 3),
        "h7s_execute_ms_avg": round(h7s_avg, 3),
        "speedup_x": round(raw_avg / max(0.001, h7s_avg), 2),
        "faster_than_uncompressed": h7s_avg < raw_avg,
        "repeats": repeats,
        "h7s_path": str(h7s_path),
        "h7s_properties": read_properties(h7s_blob),
    }


def verify_family_compat() -> dict[str, Any]:
    """Round-trip guard checks — H7 / H7e / H7s never double-wrap."""
    import tempfile

    h7 = _h7_family()
    if not h7:
        return {"ok": False, "error": "field-h7-format.py missing"}
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        native = root / "sample.txt"
        native.write_text("hostess7 family guard sample\n", encoding="utf-8")
        h7s_out = root / "sample.h7s"
        pack_any_file(native, h7s_out)
        g1 = h7.guard_pack_source(h7s_out, h7.FORMAT_H7S)
        rows.append({"case": "h7s->h7s", "skip": g1.get("skip"), "ok": bool(g1.get("skip"))})
        if hasattr(h7, "pack_archive_file"):
            h7_out = root / "sample.h7"
            h7.pack_archive_file(native, h7_out)
            g2 = h7.guard_pack_source(h7_out, h7.FORMAT)
            rows.append({"case": "h7->h7", "skip": g2.get("skip"), "ok": bool(g2.get("skip"))})
            g3 = h7.guard_pack_source(h7_out, FORMAT)
            rows.append({
                "case": "h7->h7s",
                "unwrap": g3.get("unwrap"),
                "ok": bool(g3.get("unwrap")) and not g3.get("skip"),
            })
        if hasattr(h7, "pack_h7e_file"):
            h7e_out = root / "sample.h7e"
            h7.pack_h7e_file(native, h7e_out)
            g4 = h7.guard_pack_source(h7e_out, h7.FORMAT_H7E)
            rows.append({"case": "h7e->h7e", "skip": g4.get("skip"), "ok": bool(g4.get("skip"))})
        try:
            h7.extract_h7e_to_cwd(h7s_out)
            rows.append({"case": "h7e_extract_h7s", "ok": False, "error": "should_raise"})
        except Exception as exc:
            rows.append({"case": "h7e_extract_h7s", "ok": True, "error": str(exc)[:80]})
    return {
        "schema": "field-h7-family-verify/v1",
        "ok": all(r.get("ok") for r in rows),
        "rows": rows,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "pack" and len(sys.argv) >= 3:
        src = Path(sys.argv[2])
        dest = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
        out = pack_any_file(src, dest)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("compression-progress", "compress-progress"):
        prog = _import_mod("field_compression_progress", "field-compression-progress.py")
        if prog and hasattr(prog, "read_progress"):
            print(json.dumps(prog.read_progress(), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps({"error": "progress module missing"}, indent=2))
        return 1
    if cmd in ("execute", "instant", "run") and len(sys.argv) >= 3:
        sid, slot, idx = None, None, None
        for arg in sys.argv[3:]:
            if arg.startswith("--slice="):
                sid = arg.split("=", 1)[1]
            if arg.startswith("--slot="):
                slot = int(arg.split("=", 1)[1])
            if arg.startswith("--index="):
                idx = int(arg.split("=", 1)[1])
        out = instant_execute(Path(sys.argv[2]), slice_id=sid, slot=slot, slice_index=idx)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("properties", "identify") and len(sys.argv) >= 3:
        p = Path(sys.argv[2])
        fn = identify if cmd == "identify" else read_properties
        print(json.dumps(fn(p), ensure_ascii=False, indent=2))
        return 0
    if cmd == "restore" and len(sys.argv) >= 3:
        out = restore_bytes(Path(sys.argv[2]))
        dest = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
        if dest:
            dest.write_bytes(out)
            print(json.dumps({"ok": True, "dest": str(dest), "bytes": len(out)}, indent=2))
        else:
            sys.stdout.buffer.write(out)
        return 0
    if cmd in ("bench", "benchmark", "speedup"):
        src = Path(sys.argv[2]) if len(sys.argv) > 2 else STATE / "field-chips-core.json"
        reps = 24
        for arg in sys.argv[2:]:
            if arg.startswith("--repeats="):
                reps = int(arg.split("=", 1)[1])
        print(json.dumps(benchmark_speedup(src, repeats=reps), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("verify", "verify-family"):
        print(json.dumps(verify_family_compat(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "redense" and len(sys.argv) >= 3:
        doc = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print(json.dumps(redense_stacked_chips(doc), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "format": FORMAT,
        "motto": "H7s — any file; native face identity; slice execute without decompress.",
        "cmds": [
            "pack <any-file> [dest.h7s]",
            "execute <file.h7s> [--slice=ID|--slot=N|--index=N]",
            "identify <path>",
            "properties <path>",
            "restore <file.h7s> [dest]",
            "bench [corpus]",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())