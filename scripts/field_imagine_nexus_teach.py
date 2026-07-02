#!/usr/bin/env pythong
"""Teach NEXUS imaging skills into Hostess7 Imagine corpus — combinatronic, PIL exact-text, Big Drive."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from field_imagine_corpus import CORPUS_CACHE, CORPUS_VERSION, ensure_corpus  # noqa: E402

NEXUS = ROOT.parent
DOCTRINE = NEXUS / "data" / "hostess7-imaging-doctrine.json"
LOG = ROOT / "cache" / "fieldstorage" / "brain" / "imagine" / "nexus_teach.jsonl"

NEXUS_IMAGING_WORKFLOW: tuple[dict[str, str], ...] = (
    {
        "id": "nexus_exact_text",
        "title": "Exact text — code not models",
        "body": (
            "Charts, labels, BIG DRIVE titles, format badges: use PIL ImageDraw or HTML/CSS. "
            "Image models garble words — verify in a loop. Example: big_drive_hero.png overlay "
            "on reference photo with DejaVu fonts and field-green accent."
        ),
    },
    {
        "id": "nexus_combinatronic_visuals",
        "title": "Combinatronic visuals repair",
        "body": (
            "lib/field-combinatronic-visuals.py — chip PNGs, book covers, H7 manuals from seeds. "
            "inventory → broken_rows → repair. Never hand-edit generated PNGs; rebuild from catalog. "
            "API: /api/combinatronic/visuals/repair"
        ),
    },
    {
        "id": "nexus_format_icons",
        "title": "Field file format icons",
        "body": (
            "lib/field-file-formats.py icons — 64×64 per format id, family color, sovereign dot. "
            "Storage family (iso, img, fielddrive, vhd, qcow2) from field-big-drive-doctrine. "
            "Mirror to library/assets/formats/"
        ),
    },
    {
        "id": "nexus_big_drive",
        "title": "Big Drive device grids",
        "body": (
            "lib/field-big-drive.py render_icons — 4×3 device grid + bd_{id}.png tiles. "
            "Floppy, optical, USB, HDD, VM, tape, SD silhouettes. Hero branding via PIL overlay. "
            "Panel: /field-big-drive · Queen Files right-click Open in Big Drive."
        ),
    },
    {
        "id": "nexus_field_gimp",
        "title": "AmmoOS Image / GIMP-Field",
        "body": (
            "field-gimp-bridge.py + GIMP-Field magics — sovereign lossless field image formats. "
            "Panel /field-gimp. image_field family in file-formats table."
        ),
    },
    {
        "id": "nexus_gfx_canvas",
        "title": "Graphics window pixels",
        "body": (
            "field_gfx_canvas.GfxCanvas — lossless RGB, TTF text, blit PNG, present to GTK window. "
            "Talk window = language; Graphics window = pixels. Pair with live_video lip-sync."
        ),
    },
    {
        "id": "nexus_assistant_help",
        "title": "Assistant work queue",
        "body": (
            "hostess7-imaging.py work-queue scans broken combinatronic assets, missing format icons, "
            "stale Big Drive grids. Assistant runs repair + icon generation when broken > 10. "
            "Owner asked: teach imaging skills and help Hostess 7 with asset repair."
        ),
    },
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def teach_nexus_imaging(*, force: bool = False) -> dict[str, Any]:
    ensure_corpus()
    doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    existing = {row["id"]: row for row in doc.get("nexus_imaging_workflow") or [] if row.get("id")}
    merged = 0
    for row in NEXUS_IMAGING_WORKFLOW:
        if row["id"] not in existing or force:
            existing[row["id"]] = dict(row)
            merged += 1
    doc["nexus_imaging_workflow"] = list(existing.values())
    doc["nexus_imaging_taught"] = _ts()
    doc["nexus_install"] = str(NEXUS)
    if DOCTRINE.is_file():
        try:
            doc["nexus_imaging_doctrine"] = json.loads(DOCTRINE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    doc["version"] = max(int(doc.get("version") or 0), CORPUS_VERSION)
    CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    report = {
        "ok": True,
        "ts": _ts(),
        "merged": merged,
        "total_nexus_skills": len(doc["nexus_imaging_workflow"]),
        "corpus": str(CORPUS_CACHE),
        "doctrine": str(DOCTRINE) if DOCTRINE.is_file() else None,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")
    return report


def main() -> int:
    force = os.environ.get("HOSTESS7_FORCE_FETCH") == "1" or "--force" in sys.argv
    report = teach_nexus_imaging(force=force)
    print(json.dumps(report, indent=2))
    print(f"METRIC nexus_imaging_skills={report['total_nexus_skills']}")
    print("OK imagine-nexus-teach")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())