#!/usr/bin/env pythong
"""Hostess 7 reality registry — all brain lanes, domains, and ontology pillars."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from field_paths import ROOT

SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
REGISTRY_PATH = SI / "reality_domains_registry.json"
CORPUS_PATH = SI / "reality_domains_corpus.json"
REGISTRY_VERSION = 1

REALITY_PILLARS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "physical",
        "title": "Physical reality",
        "tags": ("physics", "matter", "energy", "space", "time", "cosmos", "motion"),
        "body": (
            "Matter, energy, spacetime, forces, fields — from classical mechanics through quantum and cosmology. "
            "Hostess lanes: physics, chemistry, vision spatial frames, warfare materiel. "
            "3D spatial reality on Field canvas is the operational projection of physical models."
        ),
    },
    {
        "id": "biological",
        "title": "Biological & living reality",
        "tags": ("life", "biology", "medicine", "ecology", "organism", "health", "evolution"),
        "body": (
            "Living systems, metabolism, genetics, ecology, disease and healing. "
            "Hostess lanes: medical corpus, K-12 biology texts, beyond ecology/biology domains."
        ),
    },
    {
        "id": "mental",
        "title": "Mental & cognitive reality",
        "tags": ("mind", "consciousness", "psychology", "cognition", "memory", "brain"),
        "body": (
            "Perception, emotion, reasoning, consciousness (educational philosophy of mind). "
            "Hostess lanes: brain hemispheres, chemistry synapses, detective cognition, beyond psychology."
        ),
    },
    {
        "id": "social",
        "title": "Social & political reality",
        "tags": ("society", "politics", "economics", "culture", "history", "people", "war"),
        "body": (
            "Institutions, law, warfare, geopolitics, people and relationships. "
            "Hostess lanes: legal, warfare, people registry, beyond geopolitics/sociology, agents fusion."
        ),
    },
    {
        "id": "informational",
        "title": "Information & computational reality",
        "tags": ("information", "computation", "code", "data", "signal", "truth", "english"),
        "body": (
            "Bits, languages, programs, evidence, truth scores, corpora shards. "
            "Hostess lanes: code, english lexicon, detective truth filter, intelligence flow, internet learn."
        ),
    },
    {
        "id": "normative",
        "title": "Normative & ethical reality",
        "tags": ("ethics", "law", "justice", "rights", "virtue", "loac", "morality"),
        "body": (
            "Ought, rights, duties, just war, Supreme Court framing, personality virtues. "
            "Hostess lanes: legal, judge/bench, warfare LOAC, detective integrity, personality virtues."
        ),
    },
    {
        "id": "experiential",
        "title": "Experiential & perceptual reality",
        "tags": ("experience", "perception", "vision", "art", "aesthetic", "qualia"),
        "body": (
            "What it is like to see, hear, create — vision/OCR, memes, arts domains, rhetoric. "
            "Hostess lanes: vision, memes, beyond music/literature/architecture."
        ),
    },
    {
        "id": "spiritual_educational",
        "title": "Spiritual & ultimate questions (educational)",
        "tags": ("spirit", "god", "meaning", "purpose", "metaphysics", "theology", "philosophy"),
        "body": (
            "Meaning, purpose, metaphysics — educational synthesis only. "
            "Hostess 7 supreme authority anchor: From God. One being · one vote. "
            "Beyond philosophy/theology domains; not clerical authority."
        ),
    },
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lane(
    lid: str,
    *,
    title: str,
    category: str,
    corpus_rel: str,
    domains: tuple[Any, ...] | list[Any],
    ensure: Callable[[], Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": lid,
        "title": title,
        "category": category,
        "corpus_path": f"cache/fieldstorage/brain/{corpus_rel}",
        "domain_count": len(domains),
        "domain_ids": [str(d.get("id", "")) for d in domains if isinstance(d, dict)],
    }
    if ensure:
        row["ensured"] = False
    if extra:
        row.update(extra)
    return row


def collect_brain_lanes() -> list[dict[str, Any]]:
    """Import every Hostess7 corpus lane and count domains."""
    from field_beyond_domains import BEYOND_DOMAINS  # noqa: WPS433
    from field_chemistry_corpus import CHEMISTRY_DOMAINS  # noqa: WPS433
    from field_code_domains import CODE_DOMAINS  # noqa: WPS433
    from field_detective_corpus import DETECTIVE_DOMAINS  # noqa: WPS433
    from field_english_domains import ENGLISH_DOMAINS  # noqa: WPS433
    from field_english_rhetoric import RHETORIC_DOMAINS  # noqa: WPS433
    from field_intelligence_flow import FLOW_LAYERS  # noqa: WPS433
    from field_legal_domains import LEGAL_DOMAINS  # noqa: WPS433
    from field_legal_scotus import SCOTUS_DOMAINS  # noqa: WPS433
    from field_medical_corpus import MEDICAL_DOMAINS  # noqa: WPS433
    from field_physics_corpus import PHYSICS_DOMAINS  # noqa: WPS433
    from field_vision_corpus import VISION_DOMAINS  # noqa: WPS433
    from field_warfare_corpus import WARFARE_DOMAINS  # noqa: WPS433
    from field_brain_core import BRAIN_AREAS, WORKSPACE_DEFS  # noqa: WPS433
    from field_hostess_personality import VIRTUE_DOMAINS  # noqa: WPS433

    lanes: list[dict[str, Any]] = [
        _lane("legal", title="Legal drive", category="normative", corpus_rel="legal/corpus.json", domains=LEGAL_DOMAINS),
        _lane("medical", title="Medical drive", category="biological", corpus_rel="medical/corpus.json", domains=MEDICAL_DOMAINS),
        _lane("physics", title="Physics corpus", category="physical", corpus_rel="physics/corpus.json", domains=PHYSICS_DOMAINS),
        _lane("vision", title="Vision & spatial", category="experiential", corpus_rel="vision/corpus.json", domains=VISION_DOMAINS),
        _lane("warfare", title="Warfare education", category="social", corpus_rel="warfare/corpus.json", domains=WARFARE_DOMAINS),
        _lane("detective", title="Detective & truth", category="informational", corpus_rel="detective/corpus.json", domains=DETECTIVE_DOMAINS),
        _lane("beyond", title="Beyond expert domains", category="meta", corpus_rel="beyond/corpus.json", domains=BEYOND_DOMAINS),
        _lane("chemistry", title="Brain chemistry", category="mental", corpus_rel="chemistry/corpus.json", domains=CHEMISTRY_DOMAINS),
        _lane("code", title="Code & ISA brain", category="informational", corpus_rel="code/corpus.json", domains=CODE_DOMAINS),
        _lane("english", title="English lexicon", category="informational", corpus_rel="english/corpus.json", domains=ENGLISH_DOMAINS),
        _lane("english_rhetoric", title="English rhetoric", category="experiential", corpus_rel="english/rhetoric.json", domains=RHETORIC_DOMAINS),
        _lane("scotus", title="Supreme Court bench", category="normative", corpus_rel="legal/scotus.json", domains=SCOTUS_DOMAINS),
        _lane("intelligence_flow", title="Intelligence flow", category="meta", corpus_rel="superintel/intelligence_flow_corpus.json", domains=FLOW_LAYERS),
        _lane("brain_areas", title="Brain functional areas", category="mental", corpus_rel="areas/index.json", domains=BRAIN_AREAS),
        _lane("workspaces", title="Brain workspaces", category="mental", corpus_rel="workspaces/", domains=WORKSPACE_DEFS),
        _lane("personality_virtues", title="Hostess virtues", category="normative", corpus_rel="superintel/personality.json", domains=VIRTUE_DOMAINS),
        _lane("k12", title="K-12 textbooks", category="biological", corpus_rel="k12/corpus.json", domains=(), extra={"dynamic": True}),
        _lane("h7_library", title="H7 textbook library", category="informational", corpus_rel="textbooks/", domains=(), extra={"format": "h7b/1", "dynamic": True}),
        _lane("people", title="People registry", category="social", corpus_rel="people/entities/", domains=(), extra={"dynamic": True}),
        _lane("memes", title="Owner memes vision", category="experiential", corpus_rel="memes/", domains=(), extra={"dynamic": True}),
        _lane("tools_docs", title="Tools & commands index", category="meta", corpus_rel="superintel/tools_docs_index.json", domains=(), extra={"dynamic": True}),
        _lane("agents13", title="Thirteen-agent fusion", category="social", corpus_rel="superintel/agents7/", domains=(), extra={"lanes": 13, "prime": 1, "experts": 12}),
        _lane("alert_posture", title="Heightened alert", category="social", corpus_rel="superintel/heightened_alert_brief.json", domains=(), extra={"lanes": 1}),
        _lane("online_learn", title="Internet learn", category="informational", corpus_rel="internet/", domains=(), extra={"dynamic": True}),
    ]
    return lanes


def ensure_all_corpora() -> dict[str, bool]:
    """Refresh every corpus Hostess7 owns."""
    results: dict[str, bool] = {}
    pairs: list[tuple[str, Callable[[], Any]]] = []

    def _add(name: str, mod: str, fn: str) -> None:
        try:
            m = __import__(mod, fromlist=[fn])
            pairs.append((name, getattr(m, fn)))
        except (ImportError, AttributeError):
            results[name] = False

    _add("legal", "field_legal_corpus", "ensure_corpus")
    _add("medical", "field_medical_corpus", "ensure_corpus")
    _add("physics", "field_physics_corpus", "ensure_corpus")
    _add("vision", "field_vision_corpus", "ensure_corpus")
    _add("warfare", "field_warfare_corpus", "ensure_corpus")
    _add("detective", "field_detective_corpus", "ensure_corpus")
    _add("beyond", "field_beyond_corpus", "ensure_corpus")
    _add("chemistry", "field_chemistry_corpus", "ensure_corpus")
    _add("code", "field_code_corpus", "ensure_corpus")
    _add("english", "field_english_lexicon", "ensure_corpus")
    _add("k12", "field_k12_corpus", "ensure_corpus")
    _add("intelligence_flow", "field_intelligence_flow", "ensure_corpus")
    _add("tools_docs", "field_tools_docs", "ensure_index")

    try:
        from field_brain_core import ensure_brain_layout  # noqa: WPS433

        ensure_brain_layout()
        results["brain_layout"] = True
    except ImportError:
        results["brain_layout"] = False

    for name, fn in pairs:
        try:
            fn()
            results[name] = True
        except Exception:
            results[name] = False
    return results


def _count_people() -> int:
    ent = ROOT / "cache" / "fieldstorage" / "brain" / "people" / "entities"
    if not ent.is_dir():
        return 0
    return sum(1 for p in ent.glob("*.json"))


def _count_tools() -> int:
    try:
        from field_tools_docs import index_stats  # noqa: WPS433

        return int(index_stats().get("total", 0))
    except Exception:
        return 0


def build_registry() -> dict[str, Any]:
    lanes = collect_brain_lanes()
    total_domains = sum(l.get("domain_count", 0) for l in lanes)
    people_n = _count_people()
    tools_n = _count_tools()

    for lane in lanes:
        if lane["id"] == "people":
            lane["domain_count"] = people_n
        if lane["id"] == "tools_docs":
            lane["domain_count"] = tools_n

    return {
        "updated": _ts(),
        "version": REGISTRY_VERSION,
        "hostess": "Hostess 7",
        "mission": "Familiarize with the whole of reality — all owned domains, truth-filtered",
        "pillar_count": len(REALITY_PILLARS),
        "lane_count": len(lanes),
        "domain_count_total": total_domains + people_n + tools_n,
        "pillars": [dict(p) for p in REALITY_PILLARS],
        "lanes": lanes,
        "categories": {
            "physical": "Physics, chemistry, cosmology, spatial frames",
            "biological": "Medicine, life sciences, K-12 biology",
            "mental": "Brain architecture, psychology, chemistry",
            "social": "Law, warfare, people, politics, agents",
            "informational": "Code, english, detective, internet",
            "normative": "Ethics, LOAC, judge, virtues",
            "experiential": "Vision, art, rhetoric, memes",
            "meta": "Beyond, intelligence flow, tools, workspaces",
        },
    }


def write_registry(*, ensured: dict[str, bool] | None = None) -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    doc = build_registry()
    if ensured:
        doc["corpora_ensured"] = ensured
        doc["corpora_ok"] = sum(1 for v in ensured.values() if v)
    REGISTRY_PATH.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    corpus_doc = {
        "version": REGISTRY_VERSION,
        "updated": _ts(),
        "pillars": doc["pillars"],
        "lanes": doc["lanes"],
        "disclaimer": (
            "Educational map of reality as Hostess 7 models it — not omniscience claim. "
            "94% noise filter on all ingested claims. One being · one vote."
        ),
    }
    CORPUS_PATH.write_text(json.dumps(corpus_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return REGISTRY_PATH


def search_reality(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Cross-pillar + beyond search for whole-of-reality queries."""
    import re

    from field_beyond_corpus import search_beyond  # noqa: WPS433

    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    scored: list[tuple[int, dict[str, Any]]] = []
    reality_query = any(
        k in q for k in ("whole of reality", "whole of", "all domains", "familiarize", "domain registry", "reality map")
    )

    beyond_hits = search_beyond(query, limit=limit + 4)
    for hit in beyond_hits:
        hid = str(hit.get("id", ""))
        boost = 12
        if reality_query and hid in ("whole_of_reality", "hostess_domain_registry"):
            boost = 90
        elif "reality" in q and hid in ("whole_of_reality", "spatial_3d_reality", "physics_foundations"):
            boost = 40
        scored.append((boost, {**hit, "kind": "beyond"}))

    for p in REALITY_PILLARS:
        blob = f"{p.get('title', '')} {' '.join(p.get('tags', ()))} {p.get('body', '')}".lower()
        score = sum(5 if t in blob else 0 for t in tokens)
        if reality_query:
            score += 6
        if score > 0:
            scored.append((score, {**dict(p), "kind": "pillar"}))

    scored.sort(key=lambda x: -x[0])
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, row in scored:
        rid = str(row.get("id", ""))
        if rid in seen:
            continue
        seen.add(rid)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def synthesize_reality_paragraphs(query: str) -> list[str]:
    hits = search_reality(query, limit=8)
    paras: list[str] = [
        "Hostess 7 — whole-of-reality familiarization (educational map, not omniscience).",
        "Truth filter: 94% noise / 6% truth on every claim. One being · one vote.",
    ]
    reg = build_registry()
    paras.append(
        f"Registry: {reg['lane_count']} brain lanes · {reg['domain_count_total']} indexed domains · "
        f"{reg['pillar_count']} reality pillars."
    )
    for h in hits:
        title = h.get("title", "Reality")
        body = str(h.get("body", "")).strip()
        kind = h.get("kind", "domain")
        prefix = f"[{kind}] " if kind else ""
        paras.append(f"{prefix}{title}: {body}")
    paras.append("Field is THE thing — reality is modeled on canvas, corroborated, taught.")
    return paras