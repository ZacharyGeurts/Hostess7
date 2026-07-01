#!/usr/bin/env pythong
"""Contact classification vector — AI / Human / Unknown / Alien percentages.

Stable EMA, instant in-memory read, persisted under external-wire state.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
MANDATE = QUEEN / "data" / "queen-contact-vector.json"
VECTOR_PATH = STATE / "external-wire" / "contact-vector.json"

_AXES = ("ai", "human", "unknown", "alien")
_CACHE: dict[str, Any] | None = None

_NON_LATIN_RE = re.compile(r"[^\x00-\x7F]")
_ALIEN_MARKERS = re.compile(
    r"(non.?human|extraterrestrial|xenolingu|alien\s+origin|unknown\s+signal|anomalous\s+contact)",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def load_mandate() -> dict[str, Any]:
    return _load_json(MANDATE, {"defaults": {"ai": 30, "human": 25, "unknown": 40, "alien": 5}})


def _defaults() -> dict[str, float]:
    m = load_mandate()
    d = m.get("defaults") or {}
    return {k: float(d.get(k, 25.0)) for k in _AXES}


def _normalize(v: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, v.get(k, 0.0)) for k in _AXES)
    if total <= 0:
        return _defaults()
    return {k: round(100.0 * max(0.0, v.get(k, 0.0)) / total, 2) for k in _AXES}


def _load_vector() -> dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    doc = _load_json(VECTOR_PATH, {})
    if not doc.get("vector"):
        doc = {
            "schema": "queen-contact-vector/v1",
            "updated": _now(),
            "vector": _normalize(_defaults()),
            "samples": 0,
            "contacts": 0,
        }
    _CACHE = doc
    return doc


def vector_instant() -> dict[str, Any]:
    """O(1) read — stable percentages for UI and wire status."""
    doc = _load_vector()
    vec = doc.get("vector") or _normalize(_defaults())
    return {
        "schema": "queen-contact-vector/v1",
        "updated": doc.get("updated") or _now(),
        "vector": vec,
        "dominant": doc.get("dominant") or max(_AXES, key=lambda k: vec.get(k, 0)),
        "samples": int(doc.get("samples") or 0),
        "contacts": int(doc.get("contacts") or 0),
        "axes": list(_AXES),
        "instant": True,
    }


def _observe(body: dict[str, Any], *, payload: str = "", filters: dict[str, Any] | None = None) -> dict[str, float]:
    """Single-contact observation before EMA blend."""
    party = str(body.get("party") or body.get("peer_type") or "unknown").lower()
    channel = str(body.get("input_channel") or body.get("channel") or "").lower()
    text = (payload or str(body.get("query") or body.get("text") or ""))[:2000]
    obs = {k: 0.0 for k in _AXES}

    if party in ("alien", "xeno", "nonhuman"):
        obs["alien"] = 72.0
        obs["unknown"] = 20.0
        obs["ai"] = 4.0
        obs["human"] = 4.0
        return _normalize(obs)

    if party == "ai" or channel == "machine":
        obs["ai"] = 78.0
        obs["human"] = 8.0
        obs["unknown"] = 12.0
        obs["alien"] = 2.0
    elif party == "human" or channel in ("keystroke", "voice", "typed", "paste"):
        obs["human"] = 70.0
        obs["unknown"] = 18.0
        obs["ai"] = 10.0
        obs["alien"] = 2.0
    elif party in ("hostess7", "h7", "hostess"):
        obs["ai"] = 62.0
        obs["human"] = 18.0
        obs["unknown"] = 18.0
        obs["alien"] = 2.0
    else:
        obs["unknown"] = 55.0
        obs["ai"] = 20.0
        obs["human"] = 20.0
        obs["alien"] = 5.0

    if text.strip().startswith("{"):
        obs["ai"] = min(95.0, obs["ai"] + 12.0)
        obs["human"] = max(0.0, obs["human"] - 6.0)

    if _NON_LATIN_RE.search(text) and len(_NON_LATIN_RE.findall(text)) > 8:
        obs["alien"] = min(40.0, obs["alien"] + 15.0)
        obs["unknown"] = min(50.0, obs["unknown"] + 10.0)

    if _ALIEN_MARKERS.search(text):
        obs["alien"] = min(65.0, obs["alien"] + 25.0)

    filt = filters or {}
    truth = filt.get("truth") if isinstance(filt.get("truth"), dict) else {}
    if truth.get("verdict") == "TRUTH_REJECT":
        obs["unknown"] = min(70.0, obs["unknown"] + 15.0)

    red = filt.get("redundancy") if isinstance(filt.get("redundancy"), dict) else {}
    if red.get("verdict") == "REDUNDANCY_FAIL":
        obs["unknown"] = min(75.0, obs["unknown"] + 12.0)
        obs["alien"] = min(30.0, obs["alien"] + 5.0)

    return _normalize(obs)


def update_vector(body: dict[str, Any], *, payload: str = "", filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """EMA update — call on each external wire contact."""
    global _CACHE
    m = load_mandate()
    alpha = float((m.get("update") or {}).get("ema_alpha", 0.18))
    doc = _load_vector()
    current = {k: float((doc.get("vector") or _defaults()).get(k, 0.0)) for k in _AXES}
    obs = _observe(body, payload=payload, filters=filters)
    blended = {
        k: round((1.0 - alpha) * current[k] + alpha * obs[k], 4)
        for k in _AXES
    }
    norm = _normalize(blended)
    doc["vector"] = norm
    doc["updated"] = _now()
    doc["samples"] = int(doc.get("samples") or 0) + 1
    doc["contacts"] = int(doc.get("contacts") or 0) + 1
    doc["last_observation"] = obs
    doc["last_party"] = str(body.get("party") or "unknown")
    doc["dominant"] = max(_AXES, key=lambda k: norm[k])
    if (m.get("update") or {}).get("persist", True):
        _save_json(VECTOR_PATH, doc)
    _CACHE = doc
    return vector_instant()


def reset_vector(*, confirm: bool = False) -> dict[str, Any]:
    global _CACHE
    if not confirm:
        return {"ok": False, "error": "confirm_required"}
    doc = {
        "schema": "queen-contact-vector/v1",
        "updated": _now(),
        "vector": _normalize(_defaults()),
        "samples": 0,
        "contacts": 0,
    }
    _save_json(VECTOR_PATH, doc)
    _CACHE = doc
    return {"ok": True, **vector_instant()}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json", "instant"):
        return {"ok": True, **vector_instant()}
    if action in ("update", "observe"):
        return {"ok": True, **update_vector(body, payload=str(body.get("payload") or body.get("query") or ""))}
    if action == "reset":
        return reset_vector(confirm=bool(body.get("confirm")))
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(vector_instant(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-contact-vector.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())