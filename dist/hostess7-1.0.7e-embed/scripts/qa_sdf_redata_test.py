#!/usr/bin/env pythong
"""QA: redata lossless segments + human-serviceable SDF plates."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import field_hostess_sdf_storage as sdf  # noqa: E402
from field_hostess_sdf_storage import process_segment, verify_redata  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "brain" / "sdf"
        sdf.ROOT = Path(tmp)
        sdf.BRAIN_SDF = base
        sdf.SEGMENTS_DIR = base / "segments"
        sdf.PLATES_DIR = base / "plates"
        sdf.SDL_TEXT_DIR = base / "sdl_text"
        sdf.REGISTRY = base / "segment_registry.jsonl"
        sdf.TRUTH_LOG = base / "truth_filter.jsonl"
        sdf.QUARANTINE_DIR = base / "quarantine"
        sdf.CORPUS = base / "corpus.json"
        sdf.BRIEF = base / "sdf_storage_brief.json"

        sample = (
            "Field grid dispatch at binding eight. grep THERMO stderr jsonl. "
            "The operator reads fabric texels and packet field rows without cloud truth. " * 12
        )
        rec = process_segment(sample, source="qa", index=0)
        if rec.get("action") == "toss":
            return fail("toss action still returned — use redata")
        if not rec.get("lossless") or not rec.get("text_sha256"):
            return fail("missing lossless metadata")
        if not rec.get("truth_filter", {}).get("accepted"):
            return fail("sample segment failed truth filter")
        if not rec.get("human_pgm") or not rec.get("segment_json"):
            return fail("missing human plate or segment json")

        seg_path = sdf.SEGMENTS_DIR / f"{rec['id']}.json"
        if not seg_path.is_file():
            return fail("segment json not written")
        doc = json.loads(seg_path.read_text(encoding="utf-8"))
        if doc.get("text") != sample:
            return fail("segment text not lossless")

        report = verify_redata(brain_sdf=base)
        if not report.get("ok"):
            return fail(f"verify_redata: {report.get('failures')}")

    print(f"OK redata lossless human_plates={report.get('human_plates')}")
    print("METRIC sdf_redata_qa=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())