#!/usr/bin/env pythong
"""QA: FLD1 fly codec — lossless roundtrip on brain-shaped JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_fly_codec import bench_fly, fly_pack, fly_unpack, is_fly  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    sample = ROOT / "cache" / "fieldstorage" / "brain" / "legal" / "corpus.json"
    if not sample.is_file():
        return fail("legal corpus missing for bench")

    raw = sample.read_bytes()
    packed = fly_pack(raw)
    if not is_fly(packed):
        return fail("FLD1 did not compress corpus sample")

    restored = fly_unpack(packed)
    if restored != raw:
        return fail("FLD1 roundtrip not lossless")

    stats = bench_fly(raw)
    if not stats.get("lossless"):
        return fail("bench reports not lossless")
    if stats.get("unpack_ms", 999) > 500:
        return fail(f"unpack too slow: {stats['unpack_ms']}ms")

    # H7 fly layer
    from field_h7_book import pack_h7, unpack_h7  # noqa: E402

    text = "Line one\nLine two\nRepeated key \"body\": value\n" * 20
    blob = pack_h7(text, {"id": "qa", "title": "QA"})
    hdr, out = unpack_h7(blob)
    if out != text:
        return fail("H7B fly layer not lossless")
    if hdr.get("format") not in ("h7b/1", "h7b/2"):
        return fail("unexpected H7 format")

    print(f"OK fly_codec ratio={stats.get('ratio')} unpack_ms={stats.get('unpack_ms')}")
    print("METRIC qa_field_fly_codec=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())