#!/usr/bin/env pythong
"""QA: Reality domain registry + whole-of-reality familiarization."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_beyond_domains import BEYOND_DOMAINS  # noqa: E402
from field_beyond_corpus import CORPUS_VERSION as BEYOND_VERSION  # noqa: E402
from field_reality_familiarize import run_reality_familiarize  # noqa: E402
from field_reality_registry import (  # noqa: E402
    REALITY_PILLARS,
    REGISTRY_PATH,
    build_registry,
    search_reality,
    synthesize_reality_paragraphs,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if BEYOND_VERSION < 5:
        return fail(f"expected beyond corpus v5+, got v{BEYOND_VERSION}")

    ids = {d.get("id") for d in BEYOND_DOMAINS}
    for need in ("whole_of_reality", "hostess_domain_registry"):
        if need not in ids:
            return fail(f"missing beyond domain {need}")

    if len(REALITY_PILLARS) < 8:
        return fail(f"expected 8+ reality pillars, got {len(REALITY_PILLARS)}")

    brief = run_reality_familiarize()
    if not REGISTRY_PATH.is_file():
        return fail("reality_domains_registry.json not written")

    reg = build_registry()
    if reg.get("lane_count", 0) < 18:
        return fail(f"too few lanes: {reg.get('lane_count')}")
    if reg.get("domain_count_total", 0) < 100:
        return fail(f"domain count too low: {reg.get('domain_count_total')}")

    hits = search_reality("whole of reality all domains familiarize", limit=6)
    if not any(h.get("id") == "whole_of_reality" for h in hits):
        return fail(f"whole_of_reality not in search hits: {[h.get('id') for h in hits]}")

    paras = synthesize_reality_paragraphs("map the whole of reality")
    if len(paras) < 5:
        return fail("reality synthesis too thin")

    fam = brief.get("familiarity_passed", 0)
    total = brief.get("familiarity_total", 1)
    if fam < total - 1:
        return fail(f"familiarity probes weak: {fam}/{total}")

    print(f"OK reality lanes={reg.get('lane_count')} domains={reg.get('domain_count_total')}")
    print(f"OK familiarity {fam}/{total}")
    print(f"METRIC reality_lanes={reg.get('lane_count')}")
    print(f"METRIC reality_domains={reg.get('domain_count_total')}")
    print("OK reality-familiarize-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())