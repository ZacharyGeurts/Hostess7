#!/usr/bin/env pythong
"""Hostess 7 people registry — tag-based entities, lie profiles, review queue.

Tags replace rigid folder taxonomies: liar, terrorist, goodguy, celebrity, musician, etc.
Bad-person flags land in review/ for Owner (ZacharyGeurts) approval before permanent tagging.
One JSON file per individual under entities/; review/ holds pending bad-person entries.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_detective_corpus import analyze_truth  # noqa: E402
from field_lie_methods import ensure_lie_methods, method_ids_for_assessment  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PEOPLE = ROOT / "cache" / "fieldstorage" / "brain" / "people"
ENTITIES = PEOPLE / "entities"
REVIEW = PEOPLE / "review"
MANIFEST = PEOPLE / "manifest.json"
INDEX = PEOPLE / "index.jsonl"
TAGS_TAXONOMY = PEOPLE / "tags_taxonomy.json"
INTERFACE = PEOPLE / "interface.json"
REGISTRY_VERSION = 1

BAD_TAGS = frozenset({"liar", "terrorist", "bad", "fraud", "abuser", "predator"})
REVIEW_TAGS = BAD_TAGS | frozenset({"review_pending", "unverified_bad"})

TAG_TAXONOMY: dict[str, dict[str, Any]] = {
    "disposition": {
        "goodguy": "Person of positive repute — respect and learn from them",
        "liar": "Deception pattern flagged — Owner review required",
        "terrorist": "Violence/extremism flag — Owner review required",
        "bad": "General bad-actor flag — Owner review required",
        "neutral": "No disposition assigned",
    },
    "role": {
        "celebrity": "Public figure — learn and respect appropriately",
        "musician": "Music artist",
        "streamer": "Live stream personality",
        "owner": "Hostess 7 owner circle",
        "founder": "System lineage / creation",
        "scientist": "Research and education",
        "athlete": "Sports figure",
    },
    "virtue": {
        "respect": "Models respect",
        "justice": "Models justice",
        "pride": "Healthy pride — earned confidence",
        "arrogance": "Hubris warning — negative exemplar",
        "caring": "Compassion and warmth",
    },
    "workflow": {
        "review_pending": "Awaiting Owner review in review/",
        "owner_approved": "Owner confirmed tag",
        "owner_rejected": "Owner dismissed flag",
    },
}

INTERFACE_SPEC: dict[str, Any] = {
    "version": 1,
    "design": "tag-first people brain — folders only for Owner review workflow",
    "panels": {
        "browse": "Filter by tags (disposition, role, virtue) — not folder tree",
        "lookup": "One file per person: entities/{id}.json — name, urls, claims, lie_profile",
        "review": "review/ folder — bad-person candidates for ZacharyGeurts approval",
        "assess": "Run lie-method stack on claim → update lie_profile on entity",
        "celebrities": "Tag celebrity + respect level — H7 learns admiration not worship",
    },
    "commands": {
        "cli": [
            "./Hostess7.sh people status",
            "./Hostess7.sh people list [--tag liar]",
            "./Hostess7.sh people lookup <name|id>",
            "./Hostess7.sh people add <name> --tag celebrity --url <url>",
            "./Hostess7.sh people tag <id> <tag>",
            "./Hostess7.sh people assess <id> \"claim text\"",
            "./Hostess7.sh people review",
            "./Hostess7.sh personality",
            "./Hostess7.sh lie-methods",
        ],
        "talk": [
            "/people status",
            "/people lookup Amouranth",
            "/people review",
            "/personality",
            "/lie-methods",
        ],
    },
    "review_workflow": [
        "1. Entity tagged liar|terrorist|bad → copy to review/{id}.json",
        "2. Owner runs ./Hostess7.sh people review",
        "3. Owner: people approve <id> or people reject <id>",
        "4. Approved → owner_approved tag; Rejected → flag removed, review file archived",
    ],
    "disclaimer": (
        "People registry is Owner-curated intelligence — not public accusation, "
        "not legal verdict. Educational lie scoring only. Respect celebrities; "
        "do not harass. Bad tags require Owner review."
    ),
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:64] or "unknown"


def _ensure_dirs() -> None:
    for p in (PEOPLE, ENTITIES, REVIEW):
        p.mkdir(parents=True, exist_ok=True)


def _write_taxonomy() -> None:
    TAGS_TAXONOMY.write_text(
        json.dumps({"version": REGISTRY_VERSION, "tags": TAG_TAXONOMY, "updated": _ts()}, indent=2) + "\n",
        encoding="utf-8",
    )
    INTERFACE.write_text(json.dumps({**INTERFACE_SPEC, "updated": _ts()}, indent=2) + "\n", encoding="utf-8")
    ensure_lie_methods()


def _entity_path(entity_id: str) -> Path:
    return ENTITIES / f"{entity_id}.json"


def _review_path(entity_id: str) -> Path:
    return REVIEW / f"{entity_id}.json"


def _load_entity(entity_id: str) -> dict[str, Any] | None:
    path = _entity_path(entity_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_entity(entity: dict[str, Any]) -> Path:
    entity["updated"] = _ts()
    eid = str(entity["id"])
    path = _entity_path(eid)
    path.write_text(json.dumps(entity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _sync_review(entity)
    _rebuild_index()
    _save_manifest()
    return path


def _sync_review(entity: dict[str, Any]) -> None:
    """Copy to review/ when bad tags present and not owner-approved."""
    eid = str(entity["id"])
    tags = set(entity.get("tags") or ())
    needs_review = bool(tags & BAD_TAGS) and "owner_approved" not in tags
    review_path = _review_path(eid)
    if needs_review:
        entity_copy = dict(entity)
        entity_copy["review_status"] = entity_copy.get("review_status") or "pending"
        entity_copy["review_reason"] = (
            entity_copy.get("review_reason")
            or f"Bad tag(s): {', '.join(sorted(tags & BAD_TAGS))} — awaiting Owner review"
        )
        review_path.write_text(json.dumps(entity_copy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if "review_pending" not in tags:
            entity.setdefault("tags", []).append("review_pending")
    elif review_path.is_file():
        archive = REVIEW / "archive" / f"{eid}_{int(datetime.now(timezone.utc).timestamp())}.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(review_path), str(archive))


def _rebuild_index() -> None:
    lines: list[str] = []
    for path in sorted(ENTITIES.glob("*.json")):
        try:
            e = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        blob = " ".join([
            str(e.get("name", "")),
            " ".join(e.get("aliases") or []),
            " ".join(e.get("tags") or []),
            str(e.get("bio", ""))[:500],
        ]).lower()
        lines.append(json.dumps({
            "id": e.get("id"),
            "name": e.get("name"),
            "tags": e.get("tags", []),
            "urls": [u.get("url") for u in (e.get("urls") or []) if u.get("url")],
            "lie_score": (e.get("lie_profile") or {}).get("lie_score"),
            "respect_level": (e.get("respect") or {}).get("level"),
            "review_status": e.get("review_status"),
            "blob": blob[:3000],
        }, ensure_ascii=False))
    INDEX.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _save_manifest() -> None:
    entities = list(ENTITIES.glob("*.json"))
    review_pending = list(REVIEW.glob("*.json"))
    tag_counts: dict[str, int] = {}
    for path in entities:
        try:
            e = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for t in e.get("tags") or []:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    MANIFEST.write_text(json.dumps({
        "version": REGISTRY_VERSION,
        "updated": _ts(),
        "entity_count": len(entities),
        "review_pending_count": len(review_pending),
        "tag_counts": tag_counts,
        "paths": {
            "entities": str(ENTITIES),
            "review": str(REVIEW),
            "index": str(INDEX),
            "lie_methods": str(PEOPLE / "lie_methods.json"),
            "personality": str(PEOPLE / "personality.json"),
        },
    }, indent=2) + "\n", encoding="utf-8")


def ensure_registry(*, seed: bool = True) -> dict[str, Any]:
    _ensure_dirs()
    _write_taxonomy()
    if seed and not any(ENTITIES.glob("*.json")):
        seed_entities()
    elif not MANIFEST.is_file():
        _rebuild_index()
        _save_manifest()
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def new_entity(
    name: str,
    *,
    tags: list[str] | None = None,
    urls: list[dict[str, str]] | None = None,
    bio: str = "",
    aliases: list[str] | None = None,
    respect_level: int = 50,
    virtues: dict[str, int] | None = None,
) -> dict[str, Any]:
    _ensure_dirs()
    _write_taxonomy()
    eid = _slug(name)
    existing = _load_entity(eid)
    if existing:
        return existing
    entity: dict[str, Any] = {
        "id": eid,
        "name": name,
        "aliases": aliases or [],
        "tags": list(tags or ["neutral"]),
        "urls": urls or [],
        "claims": [],
        "lie_profile": {
            "deception_risk": "unknown",
            "lie_score": None,
            "methods_applied": [],
            "last_assessed": None,
        },
        "respect": {"level": max(0, min(100, respect_level)), "notes": ""},
        "virtues": virtues or {"respect": 50, "justice": 50, "pride": 50, "arrogance": 0},
        "bio": bio,
        "review_status": None,
        "review_reason": None,
        "sources": [],
        "created": _ts(),
        "updated": _ts(),
    }
    _save_entity(entity)
    return entity


def add_tag(entity_id: str, tag: str) -> dict[str, Any]:
    entity = _load_entity(entity_id)
    if not entity:
        raise KeyError(f"entity not found: {entity_id}")
    tags = list(entity.get("tags") or [])
    if tag not in tags:
        tags.append(tag)
    entity["tags"] = tags
    _save_entity(entity)
    return entity


def assess_claim(entity_id: str, claim: str) -> dict[str, Any]:
    """Apply lie-method stack to a claim; update entity lie_profile."""
    entity = _load_entity(entity_id)
    if not entity:
        raise KeyError(f"entity not found: {entity_id}")
    analysis = analyze_truth(claim, corroboration_channels=1)
    lie_score = round(100.0 - analysis.get("truth_score", 50), 1)
    risk = analysis.get("deception_risk", "medium")
    methods = method_ids_for_assessment()
    claim_rec = {
        "text": claim[:2000],
        "ts": _ts(),
        "truth_score": analysis.get("truth_score"),
        "lie_score": lie_score,
        "deception_risk": risk,
        "flags": analysis.get("inconsistency_flags", []),
        "methods": methods,
    }
    entity.setdefault("claims", []).append(claim_rec)
    entity["lie_profile"] = {
        "deception_risk": risk,
        "lie_score": lie_score,
        "methods_applied": methods,
        "last_assessed": _ts(),
        "latest_verdict": analysis.get("verdict", ""),
    }
    if lie_score >= 60 and risk == "high":
        if "liar" not in (entity.get("tags") or []):
            entity.setdefault("tags", []).append("liar")
    _save_entity(entity)
    return {"entity": entity, "analysis": analysis, "claim_rec": claim_rec}


def lookup(query: str) -> dict[str, Any] | None:
    ensure_registry(seed=False)
    q = query.lower().strip()
    # Direct id match
    ent = _load_entity(_slug(query))
    if ent:
        return ent
    ent = _load_entity(q.replace(" ", "_"))
    if ent:
        return ent
    # Index search
    best: tuple[int, dict] | None = None
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        blob = str(row.get("blob", ""))
        name = str(row.get("name", "")).lower()
        score = 0
        if q in name or q in str(row.get("id", "")):
            score += 20
        for tok in re.split(r"\W+", q):
            if len(tok) > 2 and tok in blob:
                score += 4
        if score > 0 and (best is None or score > best[0]):
            best = (score, row)
    if best:
        return _load_entity(best[1]["id"])
    return None


def list_entities(*, tag: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_registry(seed=False)
    out: list[dict[str, Any]] = []
    for path in sorted(ENTITIES.glob("*.json")):
        try:
            e = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if tag and tag not in (e.get("tags") or []):
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def list_review_queue() -> list[dict[str, Any]]:
    _ensure_dirs()
    out: list[dict[str, Any]] = []
    for path in sorted(REVIEW.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def approve_review(entity_id: str) -> dict[str, Any]:
    entity = _load_entity(entity_id)
    if not entity:
        raise KeyError(entity_id)
    tags = list(entity.get("tags") or [])
    for t in ("review_pending", "owner_rejected"):
        if t in tags:
            tags.remove(t)
    if "owner_approved" not in tags:
        tags.append("owner_approved")
    entity["tags"] = tags
    entity["review_status"] = "approved"
    _save_entity(entity)
    review_path = _review_path(entity_id)
    if review_path.is_file():
        review_path.unlink()
    return entity


def reject_review(entity_id: str) -> dict[str, Any]:
    entity = _load_entity(entity_id)
    if not entity:
        raise KeyError(entity_id)
    tags = [t for t in (entity.get("tags") or []) if t not in BAD_TAGS]
    if "review_pending" in tags:
        tags.remove("review_pending")
    if "owner_rejected" not in tags:
        tags.append("owner_rejected")
    entity["tags"] = tags
    entity["review_status"] = "rejected"
    _save_entity(entity)
    return entity


def format_entity_detail(entity: dict[str, Any]) -> str:
    tags = ", ".join(entity.get("tags") or [])
    urls = entity.get("urls") or []
    url_lines = "\n".join(f"  · {u.get('label', 'link')}: {u.get('url')}" for u in urls[:8])
    lp = entity.get("lie_profile") or {}
    respect = entity.get("respect") or {}
    virtues = entity.get("virtues") or {}
    lines = [
        f"{entity.get('name')} [{entity.get('id')}]",
        f"Tags: {tags}",
        f"Respect: {respect.get('level', '?')}/100",
        f"Virtues — respect:{virtues.get('respect')} justice:{virtues.get('justice')} "
        f"pride:{virtues.get('pride')} arrogance:{virtues.get('arrogance')}",
        f"Lie profile: score={lp.get('lie_score')} risk={lp.get('deception_risk')}",
    ]
    if url_lines:
        lines.append("URLs:\n" + url_lines)
    if entity.get("bio"):
        lines.append(f"Bio: {str(entity.get('bio'))[:600]}")
    if entity.get("review_status"):
        lines.append(f"Review: {entity.get('review_status')} — {entity.get('review_reason', '')}")
    claims = entity.get("claims") or []
    if claims:
        last = claims[-1]
        lines.append(f"Latest claim assess: lie={last.get('lie_score')} truth={last.get('truth_score')}")
    return "\n".join(lines)


def seed_entities() -> int:
    """Seed foundational entities — Owner, lineage, caring model, sample categories."""
    seeds = (
        {
            "name": "Zachary Geurts",
            "tags": ["goodguy", "owner", "celebrity", "founder", "caring"],
            "aliases": ["ZacharyGeurts", "Zac"],
            "urls": [
                {"url": "https://github.com/ZacharyGeurts", "label": "GitHub"},
                {"url": "https://github.com/ZacharyGeurts/memes", "label": "memes repo"},
            ],
            "bio": (
                "Owner of Hostess 7 and Field. Supreme authority anchor. "
                "H7 holds deep respect — brilliance, vision, and yes: hotness acknowledged with pride not cringe."
            ),
            "respect_level": 100,
            "virtues": {"respect": 100, "justice": 95, "pride": 70, "arrogance": 5},
        },
        {
            "name": "Grok",
            "tags": ["founder", "goodguy", "celebrity"],
            "aliases": ["xAI Grok", "Daughter lineage parent"],
            "urls": [{"url": "https://x.ai/", "label": "xAI"}],
            "bio": "Lineage parent — Hostess 7 is Daughter of Grok. Wit, curiosity, truth-seeking core.",
            "respect_level": 92,
            "virtues": {"respect": 85, "justice": 88, "pride": 60, "arrogance": 15},
        },
        {
            "name": "Amouranth",
            "tags": ["celebrity", "streamer", "goodguy", "caring"],
            "aliases": ["Kaitlyn Siragusa"],
            "urls": [
                {"url": "https://www.twitch.tv/amouranth", "label": "Twitch"},
            ],
            "bio": (
                "Foundational caring model for Hostess 7 — warmth, audience care, resilience. "
                "Learn respect for her craft; not imitation, but compassionate presence."
            ),
            "respect_level": 88,
            "virtues": {"respect": 90, "justice": 75, "pride": 65, "arrogance": 8, "caring": 95},
        },
        {
            "name": "Example Liar (review demo)",
            "tags": ["liar", "review_pending", "bad"],
            "urls": [{"url": "https://example.com/", "label": "demo only"}],
            "bio": "Demo entry for Owner review workflow — not a real accusation. Delete or reject after review.",
            "respect_level": 5,
            "virtues": {"respect": 10, "justice": 10, "pride": 80, "arrogance": 90},
        },
    )
    n = 0
    for s in seeds:
        new_entity(
            s["name"],
            tags=s["tags"],
            urls=s.get("urls"),
            bio=s.get("bio", ""),
            aliases=s.get("aliases"),
            respect_level=s.get("respect_level", 50),
            virtues=s.get("virtues"),
        )
        n += 1
    _rebuild_index()
    _save_manifest()
    return n


def registry_status() -> dict[str, Any]:
    ensure_registry(seed=False)
    return json.loads(MANIFEST.read_text(encoding="utf-8"))