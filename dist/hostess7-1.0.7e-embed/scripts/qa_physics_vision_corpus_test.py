#!/usr/bin/env pythong
"""QA: Physics, vision, motion, 3D spatial corpora."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_physics_corpus import (  # noqa: E402
    PHYSICS_CORPUS_VERSION,
    corpus_stats as physics_stats,
    ensure_corpus as ensure_physics,
    search_physics,
    synthesize_physics_paragraphs,
)
from field_vision_corpus import (  # noqa: E402
    VISION_CORPUS_VERSION,
    ensure_corpus as ensure_vision,
    search_vision,
    synthesize_vision_paragraphs,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_physics()
    ensure_vision()
    pstats = physics_stats()
    if pstats["domains"] < 12:
        return fail(f"expected 12+ physics domains, got {pstats['domains']}")
    if pstats["version"] < PHYSICS_CORPUS_VERSION:
        return fail("physics corpus version stale")

    vision_path = ROOT / "cache" / "fieldstorage" / "brain" / "vision" / "corpus.json"
    vdoc = json.loads(vision_path.read_text(encoding="utf-8"))
    if int(vdoc.get("version", 0)) < VISION_CORPUS_VERSION:
        return fail("vision corpus version stale")
    if vdoc.get("domain_count", 0) < 18:
        return fail(f"expected 18+ vision domains, got {vdoc.get('domain_count')}")

    tv = search_vision("NTSC PAL HDMI television broadcast", limit=3)
    if not any(r.get("id") == "tv_broadcast_video" for r in tv):
        return fail("TV broadcast vision search miss")

    spatial = search_physics("3d spatial quaternion transform projection", limit=3)
    if not spatial or spatial[0].get("id") not in (
        "spatial_3d_foundations", "projection_imaging", "depth_stereo_pointcloud",
    ):
        return fail(f"3d spatial search wrong: {[r.get('id') for r in spatial]}")

    motion = search_vision("optical flow motion fps animation", limit=3)
    if not any(r.get("id") in ("motion_foundations", "scene_motion_perception") for r in motion):
        return fail("motion vision search miss")

    depth = search_vision("stereo depth point cloud 3d", limit=3)
    if not any(r.get("id") in ("depth_stereo_vision", "spatial_3d_reality") for r in depth):
        return fail("depth/stereo vision search miss")

    paras = synthesize_physics_paragraphs("entropy thermodynamics field canvas")
    if not any("entropy" in p.lower() or "thermo" in p.lower() for p in paras):
        return fail("physics synthesis empty")

    vparas = synthesize_vision_paragraphs("physics motion 3d spatial bridge")
    if len(vparas) < 2:
        return fail("vision synthesis too short")

    print("OK physics vision motion 3d spatial corpora")
    print(f"METRIC physics_domains={pstats['domains']}")
    print(f"METRIC vision_domains={vdoc.get('domain_count')}")
    print(f"METRIC qa_physics_vision=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())