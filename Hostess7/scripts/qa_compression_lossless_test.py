#!/usr/bin/env pythong
"""QA: unified lossless round-trip — FLD1, H7B, ZAC7, library shelf."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_fly_codec import fly_pack, fly_unpack  # noqa: E402
from field_h7_book import pack_h7, unpack_h7, write_h7, read_h7_file  # noqa: E402
from field_library import TEXTBOOKS_DIR, build_library  # noqa: E402
from field_zac import pack_storage, restore_storage, verify_storage, STORAGE  # noqa: E402

STORAGE = ROOT / "cache" / "fieldstorage"


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def test_fld1() -> str | None:
    sample = json.dumps({"brain": "test", "lanes": ["hearing", "imagine"], "unicode": "café 日本"}, indent=2)
    packed = fly_pack(sample.encode("utf-8"))
    back = fly_unpack(packed).decode("utf-8")
    if back != sample:
        return "FLD1 roundtrip mismatch"
    return None


def test_h7() -> str | None:
    text = "Hearing line one\nChildren's book — every char: ♠\nThird line\n"
    blob = pack_h7(text, {"id": "qa", "title": "Lossless"})
    _, back = unpack_h7(blob)
    if back != text:
        return "H7 pack/unpack mismatch"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "qa.h7"
        write_h7(p, text, {"id": "qa"})
        doc = read_h7_file(p)
        if doc.get("text") != text:
            return "H7 file read mismatch"
    return None


def test_library_h7_on_disk() -> str | None:
    manifest = build_library(force_fetch=False)
    if manifest.get("h7_packed", 0) < 20:
        return f"library too few packed: {manifest.get('h7_packed')}"
    on_disk = list(TEXTBOOKS_DIR.glob("*.h7"))
    if len(on_disk) < 20:
        return f"too few .h7 on disk: {len(on_disk)}"
    for path in on_disk[:5]:
        doc = read_h7_file(path, line_start=1, line_end=3)
        if not doc.get("lines") and not doc.get("text"):
            return f"read failed: {path.name}"
        full = read_h7_file(path)
        text = full.get("text", "")
        if len(text) < 50:
            return f"book too short: {path.name}"
        meta = {k: v for k, v in full.items() if k not in ("text", "lines", "path", "line_start", "line_end")}
        with tempfile.TemporaryDirectory() as tmp:
            repack = Path(tmp) / "roundtrip.h7"
            write_h7(repack, text, meta)
            doc2 = read_h7_file(repack)
            if doc2.get("text") != text:
                return f"H7 re-pack lossy: {path.name}"
    return None


def test_zac_roundtrip() -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        mini = Path(tmp) / "fieldstorage"
        (mini / "brain" / "hearing").mkdir(parents=True)
        (mini / "textbooks").mkdir(parents=True)
        payload = json.dumps({"lossless": True, "hearing": "roundtrip", "n": 42})
        marker = mini / "brain" / "hearing" / "lossless_probe.json"
        marker.write_text(payload, encoding="utf-8")
        sample_h7 = STORAGE / "textbooks" / "gutenberg_alice.h7"
        if sample_h7.is_file():
            shutil.copy(sample_h7, mini / "textbooks" / "gutenberg_alice.h7")

        zac_dir = Path(tmp) / "zac"
        report = pack_storage(storage=mini, out_dir=zac_dir, max_shard_bytes=2 * 1024 * 1024)
        if report.get("total_files", 0) < 1:
            return "zac pack empty"

        marker.unlink(missing_ok=True)
        restore_storage(zac_dir=zac_dir, storage=mini, verify=True)
        verify = verify_storage(zac_dir=zac_dir, storage=mini)
        if not verify.get("ok"):
            return (
                f"zac verify failed missing={len(verify.get('missing', []))} "
                f"mismatch={len(verify.get('mismatches', []))}"
            )
        if not marker.is_file():
            return "probe file missing after zac restore"
        if marker.read_text(encoding="utf-8") != payload:
            return "probe bytes differ after zac round-trip"
        if sample_h7.is_file():
            restored = mini / "textbooks" / "gutenberg_alice.h7"
            if not restored.is_file():
                return "sample .h7 missing after zac restore"
            orig_text = read_h7_file(sample_h7).get("text", "")
            back_text = read_h7_file(restored).get("text", "")
            if orig_text != back_text:
                return "sample .h7 text differ after zac round-trip (lossy)"
    return None


def main() -> int:
    for name, fn in (
        ("fld1", test_fld1),
        ("h7", test_h7),
        ("library", test_library_h7_on_disk),
        ("zac", test_zac_roundtrip),
    ):
        err = fn()
        if err:
            return fail(f"{name}: {err}")
        print(f"OK lossless_{name}")

    print("METRIC qa_compression_lossless=1")
    print("OK compression-lossless-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())