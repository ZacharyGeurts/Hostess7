#!/usr/bin/env pythong
"""NEXUS hostility priority — Hell is Hell goes to Hell.

Central scoring and hell-first ordering for connections, RF threats, and field registry.
Heaven passes at zero cost. Hell rises to the top — no mercy, no friendly fire confusion.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

MOTTO = (
    "Send Hell to Hell — nothing unseen, nothing fully secure, honest rocks. "
    "Hostility first; Heaven never bumped ahead of harm."
)

SOUL_ORDER = {"hell": 0, "limbo": 1, "heaven": 2}

VERDICT_HOSTILITY = {
    "HARM_CANDIDATE": 40,
    "SUSPICIOUS": 18,
    "MONITOR": 2,
    "EPHEMERAL": 0,
    "USER_OK": -20,
}

RF_SEVERITY = {"critical": 12, "high": 8, "medium": 4, "low": 2, "info": 0}

RF_KIND_HOSTILITY = {
    "connected_rogue": 50,
    "connected_unpermitted": 45,
    "evil_twin": 40,
    "hostile_oui": 35,
    "hot_attack_correlated": 32,
    "correlated_hostile_ip": 30,
    "blocked_peer_rf": 28,
    "forever_disabled_nearby": 26,
    "pollution_cluster": 24,
    "rogue_open": 22,
    "unpermitted_spectrum": 20,
    "enterprise_downgrade": 16,
}

INTERNET_KIND_HOSTILITY = {
    "hostile": 50,
    "terror": 42,
    "internet": 0,
    "trusted": -15,
}

HELL_VERDICTS = frozenset({"HARM_CANDIDATE", "SUSPICIOUS"})
HEAVEN_VERDICTS = frozenset({"USER_OK", "EPHEMERAL", "MONITOR"})

_hh = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _heaven_hell():
    global _hh
    if _hh is not None:
        return _hh
    import importlib.util

    spec = importlib.util.spec_from_file_location("heaven_hell", INSTALL / "lib" / "heaven-hell.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _hh = mod
    return mod


def infer_soul_side(row: dict[str, Any]) -> str:
    explicit = str(row.get("soul_side") or "").strip().lower()
    if explicit in SOUL_ORDER:
        return explicit
    if row.get("hell_chosen") or row.get("kill_eligible"):
        return "hell"
    verdict = str(row.get("verdict") or "")
    trust_rank = int(row.get("trust_rank") or 5)
    scores = row.get("scores") or {}
    if int(scores.get("operator_auth") or 0) >= 10:
        return "heaven"
    if trust_rank <= 2 and verdict in HEAVEN_VERDICTS:
        return "heaven"
    if verdict in HELL_VERDICTS:
        return "hell"
    kind = str(row.get("kind") or "")
    if kind in ("hostile", "terror"):
        return "hell"
    if row.get("hostile") or row.get("block_recommended"):
        return "limbo"
    return "limbo"


def score_connection(row: dict[str, Any]) -> int:
    score = 0
    soul = infer_soul_side(row)
    if soul == "hell":
        score += 60
    elif soul == "limbo":
        score += 10
    else:
        score -= 25

    if row.get("hell_chosen"):
        score += 50
    if row.get("kill_eligible"):
        score += 30
    if row.get("block_recommended"):
        score += 20

    verdict = str(row.get("verdict") or "")
    score += VERDICT_HOSTILITY.get(verdict, 0)

    try:
        score += min(30, int(row.get("harm_total") or 0))
    except (TypeError, ValueError):
        pass

    trust_rank = int(row.get("trust_rank") or 5)
    score += max(0, trust_rank - 2) * 4

    kill_tier = str(row.get("kill_tier") or "")
    if kill_tier == "strike":
        score += 25
    elif kill_tier == "eradicate":
        score += 18
    elif kill_tier == "block":
        score += 10

    scores = row.get("scores") or {}
    score += int(scores.get("threat_linked") or 0)
    score += int(scores.get("stream_theft_risk") or 0) // 2

    sources = row.get("sources") or []
    if isinstance(sources, list):
        if "field_hostile" in sources or "blocked" in sources:
            score += 35
        if "host_attacks" in sources:
            score += 15

    try:
        heat = float((row.get("meta") or {}).get("heat") or row.get("heat") or 0)
        score += int(min(20, heat * 25))
    except (TypeError, ValueError):
        pass

    return max(0, score)


def score_rf_threat(threat: dict[str, Any], *, active_bssid: str = "") -> int:
    kind = str(threat.get("kind") or "")
    sev = str(threat.get("severity") or "")
    score = RF_KIND_HOSTILITY.get(kind, 6) + RF_SEVERITY.get(sev, 0)
    if active_bssid and str(threat.get("bssid") or "").lower() == active_bssid.lower():
        score += 20
    return score


def score_rf_threats(
    threats: list[dict[str, Any]],
    active: dict[str, Any] | None = None,
) -> int:
    active_bssid = str((active or {}).get("bssid") or "")
    total = 0
    for t in threats:
        total += score_rf_threat(t, active_bssid=active_bssid)
    return total


def score_internet_node(row: dict[str, Any]) -> int:
    kind = str(row.get("kind") or "internet")
    score = INTERNET_KIND_HOSTILITY.get(kind, 0)
    meta = row.get("meta") or {}
    sources = row.get("sources") or []
    if isinstance(sources, list):
        if "field_hostile" in sources:
            score += 40
        if "blocked" in sources:
            score += 30
        if "host_attacks" in sources:
            score += 20
        if "human_dossier" in sources:
            score += 15
    try:
        score += int(min(25, float(meta.get("heat") or 0) * 30))
    except (TypeError, ValueError):
        pass
    verdict = str(meta.get("verdict") or "")
    score += VERDICT_HOSTILITY.get(verdict, 0) // 2
    return max(0, score)


def hell_first_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    soul = infer_soul_side(row)
    return (
        SOUL_ORDER.get(soul, 1),
        0 if row.get("hell_chosen") else 1,
        0 if row.get("kill_eligible") else 1,
        -int(row.get("hostility_score") or score_connection(row)),
        int(row.get("trust_rank") or 5),
        -(int(row.get("harm_total") or 0)),
    )


def sort_hell_first(rows: list[dict[str, Any]], *, key_fn: Callable[[dict[str, Any]], tuple[Any, ...]] | None = None) -> list[dict[str, Any]]:
    key_fn = key_fn or hell_first_sort_key
    return sorted(rows, key=key_fn)


def enrich_connection(row: dict[str, Any]) -> dict[str, Any]:
    try:
        hh = _heaven_hell()
        soul, hell = hh.classify_row(row)
        row.setdefault("soul_side", soul)
        if hell:
            row["hell_chosen"] = True
    except Exception:
        row.setdefault("soul_side", infer_soul_side(row))
    row["hostility_score"] = score_connection(row)
    row["hostility_priority"] = (
        "hell_first" if row.get("soul_side") == "hell" or row.get("hell_chosen") else "normal"
    )
    return row


def enrich_internet_node(row: dict[str, Any]) -> dict[str, Any]:
    row["hostility_score"] = score_internet_node(row)
    row["soul_side"] = infer_soul_side(row)
    row["hostility_priority"] = "hell_first" if row["soul_side"] == "hell" else "normal"
    return row


def aggregate_field_hostility(panel_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    panel_doc = panel_doc or _load_json(STATE / "threat-panel.json", {})
    conn_scores: list[int] = []
    hell_count = 0
    for c in (panel_doc.get("gatekeeper") or {}).get("connections") or []:
        if not isinstance(c, dict):
            continue
        enrich_connection(c)
        conn_scores.append(int(c.get("hostility_score") or 0))
        if c.get("hell_chosen") or c.get("soul_side") == "hell":
            hell_count += 1

    rf_doc = panel_doc.get("field_rf") or _load_json(STATE / "field-rf-shield.json", {})
    rf_threats = rf_doc.get("threats") or []
    rf_score = score_rf_threats(rf_threats, rf_doc.get("active"))

    hostile_registry = 0
    hostile_path = STATE / "field-hostile.tsv"
    if hostile_path.is_file():
        try:
            hostile_registry = max(0, sum(1 for _ in hostile_path.read_text(encoding="utf-8").splitlines()) - 1)
        except OSError:
            pass

    peak = max(conn_scores) if conn_scores else 0
    total = peak + rf_score + hell_count * 8 + hostile_registry * 3
    return {
        "updated": _now(),
        "motto": MOTTO,
        "field_hostility_score": total,
        "connection_peak": peak,
        "connection_hell_count": hell_count,
        "rf_hostility_score": rf_score,
        "rf_threat_count": len(rf_threats),
        "hostile_registry": hostile_registry,
        "hell_first": True,
    }


def panel_json() -> dict[str, Any]:
    return aggregate_field_hostility()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "score-connection" and len(sys.argv) >= 3:
        row = json.loads(sys.argv[2])
        print(json.dumps(enrich_connection(row), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostility-priority.py [json|score-connection JSON]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())