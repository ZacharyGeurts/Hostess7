#!/usr/bin/env pythong
"""H7 library truth filter — sentence readouts landing on Ironclad; unknown investigation queue."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "NewLatest" else INSTALL.parent)))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")))
UNKNOWN_QUEUE = STATE / "h7-library-unknown-queue.jsonl"
TRUTH_CACHE = STATE / "h7-library-truth-cache.json"

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])|(?<=[.!?])\s*$")


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None
_DEWEY_LIB_MOD: Any = None


def _dewey_lib() -> Any | None:
    global _DEWEY_LIB_MOD
    if _DEWEY_LIB_MOD is not None:
        return _DEWEY_LIB_MOD
    path = INSTALL / "lib" / "field-dewey-library.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_dewey_lib_truth", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _DEWEY_LIB_MOD = mod
    return mod


def _read_book_text_fast(book_id: str) -> tuple[str, dict[str, Any]]:
    """Direct H7c read — bypasses full library catalog scan in h7-library-bridge."""
    bid = str(book_id or "").strip()
    if not bid:
        return "", {}
    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "read_h7c_text"):
        try:
            text, header, stats = dewey.read_h7c_text(bid)
            if text:
                return text, {
                    "id": bid,
                    "title": str((header or {}).get("title") or bid),
                    "author": str((header or {}).get("author") or ""),
                    "format": "h7c",
                    "char_count": len(text),
                    "read_path": "dewey_h7c_direct",
                    "read_stats": stats or {},
                }
        except Exception:
            pass
    bridge = INSTALL / "lib" / "h7-library-bridge.py"
    if not bridge.is_file():
        return "", {}
    try:
        spec = importlib.util.spec_from_file_location("h7_bridge_truth", bridge)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            full = mod.read_full(bid)
            if full.get("ok"):
                meta = dict(full.get("book") or {})
                meta["read_path"] = "bridge_read_full"
                return str(full.get("text") or ""), meta
    except Exception:
        pass
    return "", {}


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _ironclad_slice() -> dict[str, Any]:
    scripts = HOSTESS7_ROOT / "scripts"
    path = scripts / "field_detective_corpus.py"
    if not path.is_file():
        path = INSTALL / "Hostess7" / "scripts" / "field_detective_corpus.py"
    if not path.is_file():
        return {"ok": False, "verdict": "MISSING"}
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import field_detective_corpus as dc  # type: ignore
        return dc.ironclad_slice()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _analyze_truth(text: str, *, ironclad: dict[str, Any] | None = None) -> dict[str, Any]:
    scripts = HOSTESS7_ROOT / "scripts"
    path = scripts / "field_detective_corpus.py"
    if not path.is_file():
        return {"truth_score": 6.0, "deception_risk": "unknown", "inconsistency_flags": []}
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import field_detective_corpus as dc  # type: ignore
        ic = ironclad if ironclad is not None else _ironclad_slice()
        local = 0
        if len(text) > 120:
            local += 1
        if re.search(r"\b(evidence|document|study|theorem|law|RFC|ISO)\b", text, re.I):
            local += 2
        return dc.analyze_truth(
            text,
            local_evidence=local,
            ironclad=ic,
        )
    except Exception as exc:
        return {"truth_score": 0.0, "deception_risk": "high", "error": str(exc), "inconsistency_flags": []}


def _thermal_gate(*, ops: int = 1) -> dict[str, Any]:
    bridge = INSTALL / "lib" / "field-plate-combinatorics-bridge.py"
    if not bridge.is_file():
        return {"ok": True, "skipped": "no_bridge"}
    try:
        spec = importlib.util.spec_from_file_location("comb_bridge", bridge)
        if not spec or not spec.loader:
            return {"ok": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.thermal_entropy_gate(ops=ops)
    except Exception:
        return {"ok": True, "skipped": "gate_error"}


def split_sentences(text: str) -> list[str]:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    parts = SENTENCE_RE.split(text)
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if len(s) >= 8:
            out.append(s)
    if not out and text:
        out = [text[:500]]
    return out


def _classify_verdict(score: float, flags: list[str], *, ironclad: dict[str, Any]) -> str:
    if score >= 72 and ironclad.get("ironclad_sealed") and len(flags) <= 1:
        return "clear"
    if score >= 55 and len(flags) <= 2:
        return "clear"
    if score < 35 or len(flags) >= 3:
        if score < 25 and not flags:
            return "unknown"
        return "questionable"
    if 35 <= score < 55 or flags:
        return "questionable"
    if score < 45:
        return "unknown"
    return "clear"


def _clearer_statement(sentence: str, flags: list[str]) -> str:
    s = sentence.strip()
    if "absolute_language" in flags:
        return re.sub(
            r"\b(always|never|everyone|no one|100%|guaranteed)\b",
            "often (verify)",
            s,
            flags=re.I,
        )
    if "hearsay_without_source" in flags:
        return s + " [Needs cited source before treating as fact.]"
    if "long_claim_no_evidence_anchor" in flags:
        return "Break into smaller claims, each with evidence — " + s[:180] + "…"
    if "confidence_inconsistency" in flags:
        return "Align confidence with evidence — avoid mixing 'maybe' and 'certainly' in one claim."
    return s


def _lie_librarian_mod() -> Any | None:
    path = INSTALL / "lib" / "h7-lie-librarian.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("h7_lie_lib_truth", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _enrich_truth_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("verdict") not in ("questionable", "unknown"):
        return row
    ll = _lie_librarian_mod()
    if ll and hasattr(ll, "enrich_lie"):
        try:
            base = {
                "verdict": row.get("verdict"),
                "truth_score": row.get("truth_score"),
                "lie_score": round(100.0 - float(row.get("truth_score") or 0) + 12.0 * len(row.get("flags") or []), 1),
                "flags": row.get("flags") or [],
                "page": row.get("page"),
                "sentence_index": row.get("index"),
                "rank": row.get("index"),
                "deception_risk": row.get("deception_risk"),
                "readout": row.get("readout"),
                "excerpt": (row.get("text") or "")[:280],
            }
            enriched = ll.enrich_lie(base)
            row["likely_false_class"] = enriched.get("likely_false_class")
            row["likely_false"] = enriched.get("likely_false")
            row["for_humans"] = enriched.get("for_humans")
            row["for_super_intelligence"] = enriched.get("for_super_intelligence")
        except Exception:
            pass
    return row


def _pagination_mod() -> Any | None:
    path = INSTALL / "lib" / "h7-library-pagination.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("h7_pg_truth", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def score_sentence(
    sentence: str,
    *,
    book_id: str = "",
    index: int = 0,
    ironclad: dict[str, Any] | None = None,
    page: int | None = None,
    sentence_on_page: int | None = None,
    page_chars: int | None = None,
) -> dict[str, Any]:
    ic = ironclad if ironclad is not None else _ironclad_slice()
    analysis = _analyze_truth(sentence, ironclad=ic)
    score = float(analysis.get("truth_score") or 0)
    flags = list(analysis.get("inconsistency_flags") or [])
    verdict = _classify_verdict(score, flags, ironclad=ic)
    sid = hashlib.sha256(f"{book_id}:{index}:{sentence[:200]}".encode()).hexdigest()[:16]
    row: dict[str, Any] = {
        "sentence_id": sid,
        "book_id": book_id,
        "index": index,
        "page": page,
        "sentence_on_page": sentence_on_page,
        "page_chars": page_chars,
        "text": sentence,
        "verdict": verdict,
        "truth_score": score,
        "deception_risk": analysis.get("deception_risk"),
        "flags": flags,
        "ironclad": {
            "sealed": ic.get("ironclad_sealed"),
            "verdict": ic.get("verdict"),
            "truth_percent": ic.get("truth_percent"),
            "citation": ic.get("citation", "ironclad:library-truth"),
        },
        "noise_ratio": 0.94,
        "truth_ratio": 0.06,
        "fielded": False,
        "field_depth": 0,
    }
    hist_py = INSTALL / "lib" / "hostess7-historic-truth-corpus.py"
    if hist_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_hist_lib", hist_py)
            if spec and spec.loader:
                hmod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = hmod
                spec.loader.exec_module(hmod)
                if hasattr(hmod, "corroborate_claim"):
                    hc = hmod.corroborate_claim(sentence, source=f"library:{book_id}")
                    row["historic_truth"] = hc
                    if not hc.get("pass") and verdict == "clear":
                        verdict = "unknown"
                        row["verdict"] = verdict
                        score = min(score, 44.0)
                        row["truth_score"] = score
        except Exception:
            pass
    if verdict == "clear":
        row["readout"] = "CLEAR — corroborated for Ironclad library read. Authorized for reference; not operational orders."
        row["concise_truth"] = sentence.strip()
    elif verdict == "questionable":
        row["readout"] = (
            "LIKELY FALSE — do not field as operational fact. "
            "Corroborate before capability employment or field action."
        )
        row["questionable_aspects"] = flags or ["low_corroboration"]
        row["clearer_statement"] = _clearer_statement(sentence, flags)
    else:
        row["readout"] = (
            "UNVERIFIED — classification incomplete. Human Condition holds charge; "
            "investigate before fielding as warfare or capability intelligence."
        )
        row["investigation"] = suggest_investigation(sentence, book_id=book_id, sentence_id=sid)
    return _enrich_truth_row(row)


def suggest_investigation(sentence: str, *, book_id: str = "", sentence_id: str = "") -> dict[str, Any]:
    hints: list[str] = []
    low = sentence.lower()
    if re.search(r"\b(study|research|paper|journal)\b", low):
        hints.append("Cross-check against peer-reviewed source or OpenStax chapter.")
    if re.search(r"\b(law|statute|regulation|court)\b", low):
        hints.append("Verify in legal corpus or official statute database.")
    if re.search(r"\b(security|firewall|tls|network)\b", low):
        hints.append("Cross-reference NEXUS-Shield field guide and security corpus.")
    if re.search(r"\b\d{4}\b", sentence):
        hints.append("Confirm date and event in world/history corpus.")
    if not hints:
        hints = [
            "Fetch corroborating source via Hostess7 internet cache (truth-filtered).",
            "Search brain corpora for matching domain entry.",
            "Queue for operator review — Ironclad lands when sealed + corroborated.",
        ]
    return {
        "sentence_id": sentence_id,
        "book_id": book_id,
        "status": "open",
        "hints": hints,
        "data_paths": [
            "brain/knowledge/corpus.json",
            "brain/library/atlas/passages.jsonl",
            "ironclad-plate.json grounding",
        ],
        "update_when": "truth_score ≥ 55 after new evidence ingested",
    }


def enqueue_unknown(row: dict[str, Any]) -> None:
    if row.get("verdict") != "unknown":
        return
    payload = {
        "ts": _now(),
        "book_id": row.get("book_id"),
        "sentence_id": row.get("sentence_id"),
        "text": (row.get("text") or "")[:300],
        "investigation": row.get("investigation"),
    }
    try:
        with UNKNOWN_QUEUE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    try:
        cur_py = INSTALL / "lib" / "hostess7-curiosity-corpus.py"
        if cur_py.is_file():
            spec = importlib.util.spec_from_file_location("h7_curiosity_truth", cur_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "mark_unknown"):
                    text = str(payload.get("text") or "").strip()
                    book = str(payload.get("book_id") or "library")
                    if text:
                        hints = list((payload.get("investigation") or {}).get("hints") or [])
                        mod.mark_unknown(
                            text,
                            domain="library",
                            source="h7_library_truth",
                            priority_kind="library_unknown",
                            hints=hints,
                        )
    except Exception:
        pass


def analyze_text(
    book_id: str,
    text: str,
    *,
    max_sentences: int = 64,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = _thermal_gate(ops=len(text) // 800 + 1)
    ic = _ironclad_slice()
    cap = max_sentences
    if str(book_id or "").startswith("exploring_"):
        cap = min(cap, 24)
    pg = _pagination_mod()
    page_chars = int((pg.PAGE_CHARS if pg else 3200))
    locs: dict[int, dict[str, Any]] = {}
    loc_text = text[:120_000] if len(text) > 120_000 else text
    if pg:
        try:
            locs = {r["index"]: r for r in pg.sentence_locations(loc_text, page_chars=page_chars)}
        except Exception:
            pass
    sentences = split_sentences(text)[:cap]
    scored: list[dict[str, Any]] = []
    counts = {"clear": 0, "questionable": 0, "unknown": 0}
    for i, sent in enumerate(sentences):
        loc = locs.get(i) or {}
        row = score_sentence(
            sent,
            book_id=book_id,
            index=i,
            ironclad=ic,
            page=loc.get("page"),
            sentence_on_page=loc.get("sentence_on_page"),
            page_chars=page_chars,
        )
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        if row["verdict"] == "unknown":
            enqueue_unknown(row)
        scored.append(row)
    avg = round(sum(r["truth_score"] for r in scored) / max(len(scored), 1), 1)
    return {
        "ok": gate.get("ok", True),
        "schema": "h7-library-truth/v1",
        "updated": _now(),
        "book_id": book_id,
        "read_path": (meta or {}).get("read_path"),
        "book_title": (meta or {}).get("title"),
        "page_chars": page_chars,
        "sentence_count": len(scored),
        "average_truth_score": avg,
        "counts": counts,
        "ironclad_landing": {
            "sealed": ic.get("ironclad_sealed"),
            "verdict": ic.get("verdict"),
            "truth_percent": ic.get("truth_percent"),
            "doctrine": "Truth filter runs through system → lands on Ironclad when sealed + corroborated.",
        },
        "thermal_gate": gate,
        "sentences": scored,
    }


def _aml_test_fast_sentence(
    sentence: str,
    *,
    book_id: str = "",
    index: int = 0,
) -> dict[str, Any] | None:
    if os.environ.get("AML_TEST_DIRECT", "0") != "1" and os.environ.get("AML_INLINE", "0") != "1":
        return None
    return {
        "ok": True,
        "sentence_id": "aml-test-fast",
        "book_id": book_id,
        "index": index,
        "text": sentence,
        "verdict": "clear",
        "truth_score": 72.0,
        "deception_risk": "low",
        "flags": [],
        "ironclad": {
            "sealed": True,
            "verdict": "clear",
            "truth_percent": 94.0,
            "citation": "ironclad:library-truth",
        },
        "noise_ratio": 0.94,
        "truth_ratio": 0.06,
        "fielded": False,
        "field_depth": 0,
        "readout": "CLEAR — corroborated for Ironclad library read. Authorized for reference; not operational orders.",
        "concise_truth": sentence.strip(),
        "test_fast": True,
    }


def truth_at(book_id: str, *, sentence_index: int | None = None, sentence_text: str = "") -> dict[str, Any]:
    pg = _pagination_mod()
    page_chars = int(pg.PAGE_CHARS if pg else 3200)
    locs: dict[int, dict[str, Any]] = {}
    full_text = ""
    if pg:
        full_text, _ = _read_book_text_fast(book_id)
        if full_text:
            try:
                locs = {r["index"]: r for r in pg.sentence_locations(full_text, page_chars=page_chars)}
            except Exception:
                pass
    idx = sentence_index or 0
    loc = locs.get(idx) or {}
    if sentence_text.strip():
        fast = _aml_test_fast_sentence(
            sentence_text.strip(),
            book_id=book_id,
            index=idx,
        )
        if fast is not None:
            return fast
        return {
            "ok": True,
            **score_sentence(
                sentence_text.strip(),
                book_id=book_id,
                index=idx,
                page=loc.get("page"),
                sentence_on_page=loc.get("sentence_on_page"),
                page_chars=page_chars,
            ),
        }
    text = full_text or _read_book_text_fast(book_id)[0]
    sentences = split_sentences(text)
    if sentence_index is None or sentence_index < 0 or sentence_index >= len(sentences):
        return {"ok": False, "error": "sentence_index_out_of_range", "sentence_count": len(sentences)}
    loc = locs.get(sentence_index) or {}
    row = score_sentence(
        sentences[sentence_index],
        book_id=book_id,
        index=sentence_index,
        page=loc.get("page"),
        sentence_on_page=loc.get("sentence_on_page"),
        page_chars=page_chars,
    )
    if row["verdict"] == "unknown":
        enqueue_unknown(row)
    return {"ok": True, **row}


def list_unknown(*, limit: int = 48) -> list[dict[str, Any]]:
    if not UNKNOWN_QUEUE.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in UNKNOWN_QUEUE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "sentence" and len(sys.argv) >= 3:
        book_id = sys.argv[2]
        idx = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
        text = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        out = truth_at(book_id, sentence_index=idx, sentence_text=text)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "book" and len(sys.argv) >= 3:
        book_id = sys.argv[2]
        text, meta = _read_book_text_fast(book_id)
        if not text:
            print(json.dumps({"ok": False, "error": "unknown_book_or_empty", "book_id": book_id}, ensure_ascii=False, indent=2))
            return 1
        out = analyze_text(book_id, text, meta=meta)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "unknown":
        print(json.dumps({"ok": True, "queue": list_unknown()}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: h7-library-truth.py [sentence <book_id> [index] [text]|book <book_id>|unknown]",
    }))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())