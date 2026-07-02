#!/usr/bin/env pythong
"""QA: Hostess 7 hemisphered brain — routing, workspaces, callosum transfer speed."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_brain_core import (  # noqa: E402
    HEMISPHERE_LEFT,
    HEMISPHERE_RIGHT,
    active_workspace,
    callosum_transfer,
    ensure_brain_layout,
    fuse_hemispheres,
    partition_paragraphs,
    route_query,
    set_active_workspace,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    os.environ["HOSTESS7_WORKSPACE"] = "default"
    ensure_brain_layout()

    route = route_query("taskbar OCR at 4K legal compliance", "vision")
    if not route.cross_transfer:
        return fail("cross_transfer expected for vision+legal query")
    if route.primary_area != "occipital":
        return fail(f"expected occipital, got {route.primary_area}")

    left, right = partition_paragraphs([
        "P1 terminal shell in dos/FieldRtxShell.hpp",
        "OCR 4K viewport taskbar click at 3840x2160",
    ])
    if len(left) != 1 or len(right) != 1:
        return fail(f"partition mismatch left={len(left)} right={len(right)}")

    t0 = time.perf_counter_ns()
    result = callosum_transfer(
        HEMISPHERE_LEFT,
        HEMISPHERE_RIGHT,
        {"tokens": ["ocr", "taskbar"], "summary": "vision hit"},
        area="occipital",
    )
    elapsed = time.perf_counter_ns() - t0
    if not result.ok:
        return fail("callosum transfer failed")
    if result.elapsed_us > 50_000:
        return fail(f"callosum too slow: {result.elapsed_us}µs")
    if elapsed > 50_000_000:
        return fail(f"wall clock too slow: {elapsed // 1000}µs")

    fused = fuse_hemispheres(left, right, route, pro=True)
    if len(fused) < 2:
        return fail("fuse returned too few paragraphs")

    set_active_workspace("field")
    if active_workspace() != "field":
        return fail("workspace switch failed")
    ws_path = ROOT / "cache" / "fieldstorage" / "brain" / "workspaces" / "field" / "state.json"
    if not ws_path.is_file():
        return fail("field workspace state missing")
    state = json.loads(ws_path.read_text(encoding="utf-8"))
    if not state.get("active"):
        return fail("field workspace not active")

    manifest = ROOT / "cache" / "fieldstorage" / "brain" / "areas" / "manifest.json"
    if not manifest.is_file():
        return fail("areas manifest missing")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if len(data.get("areas", [])) < 8:
        return fail("expected 8+ brain areas")

    set_active_workspace("default")
    print("OK brain hemisphere routing + callosum + workspaces")
    print(f"METRIC callosum_us={result.elapsed_us}")
    print(f"METRIC brain_areas={len(data.get('areas', []))}")
    print("METRIC qa_brain_hemisphere=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())