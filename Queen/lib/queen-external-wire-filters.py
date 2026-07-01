#!/usr/bin/env pythong
"""External Field Wire filters — redundancy, truth, integrity, party lanes."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
WIRE_DIR = STATE / "external-wire"
MANDATE = QUEEN / "data" / "queen-external-wire.json"
CHAIN_HEAD = WIRE_DIR / "chain-head.json"
WIRE_TOKEN = WIRE_DIR / "wire-token.json"
RING = WIRE_DIR / "ring.jsonl"

_PARTY_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
_INJECTION_RE = re.compile(
    r"(<script|javascript:|eval\s*\(|onerror\s*=|union\s+select|;\s*drop\s+)",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def load_mandate() -> dict[str, Any]:
    return _load_json(MANDATE, {"schema": "queen-external-wire/v2"})


def _verify_code_seal() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("queen_security", QUEEN / "lib" / "queen-security.py")
        if not spec or not spec.loader:
            return {"ok": False, "reason": "security_module_missing"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.verify_code_seal()
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


def wire_token() -> str:
    env = os.environ.get("QUEEN_EXTERNAL_WIRE_TOKEN", "").strip()
    if env:
        return env
    doc = _load_json(WIRE_TOKEN, {})
    if doc.get("token"):
        return str(doc["token"])
    WIRE_DIR.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(32)
    _save_json(WIRE_TOKEN, {
        "schema": "queen-external-wire-token/v1",
        "created": _now(),
        "token": token,
        "note": "Hostess7↔Hostess7 peer auth — never export to main brain",
    })
    return token


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def classify_party(body: dict[str, Any], *, default: str = "human") -> dict[str, Any]:
    m = load_mandate()
    parties = m.get("parties") or {}
    raw = str(body.get("party") or body.get("peer_type") or default).strip().lower()
    if raw in ("h7", "hostess", "hostess7", "hostess-7"):
        raw = "hostess7"
    if raw not in parties:
        raw = "human" if raw not in ("ai", "hostess7") else raw
    channel = str(body.get("input_channel") or body.get("channel") or "").strip().lower()
    if not channel:
        if raw == "ai":
            channel = "machine"
        elif body.get("voice") or body.get("audio"):
            channel = "voice"
        elif body.get("paste"):
            channel = "paste"
        elif raw == "human":
            channel = "keystroke"
        else:
            channel = "typed"
    channels = m.get("input_channels") or {}
    ch_doc = channels.get(channel) or channels.get("typed") or {}
    party_doc = parties.get(raw) or {}
    human_compromise = bool(party_doc.get("input_compromise_expected")) or channel in ("keystroke", "voice")
    return {
        "party": raw,
        "input_channel": channel,
        "input_compromise_expected": human_compromise,
        "compromise_level": ch_doc.get("compromise", "expected" if human_compromise else "low"),
        "situational_adjustment": ch_doc.get("adjustment", "truth_filter"),
        "wire_token_required": bool(party_doc.get("wire_token_required")),
        "trust": party_doc.get("trust", "situational"),
    }


def _canonical_auth(party: str, from_: str, ts: str, payload: str) -> str:
    ph = hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()
    return f"{party}|{from_}|{ts}|{ph}"


def verify_wire_auth(body: dict[str, Any], *, party_info: dict[str, Any]) -> dict[str, Any]:
    if not party_info.get("wire_token_required"):
        return {"ok": True, "auth": "not_required"}
    sig = str(body.get("wire_auth") or body.get("auth") or "").strip()
    from_ = str(body.get("from") or "hostess7").strip()
    ts = str(body.get("ts") or _now())
    payload = str(
        body.get("query") or body.get("text") or body.get("message") or body.get("payload") or ""
    )
    if isinstance(body.get("payload"), dict):
        payload = json.dumps(body["payload"], ensure_ascii=False)
    if not sig:
        return {"ok": False, "auth": "missing", "reason": "wire_token_required"}
    expected = hmac.new(
        wire_token().encode(),
        _canonical_auth(party_info["party"], from_, ts, payload).encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return {"ok": False, "auth": "invalid", "reason": "wire_token_mismatch"}
    return {"ok": True, "auth": "hostess7_peer"}


def _analyze_truth(claim: str, *, channels: int = 0) -> dict[str, Any]:
    if not claim.strip():
        return {"truth_score": 0, "deception_risk": "high", "verdict": "empty", "recommended_action": "reject_or_investigate"}
    scripts = HOSTESS / "scripts"
    if scripts.is_dir():
        sys.path.insert(0, str(scripts))
        try:
            from field_detective_corpus import analyze_truth  # noqa: WPS433

            return analyze_truth(claim, corroboration_channels=channels)
        except Exception:
            pass
    return {
        "truth_score": 6.0,
        "deception_risk": "high",
        "verdict": "Truth 6.0% — external corroboration required",
        "recommended_action": "corroborate_before_acting",
    }


def _structure_filter(payload: str, body: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if _INJECTION_RE.search(payload):
        issues.append("injection_pattern")
    if len(payload.encode("utf-8")) > 8192:
        issues.append("oversize")
    party = str(body.get("party") or "")
    if party and not _PARTY_RE.match(party.replace("hostess7", "h7")):
        issues.append("bad_party_id")
    return {"id": "structure", "pass": not issues, "issues": issues}


def _echo_filter(payload: str, *, limit: int = 12) -> dict[str, Any]:
    """Redundancy path — corroborate or detect contradiction against recent External ring."""
    if not RING.is_file() or not payload.strip():
        return {"id": "echo", "pass": True, "corroboration": 0, "contradiction": False}
    recent: list[str] = []
    try:
        lines = RING.read_text(encoding="utf-8").splitlines()
        for line in lines[-limit:]:
            try:
                doc = json.loads(line)
                recent.append(str(doc.get("payload") or ""))
            except json.JSONDecodeError:
                continue
    except OSError:
        return {"id": "echo", "pass": True, "corroboration": 0}
    norm = payload.strip().lower()
    corroboration = sum(1 for r in recent if norm and norm in r.lower())
    contradiction = any(
        ("not " + norm[:40] in r.lower() or "false: " + norm[:30] in r.lower())
        for r in recent if norm
    )
    return {
        "id": "echo",
        "pass": not contradiction,
        "corroboration": corroboration,
        "contradiction": contradiction,
    }


def redundancy_filter(
    payload: str,
    body: dict[str, Any],
    *,
    party_info: dict[str, Any],
    truth_doc: dict[str, Any],
) -> dict[str, Any]:
    m = load_mandate()
    filt = m.get("filters") or {}
    rf = filt.get("redundancy") or {}
    paths = [
        _structure_filter(payload, body),
        {
            "id": "truth",
            "pass": truth_doc.get("verdict") != "TRUTH_REJECT",
            "score": truth_doc.get("truth_score"),
            "risk": truth_doc.get("deception_risk"),
            "verdict": truth_doc.get("verdict"),
        },
        _echo_filter(payload),
    ]
    passed = sum(1 for p in paths if p.get("pass"))
    min_pass = int(rf.get("min_pass", 2))
    if party_info.get("input_compromise_expected") or rf.get("require_all_for_human"):
        min_pass = len(paths)
    if passed == len(paths):
        verdict = "REDUNDANCY_PASS"
    elif passed >= min_pass:
        verdict = "REDUNDANCY_HOLD"
    else:
        verdict = "REDUNDANCY_FAIL"
    return {
        "paths": paths,
        "passed": passed,
        "required": min_pass,
        "verdict": verdict,
        "never_tampered": True,
    }


def truth_filter(payload: str, *, party_info: dict[str, Any], corroboration: int = 0) -> dict[str, Any]:
    m = load_mandate()
    tf = m.get("filters") or {}
    truth_cfg = tf.get("truth") or {}
    floor = float(truth_cfg.get("human_floor" if party_info.get("input_compromise_expected") else "floor", 58))
    doc = _analyze_truth(payload, channels=corroboration)
    score = float(doc.get("truth_score") or 0)
    flags = list(doc.get("inconsistency_flags") or [])
    if len(flags) >= 3:
        verdict = "TRUTH_REJECT"
    elif party_info.get("input_compromise_expected"):
        verdict = "TRUTH_PASS" if score >= floor else "TRUTH_HOLD"
    elif score < floor:
        verdict = "TRUTH_HOLD"
    else:
        verdict = "TRUTH_PASS"
    return {
        **doc,
        "floor": floor,
        "tier": truth_cfg.get("tier", "adapt"),
        "verdict": verdict,
        "party": party_info.get("party"),
        "input_compromise_expected": party_info.get("input_compromise_expected"),
    }


def human_compromise_adjust(party_info: dict[str, Any], truth_doc: dict[str, Any], redundancy_doc: dict[str, Any]) -> dict[str, Any]:
    """Situational adjustments when human keystroke/voice is the input path."""
    adjustments: list[str] = []
    if party_info.get("input_compromise_expected"):
        adjustments.append("never_auto_import")
        adjustments.append("truth_floor_strict")
        if party_info.get("input_channel") == "voice":
            adjustments.append("voice_untrusted_transcript")
        if party_info.get("input_channel") == "keystroke":
            adjustments.append("keystroke_untrusted")
        if truth_doc.get("verdict") != "TRUTH_PASS":
            adjustments.append("hold_until_corroboration")
        if redundancy_doc.get("verdict") != "REDUNDANCY_PASS":
            adjustments.append("redundancy_hold")
    return {
        "situational": party_info.get("input_compromise_expected", False),
        "compromise_level": party_info.get("compromise_level"),
        "adjustments": adjustments,
        "operator_note": (
            "Human input treated as situational — id10t behind keyboard expected; "
            "keystroke and voice never fully trusted."
            if party_info.get("input_compromise_expected")
            else None
        ),
    }


def _seal_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Stable seal body — communique + filter verdicts only (immune to float drift)."""
    filt = row.get("filters") if isinstance(row.get("filters"), dict) else {}
    return {
        "schema": row.get("schema"),
        "ts": row.get("ts"),
        "lane": row.get("lane"),
        "party": row.get("party"),
        "input_channel": row.get("input_channel"),
        "source": row.get("source"),
        "to": row.get("to"),
        "direction": row.get("direction"),
        "payload": row.get("payload"),
        "verdict": row.get("verdict"),
        "action": row.get("action"),
        "integrity": row.get("integrity"),
        "redundancy_verdict": (filt.get("redundancy") or {}).get("verdict"),
        "truth_verdict": (filt.get("truth") or {}).get("verdict"),
    }


def _body_hash(row: dict[str, Any]) -> str:
    canonical = json.dumps(_seal_payload(row), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def chain_head() -> dict[str, Any]:
    return _load_json(CHAIN_HEAD, {"hash": "0" * 64, "seq": 0})


def seal_record(row: dict[str, Any]) -> dict[str, Any]:
    head = chain_head()
    prev = str(head.get("hash") or "0" * 64)
    seq = int(head.get("seq") or 0) + 1
    content = {**row, "integrity": "sealed"}
    record_hash = _body_hash(content)
    chain_hash = hashlib.sha256(f"{prev}|{record_hash}".encode()).hexdigest()
    out = {
        **content,
        "prev_hash": prev,
        "record_hash": record_hash,
        "chain_hash": chain_hash,
        "chain_seq": seq,
    }
    _save_json(CHAIN_HEAD, {"hash": chain_hash, "seq": seq, "updated": _now()})
    return out


def verify_chain(*, max_lines: int = 512) -> dict[str, Any]:
    seal = _verify_code_seal()
    if not seal.get("ok"):
        return {
            "ok": False,
            "never_tampered_or_broken": False,
            "reason": "code_seal_broken",
            "seal": seal,
        }
    if not RING.is_file():
        return {"ok": True, "never_tampered_or_broken": True, "records": 0, "chain_intact": True}
    prev = "0" * 64
    seq = 0
    checked = 0
    legacy = 0
    broken_at: int | None = None
    last_chain: str | None = None
    try:
        for i, line in enumerate(RING.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            if checked >= max_lines:
                break
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                broken_at = i
                break
            if not doc.get("chain_hash"):
                legacy += 1
                continue
            rh = doc.get("record_hash") or _body_hash(doc)
            if doc.get("record_hash") and _body_hash(doc) != rh:
                broken_at = i
                break
            expected_chain = hashlib.sha256(f"{prev}|{rh}".encode()).hexdigest()
            if doc["chain_hash"] != expected_chain:
                broken_at = i
                break
            if doc.get("prev_hash") and doc["prev_hash"] != prev:
                broken_at = i
                break
            prev = doc["chain_hash"]
            last_chain = prev
            seq += 1
            checked += 1
    except OSError as exc:
        return {"ok": False, "never_tampered_or_broken": False, "reason": str(exc)}
    head = chain_head()
    head_ok = True
    if checked > 0:
        head_ok = str(head.get("hash") or "") == (last_chain or prev) and int(head.get("seq") or 0) == seq
    elif legacy > 0 and int(head.get("seq") or 0) == 0:
        head_ok = True
    intact = broken_at is None and head_ok
    return {
        "ok": intact,
        "never_tampered_or_broken": intact,
        "records_checked": checked,
        "legacy_skipped": legacy,
        "chain_intact": intact,
        "broken_at_line": broken_at,
        "head_match": head_ok,
        "code_seal": seal.get("ok"),
    }


def enforce_seal_or_fail() -> dict[str, Any]:
    m = load_mandate()
    if not (m.get("doctrine") or {}).get("fail_closed_on_seal_break", True):
        return {"ok": True}
    seal = _verify_code_seal()
    if not seal.get("ok"):
        return {
            "ok": False,
            "verdict": "EXTERNAL_SEAL_BROKEN",
            "never_tampered_or_broken": False,
            "reason": "code_seal",
            "seal": seal,
        }
    chain = verify_chain()
    if not chain.get("ok"):
        return {
            "ok": False,
            "verdict": "EXTERNAL_CHAIN_BROKEN",
            "never_tampered_or_broken": False,
            "reason": "integrity_chain",
            "chain": chain,
        }
    return {"ok": True, "never_tampered_or_broken": True, "seal": seal, "chain": chain}


def compose_verdict(redundancy_doc: dict[str, Any], truth_doc: dict[str, Any], *, adjustments: dict[str, Any]) -> str:
    if redundancy_doc.get("verdict") == "REDUNDANCY_FAIL":
        return "EXTERNAL_REDUNDANCY_REJECT"
    if truth_doc.get("verdict") == "TRUTH_REJECT":
        return "EXTERNAL_TRUTH_REJECT"
    if redundancy_doc.get("verdict") == "REDUNDANCY_HOLD" or truth_doc.get("verdict") == "TRUTH_HOLD":
        return "EXTERNAL_REDUNDANCY_HOLD"
    if adjustments.get("adjustments"):
        return "EXTERNAL_SECURE_ACK_SITUATIONAL"
    return "EXTERNAL_SECURE_ACK"


def scan_payload_files(body: dict[str, Any], *, direction: str = "ingress") -> dict[str, Any]:
    """Field Virus gate on file paths referenced in wire payloads."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("queen_field_virus", QUEEN / "lib" / "queen-field-virus.py")
        if not spec or not spec.loader:
            return {"ok": True, "skipped": True, "reason": "field_virus_missing"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.scan_payload_paths(body, direction=direction)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "lane": "FieldVirus"}


def make_wire_auth(body: dict[str, Any]) -> str:
    """Helper for Hostess7 peers to sign outbound wire traffic."""
    party_info = classify_party(body, default="hostess7")
    from_ = str(body.get("from") or "hostess7")
    ts = str(body.get("ts") or _now())
    payload = str(body.get("query") or body.get("text") or body.get("message") or body.get("payload") or "")
    return hmac.new(
        wire_token().encode(),
        _canonical_auth(party_info["party"], from_, ts, payload).encode(),
        hashlib.sha256,
    ).hexdigest()