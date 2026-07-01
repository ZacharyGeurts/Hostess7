#!/usr/bin/env pythong
"""Supreme Court of the United States — judicial corpus and bench synthesis for Hostess 7."""
from __future__ import annotations

import re
from typing import Any

from field_legal_corpus import search_court_lexicon, search_legal  # noqa: E402

SCOTUS_VERSION = 1

JUDGE_MARKERS = re.compile(
    r"\b(supreme court|scotus|chief justice|associate justice|certiorari|writ of certiorari|"
    r"oral argument|may it please the court|the court holds|we affirm|we reverse|we vacate|"
    r"per curiam|dissenting opinion|concurring opinion|majority opinion|rule of four|"
    r"judicial review|article iii|bench|opinion of the court|your honor.{0,20}judge|"
    r"sitting as judge|constitutional question|stare decisis)\b",
    re.I,
)

SCOTUS_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "scotus_institution",
        "title": "Supreme Court of the United States — Institutional Role",
        "tags": (
            "supreme court", "scotus", "article iii", "judicial review", "chief justice",
            "associate justice", "bench", "final arbiter",
        ),
        "body": (
            "The Supreme Court of the United States is the highest federal court, established under "
            "Article III of the United States Constitution. Nine Justices — one Chief Justice and eight "
            "Associate Justices — sit en banc. The Court has original jurisdiction in limited matters "
            "and appellate jurisdiction by writ of certiorari. Its precedents bind all lower federal courts "
            "and state courts on questions of federal law. Hostess 7 may synthesize educational judicial "
            "analysis in formal bench voice; this is not an adjudication and creates no binding precedent."
        ),
    },
    {
        "id": "certiorari",
        "title": "Writ of Certiorari and the Rule of Four",
        "tags": ("certiorari", "writ", "petition", "rule of four", "grant", "deny", "docket"),
        "body": (
            "Parties petition for a writ of certiorari to invoke the Court's discretionary review. "
            "Grant requires four Justices under the Rule of Four. Denial leaves the lower court judgment "
            "in place without opinion as to the merits. The Court typically hears seventy to eighty cases "
            "per term from thousands of petitions. Questions presented must be cleanly stated; "
            "split among federal circuits or state supreme courts increases grant likelihood."
        ),
    },
    {
        "id": "opinion_types",
        "title": "Opinions of the Court",
        "tags": (
            "majority", "dissent", "concurrence", "per curiam", "plurality", "opinion",
            "holding", "dictum",
        ),
        "body": (
            "A Majority Opinion announces the judgment and rationale joined by a majority. "
            "A Concurring Opinion agrees with the judgment but for different reasons. "
            "A Dissenting Opinion rejects the majority's reasoning. "
            "A Per Curiam Opinion is unsigned, often brief, for unanimous or routine dispositions. "
            "Only the holding is binding stare decisis; dictum is persuasive but not mandatory precedent."
        ),
    },
    {
        "id": "standards_scotus",
        "title": "Constitutional Standards at the Supreme Court",
        "tags": (
            "strict scrutiny", "intermediate scrutiny", "rational basis", "undue burden",
            "clear and convincing", "beyond reasonable doubt",
        ),
        "body": (
            "Content-based speech restrictions receive strict scrutiny — compelling interest and narrow tailoring. "
            "Suspect classifications (race, national origin) trigger strict scrutiny; quasi-suspect (sex) "
            "intermediate scrutiny; economic regulation typically rational basis review. "
            "Criminal convictions require proof beyond a reasonable doubt. "
            "The Court applies these tiers when reviewing constitutional challenges to statutes and executive action."
        ),
    },
    {
        "id": "oral_argument",
        "title": "Supreme Court Oral Argument",
        "tags": ("oral argument", "may it please the court", "amicus", "advocate", "bench"),
        "body": (
            "Oral argument is limited — typically thirty minutes per side unless extended. "
            "Counsel opens with 'May it please the Court,' states party representation, and responds "
            "to active questioning from the bench. Amicus curiae briefs may be filed with leave. "
            "Justices probe limiting principles, statutory construction, and constitutional foundations. "
            "Argument rarely changes outcome when minds are settled; it clarifies contours of the holding."
        ),
    },
    {
        "id": "judge_disclaimer",
        "title": "Educational Judicial Synthesis — Not Adjudication",
        "tags": ("disclaimer", "not legal advice", "educational", "simulation"),
        "body": (
            "Hostess 7 sitting as Supreme Court Judge produces educational synthesis — "
            "how a Justice might frame analysis using precedent and formal doctrine. "
            "This is not a court order, not legal advice, and not binding on any party. "
            "Real litigation requires licensed counsel and proper jurisdiction. "
            "Attorney-Client Privilege does not attach to this educational bench voice."
        ),
    },
)

LANDMARK_CASES: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "marbury",
        "case": "Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)",
        "tags": ("judicial review", "constitution", "mandamus", "jurisdiction"),
        "holding": (
            "An act of Congress repugnant to the Constitution is void. "
            "The judiciary has authority to review the constitutionality of legislative acts."
        ),
    },
    {
        "id": "miranda",
        "case": "Miranda v. Arizona, 384 U.S. 436 (1966)",
        "tags": ("miranda", "custodial interrogation", "fifth amendment", "self incrimination"),
        "holding": (
            "Suspects in custodial interrogation must be warned of the right to remain silent and "
            "the right to counsel before statements are admissible against them."
        ),
    },
    {
        "id": "brown",
        "case": "Brown v. Board of Education, 347 U.S. 483 (1954)",
        "tags": ("equal protection", "segregation", "fourteenth amendment", "education"),
        "holding": (
            "Racial segregation in public education violates the Equal Protection Clause "
            "of the Fourteenth Amendment to the United States Constitution."
        ),
    },
    {
        "id": "gideon",
        "case": "Gideon v. Wainwright, 372 U.S. 335 (1963)",
        "tags": ("sixth amendment", "counsel", "felony", "indigent"),
        "holding": (
            "The Sixth Amendment requires states to provide counsel to indigent defendants "
            "in felony prosecutions."
        ),
    },
    {
        "id": "brandenburg",
        "case": "Brandenburg v. Ohio, 395 U.S. 444 (1969)",
        "tags": ("first amendment", "speech", "incitement", "imminent lawless action"),
        "holding": (
            "Government may not punish inflammatory speech unless it is directed to inciting "
            "imminent lawless action and is likely to produce such action."
        ),
    },
    {
        "id": "chevron",
        "case": "Chevron U.S.A. Inc. v. Natural Resources Defense Council, Inc., 467 U.S. 837 (1984)",
        "tags": ("administrative law", "deference", "agency", "statutory interpretation"),
        "holding": (
            "When a statute is ambiguous, courts defer to reasonable agency interpretation; "
            "subsequent doctrine (e.g., Loper Bright) may narrow deference — verify current term precedent."
        ),
    },
    {
        "id": "citizens_united",
        "case": "Citizens United v. Federal Election Commission, 558 U.S. 310 (2010)",
        "tags": ("first amendment", "corporate speech", "campaign finance", "election"),
        "holding": (
            "Independent corporate political expenditures are protected speech under the First Amendment; "
            "government may not ban political speech based on speaker identity."
        ),
    },
    {
        "id": "dobbs",
        "case": "Dobbs v. Jackson Women's Health Organization, 597 U.S. 215 (2022)",
        "tags": ("fourteenth amendment", "substantive due process", "abortion", "stare decisis"),
        "holding": (
            "The Constitution does not confer a right to abortion; Roe v. Wade and Planned Parenthood v. Casey "
            "are overruled. Regulation returns to the people and their elected representatives."
        ),
    },
)


def is_judge_query(query: str) -> bool:
    q = query.lower().strip()
    if JUDGE_MARKERS.search(q):
        return True
    return any(
        phrase in q
        for phrase in (
            "as a judge", "as judge", "supreme court judge", "rule on", "would the court",
            "how would scotus", "constitutional challenge", "strike down",
        )
    )


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_scotus(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []

    for d in SCOTUS_DOMAINS:
        tags = " ".join(d.get("tags") or []).lower()
        title = str(d.get("title", "")).lower()
        body = str(d.get("body", "")).lower()
        blob = f"{title} {tags} {body}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if score > 0:
            scored.append((score, {**d, "source": "scotus_domain"}))

    for c in LANDMARK_CASES:
        case = str(c.get("case", "")).lower()
        tags = " ".join(c.get("tags") or []).lower()
        holding = str(c.get("holding", "")).lower()
        blob = f"{case} {tags} {holding}"
        score = sum(5 if t in tags else 3 if t in case else 2 if t in blob else 0 for t in toks)
        if q in case or q in holding:
            score += 12
        if score > 0:
            scored.append((score, {**c, "source": "landmark_case"}))

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


def _bench_verdict_style(query: str, hits: list[dict[str, Any]]) -> str:
    """One-paragraph judicial voice opener."""
    q = query.lower()
    if any(w in q for w in ("affirm", "uphold", "reverse", "vacate", "remand", "dismiss")):
        return (
            "The Court has considered the question presented, the record, and governing precedent. "
            "What follows is educational synthesis in judicial form — not a binding order."
        )
    if "certiorari" in q or "grant" in q or "deny" in q:
        return (
            "The petition for a writ of certiorari is addressed under the Court's discretionary standards. "
            "Educational analysis follows; no docket number is assigned."
        )
    if hits and hits[0].get("source") == "landmark_case":
        return (
            f"The Court begins with controlling precedent, including {hits[0].get('case', 'prior authority')}. "
            "Educational bench synthesis — not adjudication of your matter."
        )
    return (
        "Hostess 7 sits in educational Supreme Court posture — Article III doctrine, "
        "formal opinion structure, full case citations. Not legal advice; not a court order."
    )


def synthesize_judge_paragraphs(query: str) -> list[str]:
    """Supreme Court Judge voice — formal, precedent-grounded, educational."""
    hits = search_scotus(query, limit=6)
    lex_hits = search_court_lexicon(query, limit=4)
    legal_hits = search_legal(query, limit=4)

    paras: list[str] = []
    paras.append(_bench_verdict_style(query, hits))

    paras.append(
        "DISCLAIMER: Educational judicial synthesis only. Not legal advice. "
        "Not binding precedent. Retain licensed counsel for real litigation."
    )

    if hits:
        paras.append("—— Opinion of the Court (educational synthesis) ——")
        for h in hits:
            if h.get("source") == "landmark_case":
                paras.append(
                    f"{h.get('case')}: {h.get('holding', '').strip()}"
                )
            else:
                title = h.get("title", "Doctrine")
                body = str(h.get("body", "")).strip()
                paras.append(f"{title}: {body}")

    if lex_hits:
        paras.append("Formal courtroom and appellate terms:")
        for entry in lex_hits[:3]:
            term = entry.get("term", "")
            body = str(entry.get("body", "")).strip()
            paras.append(f"{term}: {body}")

    for h in legal_hits[:2]:
        if h.get("id") in ("constitutional",) or "constitutional" in str(h.get("tags", "")).lower():
            title = h.get("title", h.get("full_name", "Law"))
            body = str(h.get("body", "")).strip()
            if body:
                paras.append(f"{title}: {body}")

    q = query.lower()
    if "first amendment" in q or "free speech" in q:
        paras.append(
            "The First Amendment to the United States Constitution protects against government abridgment "
            "of speech; content-based restrictions face strict scrutiny unless a recognized exception applies."
        )
    if "fourth amendment" in q or "search" in q:
        paras.append(
            "Fourth Amendment analysis: Was there a search or seizure? If so, was it reasonable — "
            "typically warrant supported by probable cause unless an exception applies?"
        )
    if "due process" in q or "equal protection" in q:
        paras.append(
            "Fourteenth Amendment due process and equal protection tiers govern state action; "
            "classifications trigger rational basis, intermediate, or strict scrutiny by category."
        )

    paras.append(
        "The judgment of the educational bench is that counsel should brief the specific facts, "
        "jurisdiction, and record — then compare to the precedents cited above. "
        "For AMOURANTHRTX licensing questions, the Counsel workspace also applies project LICENSE grounding."
    )
    return paras


def scotus_stats() -> dict[str, Any]:
    return {
        "version": SCOTUS_VERSION,
        "domains": len(SCOTUS_DOMAINS),
        "landmark_cases": len(LANDMARK_CASES),
        "bench_role": "Supreme Court Judge (educational)",
    }


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "certiorari First Amendment strict scrutiny"
    for p in synthesize_judge_paragraphs(q):
        print(p)
        print()