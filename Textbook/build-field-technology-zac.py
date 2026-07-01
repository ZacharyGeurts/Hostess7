#!/usr/bin/env pythong
"""Build Field Technology v5 as one ZAC7 monolith with SDF brain imaging.

Source: SG/Field_Primer (22 chapters)
Output: NewLatest/Textbook/field-technology-v5.zac
QA: lossless restore + checksum verify + size comparison (PDF | Text | Web | ZAC)

  pythong build-field-technology-zac.py
  pythong build-field-technology-zac.py --verify-only
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import struct
import sys
import tarfile
import tempfile
import zlib
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SG = ROOT.parents[1]
FIELD_PRIMER = SG / "Field_Primer"
HOSTESS7 = SG / "Hostess7"
CHAPTERS = FIELD_PRIMER / "content" / "chapters"
STAGING = ROOT / "staging" / "fieldstorage"
OUT_ZAC = ROOT / "field-technology-v5.zac"
PLAIN_TEXT = ROOT / "field-technology-v5.txt"
SIZE_REPORT = ROOT / "size-comparison.json"

sys.path.insert(0, str(HOSTESS7 / "scripts"))

from field_fly_codec import fly_pack, fly_unpack, is_fly, should_fly_path  # noqa: E402
import field_hostess_sdf_storage as sdf_mod  # noqa: E402
from field_hostess_sdf_storage import ensure_corpus, ensure_dirs, segment_text, verify_redata  # noqa: E402
from field_zac import (  # noqa: E402
    HEADER_SIZE,
    KIND_DATA,
    KIND_INDEX,
    MAGIC,
    VERSION,
    _STRUCT_HEADER,
    _compress,
    _extract_tar,
    _read_header,
    _sha256,
    _sha256_file,
    _write_header,
    pack_storage,
    restore_storage,
    verify_storage,
)

CHAPTER_ORDER = [
    "01.html", "02.html", "03.html", "04.html", "05.html", "06.html",
    "07.html", "08.html", "09.html", "10.html", "11.html", "12.html",
    "13.html", "14.html", "15.html", "16.html", "17.html", "18.html",
    "19.html", "20.html", "21.html", "22.html",
]
MONO_INDEX_NAME = "ZAC7/manifest.json"
FLY_PACK_MAX_BYTES = 2 * 1024 * 1024
WORLD_REDATA = SG / "World_Redata"


def _ledger_mark_zac(storage: Path, zac_ref: str) -> int:
    """Append `.zac converted` to ledger descriptions — never re-redata source files."""
    ledger_py = WORLD_REDATA / "redata" / "ledger.py"
    if not ledger_py.is_file():
        return 0
    if str(WORLD_REDATA) not in sys.path:
        sys.path.insert(0, str(WORLD_REDATA))
    from redata.ledger import mark_zac_converted  # noqa: WPS433

    count = 0
    for path in _iter_storage_files(storage):
        mark_zac_converted(path, zac_ref=zac_ref)
        count += 1
    return count


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KiB", "MiB", "GiB"):
        n /= 1024
        if n < 1024 or unit == "GiB":
            return f"{n:.2f} {unit}"
    return f"{n:.2f} GiB"


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section|article|blockquote)>", "\n\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    text = unescape(html)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def extract_textbook() -> tuple[str, list[dict[str, Any]]]:
    parts: list[str] = []
    meta: list[dict[str, Any]] = []
    for name in CHAPTER_ORDER:
        path = CHAPTERS / name
        if not path.is_file():
            raise FileNotFoundError(f"missing chapter: {path}")
        html = path.read_text(encoding="utf-8")
        body = html_to_text(html)
        parts.append(f"=== Chapter {name.replace('.html', '')} ===\n\n{body}")
        meta.append({"file": name, "html_bytes": len(html.encode("utf-8")), "text_words": len(re.findall(r"\b\w+\b", body))})
    full = "\n\n".join(parts) + "\n"
    return full, meta


def _pack_storage_bytes(src: Path) -> tuple[bytes, bool]:
    raw = src.read_bytes()
    if is_fly(raw):
        return raw, True
    if should_fly_path(src) and len(raw) <= FLY_PACK_MAX_BYTES:
        packed = fly_pack(raw)
        return packed, is_fly(packed)
    return raw, False


def _iter_storage_files(storage: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(storage.rglob("*")):
        if path.is_file():
            paths.append(path)
    return paths


def _rel_path(storage: Path, path: Path) -> str:
    return path.relative_to(storage).as_posix()


def _tar_add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def build_staging(text: str, chapter_meta: list[dict[str, Any]]) -> dict[str, Any]:
    if STAGING.is_dir():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    textbooks = STAGING / "textbooks"
    textbooks.mkdir(parents=True)
    text_path = textbooks / "field-technology-v5.txt"
    text_path.write_text(text, encoding="utf-8")
    PLAIN_TEXT.write_text(text, encoding="utf-8")

    meta_path = textbooks / "field-technology-v5.meta.json"
    meta_doc = {
        "title": "Field Technology v5",
        "edition": "2026",
        "chapters": len(CHAPTER_ORDER),
        "source": str(FIELD_PRIMER.relative_to(SG)),
        "chapter_meta": chapter_meta,
        "built": _ts(),
    }
    meta_path.write_text(json.dumps(meta_doc, indent=2) + "\n", encoding="utf-8")

    # SDF brain imaging under staging fieldstorage
    sdf_dst = STAGING / "brain" / "sdf"
    sdf_dst.parent.mkdir(parents=True, exist_ok=True)

    # Point SDF module at staging for this build (ROOT = storage root for relative paths)
    sdf_mod.ROOT = STAGING
    for attr, rel in (
        ("BRAIN_SDF", "brain/sdf"),
        ("SEGMENTS_DIR", "brain/sdf/segments"),
        ("PLATES_DIR", "brain/sdf/plates"),
        ("SDL_TEXT_DIR", "brain/sdf/sdl_text"),
        ("CORPUS", "brain/sdf/corpus.json"),
        ("BRIEF", "brain/sdf/sdf_storage_brief.json"),
        ("REGISTRY", "brain/sdf/segment_registry.jsonl"),
        ("TRUTH_LOG", "brain/sdf/truth_filter.jsonl"),
        ("QUARANTINE_DIR", "brain/sdf/quarantine"),
    ):
        setattr(sdf_mod, attr, STAGING / rel)

    ensure_dirs()
    ensure_corpus()

    segments = segment_text(
        text,
        source="Field_Primer/content/chapters",
        title="Field Technology v5",
    )
    plate_count = sum(1 for s in segments if s.get("plate_json"))
    human_count = sum(1 for s in segments if s.get("human_pgm"))
    truth_ok = sum(1 for s in segments if s.get("truth_accepted"))
    quarantine_count = sum(1 for s in segments if s.get("quarantine"))
    sdl_count = sum(1 for s in segments if s.get("sdl_text"))

    redata = verify_redata(brain_sdf=STAGING / "brain" / "sdf")
    if not redata.get("ok"):
        raise ValueError(f"redata verify failed: {redata.get('failures', [])[:3]}")

    brain_readme = STAGING / "brain" / "field-technology-v5.brain.json"
    brain_readme.write_text(
        json.dumps(
            {
                "title": "Field Technology v5 — redata lossless + human SDF",
                "doctrine": "lossless segments always; human .human.pgm always serviceable",
                "segments": len(segments),
                "analytic_plates": plate_count,
                "human_plates": human_count,
                "truth_accepted": truth_ok,
                "quarantined": quarantine_count,
                "sdl_text": sdl_count,
                "truth_log": "brain/sdf/truth_filter.jsonl",
                "redata_verify": redata,
                "registry": str(sdf_mod.REGISTRY.relative_to(STAGING)),
                "words_target": [900, 1200],
                "built": _ts(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    files = _iter_storage_files(STAGING)
    total_bytes = sum(p.stat().st_size for p in files)
    return {
        "segments": len(segments),
        "plates": plate_count,
        "human_plates": human_count,
        "truth_accepted": truth_ok,
        "quarantined": quarantine_count,
        "sdl_text": sdl_count,
        "redata_ok": redata.get("ok"),
        "files": len(files),
        "bytes": total_bytes,
    }


def _collect_file_meta(storage: Path) -> list[dict[str, Any]]:
    meta: list[dict[str, Any]] = []
    for path in _iter_storage_files(storage):
        rel = _rel_path(storage, path)
        data, flew = _pack_storage_bytes(path)
        st = path.stat()
        meta.append(
            {
                "path": rel,
                "size": len(data),
                "logical_size": st.st_size,
                "source_size": st.st_size,
                "source_mtime_ns": st.st_mtime_ns,
                "sha256": _sha256(data),
                "fly": flew,
                "data": data,
            }
        )
    return meta


def pack_monolith(storage: Path, out_path: Path) -> dict[str, Any]:
    """One .zac file: ZAC7 header + tar(manifest + all fieldstorage files)."""
    files_meta = _collect_file_meta(storage)
    manifest = {
        "format": "zac7",
        "version": VERSION,
        "layout": "monolith",
        "created": _ts(),
        "project": "FieldTechnology",
        "title": "Field Technology v5",
        "storage_root": "cache/fieldstorage",
        "total_files": len(files_meta),
        "total_bytes": sum(m["size"] for m in files_meta),
        "fly_codec": "FLD1",
        "fly_files": sum(1 for m in files_meta if m["fly"]),
        "files": [{k: v for k, v in m.items() if k != "data"} for m in files_meta],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    buf = io.BytesIO()
    fly_count = 0
    with tarfile.open(fileobj=buf, mode="w") as tar:
        _tar_add_bytes(tar, MONO_INDEX_NAME, manifest_bytes)
        for entry in files_meta:
            if entry["fly"]:
                fly_count += 1
            _tar_add_bytes(tar, entry["path"], entry["data"])
    body = buf.getvalue()
    compressed, digest = _compress(body, level=9)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fp:
        _write_header(
            fp,
            kind=KIND_DATA,
            shard_id=0,
            shard_total=1,
            uncompressed=len(body),
            compressed=compressed,
            payload_hash=digest,
        )

    return {
        "path": str(out_path),
        "files": len(files_meta),
        "uncompressed": len(body),
        "compressed": len(compressed) + HEADER_SIZE,
        "payload_compressed": len(compressed),
        "fly_files": fly_count,
        "segments_manifest": MONO_INDEX_NAME,
    }


def restore_monolith(zac_path: Path, storage: Path) -> dict[str, Any]:
    storage.mkdir(parents=True, exist_ok=True)
    if storage.is_dir() and any(storage.iterdir()):
        shutil.rmtree(storage)
        storage.mkdir(parents=True)

    with zac_path.open("rb") as fp:
        parsed = _read_header(fp)
    restored = _extract_tar(parsed["body"], storage)
    manifest_path = storage / MONO_INDEX_NAME
    if not manifest_path.is_file():
        raise ValueError(f"monolith missing embedded manifest: {MONO_INDEX_NAME}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"restored": len(restored), "manifest": manifest}


def verify_monolith(zac_path: Path, storage: Path) -> dict[str, Any]:
    with zac_path.open("rb") as fp:
        parsed = _read_header(fp)
    if parsed["kind"] != KIND_DATA:
        raise ValueError("monolith must be KIND_DATA shard")
    if parsed["shard_total"] != 1:
        raise ValueError("monolith shard_total must be 1")

    manifest: dict[str, Any] | None = None
    tar_digests: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(parsed["body"]), mode="r:") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            digest = _sha256(data)
            tar_digests[member.name] = digest
            if member.name == MONO_INDEX_NAME:
                manifest = json.loads(data.decode("utf-8"))

    if not manifest:
        raise ValueError("no manifest in monolith")

    for entry in manifest.get("files", []):
        rel = entry["path"]
        digest = tar_digests.get(rel)
        if digest is None:
            raise ValueError(f"tar missing file: {rel}")
        if digest != entry["sha256"]:
            raise ValueError(f"tar checksum mismatch: {rel}")

    missing: list[str] = []
    mismatches: list[dict[str, str]] = []
    for entry in manifest.get("files", []):
        rel = entry["path"]
        dest = storage / rel
        if not dest.is_file():
            missing.append(rel)
            continue
        digest = _sha256_file(dest)
        if digest != entry["sha256"]:
            mismatches.append({"path": rel, "expected": entry["sha256"], "actual": digest})

    return {
        "ok": not missing and not mismatches,
        "total_files": manifest.get("total_files", 0),
        "missing": missing,
        "mismatches": mismatches,
        "format": manifest.get("format"),
        "layout": manifest.get("layout"),
    }


def verify_zac_header(zac_path: Path) -> dict[str, Any]:
    with zac_path.open("rb") as fp:
        raw = fp.read(HEADER_SIZE)
    magic, version, kind, shard_id, shard_total, uncompressed, compressed_size, payload_hash = (
        _STRUCT_HEADER.unpack(raw)
    )
    if magic != MAGIC:
        raise ValueError(f"bad magic: {magic!r}")
    return {
        "magic": magic.decode("ascii", errors="replace"),
        "version": version,
        "kind": kind,
        "shard_id": shard_id,
        "shard_total": shard_total,
        "uncompressed": uncompressed,
        "compressed_size": compressed_size,
        "sha256": payload_hash.hex(),
    }


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def build_size_comparison(zac_bytes: int, text_bytes: int) -> dict[str, Any]:
    pdf_bytes = dir_size(FIELD_PRIMER / "pdf")
    web_bytes = dir_size(FIELD_PRIMER / "docs")
    html_bytes = dir_size(CHAPTERS)

    rows = [
        {"format": "PDF", "path": str(FIELD_PRIMER / "pdf"), "bytes": pdf_bytes, "human": _format_bytes(pdf_bytes)},
        {"format": "Text", "path": str(PLAIN_TEXT), "bytes": text_bytes, "human": _format_bytes(text_bytes)},
        {"format": "Web", "path": str(FIELD_PRIMER / "docs"), "bytes": web_bytes, "human": _format_bytes(web_bytes)},
        {"format": "HTML source", "path": str(CHAPTERS), "bytes": html_bytes, "human": _format_bytes(html_bytes)},
        {"format": "ZAC Field Technology", "path": str(OUT_ZAC), "bytes": zac_bytes, "human": _format_bytes(zac_bytes)},
    ]
    baseline_pdf = pdf_bytes or 1
    for row in rows:
        row["ratio_vs_pdf"] = round(row["bytes"] / baseline_pdf, 3)

    report = {
        "built": _ts(),
        "title": "Field Technology v5 — format size comparison",
        "rows": rows,
        "winner_smallest": min(rows, key=lambda r: r["bytes"])["format"],
        "zac_vs_pdf_pct": round(100 * zac_bytes / baseline_pdf, 1),
    }
    SIZE_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def print_size_table(report: dict[str, Any]) -> None:
    print("\n=== Field Technology v5 — size comparison ===\n")
    print(f"{'Format':<22} {'Bytes':>12}  {'Size':>10}  {'vs PDF':>8}")
    print("-" * 58)
    for row in report["rows"]:
        print(
            f"{row['format']:<22} {row['bytes']:>12,}  {row['human']:>10}  {row['ratio_vs_pdf']:>7.3f}x"
        )
    print("-" * 58)
    print(f"Smallest: {report['winner_smallest']} · ZAC is {report['zac_vs_pdf_pct']}% of PDF size\n")


def cross_check_hostess7_pack(storage: Path) -> dict[str, Any]:
    """Standard ZAC7 multi-shard pack + restore — must also pass."""
    with tempfile.TemporaryDirectory() as tmp:
        zac_dir = Path(tmp) / "zac"
        restore_to = Path(tmp) / "restored"
        report = pack_storage(
            storage=storage,
            out_dir=zac_dir,
            max_shard_bytes=512 * 1024 * 1024,
            index_name="field-technology-v5-split.zac",
            fast=False,
            force=True,
        )
        restore_storage(
            zac_dir=zac_dir,
            index_name="field-technology-v5-split.zac",
            storage=restore_to,
            verify=True,
        )
        verify = verify_storage(
            zac_dir=zac_dir,
            index_name="field-technology-v5-split.zac",
            storage=restore_to,
        )
        if not verify.get("ok"):
            raise ValueError("Hostess7 split ZAC7 verify failed")
        return {
            "data_shards": report.get("data_shards"),
            "compressed_bytes": report.get("compressed_bytes"),
            "total_files": report.get("total_files"),
        }


def main() -> int:
    verify_only = "--verify-only" in sys.argv
    if verify_only:
        if not OUT_ZAC.is_file():
            print(f"FAIL missing {OUT_ZAC}", file=sys.stderr)
            return 1
        with tempfile.TemporaryDirectory() as tmp:
            restored = Path(tmp) / "fieldstorage"
            restore_monolith(OUT_ZAC, restored)
            result = verify_monolith(OUT_ZAC, restored)
            header = verify_zac_header(OUT_ZAC)
        print(json.dumps({"header": header, "verify": result}, indent=2))
        if not result.get("ok"):
            print("FAIL monolith verify", file=sys.stderr)
            return 1
        print("OK verify-only")
        return 0

    if not CHAPTERS.is_dir():
        print(f"FAIL Field_Primer chapters missing: {CHAPTERS}", file=sys.stderr)
        return 1

    print("Extracting Field Technology v5 text…")
    text, chapter_meta = extract_textbook()
    text_bytes = len(text.encode("utf-8"))
    print(f"  {len(CHAPTER_ORDER)} chapters · {_format_bytes(text_bytes)} plain text")

    print("Building staging fieldstorage + SDF imaging…")
    staging_info = build_staging(text, chapter_meta)
    print(
        f"  {staging_info['segments']} Mayer segments · {staging_info['plates']} analytic · "
        f"{staging_info['human_plates']} human SDF · truth={staging_info['truth_accepted']} · "
        f"quarantine={staging_info['quarantined']} · {staging_info['files']} files · "
        f"{_format_bytes(staging_info['bytes'])}"
    )

    print(f"Packing monolith → {OUT_ZAC.name}…")
    pack_info = pack_monolith(STAGING, OUT_ZAC)
    marked = _ledger_mark_zac(STAGING, OUT_ZAC.name)
    if marked:
        print(f"  ledger: {marked} file(s) annotated · .zac converted (no re-redata)")
    header = verify_zac_header(OUT_ZAC)
    print(
        f"  ZAC7 v{header['version']} · {_format_bytes(pack_info['compressed'])} on disk "
        f"({pack_info['files']} files, FLD1×{pack_info['fly_files']})"
    )

    print("Verify lossless restore…")
    with tempfile.TemporaryDirectory() as tmp:
        restored = Path(tmp) / "fieldstorage"
        restore_monolith(OUT_ZAC, restored)
        verify = verify_monolith(OUT_ZAC, restored)
    if not verify.get("ok"):
        print(f"FAIL verify: missing={verify.get('missing')} mismatches={verify.get('mismatches')}", file=sys.stderr)
        return 1
    print(f"  OK {verify['total_files']} files checksum-matched")

    print("Cross-check Hostess7 split ZAC7 pack/restore…")
    split = cross_check_hostess7_pack(STAGING)
    print(f"  OK split pack ({split['data_shards']} data shard(s), {_format_bytes(split['compressed_bytes'])})")

    zac_bytes = OUT_ZAC.stat().st_size
    report = build_size_comparison(zac_bytes, text_bytes)
    print_size_table(report)

    summary = {
        "zac": str(OUT_ZAC),
        "text": str(PLAIN_TEXT),
        "size_report": str(SIZE_REPORT),
        "header": header,
        "pack": pack_info,
        "staging": staging_info,
        "verify_ok": True,
        "split_zac7_ok": True,
    }
    (ROOT / "build-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("OK field-technology-v5.zac")
    print(f"METRIC zac_bytes={zac_bytes}")
    print(f"METRIC sdf_segments={staging_info['segments']}")
    print(f"METRIC sdf_plates={staging_info['plates']}")
    print(f"METRIC sdf_human_plates={staging_info['human_plates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())