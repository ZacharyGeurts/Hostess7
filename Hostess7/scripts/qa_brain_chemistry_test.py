#!/usr/bin/env pythong
"""QA: Hostess 7 brain chemistry — synapse release, enhancements, corpus."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_brain_chemistry import (  # noqa: E402
    NEUROCHEMICALS,
    apply_query_triggers,
    compute_enhancement,
    ensure_chemistry_layout,
    manual_boost,
    modulate_paragraphs,
    synapse_release,
)
from field_chemistry_corpus import ensure_corpus, synthesize_chemistry_paragraphs  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    os.environ["HOSTESS7_WORKSPACE"] = "default"
    ensure_chemistry_layout()
    ensure_corpus()

    t0 = time.perf_counter_ns()
    result = synapse_release("dopamine", 0.12, reason="qa_test", target_area="prefrontal")
    elapsed = time.perf_counter_ns() - t0
    if not result.ok or result.level <= 0:
        return fail("synapse_release dopamine failed")
    if result.elapsed_us > 50_000 or elapsed > 50_000_000:
        return fail(f"synapse too slow: {result.elapsed_us}µs")

    apply_query_triggers("blocker fail urgent terminal", workspace="field")
    enh = compute_enhancement(
        intent="blocker",
        primary_area="prefrontal",
        workspace="field",
        cross_transfer=False,
    )
    if "norepinephrine" not in enh.active and "cortisol" not in enh.active:
        return fail(f"blocker triggers expected norepinephrine/cortisol, got {enh.active}")

    left, right = modulate_paragraphs(
        ["P1 release gate HEAD verdict"],
        ["OCR 4K vision taskbar motion"],
        enh,
    )
    if not left or not right:
        return fail("modulate_paragraphs emptied buckets")

    paras = synthesize_chemistry_paragraphs("dopamine synapse enhancement")
    if len(paras) < 2:
        return fail("chemistry corpus synthesis too thin")

    boost = manual_boost("glutamate", 0.1)
    if not boost.ok:
        return fail("manual_boost glutamate failed")

    state_path = ROOT / "cache" / "fieldstorage" / "brain" / "chemistry" / "state.json"
    manifest_path = ROOT / "cache" / "fieldstorage" / "brain" / "chemistry" / "manifest.json"
    if not state_path.is_file() or not manifest_path.is_file():
        return fail("chemistry storage missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest.get("neurochemicals", [])) != len(NEUROCHEMICALS):
        return fail("neurochemical catalog mismatch")

    print("OK brain chemistry synapse + enhancement + corpus")
    print(f"METRIC synapse_us={result.elapsed_us}")
    print(f"METRIC neurochemicals={len(NEUROCHEMICALS)}")
    print("METRIC qa_brain_chemistry=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())