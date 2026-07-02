#!/usr/bin/env pythong
"""Field legal corpus — full formal law words for court; no shorthands on actual laws."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from field_legal_catalog import catalog_count  # noqa: E402
from field_legal_court_lexicon import COURT_LEXICON, LEXICON_CATEGORIES  # noqa: E402
from field_legal_domains import LEGAL_CORPUS_VERSION, LEGAL_DOMAINS  # noqa: E402

from field_legal_infinite import (  # noqa: E402
    INDEX,
    ingest_catalog,
    infinite_status,
    search_infinite,
)

ROOT = Path(__file__).resolve().parents[1]
LICENSE = ROOT / "LICENSE"
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "legal" / "corpus.json"

# Expand common shorthands to full formal names when synthesizing
FORMAL_EXPANSIONS: dict[str, str] = {
    "FRCP 12(b)(6)": "Federal Rule of Civil Procedure 12(b)(6)",
    "FRE 802": "Federal Rule of Evidence 802",
    "Rule 802": "Federal Rule of Evidence 802",
    "UCC": "Uniform Commercial Code",
    "FRCP": "Federal Rules of Civil Procedure",
    "FRCrP": "Federal Rules of Criminal Procedure",
    "FRE": "Federal Rules of Evidence",
    "FAA": "Federal Arbitration Act",
    "GDPR": "General Data Protection Regulation",
    "CCPA": "California Consumer Privacy Act",
    "CPRA": "California Privacy Rights Act",
    "DTSA": "Defend Trade Secrets Act",
    "UTSA": "Uniform Trade Secrets Act",
    "DMCA": "Digital Millennium Copyright Act",
    "OFAC": "Office of Foreign Assets Control",
    "FLSA": "Fair Labor Standards Act",
    "ADA": "Americans with Disabilities Act",
    "ADEA": "Age Discrimination in Employment Act",
    "IIED": "intentional infliction of emotional distress",
    "NDA": "non-disclosure agreement",
    "APA": "Administrative Procedure Act",
    "IRS": "Internal Revenue Service",
    "GPL": "GNU General Public License",
    "GPL v3": "GNU General Public License Version 3",
    "Rule 56": "Federal Rule of Civil Procedure 56",
    "Rule 11": "Federal Rule of Criminal Procedure 11",
    "Rule 802": "Federal Rule of Evidence 802",
    "§": "Section ",
}


def _load_amouranthrtx_license() -> str:
    if not LICENSE.is_file():
        return "AMOURANTHRTX LICENSE file not found in tree."
    return LICENSE.read_text(encoding="utf-8", errors="replace").strip()


def build_corpus() -> dict:
    domains: list[dict] = []
    for entry in LEGAL_DOMAINS:
        row = dict(entry)
        if row["id"] == "amouranthrtx_license":
            row["body"] = _load_amouranthrtx_license()
        domains.append(row)
    return {
        "version": LEGAL_CORPUS_VERSION,
        "domains": domains,
        "lexicon": list(COURT_LEXICON),
        "lexicon_categories": list(LEXICON_CATEGORIES),
        "domain_count": len(domains),
        "lexicon_count": len(COURT_LEXICON),
        "formal_mode": True,
        "infinite_drive": True,
        "catalog_seed_count": catalog_count(),
        "disclaimer": (
            "Hostess 7 legal corpus is educational synthesis using full formal legal terminology. "
            "Not legal advice. Attorney-Client Privilege does not attach. "
            "Consult a licensed attorney admitted in your jurisdiction before acting."
        ),
    }


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < LEGAL_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        CORPUS_CACHE.write_text(json.dumps(build_corpus(), indent=2) + "\n", encoding="utf-8")
    if not INDEX.is_file():
        try:
            ingest_catalog(vacuum=False)
        except OSError:
            pass
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def _expand_formal(text: str) -> str:
    """Replace shorthands with full formal law names."""
    out = text
    for short, full in sorted(FORMAL_EXPANSIONS.items(), key=lambda x: -len(x[0])):
        if short in ("§",):
            out = out.replace(short, full)
        else:
            out = re.sub(rf"\b{re.escape(short)}\b", full, out)
    return out


def _license_query(q: str) -> bool:
    return bool(
        re.search(r"\b(gpl|general public license|copyleft)\b", q)
        or ("license" in q and any(k in q for k in ("derivative", "source", "copyright", "copyleft")))
    )


def search_legal(query: str, *, limit: int = 8) -> list[dict]:
    ensure_corpus()
    q = query.lower()
    license_query = _license_query(q)
    out: list[dict] = []
    seen: set[str] = set()
    try:
        doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        doc = build_corpus()
    domains = doc.get("domains") or []
    toks = _tokens(query)
    scored: list[tuple[int, dict]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        title = str(d.get("title", "")).lower()
        body = str(d.get("body", "")).lower()
        blob = f"{title} {tags} {body}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("lawyer", "attorney", "counsel", "bar examination", "hire a lawyer")):
            if d.get("id") in ("lawyer_role", "hiring_lawyer", "ethics"):
                score += 15
        if license_query or any(k in q for k in ("gpl", "license", "copyright", "amouranthrtx")):
            if d.get("id") in ("ip", "amouranthrtx_license", "media_policy"):
                score += 30 if license_query else 15
        if any(k in q for k in ("contract", "breach", "non-disclosure")):
            if d.get("id") == "contract":
                score += 12
        if any(k in q for k in ("court", "trial", "motion", "objection", "hearsay")):
            if d.get("id") in ("litigation", "evidence_rules", "criminal_procedure"):
                score += 10
        if any(k in q for k in ("supreme court", "scotus", "certiorari", "chief justice", "bench", "dissent")):
            if d.get("id") == "supreme_court":
                score += 20
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    for _, d in scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        d = dict(d)
        d["source"] = "domain"
        out.append(d)
        if len(out) >= limit:
            break

    if license_query and out:
        return out[:limit]

    infinite_limit = 0 if license_query else limit
    for row in search_infinite(query, limit=infinite_limit or limit):
        sid = str(row.get("id", row.get("full_name", "")))
        if sid in seen:
            continue
        seen.add(sid)
        out.append({
            "id": sid,
            "title": row.get("full_name", ""),
            "full_name": row.get("full_name", ""),
            "body": row.get("body", ""),
            "jurisdiction": row.get("jurisdiction", ""),
            "category": row.get("category", ""),
            "source": "infinite_drive",
        })
        if len(out) >= limit:
            break
    return out[:limit]


def search_court_lexicon(query: str, *, limit: int = 6) -> list[dict]:
    ensure_corpus()
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for entry in COURT_LEXICON:
        term = str(entry.get("term", "")).lower()
        tags = " ".join(entry.get("tags") or []).lower()
        body = str(entry.get("body", "")).lower()
        blob = f"{term} {tags} {body}"
        score = sum(5 if t in term else 4 if t in tags else 2 if t in blob else 0 for t in toks)
        if q in term or q in blob:
            score += 10
        if re.search(rf"\b{re.escape(term)}\b", q):
            score += 15
        if score > 0:
            scored.append((score, dict(entry)))
    scored.sort(key=lambda x: (-x[0], x[1].get("term", "")))
    seen: set[str] = set()
    out: list[dict] = []
    for _, e in scored:
        eid = str(e.get("id", ""))
        if eid in seen:
            continue
        seen.add(eid)
        out.append(e)
        if len(out) >= limit:
            break
    return out


def synthesize_legal_paragraphs(query: str) -> list[str]:
    from field_legal_scotus import is_judge_query, synthesize_judge_paragraphs  # noqa: WPS433

    if is_judge_query(query):
        return synthesize_judge_paragraphs(query)
    q_low = query.lower()
    license_query = _license_query(q_low)
    court_query = any(
        k in q_low
        for k in (
            "court", "trial", "motion", "objection", "hearsay", "deposition",
            "pleading", "complaint", "voir dire", "summary judgment", "your honor",
            "cross examination", "opening statement", "indictment", "arraignment",
        )
    )
    domain_hits = search_legal(query, limit=8 if court_query else 6)
    lex_hits = search_court_lexicon(query, limit=6 if court_query else 3)
    if not domain_hits:
        domain_hits = search_legal("law attorney contract tort litigation", limit=3)
    if not lex_hits and court_query:
        lex_hits = search_court_lexicon("motion objection hearsay trial", limit=4)

    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"

    paras.append(
        "Not legal advice. Attorney-Client Privilege does not attach. "
        "Verify with licensed counsel admitted in your jurisdiction before acting."
    )

    if court_query and lex_hits:
        paras.append(
            "Court lexicon — full formal terms (no abbreviations for governing rules):"
        )
        for entry in lex_hits:
            term = entry.get("term", "Term")
            body = _expand_formal(str(entry.get("body", "")).strip())
            paras.append(f"{term}: {body}")

    if domain_hits and not pro:
        paras.append("Infinite legal drive — full formal law names (no abbreviations):")
    for h in domain_hits:
        title = h.get("full_name") or h.get("title", "Law")
        body = _expand_formal(str(h.get("body", "")).strip())
        if not body:
            continue
        juris = h.get("jurisdiction", "")
        prefix = f"[{juris}] " if juris and not pro else ""
        paras.append(f"{prefix}{title}: {body}")

    if not court_query and not license_query and lex_hits:
        paras.append("Applicable court forms and formal terms:")
        for entry in lex_hits[:3]:
            term = entry.get("term", "")
            body = _expand_formal(str(entry.get("body", "")).strip())
            paras.append(f"{term}: {body}")

    return paras


def corpus_stats() -> dict:
    ensure_corpus()
    doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    inf = infinite_status()
    return {
        "version": doc.get("version", LEGAL_CORPUS_VERSION),
        "domains": doc.get("domain_count", len(LEGAL_DOMAINS)),
        "lexicon": doc.get("lexicon_count", len(COURT_LEXICON)),
        "formal_mode": doc.get("formal_mode", True),
        "infinite_indexed": inf.get("indexed", 0),
        "infinite_bytes": inf.get("shard_bytes", 0),
        "catalog_seed": catalog_count(),
    }


if __name__ == "__main__":
    ensure_corpus()
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Motion for Summary Judgment hearsay objection"
    for p in synthesize_legal_paragraphs(q):
        print(p)
        print()