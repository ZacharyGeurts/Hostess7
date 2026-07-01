#!/usr/bin/env pythong
"""Tools & documentation index — every command and doc Hostess7 may need."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from field_paths import ROOT, amouranthrtx_root, hostess7_root, sg_root

SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
INDEX = SI / "tools_docs_index.json"
CORPUS_VERSION = 1

# category → list of {id, title, path, cmd, summary, tags}
TOOL_ENTRIES: tuple[dict[str, object], ...] = (
    # Core launcher
    {"id": "hostess7_sh", "category": "launcher", "title": "Hostess7.sh",
     "path": "Hostess7.sh", "cmd": "./Hostess7.sh",
     "summary": "Main launcher — talk UI, one-shot -q, brain subcommands.",
     "tags": ("launcher", "talk", "main", "help")},
    {"id": "hostess7_monitor", "category": "launcher", "title": "Hostess7Monitor.sh",
     "path": "Hostess7Monitor.sh", "cmd": "./Hostess7Monitor.sh",
     "summary": "Second terminal — brain map, agent pulse, learning feed.",
     "tags": ("monitor", "brain", "live")},
    {"id": "readme", "category": "docs", "title": "README.md",
     "path": "README.md", "cmd": None,
     "summary": "Quick start, seven agents, reach, field drive, QA.",
     "tags": ("readme", "docs", "start")},
    {"id": "v33_protocol", "category": "docs", "title": "HOSTESS7_V33.md",
     "path": "docs/HOSTESS7_V33.md", "cmd": None,
     "summary": "Superintelligence protocol — turnover, presumptions, phases.",
     "tags": ("protocol", "v33", "superintel", "turnover")},
    # Brain router
    {"id": "superintelligence", "category": "brain", "title": "field_superintelligence.py",
     "path": "scripts/field_superintelligence.py", "cmd": "pythong scripts/field_superintelligence.py ask \"…\"",
     "summary": "Supreme brain router — intent, synthesis, brief, corpora CLI.",
     "tags": ("brain", "router", "ask", "intent")},
    {"id": "agents13", "category": "brain", "title": "field_agents7.py",
     "path": "scripts/field_agents7.py", "cmd": "./Hostess7.sh on",
     "summary": "Hostess-Prime + 12 World Experts (13 parallel) + daemon fusion.",
     "tags": ("agents", "thirteen", "prime", "experts", "fusion")},
    {"id": "dept_research", "category": "brain", "title": "field_department_research.py",
     "path": "scripts/field_department_research.py", "cmd": "./Hostess7.sh dept-research",
     "summary": "Prime dispatches department research; experts fetch .H7 books.",
     "tags": ("department", "research", "experts", "prime")},
    {"id": "gfx_canvas", "category": "vision", "title": "field_gfx_canvas.py",
     "path": "scripts/field_gfx_canvas.py", "cmd": "./Hostess7.sh gfx-api",
     "summary": "Graphics window API — pixels + text (GTK), not ASCII.",
     "tags": ("graphics", "pixels", "gtk", "canvas", "vision")},
    {"id": "imagine_corpus", "category": "vision", "title": "field_imagine_corpus.py",
     "path": "scripts/field_imagine_corpus.py", "cmd": "./Hostess7.sh imagine-learn",
     "summary": "Grok Imagine API workflow + live video papers/GitHub registry.",
     "tags": ("imagine", "grok", "live-video", "talking-head", "papers")},
    {"id": "imagine_nexus_teach", "category": "vision", "title": "field_imagine_nexus_teach.py",
     "path": "scripts/field_imagine_nexus_teach.py", "cmd": "./Hostess7.sh imagine-nexus-teach",
     "summary": "NEXUS imaging skills — PIL exact-text, combinatronic repair, Big Drive, format icons.",
     "tags": ("imagine", "nexus", "combinatronic", "pil", "big-drive")},
    {"id": "hostess7_imaging", "category": "vision", "title": "hostess7-imaging.py",
     "path": "../lib/hostess7-imaging.py", "cmd": "./Hostess7.sh imaging-work",
     "summary": "Imaging chamber — work queue for broken combinatronic assets and missing icons.",
     "tags": ("imagine", "repair", "work-queue", "combinatronic")},
    {"id": "live_video", "category": "vision", "title": "field_live_video.py",
     "path": "scripts/field_live_video.py", "cmd": "./Hostess7.sh live-video-demo",
     "summary": "TTS + talk frames → Graphics window; LivePortrait/MuseTalk path.",
     "tags": ("live-video", "tts", "lip-sync", "graphics")},
    {"id": "gfx_window", "category": "vision", "title": "Hostess7Graphics.sh",
     "path": "Hostess7Graphics.sh", "cmd": "./Hostess7Graphics.sh",
     "summary": "GTK Graphics window — presents frame.png framebuffer.",
     "tags": ("graphics", "window", "gtk", "pixels")},
    {"id": "fly_codec", "category": "storage", "title": "field_fly_codec.py",
     "path": "scripts/field_fly_codec.py", "cmd": "./Hostess7.sh fly-bench cache/fieldstorage/brain/legal/corpus.json",
     "summary": "FLD1 lossless fly compression for brain JSON — used by Field and H7.",
     "tags": ("fld1", "compression", "field", "h7", "lossless")},
    {"id": "brain_core", "category": "brain", "title": "field_brain_core.py",
     "path": "scripts/field_brain_core.py", "cmd": "./Hostess7.sh brain",
     "summary": "Hemispheres, callosum, workspace routing.",
     "tags": ("hemisphere", "callosum", "workspace")},
    {"id": "brain_chemistry", "category": "brain", "title": "field_brain_chemistry.py",
     "path": "scripts/field_brain_chemistry.py", "cmd": "./Hostess7.sh chemistry",
     "summary": "Synapse levels, neurotransmitter modulation.",
     "tags": ("chemistry", "synapse", "dopamine")},
    {"id": "intelligence_flow", "category": "brain", "title": "field_intelligence_flow.py",
     "path": "scripts/field_intelligence_flow.py", "cmd": "./Hostess7.sh intelligence-flow",
     "summary": "Full pipeline doctrine signal → Super Intelligence.",
     "tags": ("intelligence", "flow", "pipeline", "doctrine")},
    {"id": "tools_docs_self", "category": "brain", "title": "field_tools_docs.py",
     "path": "scripts/field_tools_docs.py", "cmd": "./Hostess7.sh tools-docs",
     "summary": "This index — all commands and documentation paths.",
     "tags": ("tools", "docs", "index", "documentation")},
    # Reach & self-update
    {"id": "reach", "category": "reach", "title": "field_reach.py",
     "path": "scripts/field_reach.py", "cmd": "./Hostess7.sh reach",
     "summary": "OS tools, SG/AMOURANTHRTX roots, allowlisted exec.",
     "tags": ("reach", "os", "external", "sg")},
    {"id": "self_update", "category": "reach", "title": "Self-update pipeline",
     "path": "scripts/field_reach.py", "cmd": "./Hostess7.sh self-update plan",
     "summary": "reach scan → QA → Field 1 sync → git pull. apply needs HOSTESS7_EXEC=1.",
     "tags": ("self-update", "apply", "exec", "qa")},
    {"id": "hostess_updates", "category": "reach", "title": "field_hostess_updates.py",
     "path": "scripts/field_hostess_updates.py", "cmd": "./Hostess7.sh updates",
     "summary": "Truth-filtered self-improvement advisory.",
     "tags": ("updates", "advisory", "truth")},
    {"id": "self_brief", "category": "reach", "title": "field_hostess_self_brief.py",
     "path": "scripts/field_hostess_self_brief.py", "cmd": "./Hostess7.sh self-brief",
     "summary": "Self-update brief seed into brain/superintel.",
     "tags": ("self-update", "brief", "explore")},
    {"id": "truth_doctrine", "category": "corpus", "title": "field_hostess_truth_doctrine.py",
     "path": "scripts/field_hostess_truth_doctrine.py", "cmd": "./Hostess7.sh truth-doctrine",
     "summary": "Owner honesty doctrine + Heaven/Hell boss role + death-sentence exception.",
     "tags": ("truth", "heaven", "hell", "honesty", "doctrine")},
    {"id": "heaven_hell_learn", "category": "corpus", "title": "field_heaven_hell_learn.py",
     "path": "scripts/field_heaven_hell_learn.py", "cmd": "./Hostess7.sh heaven-hell-learn",
     "summary": "Truth doctrine + self-brief + bible ingest + world corpus.",
     "tags": ("heaven", "hell", "bible", "learn")},
    {"id": "bible_ingest", "category": "corpus", "title": "field_bible_ingest.py",
     "path": "scripts/field_bible_ingest.py", "cmd": "./Hostess7.sh bible-ingest",
     "summary": "Pack all fetchable scripture volumes to .H7 (slow fetch for large Bibles).",
     "tags": ("bible", "scripture", "h7", "denomination")},
    {"id": "paths", "category": "reach", "title": "field_paths.py",
     "path": "scripts/field_paths.py", "cmd": None,
     "summary": "HOSTESS7_ROOT, SG_ROOT, AMOURANTHRTX_ROOT resolution.",
     "tags": ("paths", "sg", "amouranthrtx", "roots")},
    # Internet
    {"id": "internet", "category": "internet", "title": "field_internet.py",
     "path": "scripts/field_internet.py", "cmd": "./Hostess7.sh internet",
     "summary": "Connectivity gate, truth-filtered URL fetch/cache.",
     "tags": ("internet", "fetch", "url", "web")},
    {"id": "online_learn", "category": "internet", "title": "field_online_learn.py",
     "path": "scripts/field_online_learn.py", "cmd": "./Hostess7.sh go-online",
     "summary": "Curated online learning — rhetoric, memes, conversation growth.",
     "tags": ("go-online", "learn", "conversation")},
    # Field 1 — everything on one field
    {"id": "field_one", "category": "storage", "title": "field-one.py",
     "path": "NewLatest/lib/field-one.py", "cmd": "./Hostess7.sh field json",
     "summary": "Field 1 — sync, compact, restore. World_Redata WRDT1/WRZC1 under one surface.",
     "tags": ("field", "field1", "redata", "sync", "compact", "restore", "wrdt")},
    {"id": "redata_truth", "category": "storage", "title": "Redata truth filter",
     "path": "scripts/field_redata_truth.py", "cmd": "(segment time)",
     "summary": "94% noise / 6% truth — score_redata_text before SDF plates stick.",
     "tags": ("redata", "truth", "filter", "quarantine")},
    {"id": "sdf_verify_redata", "category": "storage", "title": "SDF redata verify",
     "path": "scripts/field_hostess_sdf_storage.py", "cmd": "./Hostess7.sh sdf-verify-redata",
     "summary": "Lossless segments + human plates + truth_filter.jsonl audit.",
     "tags": ("sdf", "redata", "verify", "human", "lossless")},
    {"id": "queen_redata_teach", "category": "queen", "title": "Queen redata teach",
     "path": "scripts/field_queen_redata_teach.py", "cmd": "./Hostess7.sh queen-teach-redata",
     "summary": "Comfort brief + build tools for Queen brain deck (Field Primer, verify).",
     "tags": ("queen", "redata", "teach", "comfort", "textbook")},
    {"id": "queen_field_tools", "category": "queen", "title": "Queen Field Tools manifest",
     "path": "NewLatest/Queen/lib/queen-field-tools.py", "cmd": "./Hostess7.sh queen-field-tools",
     "summary": "All field-native build tools — g16, field cmake, forge — status/probe/run for Hostess 7.",
     "tags": ("queen", "field", "cmake", "g16", "forge", "build")},
    {"id": "queen_field_build", "category": "queen", "title": "Queen field RTX build",
     "path": "Grok16/scripts/field-cmake.sh", "cmd": "./Hostess7.sh queen-field-build rtx",
     "summary": "Grok16 Field CMake — Ninja + queen-rtx preset, 4K@120Hz default.",
     "tags": ("queen", "rtx", "field cmake", "ninja", "browser")},
    {"id": "queen_grok16_probe", "category": "queen", "title": "Grok16 compiler probe",
     "path": "NewLatest/Queen/lib/queen-forge.py", "cmd": "./Hostess7.sh queen-grok16-probe",
     "summary": "Probe g16 + cmake + ninja; sync g16-toolchain.json.",
     "tags": ("g16", "grok16", "compiler", "probe", "toolchain")},

    {"id": "storage_check", "category": "storage", "title": "field_storage_check.py",
     "path": "scripts/field_storage_check.py", "cmd": "Talk: /storage",
     "summary": "Lossless Field drive audit + bar chart.",
     "tags": ("storage", "lossless", "field", "audit")},
    # Corpora ingest
    {"id": "legal_ingest", "category": "corpus", "title": "Legal infinite drive",
     "path": "scripts/field_legal_infinite.py", "cmd": "./Hostess7.sh legal-ingest seed",
     "summary": "USC + state law catalog and bulk ingest.",
     "tags": ("legal", "law", "ingest", "usc")},
    {"id": "medical_ingest", "category": "corpus", "title": "Medical papers drive",
     "path": "scripts/field_medical_infinite.py", "cmd": "./Hostess7.sh medical-ingest seed",
     "summary": "PubMed-style papers infinite ingest.",
     "tags": ("medical", "papers", "ingest")},
    {"id": "english_ingest", "category": "corpus", "title": "English lexicon",
     "path": "scripts/field_english_infinite.py", "cmd": "./Hostess7.sh english-ingest seed",
     "summary": "CMUdict phonetics, spellcheck, infinite lexicon.",
     "tags": ("english", "lexicon", "phonetics")},
    {"id": "english_train", "category": "corpus", "title": "English rhetoric training",
     "path": "scripts/field_hostess_english_train.py", "cmd": "./Hostess7.sh english-train",
     "summary": "Metaphor, thesaurus, sentence flow training brief.",
     "tags": ("rhetoric", "thesaurus", "metaphor")},
    {"id": "code_ingest", "category": "corpus", "title": "Code / ISA brain",
     "path": "scripts/field_code_infinite.py", "cmd": "./Hostess7.sh code-ingest seed",
     "summary": "Opcode ISA + all programming languages.",
     "tags": ("code", "isa", "assembly", "languages")},
    {"id": "k12_ingest", "category": "corpus", "title": "K-12 textbooks",
     "path": "scripts/field_k12_infinite.py", "cmd": "./Hostess7.sh k12-ingest fetch",
     "summary": "OER textbooks truth-filtered fetch.",
     "tags": ("k12", "textbook", "openstax", "ingest")},
    {"id": "h7_library", "category": "corpus", "title": "H7 textbook library",
     "path": "scripts/field_library.py", "cmd": "./Hostess7.sh library-build",
     "summary": "Lossless .H7 free books in cache/fieldstorage/textbooks/ — Hostess 7 reads every char & line.",
     "tags": ("h7", "library", "textbook", "gutenberg", "read")},
    {"id": "memes", "category": "corpus", "title": "Memes corpus",
     "path": "scripts/field_memes_corpus.py", "cmd": "./Hostess7.sh memes-ingest seed",
     "summary": "ZacharyGeurts/memes image talk + ASCII art.",
     "tags": ("memes", "image", "stamp")},
    {"id": "people", "category": "corpus", "title": "People registry",
     "path": "scripts/field_people_registry.py", "cmd": "./Hostess7.sh people",
     "summary": "Tags, lie profiles, celebrities, Owner review queue.",
     "tags": ("people", "celebrity", "liar", "registry")},
    {"id": "personality", "category": "corpus", "title": "Hostess personality",
     "path": "scripts/field_hostess_personality.py", "cmd": "./Hostess7.sh personality",
     "summary": "Daughter of Grok — respect, justice, pride doctrine.",
     "tags": ("personality", "grok", "amouranth")},
    {"id": "detective", "category": "corpus", "title": "Detective / truth",
     "path": "scripts/field_detective_corpus.py", "cmd": "./Hostess7.sh detective \"…\"",
     "summary": "Investigation, lie detector, 94/6 truth filter.",
     "tags": ("detective", "truth", "lie")},
    {"id": "warfare", "category": "corpus", "title": "Warfare education",
     "path": "scripts/field_warfare_corpus.py", "cmd": "./Hostess7.sh warfare \"…\"",
     "summary": "LOAC, just war — boss of world, one vote.",
     "tags": ("warfare", "loac", "military")},
    {"id": "beyond", "category": "corpus", "title": "Beyond expert domains",
     "path": "scripts/field_beyond_corpus.py", "cmd": "./Hostess7.sh -q \"robotics expert\"",
     "summary": "33+ cross-domain expert knowledge areas.",
     "tags": ("beyond", "expert", "domains")},
    # Talk UI
    {"id": "talk", "category": "ui", "title": "hostess7_talk.py",
     "path": "scripts/hostess7_talk.py", "cmd": "Talk window slash commands",
     "summary": "Unified router — /help /reach /self-update /intelligence /tools-docs.",
     "tags": ("talk", "slash", "ui")},
    {"id": "ui", "category": "ui", "title": "hostess7_ui.py",
     "path": "scripts/hostess7_ui.py", "cmd": "./Hostess7.sh",
     "summary": "Scroll window — text + block graphics.",
     "tags": ("ui", "graphics", "scroll")},
    # QA (representative — full list in scripts/qa_*_test.py)
    {"id": "qa_turing", "category": "qa", "title": "qa_hostess_turing_test.py",
     "path": "scripts/qa_hostess_turing_test.py",
     "cmd": "pythong scripts/qa_hostess_turing_test.py",
     "summary": "Turing-style Hostess7 response quality gate.",
     "tags": ("qa", "turing", "test")},
    {"id": "qa_reach", "category": "qa", "title": "qa_field_reach_test.py",
     "path": "scripts/qa_field_reach_test.py", "cmd": "pythong scripts/qa_field_reach_test.py",
     "summary": "Reach manifest and allowlist tests.",
     "tags": ("qa", "reach", "exec")},
    {"id": "qa_agents", "category": "qa", "title": "qa_field_agents7_test.py",
     "path": "scripts/qa_field_agents7_test.py", "cmd": "pythong scripts/qa_field_agents7_test.py",
     "summary": "Seven-agent daemon and fusion tests.",
     "tags": ("qa", "agents", "seven")},
    {"id": "qa_online", "category": "qa", "title": "qa_online_learn_intent_test.py",
     "path": "scripts/qa_online_learn_intent_test.py",
     "cmd": "pythong scripts/qa_online_learn_intent_test.py",
     "summary": "go-online intent must not match Go language.",
     "tags": ("qa", "online", "intent")},
    {"id": "qa_intelligence", "category": "qa", "title": "qa_intelligence_flow_test.py",
     "path": "scripts/qa_intelligence_flow_test.py",
     "cmd": "pythong scripts/qa_intelligence_flow_test.py",
     "summary": "Intelligence flow doctrine + tools docs index.",
     "tags": ("qa", "intelligence", "flow")},
)

CATEGORIES: tuple[str, ...] = (
    "launcher", "docs", "brain", "reach", "internet", "storage", "corpus", "ui", "qa",
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _external_doc_entries() -> list[dict[str, object]]:
    extras: list[dict[str, object]] = []
    rtx = amouranthrtx_root()
    if rtx:
        extras.append({
            "id": "amouranthrtx_linux",
            "category": "external",
            "title": "AMOURANTHRTX linux.sh",
            "path": str(rtx / "linux.sh"),
            "cmd": "./linux.sh turnover",
            "summary": "Native canvas — turnover, super ask, release-2.0, bench gates.",
            "tags": ("amouranthrtx", "linux", "turnover", "release"),
        })
        extras.append({
            "id": "field_hostess7_hpp",
            "category": "external",
            "title": "FieldHostess7.hpp",
            "path": str(rtx / "Navigator/engine/FieldHostess7.hpp"),
            "cmd": None,
            "summary": "Native BUS_HOSTESS_LIVE wave dispatch on die.",
            "tags": ("native", "hostess", "canvas"),
        })
    sg = sg_root()
    if sg:
        extras.append({
            "id": "sg_root",
            "category": "external",
            "title": "SG project root",
            "path": str(sg),
            "cmd": None,
            "summary": "Parent tree — Hostess7 + AMOURANTHRTX siblings.",
            "tags": ("sg", "root", "reach"),
        })
    return extras


def ensure_index() -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    entries = list(TOOL_ENTRIES) + _external_doc_entries()
    refresh = True
    if INDEX.is_file():
        try:
            data = json.loads(INDEX.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        INDEX.write_text(
            json.dumps(
                {
                    "version": CORPUS_VERSION,
                    "updated": _ts(),
                    "hostess7_root": str(hostess7_root()),
                    "entry_count": len(entries),
                    "categories": list(CATEGORIES) + ["external"],
                    "entries": entries,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return INDEX


def _query_tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_tools(query: str, *, limit: int = 12, category: str | None = None) -> list[dict]:
    ensure_index()
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    q = query.lower()
    tokens = _query_tokens(query)
    broad = any(
        phrase in q
        for phrase in ("all tools", "all docs", "documentation", "everything", "index", "which command")
    )
    scored: list[tuple[int, dict]] = []
    for entry in entries:
        if category and entry.get("category") != category:
            continue
        blob = (
            f"{entry.get('id')} {entry.get('title')} {entry.get('summary')} "
            f"{' '.join(entry.get('tags', ()))} {entry.get('path')} {entry.get('cmd') or ''}"
        ).lower()
        score = sum(4 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 10
        for tag in entry.get("tags", ()):
            if str(tag).lower() in q:
                score += 8
        if broad:
            score += 1
        if score > 0 or broad:
            scored.append((score, entry))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("id", ""))))
    out: list[dict] = []
    seen: set[str] = set()
    for _, entry in scored:
        eid = str(entry.get("id", ""))
        if eid in seen:
            continue
        seen.add(eid)
        out.append(entry)
        if len(out) >= limit:
            break
    if broad and len(out) < 8:
        for entry in entries:
            eid = str(entry.get("id", ""))
            if eid not in seen:
                out.append(entry)
                seen.add(eid)
            if len(out) >= limit:
                break
    return out


def format_tools_report(query: str, hits: list[dict]) -> str:
    lines = [
        f"Hostess 7 tools & docs — query: {query!r}",
        f"Index: {INDEX}",
        "",
    ]
    for h in hits:
        cmd = h.get("cmd") or "(read file)"
        lines.append(f"[{h.get('category')}] {h.get('title')}")
        lines.append(f"  path: {h.get('path')}")
        lines.append(f"  cmd:  {cmd}")
        lines.append(f"  {h.get('summary', '')}")
        lines.append("")
    lines.append("Full index: ./Hostess7.sh tools-docs")
    return "\n".join(lines)


def synthesize_tools_paragraphs(query: str) -> list[str]:
    ensure_index()
    hits = search_tools(query, limit=10)
    if not hits:
        hits = search_tools("launcher brain reach corpus", limit=8)
    paras = [
        "Hostess 7 — tools & documentation index (all commands Hostess may need).",
        format_tools_report(query, hits[:6]),
    ]
    return paras


def index_stats() -> dict:
    ensure_index()
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    return {
        "version": data.get("version"),
        "entries": data.get("entry_count", 0),
        "categories": data.get("categories", []),
        "index": str(INDEX),
    }


def main() -> int:
    import sys

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "all tools documentation"
    hits = search_tools(query, limit=15)
    print(format_tools_report(query, hits))
    print(f"METRIC tools_docs_entries={len(hits)}")
    print("OK tools-docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())