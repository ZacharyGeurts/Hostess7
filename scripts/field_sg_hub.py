#!/usr/bin/env pythong
"""SG/Hostess7 main hub — canonical folder, TEAM drive sync, reach map."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SG_ROOT = ROOT.parent
HUB_MANIFEST = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "sg_hub.json"

LINKED_ROOTS: tuple[dict[str, str], ...] = (
    {"name": "Hostess7", "path": str(ROOT), "role": "canonical_main"},
    {"name": "NewLatest", "path": str(SG_ROOT / "NewLatest"), "role": "nexus_field_stack"},
    {"name": "KILROY", "path": str(SG_ROOT / "NewLatest" / "KILROY"), "role": "field_die_kernel"},
    {"name": "field_mirror", "path": str(SG_ROOT / "NewLatest" / ".nexus-field-drive"), "role": "live_field_root"},
    {"name": "AMOURANTHRTX", "path": str(SG_ROOT / "AMOURANTHRTX"), "role": "field_research"},
    {"name": "memes", "path": str(SG_ROOT / "memes"), "role": "vision_archive"},
    {"name": "TEAM_drive", "path": "/media/default/HOSTESS7_TEAM", "role": "physical_team_data"},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def hub_status() -> dict:
    entries = []
    for item in LINKED_ROOTS:
        p = Path(item["path"])
        entries.append({
            **item,
            "present": p.is_dir() or p.is_file(),
            "writable": p.is_dir() and os.access(p, os.W_OK),
        })
    doc = {
        "updated": _ts(),
        "canonical": str(ROOT),
        "sg_root": str(SG_ROOT),
        "policy": (
            "SG/Hostess7 is the main folder; NewLatest is the live field stack; "
            ".nexus-field-drive is the host field mirror (not nested on TEAM); "
            "KILROY Field Die anchors kill tech at the kernel bottom."
        ),
        "roots": entries,
    }
    HUB_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    HUB_MANIFEST.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def print_hub(doc: dict) -> None:
    print("=== SG / Hostess7 Hub ===")
    print(f"Canonical: {doc['canonical']}")
    print(f"SG root:   {doc['sg_root']}")
    print(doc["policy"])
    print()
    for r in doc["roots"]:
        flag = "OK" if r["present"] else "missing"
        wr = "rw" if r.get("writable") else "ro"
        print(f"  [{flag}] {r['name']:14} {wr:3} {r['role']:16} {r['path']}")
    print(f"\nManifest: {HUB_MANIFEST}")
    print("METRIC sg_hub=1")
    print("OK sg-hub")


def sync_team_hint() -> None:
    print("\nField 1 sync: ./Hostess7.sh field sync  (rsync fieldstorage → TEAM NVMe)")
    print("Field 1 compact: ./Hostess7.sh field compact")


def main() -> int:
    doc = hub_status()
    print_hub(doc)
    sync_team_hint()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())