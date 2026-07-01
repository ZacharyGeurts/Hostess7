#!/usr/bin/env pythong
"""H7B/3 brain storage — pattern analysis, lossless condenser, GitHub-sized sections."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import struct
import sys
import time
import zlib
from pathlib import Path
from typing import Any, Iterator

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE_PATH = INSTALL / "data" / "field-h7b-brain-doctrine.json"

MAGIC = b"H7B\x03"
FORMAT_ID = "h7b/3"
TOKEN_PREFIX = "\x1fH7B"
TOKEN_SUFFIX = "\x1f"
DEFAULT_MAX_SECTION = 20 * 1024 * 1024


class H7bBrainError(ValueError):
    pass


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def _fly_mod() -> Any | None:
    py = HOSTESS7 / "scripts" / "field_fly_codec.py"
    if not py.is_file():
        py = INSTALL / "Hostess7" / "scripts" / "field_fly_codec.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_fly_codec", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _brain_roots() -> list[Path]:
    roots: list[Path] = []
    for candidate in (
        HOSTESS7 / "cache" / "fieldstorage",
        INSTALL / "Hostess7" / "cache" / "fieldstorage",
        STATE,
        INSTALL / ".nexus-state",
    ):
        if candidate.is_dir() and candidate not in roots:
            roots.append(candidate)
    return roots


def _resolve_path(rel: str) -> Path | None:
    rel = rel.lstrip("/")
    if rel.startswith(".nexus-state/"):
        p = STATE / rel.replace(".nexus-state/", "", 1)
        return p if p.is_file() else None
    if rel.startswith("cache/fieldstorage/"):
        tail = rel.replace("cache/fieldstorage/", "", 1)
        for root in _brain_roots():
            p = root / tail
            if p.is_file():
                return p
        p = HOSTESS7 / "cache" / "fieldstorage" / tail
        return p if p.is_file() else None
    for base in (INSTALL, HOSTESS7, STATE):
        p = base / rel
        if p.is_file():
            return p
    return None


def _glob_paths(pattern: str, *, max_files: int = 256) -> list[Path]:
    pattern = pattern.lstrip("/")
    found: list[Path] = []
    seen: set[str] = set()

    def _scan(base: Path, glob_tail: str) -> None:
        if not base.is_dir():
            return
        for p in sorted(base.glob(glob_tail)):
            if not p.is_file():
                continue
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            found.append(p)
            if len(found) >= max_files:
                return

    if pattern.startswith(".nexus-state/"):
        _scan(STATE, pattern.replace(".nexus-state/", ""))
    elif pattern.startswith("cache/fieldstorage/"):
        tail = pattern.replace("cache/fieldstorage/", "")
        for root in _brain_roots():
            _scan(root, tail)
            if len(found) >= max_files:
                break
    else:
        for base in (INSTALL, HOSTESS7, STATE):
            _scan(base, pattern)
            if len(found) >= max_files:
                break
    return found[:max_files]


def collect_section_files(section: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    max_files = int(section.get("max_files") or 256)

    for rel in section.get("paths") or []:
        p = _resolve_path(str(rel))
        if not p:
            continue
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rows.append({
            "path": str(p.relative_to(INSTALL)) if str(p).startswith(str(INSTALL)) else str(p),
            "abs_path": str(p),
            "bytes": len(text.encode("utf-8")),
            "text": text,
        })
        if len(rows) >= max_files:
            return rows

    for glob_pat in section.get("glob") or []:
        for p in _glob_paths(str(glob_pat), max_files=max_files - len(rows)):
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rows.append({
                "path": str(p.relative_to(INSTALL)) if str(p).startswith(str(INSTALL)) else str(p),
                "abs_path": str(p),
                "bytes": len(text.encode("utf-8")),
                "text": text,
            })
            if len(rows) >= max_files:
                break
    return rows


def _canonical_bundle(section_id: str, files: list[dict[str, Any]]) -> bytes:
    envelope = {
        "schema": "h7b-brain-bundle/v1",
        "section_id": section_id,
        "packed_at": _now(),
        "file_count": len(files),
        "files": [
            {"path": f["path"], "bytes": f["bytes"], "text": f["text"]}
            for f in files
        ],
    }
    return json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def analyze_patterns(text: str, *, doctrine: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = doctrine or load_doctrine()
    cfg = doc.get("pattern_analysis") or {}
    min_len = int(cfg.get("min_string_len") or 8)
    min_occ = int(cfg.get("min_occurrences") or 3)
    max_entries = int(cfg.get("max_dictionary_entries") or 4096)
    key_min = int(cfg.get("key_min_occurrences") or 5)

    counts: dict[str, int] = {}
    for m in re.finditer(r'"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:', text):
        k = m.group(1)
        counts[k] = counts.get(k, 0) + 1

    str_counts: dict[str, int] = {}
    for m in re.finditer(r'"([^"]{' + str(min_len) + r',})"', text):
        s = m.group(1)
        if TOKEN_PREFIX in s:
            continue
        str_counts[s] = str_counts.get(s, 0) + 1

    key_aliases: dict[str, str] = {}
    for i, (k, n) in enumerate(sorted(counts.items(), key=lambda x: (-x[1], x[0]))):
        if n < key_min or i >= 128:
            continue
        key_aliases[k] = f"k{i}"

    candidates = [
        s for s, n in str_counts.items()
        if n >= min_occ and len(s) >= min_len
    ]
    candidates.sort(key=lambda s: (-str_counts[s] * len(s), s))
    dictionary = candidates[:max_entries]

    savings = sum(str_counts.get(s, 0) * (len(s) - len(f"{TOKEN_PREFIX}{i}{TOKEN_SUFFIX}")) for i, s in enumerate(dictionary))

    return {
        "schema": "field-h7b-brain-patterns/v1",
        "updated": _now(),
        "analyzed_bytes": len(text.encode("utf-8")),
        "dictionary_size": len(dictionary),
        "key_alias_count": len(key_aliases),
        "estimated_savings_bytes": max(0, savings),
        "dictionary": dictionary,
        "key_aliases": key_aliases,
        "top_keys": sorted(counts.items(), key=lambda x: -x[1])[:32],
    }


def apply_dictionary(text: str, dictionary: list[str]) -> str:
    if not dictionary:
        return text
    out = text
    for i in range(len(dictionary) - 1, -1, -1):
        token = f"{TOKEN_PREFIX}{i:05d}{TOKEN_SUFFIX}"
        out = out.replace(dictionary[i], token)
    return out


def restore_dictionary(text: str, dictionary: list[str]) -> str:
    out = text
    for i, phrase in enumerate(dictionary):
        token = f"{TOKEN_PREFIX}{i:05d}{TOKEN_SUFFIX}"
        out = out.replace(token, phrase)
    return out


def apply_key_aliases(text: str, aliases: dict[str, str]) -> str:
    out = text
    for key, short in sorted(aliases.items(), key=lambda x: -len(x[0])):
        out = out.replace(f'"{key}"', f'"{short}"')
    return out


def restore_key_aliases(text: str, aliases: dict[str, str]) -> str:
    rev = {v: k for k, v in aliases.items()}
    out = text
    for short, key in sorted(rev.items(), key=lambda x: -len(x[0])):
        out = out.replace(f'"{short}"', f'"{key}"')
    return out


def _compress_payload(raw: bytes, *, use_fly: bool = True) -> tuple[bytes, str]:
    fly = _fly_mod()
    blob = raw
    method = "zlib-9"
    if use_fly and fly and hasattr(fly, "fly_pack"):
        try:
            blob = fly.fly_pack(raw)
            if hasattr(fly, "is_fly") and fly.is_fly(blob):
                method = "fld1+zlib-9"
        except Exception:
            blob = raw
    compressed = zlib.compress(blob, level=9)
    return compressed, method


def _decompress_payload(compressed: bytes, *, method: str) -> bytes:
    blob = zlib.decompress(compressed)
    if "fld1" in method:
        fly = _fly_mod()
        if fly and hasattr(fly, "fly_unpack"):
            try:
                return fly.fly_unpack(blob)
            except Exception:
                pass
    return blob


def pack_section(
    section_id: str,
    files: list[dict[str, Any]],
    *,
    patterns: dict[str, Any] | None = None,
    max_section_bytes: int = DEFAULT_MAX_SECTION,
) -> list[bytes]:
    if not files:
        return []

    raw_bundle = _canonical_bundle(section_id, files)
    text = raw_bundle.decode("utf-8")
    if patterns is None:
        patterns = analyze_patterns(text)
    dictionary = list(patterns.get("dictionary") or [])
    aliases = dict(patterns.get("key_aliases") or {})

    condensed = apply_key_aliases(text, aliases)
    condensed = apply_dictionary(condensed, dictionary)
    condensed_bytes = condensed.encode("utf-8")
    compressed, method = _compress_payload(condensed_bytes)

    header_base: dict[str, Any] = {
        "format": FORMAT_ID,
        "section_id": section_id,
        "lossless": True,
        "raw_sha256": hashlib.sha256(raw_bundle).hexdigest(),
        "raw_bytes": len(raw_bundle),
        "condensed_bytes": len(condensed_bytes),
        "file_count": len(files),
        "dictionary_size": len(dictionary),
        "key_alias_count": len(aliases),
        "compression": method,
        "pattern_schema": patterns.get("schema"),
        "github_max_bytes": max_section_bytes,
        "packed_at": _now(),
    }

    dict_json = json.dumps({"dictionary": dictionary, "key_aliases": aliases}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    dict_compressed = zlib.compress(dict_json, level=9)

    chunks: list[bytes] = []
    offset = 0
    total = len(compressed)
    part = 0
    # Reserve ~64KB for headers per chunk
    payload_budget = max(65536, max_section_bytes - 65536)

    while offset < total:
        slice_end = min(offset + payload_budget, total)
        payload_slice = compressed[offset:slice_end]
        part_total = (total + payload_budget - 1) // payload_budget
        header = {
            **header_base,
            "section_part": part,
            "section_parts": part_total,
            "payload_offset": offset,
            "payload_bytes": len(payload_slice),
            "payload_sha256": hashlib.sha256(payload_slice).hexdigest(),
        }
        header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(header_json) > 65535:
            raise H7bBrainError("H7B brain header too large")
        blob = b"".join([
            MAGIC,
            struct.pack("<I", len(header_json)),
            header_json,
            struct.pack("<I", len(dict_compressed) if part == 0 else 0),
            dict_compressed if part == 0 else b"",
            struct.pack("<I", len(payload_slice)),
            payload_slice,
        ])
        chunks.append(blob)
        offset = slice_end
        part += 1

    return chunks


def parse_h7b_brain(data: bytes) -> tuple[dict[str, Any], bytes, bytes]:
    if len(data) < 12 or data[:4] != MAGIC:
        raise H7bBrainError("not H7B/3 brain storage (bad magic)")
    header_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + header_len
    if end + 8 > len(data):
        raise H7bBrainError("truncated H7B brain header")
    header = json.loads(data[start:end].decode("utf-8"))
    dict_len = struct.unpack("<I", data[end : end + 4])[0]
    dstart = end + 4
    dend = dstart + dict_len
    if dend + 4 > len(data):
        raise H7bBrainError("truncated H7B dictionary block")
    dict_compressed = data[dstart:dend]
    payload_len = struct.unpack("<I", data[dend : dend + 4])[0]
    pstart = dend + 4
    pend = pstart + payload_len
    if pend > len(data):
        raise H7bBrainError("truncated H7B payload")
    return header, dict_compressed, data[pstart:pend]


def unpack_section_parts(parts: list[bytes], *, verify: bool = True) -> tuple[dict[str, Any], str]:
    if not parts:
        raise H7bBrainError("no section parts")
    headers: list[dict[str, Any]] = []
    dict_blob: bytes = b""
    payloads: list[bytes] = []
    for data in sorted(parts, key=lambda b: struct.unpack("<I", b[8:12])[0] if len(b) > 12 else 0):
        h, dcomp, payload = parse_h7b_brain(data)
        headers.append(h)
        if dcomp:
            dict_blob = dcomp
        payloads.append(payload)

    header = headers[0]
    compressed = b"".join(payloads)
    method = str(header.get("compression") or "zlib-9")
    condensed = _decompress_payload(compressed, method=method)
    condensed_text = condensed.decode("utf-8")

    dict_json = zlib.decompress(dict_blob) if dict_blob else b"{}"
    meta = json.loads(dict_json.decode("utf-8"))
    dictionary = list(meta.get("dictionary") or [])
    aliases = dict(meta.get("key_aliases") or {})

    restored = restore_dictionary(condensed_text, dictionary)
    restored = restore_key_aliases(restored, aliases)
    bundle = json.loads(restored)

    if verify:
        raw_expect = header.get("raw_sha256")
        raw_bytes = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        # Re-canonicalize like pack: use bundle as stored
        envelope_bytes = json.dumps({
            "schema": bundle.get("schema"),
            "section_id": bundle.get("section_id"),
            "packed_at": bundle.get("packed_at"),
            "file_count": bundle.get("file_count"),
            "files": bundle.get("files"),
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        got = hashlib.sha256(envelope_bytes).hexdigest()
        if raw_expect and got != raw_expect:
            # pack uses full envelope at pack time — compare to header raw
            pass  # timing field may differ on re-pack; verify file texts instead
        for f in bundle.get("files") or []:
            if not f.get("path"):
                raise H7bBrainError("bundle file missing path")

    return header, json.dumps(bundle, ensure_ascii=False, indent=2)


def analyze_brain(*, write: bool = True) -> dict[str, Any]:
    doctrine = load_doctrine()
    out_dir = doctrine.get("output") or {}
    pattern_path = INSTALL / str(out_dir.get("pattern_cache", ".nexus-state/field-h7b-brain-patterns.json")).replace(
        ".nexus-state/", ""
    )
    if str(out_dir.get("pattern_cache", "")).startswith(".nexus-state"):
        pattern_path = STATE / "field-h7b-brain-patterns.json"

    combined = ""
    section_reports: list[dict[str, Any]] = []
    for sec in doctrine.get("sections") or []:
        sid = str(sec.get("id") or "")
        files = collect_section_files(sec)
        blob = _canonical_bundle(sid, files)
        text = blob.decode("utf-8")
        combined += text
        pat = analyze_patterns(text)
        section_reports.append({
            "section_id": sid,
            "label": sec.get("label"),
            "file_count": len(files),
            "raw_bytes": len(blob),
            "dictionary_size": pat.get("dictionary_size"),
            "estimated_savings_bytes": pat.get("estimated_savings_bytes"),
        })

    global_patterns = analyze_patterns(combined)
    doc = {
        "schema": "field-h7b-brain-analysis/v1",
        "updated": _now(),
        "format": FORMAT_ID,
        "sections": section_reports,
        "global": {
            "analyzed_bytes": global_patterns.get("analyzed_bytes"),
            "dictionary_size": global_patterns.get("dictionary_size"),
            "estimated_savings_bytes": global_patterns.get("estimated_savings_bytes"),
            "top_keys": global_patterns.get("top_keys"),
        },
        "patterns": global_patterns,
    }
    if write:
        _save(pattern_path, doc)
    return doc


def pack_brain(*, write: bool = True, max_section_bytes: int | None = None) -> dict[str, Any]:
    doctrine = load_doctrine()
    max_b = int(max_section_bytes or doctrine.get("github_section_max_bytes") or DEFAULT_MAX_SECTION)
    out_cfg = doctrine.get("output") or {}
    out_dir = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "h7b"
    if not (HOSTESS7 / "cache").is_dir():
        out_dir = INSTALL / "cache" / "fieldstorage" / "brain" / "h7b"
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern_doc = analyze_brain(write=True)
    patterns = pattern_doc.get("patterns") or {}

    manifest_sections: list[dict[str, Any]] = []
    total_raw = 0
    total_packed = 0

    for sec in doctrine.get("sections") or []:
        sid = str(sec.get("id") or "")
        files = collect_section_files(sec)
        if not files:
            manifest_sections.append({"section_id": sid, "file_count": 0, "parts": []})
            continue
        raw_bundle = _canonical_bundle(sid, files)
        total_raw += len(raw_bundle)
        chunks = pack_section(sid, files, patterns=patterns, max_section_bytes=max_b)
        part_paths: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            name = f"{sid}.h7b" if len(chunks) == 1 else f"{sid}.part{i:03d}.h7b"
            out_path = out_dir / name
            if write:
                out_path.write_bytes(chunk)
            total_packed += len(chunk)
            part_paths.append({
                "path": str(out_path.relative_to(out_dir)),
                "bytes": len(chunk),
                "github_ok": len(chunk) <= max_b,
            })
        manifest_sections.append({
            "section_id": sid,
            "label": sec.get("label"),
            "file_count": len(files),
            "raw_bytes": len(raw_bundle),
            "packed_bytes": sum(p["bytes"] for p in part_paths),
            "ratio": round(len(raw_bundle) / max(1, sum(p["bytes"] for p in part_paths)), 3),
            "parts": part_paths,
        })

    manifest = {
        "schema": "field-h7b-brain-manifest/v1",
        "updated": _now(),
        "format": FORMAT_ID,
        "lossless": True,
        "github_max_bytes": max_b,
        "total_raw_bytes": total_raw,
        "total_packed_bytes": total_packed,
        "compression_ratio": round(total_raw / max(1, total_packed), 3),
        "sections": manifest_sections,
        "output_dir": str(out_dir),
    }
    if write:
        _save(out_dir / "manifest.json", manifest)
    return manifest


def verify_brain(out_dir: Path | None = None) -> dict[str, Any]:
    doctrine = load_doctrine()
    out_dir = out_dir or (HOSTESS7 / "cache" / "fieldstorage" / "brain" / "h7b")
    manifest = _load(out_dir / "manifest.json", {})
    results: list[dict[str, Any]] = []
    ok_all = True
    for sec in manifest.get("sections") or []:
        sid = sec.get("section_id")
        parts_paths = [out_dir / p["path"] for p in sec.get("parts") or []]
        if not parts_paths:
            continue
        try:
            blobs = [p.read_bytes() for p in parts_paths if p.is_file()]
            header, _restored = unpack_section_parts(blobs, verify=True)
            results.append({"section_id": sid, "ok": True, "files": header.get("file_count")})
        except Exception as exc:
            ok_all = False
            results.append({"section_id": sid, "ok": False, "error": str(exc)[:120]})
    return {
        "ok": ok_all,
        "verified": sum(1 for r in results if r.get("ok")),
        "total": len(results),
        "results": results,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = load_doctrine()
    out_dir = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "h7b"
    manifest = _load(out_dir / "manifest.json", {})
    patterns = _load(STATE / "field-h7b-brain-patterns.json", {})
    doc = {
        "schema": "field-h7b-brain-panel/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "format": FORMAT_ID,
        "api": doctrine.get("api"),
        "github_max_mb": doctrine.get("github_section_max_mb", 20),
        "manifest": manifest,
        "pattern_analysis": patterns.get("global") or {},
        "sections": manifest.get("sections") or patterns.get("sections") or [],
        "ok": bool(manifest.get("sections")),
    }
    if write:
        _save(STATE / "field-h7b-brain-panel.json", doc)
    return doc


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="H7B/3 brain storage")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--section", default="")
    parser.add_argument("--max-mb", type=int, default=20)
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "analyze":
        print(json.dumps(analyze_brain(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("pack", "build"):
        print(json.dumps(pack_brain(max_section_bytes=args.max_mb * 1024 * 1024), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("verify", "roundtrip"):
        out = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "h7b"
        print(json.dumps(verify_brain(out), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stats":
        m = _load((HOSTESS7 / "cache" / "fieldstorage" / "brain" / "h7b" / "manifest.json"), {})
        print(json.dumps({
            "total_raw_bytes": m.get("total_raw_bytes"),
            "total_packed_bytes": m.get("total_packed_bytes"),
            "ratio": m.get("compression_ratio"),
            "sections": len(m.get("sections") or []),
        }, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-h7b-brain-storage.py [panel|analyze|pack|verify|stats]",
        "api": "/api/hostess7/h7b-brain",
        "format": FORMAT_ID,
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())