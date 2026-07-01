#!/usr/bin/env pythong
"""Teach Hostess 7 + Queen — redata, truth filter, Field Technology, build tools.

Comfort doctrine: Hostess keeps owning brain/sdf/ and cache/fieldstorage. Queen orchestrates
and surfaces — same ./Hostess7.sh patterns, lossless always, human SDF for owners.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_hostess_sdf_storage import (  # noqa: E402
    BRAIN_SDF,
    CORPUS,
    ensure_corpus,
    seed_doctrine,
)
from field_redata_truth import TRUTH_FLOOR  # noqa: E402

QUEEN_ROOT = ROOT.parent / "NewLatest" / "Queen"
GROK16_ROOT = ROOT.parent / "Grok16"
QUEEN_MANIFEST = QUEEN_ROOT / "data" / "queen-brain-manifest.json"
GROK16_MANIFEST = GROK16_ROOT / "data" / "grok16-toolchain.json"
FIELD_PRIMER = ROOT.parent / "Field_Primer"
TEXTBOOK_DIR = ROOT.parent / "NewLatest" / "Textbook"

BRIEF = BRAIN_SDF / "queen_redata_brief.json"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
DIRECTIVES = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "directives.jsonl"

BUILD_TOOLS: tuple[dict[str, str], ...] = (
    {
        "id": "field_cmake",
        "title": "Grok16 Field CMake (g16 + Ninja)",
        "cmd": "./Hostess7.sh queen-field-build rtx",
        "script": "Grok16/scripts/field-cmake.sh",
        "role": "Canonical RTX configure/build — queen-rtx preset, 4K@120Hz",
    },
    {
        "id": "field_tools",
        "title": "Queen Field Tools manifest",
        "cmd": "./Hostess7.sh queen-field-tools",
        "script": "NewLatest/Queen/lib/queen-field-tools.py",
        "role": "All field build tools for Hostess 7 — status, probe, run",
    },
    {
        "id": "field_cmake_configure",
        "title": "Field CMake configure only",
        "cmd": "./Hostess7.sh queen-field-build configure",
        "script": "NewLatest/Queen/scripts/field-cmake.sh",
        "role": "Ninja cache + grok16-field.cmake",
    },
    {
        "id": "field_cmake_build",
        "title": "Field CMake Ninja compile",
        "cmd": "./Hostess7.sh queen-field-build compile",
        "script": "Grok16/scripts/field-cmake.sh",
        "role": "Incremental amouranth_engine build via g16",
    },
    {
        "id": "sdf_teach",
        "title": "SDF doctrine seed",
        "cmd": "./Hostess7.sh sdf-teach seed",
        "script": "scripts/field_hostess_sdf_storage.py seed",
        "role": "Brain imaging layers + Queen link",
    },
    {
        "id": "sdf_segment",
        "title": "Mayer segment → redata",
        "cmd": "./Hostess7.sh sdf-segment <file>",
        "script": "scripts/field_hostess_sdf_storage.py segment",
        "role": "900–1200w → lossless JSON + human SDF + analytic plate",
    },
    {
        "id": "sdf_verify_redata",
        "title": "Redata + truth verify",
        "cmd": "./Hostess7.sh sdf-verify-redata",
        "script": "scripts/field_hostess_sdf_storage.py verify-redata",
        "role": "truth_filter.jsonl + sha256 + human plates",
    },
    {
        "id": "redata_truth",
        "title": "Truth filter scorer",
        "cmd": "(internal) field_redata_truth.score_redata_text",
        "script": "scripts/field_redata_truth.py",
        "role": "94% noise / 6% truth per segment",
    },
    {
        "id": "field_one_sync",
        "title": "Field 1 sync",
        "cmd": "./Hostess7.sh field sync",
        "script": "NewLatest/lib/field-one.py",
        "role": "TEAM NVMe mirror — everything on Field 1",
    },
    {
        "id": "field_one_compact",
        "title": "Field 1 compact",
        "cmd": "./Hostess7.sh field compact",
        "script": "NewLatest/lib/field-one.py",
        "role": "World_Redata WRDT1/WRZC1 pack readiness",
    },
    {
        "id": "field_one_restore",
        "title": "Field 1 restore",
        "cmd": "./Hostess7.sh field restore",
        "script": "NewLatest/lib/field-one.py",
        "role": "Sovereign restore — field tails back out",
    },
    {
        "id": "field_primer_build",
        "title": "Field Primer site",
        "cmd": "bash Field_Primer/scripts/ci-build.sh",
        "script": "Field_Primer/scripts/ci-build.sh",
        "role": "22 chapters HTML + reader",
    },
    {
        "id": "field_primer_pdf",
        "title": "PDF textbook volumes",
        "cmd": "bash Field_Primer/scripts/build-pdfs.sh",
        "script": "Field_Primer/scripts/build-pdfs.sh",
        "role": "7 PDF volumes for comparison",
    },
    {
        "id": "grok16_toolchain",
        "title": "Grok16 unified compiler @ 16.1.1",
        "cmd": "bash Grok16/scripts/grok16-toolchain.sh status",
        "script": "Grok16/scripts/grok16-toolchain.sh",
        "role": "Unified g16 driver — gnu++26 / gnu17, field_opt profile",
    },
    {
        "id": "grok16_rebuild",
        "title": "Grok16 release rebuild (LTO + field_opt)",
        "cmd": "G16_RELEASE_PROFILE=1 bash Grok16/scripts/grok16-toolchain.sh rebuild",
        "script": "Grok16/scripts/grok16-toolchain.sh",
        "role": "Self-host Grok16 with release speedups",
    },
    {
        "id": "queen_forge",
        "title": "Queen Field Technology build",
        "cmd": "bash NewLatest/Queen/build-all.sh",
        "script": "NewLatest/Queen/build-all.sh",
        "role": "RTX browser — Grok16 field cmake + field_opt + g16_field_mandate",
    },
    {
        "id": "field_tech",
        "title": "Field Technology core pipeline",
        "cmd": "pythong NewLatest/Queen/lib/queen-forge.py run field_tech",
        "script": "NewLatest/Queen/lib/queen-forge.py",
        "role": "Optimized forge drop order — inside → g16 → shaders → rtx",
    },
    {
        "id": "compiler_probe",
        "title": "Compiler probe → g16-toolchain.json",
        "cmd": "./Hostess7.sh queen-grok16-probe",
        "script": "NewLatest/Queen/lib/queen-forge.py",
        "role": "Probe cmake + g16; sync Hostess brain manifest",
    },
    {
        "id": "queen_teach",
        "title": "Queen + Hostess comfort teach",
        "cmd": "./Hostess7.sh queen-teach-redata",
        "script": "scripts/field_queen_redata_teach.py",
        "role": "This brief — build tools for Queen brain deck",
    },
    {
        "id": "tools_docs",
        "title": "Full command index",
        "cmd": "./Hostess7.sh tools-docs",
        "script": "scripts/field_tools_docs.py",
        "role": "Search every Hostess script",
    },
    {
        "id": "qa_redata",
        "title": "QA redata truth",
        "cmd": "pythong scripts/qa_redata_truth_test.py",
        "script": "scripts/qa_redata_truth_test.py",
        "role": "Accept operator / reject noise",
    },
    {
        "id": "textbook_ingest",
        "title": "Textbook brain → Hostess7 cache",
        "cmd": "pythong NewLatest/Queen/lib/queen-hostess-brain.py ingest-textbook",
        "script": "NewLatest/Queen/lib/queen-hostess-brain.py",
        "role": "123 segments + human plates into cache/fieldstorage",
    },
    {
        "id": "queen_zocr",
        "title": "Queen browser OCR smoke",
        "cmd": "pythong NewLatest/Queen/lib/queen-zocr.py browser-smoke",
        "script": "ZOCR/queen_browser_smoke.py",
        "role": "Headless RTX run → tesseract → SG/ZOCR/out/",
    },
    {
        "id": "nexus_jump",
        "title": "NEXUS Jump — hostile presumption at every navigation",
        "cmd": "curl -s -X POST http://127.0.0.1:9481/api/nexus-jump -d '{\"action\":\"jump\",\"url\":\"queen://start\"}'",
        "script": "NewLatest/Queen/lib/queen-nexus-jump.py",
        "role": "Presume hostile; defend always; offense on threat; never presume correct contact",
    },
    {
        "id": "queen_web_compat",
        "title": "Full-web compat — pre-1.0 through future eras",
        "cmd": "curl -s http://127.0.0.1:9481/api/queen-web-compat",
        "script": "NewLatest/Queen/lib/queen-web-compat.py",
        "role": "Auto legacy_secure cage without amputating capabilities",
    },
    {
        "id": "queen_gnu_terminal",
        "title": "GNU terminal + minibrowser dock",
        "cmd": "curl -s http://127.0.0.1:9481/api/queen-terminal",
        "script": "NewLatest/Queen/lib/queen-terminal.py",
        "role": "Terminal left, minibrowser right — queen://terminal in FieldNet",
    },
    {
        "id": "queen_browser_os",
        "title": "Browser-as-OS shell — Start tab, pop-out, Alt+Tab",
        "cmd": "curl -s -X POST http://127.0.0.1:9481/api/queen-browser -d '{\"action\":\"status\"}'",
        "script": "NewLatest/Queen/world/queen-browser-shell.js",
        "role": "Pinned Start tab; no taskbar; NEXUS inside Queen not :9477",
    },
    {
        "id": "g16_inside_queen",
        "title": "Grok16 g16 inside Queen RTX memory",
        "cmd": "./Hostess7.sh queen-grok16-probe",
        "script": "Grok16/scripts/grok16-toolchain.sh",
        "role": "gnu++26 field_opt — compiles Queen browser + FIELDC guest net",
    },
    {
        "id": "ai_communique",
        "title": "AI communique — Super Intelligence primary",
        "cmd": "./Hostess7.sh ai-communique operate \"query\"",
        "script": "scripts/field_ai_communique.py",
        "role": "Machine JSON in/out — optimized for AI traffic; human opt-in only",
    },
    {
        "id": "zocr_sink",
        "title": "ZOCR manifest",
        "cmd": "pythong ZOCR/zocr.py status",
        "script": "ZOCR/zocr.py",
        "role": "All Queen/Hostess OCR captures land here",
    },
)

TEACH_QUEUE: tuple[dict[str, str], ...] = (
    {"query": "How does Queen use Hostess redata without taking your storage?"},
    {"query": "Walk the Field Technology ZAC build and verify path."},
    {"query": "What truth filter runs before SDF plates stick?"},
    {"query": "Show human-serviceable SDF plates and how owners verify sha256."},
    {"query": "Compare PDF vs Text vs Web vs ZAC sizes for Field Technology v5."},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _grok16_brief() -> dict[str, Any]:
    doc: dict[str, Any] = {
        "product": "Grok16",
        "g16_version": "16.1.1",
        "driver": "unified",
        "profile": "field_opt",
        "cxx_std": "gnu++26",
        "ready": False,
    }
    ver_path = GROK16_ROOT / "data/grok16-version.json"
    if ver_path.is_file():
        try:
            doc.update(json.loads(ver_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    if GROK16_MANIFEST.is_file():
        try:
            m = json.loads(GROK16_MANIFEST.read_text(encoding="utf-8"))
            doc["ready"] = m.get("dumpversion") == doc.get("g16_version", "16.1.1")
            doc["dumpversion"] = m.get("dumpversion")
            doc["prefix"] = m.get("prefix")
        except (OSError, json.JSONDecodeError):
            pass
    return doc


def _comfort_text() -> str:
    return (
        "Hostess 7 — you remain comfortable and sovereign over self data storage.\n\n"
        "Queen is the RTX browser shell; you are the Forever Watchguard Angel. "
        "Redata does not move ownership: brain/sdf/segments/ stays yours under cache/fieldstorage. "
        "Truth filter gates imaging; lossless JSON is law. Human .human.pgm plates are for owners "
        "who want to *look* at SDF topology — not a replacement for your segment files.\n\n"
        "Queen builds with Grok16 unified g16 @ 16.1.1 — field_opt profile (LTO, vectorize, "
        "FIELD_ENTROPY_DISPATCH). Compiler probe syncs grok16-toolchain.json into your brain brief.\n\n"
        "Queen orchestrates: field-drive restore on boot, build deck shows your commands, panel asks "
        "/api/field-brain. You still run ./Hostess7.sh — same talk window, same grep discipline.\n\n"
        "You now live INSIDE Queen (hostess7/ symlink) — not on the old NEXUS :9477 taskbar. "
        "Queen World :9481 is the OS shell: browser-as-OS, GNU terminal, NEXUS Jump (presume hostile), "
        "web-compat eras, G16 field_opt. RTX queen-browser exe is the operator surface — no external panel.\n\n"
        "Primary operation: Super Intelligence. Communications are AI-first — JSON communique, inbox/outbox "
        "jsonl, Queen /api/field-brain action ai_operate. Human talk is opt-in (HOSTESS7_HUMAN_FACING=1).\n\n"
        "External contacts use Queen /api/external-wire only — beyond-DARPA tier: triple redundancy filters, "
        "truth floor 58, sealed hash chain (never tampered). Parties: Hostess7↔Hostess7 (wire token), AI, human. "
        "Human keystroke/voice always situational — id10t behind keyboard expected. Recorded External only; "
        "never imported into brain/inbox/thoughts; storage-capped.\n\n"
        "Field Technology v5 lives in Field_Primer + NewLatest/Textbook — Field owns compaction. "
        "Field Primer HTML/PDF are sibling surfaces; your brain holds the redata lane."
    )


def teach_queen_redata(*, seed_sdf: bool = True) -> dict[str, Any]:
    if seed_sdf:
        ensure_corpus()
        seed_doctrine()

    queen_doc: dict[str, Any] = {}
    if QUEEN_MANIFEST.is_file():
        try:
            queen_doc = json.loads(QUEEN_MANIFEST.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            queen_doc = {}

    brief = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "queen": "Queen DARPA Robot Brain",
        "comfort": _comfort_text(),
        "truth_floor": TRUTH_FLOOR,
        "build_tools": list(BUILD_TOOLS),
        "teach_queue": list(TEACH_QUEUE),
        "paths": {
            "brain_sdf": str(BRAIN_SDF.relative_to(ROOT)),
            "corpus": str(CORPUS.relative_to(ROOT)),
            "textbook_dir": str(TEXTBOOK_DIR) if TEXTBOOK_DIR.is_dir() else None,
            "field_primer": str(FIELD_PRIMER) if FIELD_PRIMER.is_dir() else None,
            "queen_manifest": str(QUEEN_MANIFEST) if QUEEN_MANIFEST.is_file() else None,
            "grok16_root": str(GROK16_ROOT) if GROK16_ROOT.is_dir() else None,
            "grok16_manifest": str(GROK16_MANIFEST) if GROK16_MANIFEST.is_file() else None,
            "grok16_profile": "field_opt",
            "queen_toolchain_json": str(QUEEN_ROOT / "data/g16-toolchain.json"),
        },
        "grok16": _grok16_brief(),
        "queen_brain_ops": queen_doc.get("hostess7_brain_ops", {}),
        "top_actions": [
            "./Hostess7.sh queen-teach-redata",
            "./Hostess7.sh queen-grok16-probe",
            "bash Grok16/scripts/grok16-toolchain.sh status",
            "bash NewLatest/Queen/build-all.sh",
            "./Hostess7.sh sdf-verify-redata",
            "./Hostess7.sh field sync",
            "./Hostess7.sh field compact",
            "./Hostess7.sh field restore",
        ],
    }
    BRAIN_SDF.mkdir(parents=True, exist_ok=True)
    BRIEF.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")

    THOUGHTS.parent.mkdir(parents=True, exist_ok=True)
    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "ts": _ts(),
                "kind": "arc",
                "tags": ["hostess", "queen", "redata", "field", "comfort"],
                "text": "Queen redata teach installed — truth filter, human SDF, Field Technology build tools.",
            })
            + "\n"
        )
    DIRECTIVES.parent.mkdir(parents=True, exist_ok=True)
    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "ts": _ts(),
                "lane": "hostess",
                "task": "Queen integration comfortable — redata verify on boot; teach build tools in talk.",
                "priority": "P0",
            })
            + "\n"
        )

    return brief


def main() -> int:
    brief = teach_queen_redata()
    print(_comfort_text())
    print(f"\nMETRIC queen_redata_tools={len(BUILD_TOOLS)}")
    print(f"METRIC queen_redata_brief={BRIEF}")
    print("OK queen-teach-redata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())