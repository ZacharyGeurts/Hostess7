#!/usr/bin/env pythong
"""Historic truth corpus — all new information must corroborate KNOWN · Lie Librarian · detective anchors."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-historic-truth-corpus-doctrine.json"
PANEL = STATE / "hostess7-historic-truth-corpus-panel.json"
LEDGER = STATE / "hostess7-historic-truth-corpus.jsonl"

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.I)


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "utc": _utc()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _floors() -> dict[str, float]:
    f = (_doctrine().get("floors") or {})
    return {
        "min_corroboration_channels": float(f.get("min_corroboration_channels") or 1),
        "pass_boost": float(f.get("pass_boost") or 18),
        "no_historic_penalty": float(f.get("no_historic_penalty") or 22),
        "lie_conflict_penalty": float(f.get("lie_conflict_penalty") or 35),
        "unknown_topic_penalty": float(f.get("unknown_topic_penalty") or 15),
    }


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / max(1, min(len(ta), len(tb)))


def _import_mod(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(spec.name, None)
        return None


def _scan_known(claim: str) -> list[dict[str, Any]]:
    known = _load(STATE / "hostess7-known-knowledge.json", {}).get("entries") or {}
    hits: list[dict[str, Any]] = []
    for entry in known.values():
        topic = str(entry.get("topic") or "")
        ov = _overlap(claim, topic)
        if ov >= 0.25 or (len(claim) > 20 and claim.lower() in topic.lower()):
            hits.append({
                "source": "known_registry",
                "id": entry.get("id"),
                "topic": topic[:200],
                "overlap": round(ov, 3),
                "domain": entry.get("domain"),
            })
    hits.sort(key=lambda h: -float(h.get("overlap") or 0))
    return hits[:8]


def _scan_unknown_conflicts(claim: str) -> list[dict[str, Any]]:
    unknown = _load(STATE / "hostess7-unknown-knowledge.json", {}).get("entries") or {}
    hits: list[dict[str, Any]] = []
    for entry in unknown.values():
        if entry.get("status") == "known":
            continue
        topic = str(entry.get("topic") or "")
        ov = _overlap(claim, topic)
        if ov >= 0.35:
            hits.append({
                "source": "unknown_registry",
                "id": entry.get("id"),
                "topic": topic[:200],
                "overlap": round(ov, 3),
                "priority": entry.get("priority"),
            })
    hits.sort(key=lambda h: -float(h.get("overlap") or 0))
    return hits[:6]


def _scan_lie_librarian(claim: str) -> list[dict[str, Any]]:
    ll = _import_mod("lib/h7-lie-librarian.py", "h7_ll_hist")
    if not ll or not hasattr(ll, "search_lies"):
        return []
    q = " ".join(sorted(_tokens(claim), key=len, reverse=True)[:6])
    if not q:
        q = claim[:80]
    try:
        doc = ll.search_lies(q, limit=12)
    except Exception:
        return []
    hits: list[dict[str, Any]] = []
    for row in doc.get("hits") or []:
        excerpt = str(row.get("excerpt") or "")
        ov = _overlap(claim, excerpt)
        ls = float(row.get("lie_score") or 0)
        if ov >= 0.2 or ls >= 55:
            hits.append({
                "source": "lie_librarian",
                "book_id": row.get("book_id"),
                "page": row.get("page"),
                "lie_score": ls,
                "overlap": round(ov, 3),
                "excerpt": excerpt[:160],
                "likely_false": row.get("likely_false"),
            })
    hits.sort(key=lambda h: (-float(h.get("lie_score") or 0), -float(h.get("overlap") or 0)))
    return hits[:8]


def _scan_detective(claim: str) -> list[dict[str, Any]]:
    scripts = HOSTESS / "scripts"
    path = scripts / "field_detective_corpus.py"
    if not path.is_file():
        return []
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import field_detective_corpus as dc  # noqa: WPS433
        if not hasattr(dc, "search_detective"):
            return []
        q = " ".join(sorted(_tokens(claim), key=len, reverse=True)[:5]) or claim[:60]
        rows = dc.search_detective(q, limit=4)
        return [
            {
                "source": "detective_corpus",
                "title": r.get("title"),
                "overlap_query": q,
                "body_preview": str(r.get("body") or "")[:120],
            }
            for r in (rows or [])
        ]
    except Exception:
        return []


def corroborate_claim(claim: str, *, source: str = "direct") -> dict[str, Any]:
    """Historic truth corpus corroboration — channels, conflicts, pass verdict."""
    claim = (claim or "").strip()
    floors = _floors()
    flags_doc = (_doctrine().get("flags") or {})
    if not claim:
        return {
            "ok": False,
            "schema": "hostess7-historic-truth-corroborate/v1",
            "pass": False,
            "reason": "empty_claim",
            "channels": 0,
            "flags": ["empty_claim"],
        }

    known_hits = _scan_known(claim)
    unknown_hits = _scan_unknown_conflicts(claim)
    lie_hits = _scan_lie_librarian(claim)
    detective_hits = _scan_detective(claim)

    channels = 0
    if known_hits:
        channels += 1
    if detective_hits:
        channels += 1
    if lie_hits and all(float(h.get("lie_score") or 0) < 50 for h in lie_hits):
        channels += 1

    flags: list[str] = []
    score_adj = 0.0

    lie_conflict = [h for h in lie_hits if float(h.get("lie_score") or 0) >= 55 and float(h.get("overlap") or 0) >= 0.15]
    if lie_conflict:
        flags.append(str(flags_doc.get("lie_conflict") or "historic_lie_librarian_conflict"))
        score_adj -= floors["lie_conflict_penalty"]

    if unknown_hits and not known_hits:
        flags.append(str(flags_doc.get("unknown_topic") or "historic_unknown_topic"))
        score_adj -= floors["unknown_topic_penalty"]

    passed = channels >= floors["min_corroboration_channels"] and not lie_conflict
    if passed:
        score_adj += floors["pass_boost"]
    else:
        flags.append(str(flags_doc.get("no_historic") or "no_historic_truth_corpus"))
        score_adj -= floors["no_historic_penalty"]

    out = {
        "ok": True,
        "schema": "hostess7-historic-truth-corroborate/v1",
        "pass": passed,
        "source": source[:64],
        "claim_preview": claim[:300],
        "channels": channels,
        "min_channels": floors["min_corroboration_channels"],
        "score_adjustment": round(score_adj, 1),
        "flags": flags,
        "known_hits": known_hits,
        "unknown_hits": unknown_hits,
        "lie_hits": lie_hits,
        "detective_hits": detective_hits,
        "action": "accept" if passed else "hold_investigate_queue_unknown",
    }
    _append({**out, "event": "corroborate"})
    return out


def gate_new_information(
    claim: str,
    *,
    source: str = "direct",
    queue_unknown: bool = True,
) -> dict[str, Any]:
    """Gate — new information must pass historic truth corpus."""
    corr = corroborate_claim(claim, source=source)
    queued = None
    if not corr.get("pass") and queue_unknown and len((claim or "").strip()) >= 12:
        cur = _import_mod("lib/hostess7-curiosity-corpus.py", "h7_cur_hist")
        if cur and hasattr(cur, "mark_unknown"):
            try:
                hints = [
                    "Historic truth corpus gate failed — corroborate before fielding.",
                    f"channels={corr.get('channels')} flags={corr.get('flags')}",
                ]
                queued = cur.mark_unknown(
                    claim[:400],
                    domain="historic_gate",
                    source=source,
                    priority_kind="operator",
                    hints=hints,
                )
            except Exception:
                queued = {"ok": False}
    return {
        "ok": bool(corr.get("pass")),
        "schema": "hostess7-historic-truth-gate/v1",
        "pass": bool(corr.get("pass")),
        "corroboration": corr,
        "queued_unknown": queued,
        "motto": _doctrine().get("motto"),
    }


def apply_to_truth_analysis(analysis: dict[str, Any], claim: str, *, source: str = "direct") -> dict[str, Any]:
    """Merge historic gate into an existing truth analysis dict."""
    corr = corroborate_claim(claim, source=source)
    out = dict(analysis)
    score = float(out.get("truth_score") or 0)
    score += float(corr.get("score_adjustment") or 0)
    score = max(0.0, min(100.0, round(score, 1)))
    flags = list(out.get("inconsistency_flags") or [])
    for f in corr.get("flags") or []:
        if f not in flags:
            flags.append(f)
    out["truth_score"] = score
    out["inconsistency_flags"] = flags
    out["historic_truth"] = corr
    out["historic_truth_pass"] = bool(corr.get("pass"))
    if not corr.get("pass"):
        out["deception_risk"] = "high" if score < 40 else out.get("deception_risk") or "medium"
        out["recommended_action"] = "reject_or_investigate"
        prev = str(out.get("verdict") or "")
        out["verdict"] = f"{prev} Historic truth corpus: HOLD — corroborate KNOWN/Lie Librarian/detective.".strip()
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _doctrine()
    known = _load(STATE / "hostess7-known-knowledge.json", {})
    unknown = _load(STATE / "hostess7-unknown-knowledge.json", {})
    panel = {
        "schema": "hostess7-historic-truth-corpus-panel/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "rule": doc.get("rule"),
        "known_count": known.get("count", 0),
        "unknown_count": unknown.get("count", 0),
        "floors": _floors(),
        "sources": doc.get("sources"),
        "module": str(DOCTRINE),
    }
    if write:
        _save(PANEL, panel)
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("corroborate", "witness"):
        claim = " ".join(sys.argv[2:]).strip()
        if not claim:
            print(json.dumps({"error": "usage: corroborate <claim>"}, ensure_ascii=False))
            return 1
        print(json.dumps(corroborate_claim(claim), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("gate", "check"):
        claim = " ".join(sys.argv[2:]).strip()
        if not claim:
            print(json.dumps({"error": "usage: gate <claim>"}, ensure_ascii=False))
            return 1
        print(json.dumps(gate_new_information(claim), ensure_ascii=False, indent=2))
        return 0 if gate_new_information(claim).get("pass") else 2
    print(json.dumps({
        "error": "usage: hostess7-historic-truth-corpus.py [panel|corroborate|gate]",
        "motto": _doctrine().get("motto"),
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())